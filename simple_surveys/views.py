from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import timedelta
import json
import logging

from .models import SimpleSurvey, SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession
from .forms import SimpleSurveyForm, HealthSurveyForm, FuneralSurveyForm
from .engine import SimpleSurveyEngine
from .comparison_adapter import SimpleSurveyComparisonAdapter
from .session_manager import SessionManager, SessionValidationError

logger = logging.getLogger(__name__)


class FeatureSurveyView(View):
    """
    Feature-based survey view for health and funeral insurance types.
    Uses SimpleSurvey model with feature-specific questions.
    """
    
    def get(self, request, category):
        """Display feature-based survey form for the specified category"""
        # Validate category
        if category not in ['health', 'funeral']:
            raise Http404("Invalid survey category")
        
        # Get or create survey instance from session
        survey_id = request.session.get(f'survey_{category}_id')
        survey = None
        
        if survey_id:
            try:
                survey = SimpleSurvey.objects.get(id=survey_id)
            except SimpleSurvey.DoesNotExist:
                survey = None
        
        # Create appropriate form based on category
        if category == 'health':
            form = HealthSurveyForm(instance=survey)
        else:
            form = FuneralSurveyForm(instance=survey)
        
        context = {
            'category': category,
            'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
            'form': form,
            'survey': survey,
        }
        
        return render(request, 'surveys/feature_survey_form.html', context)
    
    def post(self, request, category):
        """Process feature-based survey form submission"""
        # Validate category
        if category not in ['health', 'funeral']:
            raise Http404("Invalid survey category")
        
        # Get existing survey instance if available
        survey_id = request.session.get(f'survey_{category}_id')
        survey = None
        
        if survey_id:
            try:
                survey = SimpleSurvey.objects.get(id=survey_id)
            except SimpleSurvey.DoesNotExist:
                survey = None
        
        # Create appropriate form based on category
        if category == 'health':
            form = HealthSurveyForm(request.POST, instance=survey)
        else:
            form = FuneralSurveyForm(request.POST, instance=survey)
        
        if form.is_valid():
            # Save the survey
            survey = form.save()
            
            # Store survey ID in session
            request.session[f'survey_{category}_id'] = survey.id
            
            # Redirect to results processing
            return redirect('simple_surveys:feature_results', category=category)
        
        # Form has errors, redisplay with errors
        context = {
            'category': category,
            'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
            'form': form,
            'survey': survey,
        }
        
        return render(request, 'surveys/feature_survey_form.html', context)


class FeatureResultsView(View):
    """
    View for processing feature-based survey and displaying results.
    Integrates with the comparison system to show matching policies.
    """
    
    def get(self, request, category):
        """Process survey and display matching policies"""
        # Validate category
        if category not in ['health', 'funeral']:
            raise Http404("Invalid survey category")
        
        # Get survey from session
        survey_id = request.session.get(f'survey_{category}_id')
        if not survey_id:
            return redirect('simple_surveys:feature_survey', category=category)
        
        try:
            survey = SimpleSurvey.objects.get(id=survey_id)
        except SimpleSurvey.DoesNotExist:
            return redirect('simple_surveys:feature_survey', category=category)
        
        # Validate survey is complete
        if not survey.is_complete():
            return redirect('simple_surveys:feature_survey', category=category)
        
        try:
            # Import comparison system
            from comparison.feature_matching_engine import FeatureMatchingEngine
            from comparison.models import FeatureComparisonResult
            from policies.models import BasePolicy
            
            # Get user preferences from survey
            user_preferences = survey.get_preferences_dict()
            
            # Initialize matching engine
            insurance_type = 'HEALTH' if category == 'health' else 'FUNERAL'
            matching_engine = FeatureMatchingEngine(insurance_type)
            
            # Get policies of the appropriate type
            policies = BasePolicy.objects.filter(
                policy_features__insurance_type=insurance_type
            ).select_related('policy_features', 'organization')
            
            # Calculate matches for each policy
            policy_results = []
            for policy in policies:
                compatibility = matching_engine.calculate_policy_compatibility(policy, user_preferences)
                
                if compatibility['overall_score'] > 0:  # Only include policies with some compatibility
                    policy_results.append({
                        'policy': policy,
                        'compatibility': compatibility,
                        'overall_score': compatibility['overall_score'],
                        'matches': compatibility['matches'],
                        'mismatches': compatibility['mismatches'],
                        'explanation': compatibility['explanation']
                    })
            
            # Sort by compatibility score (highest first)
            policy_results.sort(key=lambda x: x['overall_score'], reverse=True)
            
            # Store results in session for potential later use
            request.session[f'results_{category}'] = {
                'survey_id': survey.id,
                'total_policies': len(policy_results),
                'generated_at': timezone.now().isoformat()
            }
            
            context = {
                'category': category,
                'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
                'survey': survey,
                'user_preferences': user_preferences,
                'policy_results': policy_results,
                'total_results': len(policy_results),
                'best_match': policy_results[0] if policy_results else None,
            }
            
            return render(request, 'surveys/feature_survey_results.html', context)
            
        except Exception as e:
            logger.error(f"Error processing feature survey results for {category}: {e}")
            context = {
                'category': category,
                'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
                'error_message': 'Unable to process your survey results. Please try again.',
                'survey': survey,
            }
            return render(request, 'surveys/feature_survey_results.html', context)


class SurveyView(View):
    """
    Main view for displaying survey questions by category (health/funeral).
    Handles session management for anonymous users.
    """
    
    def get(self, request, category):
        """Display survey form for the specified category"""
        # Validate category
        if category not in ['health', 'funeral']:
            raise Http404("Invalid survey category")
        
        try:
            # Create or get session using SessionManager
            quotation_session, created = SessionManager.create_or_get_session(request, category)
            session_key = quotation_session.session_key
            
            # Initialize survey engine
            engine = SimpleSurveyEngine(category)
            questions = engine.get_questions()
            
            # Get existing responses for this session/category
            existing_responses = {}
            responses = SimpleSurveyResponse.objects.for_session_category(session_key, category)
            for response in responses:
                existing_responses[response.question.field_name] = response.response_value
            
            # Get completion status
            completion_status = engine.get_completion_status(session_key)
            
            context = {
                'category': category,
                'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
                'questions': questions,
                'existing_responses': existing_responses,
                'completion_status': completion_status,
                'session_key': session_key,
                'session_created': created,
            }
            
            return render(request, 'surveys/simple_survey_form.html', context)
            
        except ValueError as e:
            logger.error(f"Invalid category for survey: {e}")
            raise Http404("Invalid survey category")
        except Exception as e:
            logger.error(f"Error displaying survey for category {category}: {e}")
            return render(request, 'surveys/simple_survey_form.html', {
                'error_message': 'Unable to load survey questions. Please try again.',
                'category': category
            })


@require_POST
@csrf_exempt
def save_response_ajax(request):
    """
    AJAX endpoint for saving individual responses.
    Expects JSON data with question_id, response_value, and category.
    """
    try:
        # Parse JSON data
        data = json.loads(request.body)
        question_id = data.get('question_id')
        response_value = data.get('response_value')
        category = data.get('category')
        
        # Validate required fields
        if not all([question_id, category]):
            return JsonResponse({
                'success': False,
                'errors': ['Missing required fields: question_id and category']
            }, status=400)
        
        # Validate category
        if category not in ['health', 'funeral']:
            return JsonResponse({
                'success': False,
                'errors': ['Invalid category']
            }, status=400)
        
        # Validate session
        session_key = request.session.session_key
        if not session_key:
            return JsonResponse({
                'success': False,
                'errors': ['No active session']
            }, status=400)
        
        validation_result = SessionManager.validate_session(session_key, category)
        if not validation_result['valid']:
            return JsonResponse({
                'success': False,
                'errors': [f'Session validation failed: {validation_result["error"]}']
            }, status=400)
        
        # Initialize survey engine and save response
        engine = SimpleSurveyEngine(category)
        result = engine.save_response(session_key, question_id, response_value)
        
        if result['success']:
            # Extend session expiry on successful response
            SessionManager.extend_session(session_key, category)
            
            # Check if survey is now complete
            is_complete = engine.is_survey_complete(session_key)
            completion_status = engine.get_completion_status(session_key)
            
            return JsonResponse({
                'success': True,
                'response_id': result['response_id'],
                'is_complete': is_complete,
                'completion_status': completion_status
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': result['errors']
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'errors': ['Invalid JSON data']
        }, status=400)
    except Exception as e:
        logger.error(f"Error saving response via AJAX: {e}")
        return JsonResponse({
            'success': False,
            'errors': ['Server error occurred']
        }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ProcessSurveyView(View):
    """
    View for processing completed surveys and generating quotations.
    Handles the transition from survey completion to quotation results.
    """
    
    def post(self, request, category):
        """Process completed survey and generate quotations"""
        # Validate category
        if category not in ['health', 'funeral']:
            raise Http404("Invalid survey category")
        
        # Validate session
        session_key = request.session.session_key
        if not session_key:
            return JsonResponse({
                'success': False,
                'error': 'No active session'
            }, status=400)
        
        validation_result = SessionManager.validate_session(session_key, category)
        if not validation_result['valid']:
            return JsonResponse({
                'success': False,
                'error': f'Session validation failed: {validation_result["error"]}'
            }, status=400)
        
        try:
            # Initialize survey engine
            engine = SimpleSurveyEngine(category)
            
            # Check if survey is complete
            if not engine.is_survey_complete(session_key):
                return JsonResponse({
                    'success': False,
                    'error': 'Survey is not complete. Please answer all required questions.'
                }, status=400)
            
            # Process responses to quotation criteria
            criteria = engine.process_responses(session_key)
            
            # Update quotation session with criteria
            quotation_session = validation_result['session']
            quotation_session.update_criteria(criteria)
            
            # Generate quotations using comparison adapter
            adapter = SimpleSurveyComparisonAdapter(category)
            quotation_result = adapter.generate_quotations(session_key)
            
            # Check if quotation generation was successful
            if not quotation_result.get('success'):
                return JsonResponse({
                    'success': False,
                    'error': quotation_result.get('error', 'Unable to generate quotations')
                }, status=500)
            
            # Extract policies from the result
            quotations = quotation_result.get('policies', [])
            
            # Mark session as completed
            quotation_session.mark_completed()
            
            # Store quotations in session for results page
            request.session[f'quotations_{category}'] = quotations
            request.session[f'criteria_{category}'] = criteria
            request.session[f'quotation_metadata_{category}'] = {
                'total_policies_evaluated': quotation_result.get('total_policies_evaluated', 0),
                'best_match': quotation_result.get('best_match'),
                'summary': quotation_result.get('summary', {}),
                'generated_at': quotation_result.get('generated_at')
            }
            
            return JsonResponse({
                'success': True,
                'quotations_count': len(quotations),
                'redirect_url': f'/survey/{category}/results/'
            })
            
        except Exception as e:
            logger.error(f"Error processing survey for category {category}: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Unable to generate quotations. Please try again.'
            }, status=500)
    
    def get(self, request, category):
        """Redirect GET requests to survey form"""
        return render(request, 'surveys/simple_survey_form.html', {
            'category': category,
            'error_message': 'Please complete the survey first.'
        })


class SurveyResultsView(View):
    """
    View for displaying quotation results after survey completion.
    Shows the top matching policies in a comparison format.
    """
    
    def get(self, request, category):
        """Display quotation results for the category"""
        # Validate category
        if category not in ['health', 'funeral']:
            raise Http404("Invalid survey category")
        
        # Check for quotations in session
        quotations_key = f'quotations_{category}'
        criteria_key = f'criteria_{category}'
        metadata_key = f'quotation_metadata_{category}'
        
        quotations = request.session.get(quotations_key)
        criteria = request.session.get(criteria_key)
        metadata = request.session.get(metadata_key, {})
        
        if not quotations:
            # No quotations found, redirect to survey
            return render(request, 'surveys/simple_survey_results.html', {
                'category': category,
                'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
                'message': 'No quotations found. Please complete the survey first.'
            })
        
        try:
            # Get session information
            session_key = request.session.session_key
            quotation_session = None
            
            if session_key:
                try:
                    quotation_session = QuotationSession.objects.get(
                        session_key=session_key,
                        category=category
                    )
                except QuotationSession.DoesNotExist:
                    pass
            
            context = {
                'category': category,
                'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
                'quotations': quotations,
                'criteria': criteria,
                'quotation_session': quotation_session,
                'total_quotations': len(quotations),
                'metadata': metadata,
                'best_match': metadata.get('best_match'),
                'summary': metadata.get('summary', {})
            }
            
            return render(request, 'surveys/simple_survey_results.html', context)
            
        except Exception as e:
            logger.error(f"Error displaying results for category {category}: {e}")
            return render(request, 'surveys/simple_survey_form.html', {
                'error_message': 'Unable to display results. Please try again.',
                'category': category
            })


@require_http_methods(["GET"])
def survey_status_ajax(request, category):
    """
    AJAX endpoint to get current survey completion status.
    Used for updating progress indicators.
    """
    # Validate category
    if category not in ['health', 'funeral']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid category'
        }, status=400)
    
    # Validate session
    session_key = request.session.session_key
    if not session_key:
        return JsonResponse({
            'success': False,
            'error': 'No active session'
        }, status=400)
    
    validation_result = SessionManager.validate_session(session_key, category)
    if not validation_result['valid']:
        return JsonResponse({
            'success': False,
            'error': f'Session validation failed: {validation_result["error"]}'
        }, status=400)
    
    try:
        # Get completion status
        engine = SimpleSurveyEngine(category)
        status = engine.get_completion_status(session_key)
        
        return JsonResponse({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting survey status for category {category}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to get survey status'
        }, status=500)


def home(request):
    """
    Home page using the main index.html template.
    """
    return render(request, 'public/index.html', {})


def health_page(request):
    """
    Health insurance page using the main health.html template.
    """
    return render(request, 'public/health.html', {})


def funerals_page(request):
    """
    Funeral insurance page using the main funerals.html template.
    """
    return render(request, 'public/funerals.html', {})


def direct_survey(request, category_slug):
    """
    Direct survey entry point that redirects to the feature-based survey.
    This matches the URL pattern used in the templates.
    """
    # Map category slugs to our internal category names
    category_mapping = {
        'health': 'health',
        'funeral': 'funeral'
    }
    
    category = category_mapping.get(category_slug)
    if not category:
        raise Http404("Invalid survey category")
    
    # Redirect to the feature-based survey view (new default)
    return redirect('simple_surveys:feature_survey', category=category)


def session_expired_view(request):
    """
    View to handle expired session errors gracefully.
    Provides user-friendly message and options to restart.
    """
    category = request.GET.get('category', '')
    
    context = {
        'category': category,
        'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
        'message': 'Your session has expired. Please start a new survey to continue.',
        'show_restart_button': True
    }
    
    return render(request, 'surveys/simple_survey_form.html', context)


def session_error_view(request):
    """
    View to handle general session errors.
    Provides user-friendly error message and recovery options.
    """
    error_type = request.GET.get('error', 'unknown')
    category = request.GET.get('category', '')
    
    error_messages = {
        'no_session': 'No active session found. Please start a new survey.',
        'invalid_session': 'Your session is invalid. Please start a new survey.',
        'expired': 'Your session has expired. Please start a new survey.',
        'validation_failed': 'Session validation failed. Please start a new survey.',
        'unknown': 'A session error occurred. Please start a new survey.'
    }
    
    context = {
        'category': category,
        'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
        'error_type': error_type,
        'message': error_messages.get(error_type, error_messages['unknown']),
        'show_restart_button': True
    }
    
    return render(request, 'surveys/simple_survey_form.html', context)


@require_http_methods(["GET"])
def policy_benefits_ajax(request, policy_id):
    """
    AJAX endpoint to get comprehensive benefits data for a specific policy.
    Returns PolicyFeatures, AdditionalFeatures, and Rewards data.
    """
    try:
        # Import policy models
        from policies.models import BasePolicy, PolicyFeatures, AdditionalFeatures, Rewards
        
        # Get the policy
        policy = get_object_or_404(BasePolicy, id=policy_id, is_active=True)
        
        # Increment view count
        policy.increment_views()
        
        # Get policy features
        policy_features = None
        features_data = {}
        try:
            policy_features = policy.policy_features
            features_data = policy_features.get_all_features_dict()
        except PolicyFeatures.DoesNotExist:
            pass
        
        # Get additional features
        additional_features = policy.additional_features.all().order_by('display_order', 'title')
        additional_features_data = []
        for feature in additional_features:
            additional_features_data.append({
                'title': feature.title,
                'description': feature.description,
                'coverage_details': feature.coverage_details,
                'icon': feature.icon,
                'is_highlighted': feature.is_highlighted,
            })
        
        # Get rewards
        rewards = policy.rewards.filter(is_active=True).order_by('display_order', 'title')
        rewards_data = []
        for reward in rewards:
            rewards_data.append({
                'title': reward.title,
                'description': reward.description,
                'reward_type': reward.get_reward_type_display(),
                'display_value': reward.get_display_value(),
                'eligibility_criteria': reward.eligibility_criteria,
                'terms_and_conditions': reward.terms_and_conditions,
            })
        
        # Format policy features for display
        formatted_features = {}
        if policy_features:
            if policy_features.insurance_type == 'HEALTH':
                if features_data.get('annual_limit_per_family'):
                    formatted_features['Annual Limit per Family'] = f"R{features_data['annual_limit_per_family']:,.2f}"
                if features_data.get('annual_limit_per_member'):
                    formatted_features['Annual Limit per Member'] = f"R{features_data['annual_limit_per_member']:,.2f}"
                if features_data.get('monthly_household_income'):
                    formatted_features['Monthly Household Income Requirement'] = f"R{features_data['monthly_household_income']:,.2f}"
                if features_data.get('currently_on_medical_aid') is not None:
                    formatted_features['Currently on Medical Aid'] = 'Yes' if features_data['currently_on_medical_aid'] else 'No'
                if features_data.get('ambulance_coverage') is not None:
                    formatted_features['Ambulance Coverage'] = 'Included' if features_data['ambulance_coverage'] else 'Not Included'
                if features_data.get('in_hospital_benefit') is not None:
                    formatted_features['In-Hospital Benefit'] = 'Included' if features_data['in_hospital_benefit'] else 'Not Included'
                if features_data.get('out_hospital_benefit') is not None:
                    formatted_features['Out-of-Hospital Benefit'] = 'Included' if features_data['out_hospital_benefit'] else 'Not Included'
                if features_data.get('chronic_medication_availability') is not None:
                    formatted_features['Chronic Medication'] = 'Available' if features_data['chronic_medication_availability'] else 'Not Available'
            
            elif policy_features.insurance_type == 'FUNERAL':
                if features_data.get('cover_amount'):
                    formatted_features['Cover Amount'] = f"R{features_data['cover_amount']:,.2f}"
                if features_data.get('marital_status_requirement'):
                    formatted_features['Marital Status Requirement'] = features_data['marital_status_requirement']
                if features_data.get('gender_requirement'):
                    formatted_features['Gender Requirement'] = features_data['gender_requirement']
        
        # Prepare response data
        response_data = {
            'success': True,
            'policy': {
                'id': policy.id,
                'name': policy.name,
                'organization': policy.organization.name,
                'category': policy.category.name,
                'base_premium': float(policy.base_premium),
                'coverage_amount': float(policy.coverage_amount),
                'description': policy.description,
            },
            'features': formatted_features,
            'additional_features': additional_features_data,
            'rewards': rewards_data,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error getting policy benefits for policy {policy_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to load policy benefits. Please try again.'
        }, status=500)
