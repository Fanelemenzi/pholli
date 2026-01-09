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

from .models import SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession
from .engine import SimpleSurveyEngine
from .comparison_adapter import SimpleSurveyComparisonAdapter
from .session_manager import SessionManager, SessionValidationError

logger = logging.getLogger(__name__)


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
                'redirect_url': f'/simple-surveys/{category}/results/'
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
    Direct survey entry point that redirects to the appropriate survey.
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
    
    # Redirect to the survey view
    return redirect('simple_surveys:survey', category=category)


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
