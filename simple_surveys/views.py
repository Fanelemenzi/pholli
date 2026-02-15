from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession
from policies.models import BasePolicy, PolicyCategory
from comparison.feature_matching_engine import FeatureMatchingEngine
from comparison.feature_comparison_manager import FeatureComparisonManager
import logging

logger = logging.getLogger(__name__)


def home(request):
    """Main home page view"""
    return render(request, 'public/index.html', {})


def health_page(request):
    """Health insurance information page"""
    return render(request, 'public/health.html', {})


def funerals_page(request):
    """Funeral insurance information page"""
    return render(request, 'public/funerals.html', {})


def direct_survey(request, category_slug):
    """
    Direct survey entry point that redirects to the appropriate survey.
    This maintains compatibility with the existing URL structure.
    """
    if category_slug in ['funeral', 'health']:
        # Redirect to the survey view within this app
        return redirect('survey', category=category_slug)
    else:
        raise Http404("Survey category not found")


# Survey view classes - these handle survey functionality
class SurveyView(View):
    """Survey view that renders survey forms"""
    def get(self, request, category):
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        # Generate survey questions based on category
        questions = self.get_survey_questions(category)
        
        # Get existing responses for this session and category
        existing_responses = self.get_existing_responses(session_key, category)
        
        # Calculate completion status
        completion_status = self.calculate_completion_status(questions, existing_responses)
        
        context = {
            'category': category,
            'category_display': category.title(),
            'completion_status': completion_status,
            'questions': questions,
            'existing_responses': existing_responses,
            'session_key': session_key
        }
        return render(request, 'surveys/simple_survey_form_fixed.html', context)
    
    def get_existing_responses(self, session_key, category):
        """Get existing responses for this session and category"""
        responses = SimpleSurveyResponse.objects.filter(
            session_key=session_key,
            category=category
        ).select_related('question')
        
        response_dict = {}
        for response in responses:
            response_dict[response.question.field_name] = response.response_value
        
        return response_dict
    
    def calculate_completion_status(self, questions, existing_responses):
        """Calculate completion status based on questions and responses"""
        required_questions = [q for q in questions if q.get('is_required', True)]
        total_required = len(required_questions)
        
        if total_required == 0:
            return {
                'completion_percentage': 100,
                'answered_required': 0,
                'required_questions': 0,
                'is_complete': True
            }
        
        # Count answered required questions
        answered_required = 0
        for question in required_questions:
            field_name = question.get('field_name')
            if field_name in existing_responses:
                response_value = existing_responses[field_name]
                # Check if response is not empty
                if response_value is not None and response_value != '' and response_value != []:
                    answered_required += 1
        
        # Calculate percentage
        completion_percentage = int((answered_required / total_required) * 100)
        is_complete = answered_required == total_required
        
        return {
            'completion_percentage': completion_percentage,
            'answered_required': answered_required,
            'required_questions': total_required,
            'is_complete': is_complete
        }
    
    def get_survey_questions(self, category):
        """Load survey questions from database based on category"""
        questions = SimpleSurveyQuestion.objects.for_category(category)
        
        # Convert to the format expected by the template
        question_list = []
        for question in questions:
            question_dict = {
                'id': question.pk,
                'question_text': question.question_text,
                'field_name': question.field_name,
                'input_type': question.input_type,
                'is_required': question.is_required,
                'choices': question.get_choices_list(),
                'validation_rules': question.validation_rules,
            }
            question_list.append(question_dict)
        
        return question_list


class ProcessSurveyView(View):
    """Process survey responses"""
    def post(self, request, category):
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        # Process form data
        responses_saved = 0
        errors = []
        
        # Get all questions for this category
        questions = SimpleSurveyQuestion.objects.for_category(category)
        question_dict = {q.field_name: q for q in questions}
        
        # Process each form field
        for field_name, value in request.POST.items():
            if field_name in ['csrfmiddlewaretoken']:
                continue
                
            if field_name in question_dict:
                question = question_dict[field_name]
                
                # Handle checkbox fields (multiple values)
                if question.input_type == 'checkbox':
                    checkbox_values = request.POST.getlist(field_name)
                    value = checkbox_values if checkbox_values else []
                
                # Save or update response
                response, created = SimpleSurveyResponse.objects.update_or_create(
                    session_key=session_key,
                    question=question,
                    defaults={
                        'category': category,
                        'response_value': value
                    }
                )
                responses_saved += 1
        
        # Create or update quotation session
        quotation_session, created = QuotationSession.objects.update_or_create(
            session_key=session_key,
            category=category,
            defaults={
                'expires_at': timezone.now() + timedelta(hours=24)
            }
        )
        
        # Check if survey is complete
        completion_status = self.calculate_completion_status(session_key, category)
        if completion_status['is_complete']:
            quotation_session.mark_completed()
        
        # Redirect to results
        return redirect('results', category=category)
    
    def calculate_completion_status(self, session_key, category):
        """Calculate completion status for a session"""
        # Get all required questions
        required_questions = SimpleSurveyQuestion.objects.filter(
            category=category,
            is_required=True
        )
        total_required = required_questions.count()
        
        if total_required == 0:
            return {'is_complete': True, 'completion_percentage': 100}
        
        # Count answered required questions
        answered_responses = SimpleSurveyResponse.objects.filter(
            session_key=session_key,
            category=category,
            question__is_required=True
        ).exclude(response_value__in=['', None, []])
        
        answered_count = answered_responses.count()
        completion_percentage = int((answered_count / total_required) * 100)
        
        return {
            'is_complete': answered_count == total_required,
            'completion_percentage': completion_percentage,
            'answered_required': answered_count,
            'required_questions': total_required
        }


class SurveyResultsView(View):
    """Display survey results with feature-based policy matching"""
    def get(self, request, category):
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        try:
            # Get user responses for this session and category
            responses = SimpleSurveyResponse.objects.filter(
                session_key=session_key,
                category=category
            ).select_related('question')
            
            if not responses.exists():
                context = {
                    'category': category,
                    'category_display': category.title(),
                    'quotations': [],
                    'total_quotations': 0,
                    'message': 'Please complete the survey first to see your personalized quotes.',
                    'metadata': {'total_policies_evaluated': 0, 'fallback_used': False}
                }
                return render(request, 'surveys/simple_survey_results.html', context)
            
            # Convert responses to user preferences
            user_preferences = self.convert_responses_to_preferences(responses, category)
            
            # Get relevant policies from database
            policies = self.get_relevant_policies(category)
            
            if not policies.exists():
                context = {
                    'category': category,
                    'category_display': category.title(),
                    'quotations': [],
                    'total_quotations': 0,
                    'message': f'No {category} policies are currently available. Please try again later.',
                    'metadata': {'total_policies_evaluated': 0, 'fallback_used': False}
                }
                return render(request, 'surveys/simple_survey_results.html', context)
            
            # Use feature matching engine to compare policies
            quotations = self.generate_policy_quotations(policies, user_preferences, category)
            
            # Prepare context for template
            context = {
                'category': category,
                'category_display': category.title(),
                'quotations': quotations,
                'total_quotations': len(quotations),
                'metadata': {
                    'total_policies_evaluated': policies.count(),
                    'fallback_used': False,
                    'matching_engine': 'feature_based'
                }
            }
            
            # Log successful matching
            logger.info(f"Generated {len(quotations)} quotations for {category} survey (session: {session_key})")
            
            return render(request, 'surveys/simple_survey_results.html', context)
            
        except Exception as e:
            logger.error(f"Error generating survey results for {category}: {str(e)}")
            context = {
                'category': category,
                'category_display': category.title(),
                'quotations': [],
                'total_quotations': 0,
                'message': 'An error occurred while processing your survey. Please try again.',
                'metadata': {'total_policies_evaluated': 0, 'fallback_used': True}
            }
            return render(request, 'surveys/simple_survey_results.html', context)
    
    def convert_responses_to_preferences(self, responses, category):
        """Convert survey responses to user preferences for feature matching"""
        preferences = {}
        
        for response in responses:
            field_name = response.question.field_name
            value = response.response_value
            
            # Convert response values to appropriate types for feature matching
            if response.question.input_type == 'number':
                try:
                    preferences[field_name] = Decimal(str(value)) if value else None
                except (ValueError, TypeError):
                    preferences[field_name] = None
            elif response.question.input_type == 'select':
                # Handle range selections for annual limits
                if 'annual_limit' in field_name and isinstance(value, str):
                    preferences[f"{field_name}_range"] = value
                    # Also convert to numeric value for compatibility
                    numeric_value = self.convert_range_to_numeric(value)
                    if numeric_value:
                        preferences[field_name] = numeric_value
                else:
                    preferences[field_name] = value
            elif response.question.input_type in ['radio', 'checkbox']:
                if response.question.input_type == 'checkbox' and isinstance(value, list):
                    # For checkboxes, convert to boolean flags
                    for item in value:
                        preferences[f"{field_name}_{item}"] = True
                else:
                    # Convert yes/no responses to boolean
                    if isinstance(value, str):
                        if value.lower() in ['yes', 'true', '1']:
                            preferences[field_name] = True
                        elif value.lower() in ['no', 'false', '0']:
                            preferences[field_name] = False
                        else:
                            preferences[field_name] = value
                    else:
                        preferences[field_name] = value
            else:
                preferences[field_name] = value
        
        # Add category-specific preference mappings
        if category == 'health':
            preferences = self.map_health_preferences(preferences)
        elif category == 'funeral':
            preferences = self.map_funeral_preferences(preferences)
        
        return preferences
    
    def convert_range_to_numeric(self, range_value):
        """Convert range strings to numeric values for compatibility"""
        range_mappings = {
            # Annual limit ranges
            '10k-50k': Decimal('30000'),
            '50k-100k': Decimal('75000'),
            '100k-250k': Decimal('175000'),
            '250k-500k': Decimal('375000'),
            '500k-1m': Decimal('750000'),
            '1m-2m': Decimal('1500000'),
            '2m-5m': Decimal('3500000'),
            '5m-plus': Decimal('7500000'),
            # Funeral cover ranges
            '10k-25k': Decimal('17500'),
            '25k-50k': Decimal('37500'),
            '50k-75k': Decimal('62500'),
            '75k-100k': Decimal('87500'),
            '100k-150k': Decimal('125000'),
            '150k-200k': Decimal('175000'),
            '200k-plus': Decimal('250000'),
        }
        return range_mappings.get(range_value)
    
    def map_health_preferences(self, preferences):
        """Map health survey responses to feature matching fields"""
        mapped = preferences.copy()
        
        # Map common health survey fields to PolicyFeatures fields
        field_mappings = {
            'monthly_budget': 'monthly_household_income',
            'preferred_annual_limit': 'annual_limit_per_family',
            'wants_hospital_cover': 'in_hospital_benefit',
            'wants_outpatient_cover': 'out_hospital_benefit',
            'needs_chronic_medication': 'chronic_medication_availability',
            'wants_ambulance_cover': 'ambulance_coverage',
            'currently_insured': 'currently_on_medical_aid'
        }
        
        for survey_field, feature_field in field_mappings.items():
            if survey_field in preferences:
                mapped[feature_field] = preferences[survey_field]
        
        return mapped
    
    def map_funeral_preferences(self, preferences):
        """Map funeral survey responses to feature matching fields"""
        mapped = preferences.copy()
        
        # Map common funeral survey fields to PolicyFeatures fields
        field_mappings = {
            'preferred_cover_amount': 'cover_amount',
            'monthly_income': 'monthly_net_income',
            'marital_status': 'marital_status_requirement',
            'gender': 'gender_requirement'
        }
        
        for survey_field, feature_field in field_mappings.items():
            if survey_field in preferences:
                mapped[feature_field] = preferences[survey_field]
        
        return mapped
    
    def get_relevant_policies(self, category):
        """Get relevant policies for the category"""
        try:
            # Get policies with features for the category
            policies = BasePolicy.objects.filter(
                category__slug=category,
                is_active=True,
                approval_status='APPROVED'
            ).select_related(
                'organization', 'category', 'policy_features'
            ).prefetch_related(
                'additional_features'
            )
            
            # Filter policies that have PolicyFeatures
            policies = policies.filter(policy_features__isnull=False)
            
            return policies
            
        except Exception as e:
            logger.error(f"Error getting relevant policies for {category}: {str(e)}")
            return BasePolicy.objects.none()
    
    def generate_policy_quotations(self, policies, user_preferences, category):
        """Generate policy quotations using feature matching engine"""
        try:
            # Initialize feature matching engine
            insurance_type = category.upper()
            engine = FeatureMatchingEngine(insurance_type)
            
            quotations = []
            
            for policy in policies:
                try:
                    # Calculate compatibility
                    compatibility_result = engine.calculate_policy_compatibility(
                        policy, user_preferences
                    )
                    
                    # Create quotation object
                    quotation = self.create_quotation_from_policy(
                        policy, compatibility_result, category
                    )
                    
                    if quotation:
                        quotations.append(quotation)
                        
                except Exception as e:
                    logger.warning(f"Error processing policy {policy.id}: {str(e)}")
                    continue
            
            # Sort by compatibility score (descending)
            quotations.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            # Limit to top 10 results
            return quotations[:10]
            
        except Exception as e:
            logger.error(f"Error generating quotations: {str(e)}")
            return []
    
    def create_quotation_from_policy(self, policy, compatibility_result, category):
        """Create quotation object from policy and compatibility result"""
        try:
            # Get policy features
            policy_features = policy.get_policy_features()
            
            # Create quotation object
            quotation = {
                'id': policy.id,
                'name': policy.name,
                'plan_name': policy.name,
                'provider_name': policy.organization.name,
                'organization': policy.organization.name,
                'monthly_premium': float(policy.base_premium),
                'coverage_amount': float(policy.coverage_amount),
                'match_score': round(compatibility_result['overall_score'] * 100, 1),
                'policy_features': self.format_policy_features(policy_features),
                'key_benefits': self.extract_key_benefits(policy, compatibility_result, category),
                'provider_logo': None,  # Could be added later
            }
            
            return quotation
            
        except Exception as e:
            logger.error(f"Error creating quotation for policy {policy.id}: {str(e)}")
            return None
    
    def format_policy_features(self, policy_features):
        """Format policy features for template display"""
        if not policy_features:
            return None
        
        features = {}
        
        # Common features for both insurance types
        if hasattr(policy_features, 'annual_limit_per_family') and policy_features.annual_limit_per_family:
            features['annual_limit_per_family'] = policy_features.annual_limit_per_family
        
        if hasattr(policy_features, 'annual_limit_per_member') and policy_features.annual_limit_per_member:
            features['annual_limit_per_member'] = policy_features.annual_limit_per_member
        
        if hasattr(policy_features, 'annual_limit_family_range') and policy_features.annual_limit_family_range:
            features['annual_limit_family_range'] = policy_features.annual_limit_family_range
        
        if hasattr(policy_features, 'annual_limit_member_range') and policy_features.annual_limit_member_range:
            features['annual_limit_member_range'] = policy_features.annual_limit_member_range
        
        # Health-specific features
        if policy_features.insurance_type == 'HEALTH':
            if hasattr(policy_features, 'in_hospital_benefit_level') and policy_features.in_hospital_benefit_level:
                features['in_hospital_benefit_level'] = policy_features.in_hospital_benefit_level
            elif hasattr(policy_features, 'in_hospital_benefit'):
                features['in_hospital_benefit'] = policy_features.in_hospital_benefit
            
            if hasattr(policy_features, 'out_hospital_benefit_level') and policy_features.out_hospital_benefit_level:
                features['out_hospital_benefit_level'] = policy_features.out_hospital_benefit_level
            elif hasattr(policy_features, 'out_hospital_benefit'):
                features['out_hospital_benefit'] = policy_features.out_hospital_benefit
            
            if hasattr(policy_features, 'ambulance_coverage'):
                features['ambulance_coverage'] = policy_features.ambulance_coverage
            
            if hasattr(policy_features, 'chronic_medication_availability'):
                features['chronic_medication_availability'] = policy_features.chronic_medication_availability
        
        # Funeral-specific features
        elif policy_features.insurance_type == 'FUNERAL':
            if hasattr(policy_features, 'cover_amount') and policy_features.cover_amount:
                features['cover_amount'] = policy_features.cover_amount
            
            if hasattr(policy_features, 'cover_amount_range') and policy_features.cover_amount_range:
                features['cover_amount_range'] = policy_features.cover_amount_range
        
        return features if features else None
    
    def extract_key_benefits(self, policy, compatibility_result, category):
        """Extract key benefits from policy and compatibility result"""
        benefits = []
        
        try:
            # Add benefits based on matches
            matches = compatibility_result.get('matches', [])
            for match in matches[:3]:  # Top 3 matches
                feature_name = match.get('feature', '')
                if feature_name:
                    benefits.append(f"✓ {feature_name}")
            
            # Add category-specific benefits
            if category == 'health':
                benefits.extend(self.get_health_benefits(policy))
            elif category == 'funeral':
                benefits.extend(self.get_funeral_benefits(policy))
            
            # Add general benefits
            benefits.append(f"Coverage up to R{policy.coverage_amount:,.0f}")
            benefits.append(f"Monthly premium from R{policy.base_premium:,.0f}")
            
            return benefits[:5]  # Limit to 5 benefits
            
        except Exception as e:
            logger.error(f"Error extracting benefits for policy {policy.id}: {str(e)}")
            return [f"Coverage up to R{policy.coverage_amount:,.0f}"]
    
    def get_health_benefits(self, policy):
        """Get health-specific benefits"""
        benefits = []
        
        # Check if it's a HealthPolicy instance
        if hasattr(policy, 'includes_hospital_cover') and policy.includes_hospital_cover:
            benefits.append("Hospital coverage included")
        
        if hasattr(policy, 'includes_outpatient_cover') and policy.includes_outpatient_cover:
            benefits.append("Outpatient benefits included")
        
        if hasattr(policy, 'ambulance_cover') and policy.ambulance_cover:
            benefits.append("Ambulance coverage")
        
        if hasattr(policy, 'chronic_medication_covered') and policy.chronic_medication_covered:
            benefits.append("Chronic medication covered")
        
        return benefits
    
    def get_funeral_benefits(self, policy):
        """Get funeral-specific benefits"""
        benefits = []
        
        # Check if it's a FuneralPolicy instance
        if hasattr(policy, 'includes_coffin') and policy.includes_coffin:
            benefits.append("Coffin included")
        
        if hasattr(policy, 'includes_transport') and policy.includes_transport:
            benefits.append("Transport included")
        
        if hasattr(policy, 'repatriation_covered') and policy.repatriation_covered:
            benefits.append("Repatriation covered")
        
        if hasattr(policy, 'grocery_benefit') and policy.grocery_benefit:
            benefits.append("Grocery benefit included")
        
        return benefits


class FeatureSurveyView(View):
    """Feature-based survey view"""
    def get(self, request, category):
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        # Generate feature survey questions
        questions = self.get_feature_survey_questions(category)
        
        # Get existing responses for this session and category
        existing_responses = self.get_existing_responses(session_key, category)
        
        # Calculate completion status
        completion_status = self.calculate_completion_status(questions, existing_responses)
        
        context = {
            'category': category,
            'category_display': f'{category.title()} Feature',
            'completion_status': completion_status,
            'questions': questions,
            'existing_responses': existing_responses,
            'session_key': session_key
        }
        return render(request, 'surveys/simple_survey_form_fixed.html', context)
    
    def get_existing_responses(self, session_key, category):
        """Get existing responses for this session and category"""
        responses = SimpleSurveyResponse.objects.filter(
            session_key=session_key,
            category=category
        ).select_related('question')
        
        response_dict = {}
        for response in responses:
            response_dict[response.question.field_name] = response.response_value
        
        return response_dict
    
    def calculate_completion_status(self, questions, existing_responses):
        """Calculate completion status based on questions and responses"""
        required_questions = [q for q in questions if q.get('is_required', True)]
        total_required = len(required_questions)
        
        if total_required == 0:
            return {
                'completion_percentage': 100,
                'answered_required': 0,
                'required_questions': 0,
                'is_complete': True
            }
        
        # Count answered required questions
        answered_required = 0
        for question in required_questions:
            field_name = question.get('field_name')
            if field_name in existing_responses:
                response_value = existing_responses[field_name]
                # Check if response is not empty
                if response_value is not None and response_value != '' and response_value != []:
                    answered_required += 1
        
        # Calculate percentage
        completion_percentage = int((answered_required / total_required) * 100)
        is_complete = answered_required == total_required
        
        return {
            'completion_percentage': completion_percentage,
            'answered_required': answered_required,
            'required_questions': total_required,
            'is_complete': is_complete
        }
    
    def get_survey_questions(self, category):
        """Load survey questions from database based on category"""
        questions = SimpleSurveyQuestion.objects.for_category(category)
        
        # Convert to the format expected by the template
        question_list = []
        for question in questions:
            question_dict = {
                'id': question.pk,
                'question_text': question.question_text,
                'field_name': question.field_name,
                'input_type': question.input_type,
                'is_required': question.is_required,
                'choices': question.get_choices_list(),
                'validation_rules': question.validation_rules,
            }
            question_list.append(question_dict)
        
        return question_list
    
    def get_feature_survey_questions(self, category):
        """Generate feature-based survey questions from database"""
        base_questions = self.get_survey_questions(category)
        
        # Add feature-specific questions
        feature_questions = [
            {
                'id': 'feature_1',
                'question_text': 'Which features are most important to you?',
                'field_name': 'important_features',
                'input_type': 'checkbox',
                'is_required': True,
                'choices': [
                    ('online_claims', 'Online Claims Processing'),
                    ('24_7_support', '24/7 Customer Support'),
                    ('mobile_app', 'Mobile App'),
                    ('network_hospitals', 'Large Hospital Network'),
                    ('quick_approval', 'Quick Approval Process'),
                    ('wellness_programs', 'Wellness Programs')
                ]
            },
            {
                'id': 'feature_2',
                'question_text': 'How do you prefer to manage your policy?',
                'field_name': 'management_preference',
                'input_type': 'radio',
                'is_required': True,
                'choices': [
                    ('online', 'Online Portal'),
                    ('mobile', 'Mobile App'),
                    ('phone', 'Phone Support'),
                    ('branch', 'Physical Branch')
                ]
            }
        ]
        
        return base_questions + feature_questions


class FeatureResultsView(View):
    """Feature-based survey results"""
    def get(self, request, category):
        # Render feature results
        context = {
            'category': category,
            'category_display': f'{category.title()} Feature',
            'quotations': [],  # Will be populated by actual feature comparison engine
            'total_quotations': 0,
            'message': 'Feature survey processing complete. Enhanced results will be displayed here.',
            'metadata': {
                'total_policies_evaluated': 0,
                'fallback_used': False
            }
        }
        return render(request, 'surveys/simple_survey_results.html', context)


# AJAX endpoints - these should integrate with existing survey functionality
@require_POST
@csrf_exempt
def save_response_ajax(request, category=None):
    """Save survey response via AJAX and return updated progress"""
    try:
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        # Get form data
        field_name = request.POST.get('field_name')
        response_value = request.POST.get('response_value')
        
        if not field_name or not category:
            return JsonResponse({
                'status': 'error', 
                'message': 'Missing field_name or category'
            })
        
        # Get the question
        try:
            question = SimpleSurveyQuestion.objects.get(
                category=category,
                field_name=field_name
            )
        except SimpleSurveyQuestion.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Question not found'
            })
        
        # Handle checkbox fields
        if question.input_type == 'checkbox':
            checkbox_values = request.POST.getlist('response_value')
            response_value = checkbox_values if checkbox_values else []
        elif isinstance(response_value, str) and response_value.startswith('['):
            # Handle JSON-like string arrays from frontend
            try:
                import json
                response_value = json.loads(response_value)
            except:
                pass
        
        # Save response
        response, created = SimpleSurveyResponse.objects.update_or_create(
            session_key=session_key,
            question=question,
            defaults={
                'category': category,
                'response_value': response_value
            }
        )
        
        # Calculate updated progress
        progress = calculate_progress_for_session(session_key, category)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Response saved',
            'progress': progress
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def calculate_progress_for_session(session_key, category):
    """Helper function to calculate progress for a session"""
    # Get all required questions
    required_questions = SimpleSurveyQuestion.objects.filter(
        category=category,
        is_required=True
    )
    total_required = required_questions.count()
    
    if total_required == 0:
        return {
            'completion_percentage': 100,
            'answered_required': 0,
            'required_questions': 0,
            'is_complete': True
        }
    
    # Count answered required questions
    answered_responses = SimpleSurveyResponse.objects.filter(
        session_key=session_key,
        category=category,
        question__is_required=True
    ).exclude(response_value__in=['', None, []])
    
    answered_count = answered_responses.count()
    completion_percentage = int((answered_count / total_required) * 100)
    
    return {
        'completion_percentage': completion_percentage,
        'answered_required': answered_count,
        'required_questions': total_required,
        'is_complete': answered_count == total_required
    }


def survey_status_ajax(request, category):
    """Get survey status via AJAX"""
    try:
        if not request.session.session_key:
            return JsonResponse({
                'status': 'no_session',
                'progress': {
                    'completion_percentage': 0,
                    'answered_required': 0,
                    'required_questions': 0,
                    'is_complete': False
                }
            })
        
        session_key = request.session.session_key
        progress = calculate_progress_for_session(session_key, category)
        
        return JsonResponse({
            'status': 'active',
            'category': category,
            'progress': progress
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def policy_benefits_ajax(request, policy_id):
    """Get policy benefits via AJAX"""
    try:
        # Get the policy
        policy = get_object_or_404(BasePolicy, id=policy_id, is_active=True)
        
        # Get policy features
        policy_features = policy.get_policy_features()
        
        # Prepare response data
        response_data = {
            'success': True,
            'policy': {
                'id': policy.id,
                'name': policy.name,
                'organization': policy.organization.name,
                'base_premium': float(policy.base_premium),
                'coverage_amount': float(policy.coverage_amount)
            },
            'features': {},
            'additional_features': [],
            'rewards': []
        }
        
        # Add policy features
        if policy_features:
            features = {}
            
            if policy_features.insurance_type == 'HEALTH':
                if policy_features.annual_limit_per_family:
                    features['Annual Family Limit'] = f"R{policy_features.annual_limit_per_family:,.0f}"
                
                if policy_features.annual_limit_family_range:
                    features['Family Limit Range'] = policy_features.annual_limit_family_range
                
                if policy_features.in_hospital_benefit_level:
                    features['In-Hospital Coverage'] = policy_features.in_hospital_benefit_level.replace('_', ' ').title()
                
                if policy_features.out_hospital_benefit_level:
                    features['Out-of-Hospital Coverage'] = policy_features.out_hospital_benefit_level.replace('_', ' ').title()
                
                if policy_features.ambulance_coverage is not None:
                    features['Ambulance Coverage'] = 'Yes' if policy_features.ambulance_coverage else 'No'
                
                if policy_features.chronic_medication_availability is not None:
                    features['Chronic Medication'] = 'Available' if policy_features.chronic_medication_availability else 'Not Available'
            
            elif policy_features.insurance_type == 'FUNERAL':
                if policy_features.cover_amount:
                    features['Coverage Amount'] = f"R{policy_features.cover_amount:,.0f}"
                
                if policy_features.cover_amount_range:
                    features['Coverage Range'] = policy_features.cover_amount_range
                
                if policy_features.funeral_service_type:
                    features['Service Type'] = policy_features.funeral_service_type.replace('_', ' ').title()
            
            response_data['features'] = features
        
        # Add additional features from the policy
        additional_features = []
        if hasattr(policy, 'additional_features'):
            for feature in policy.additional_features.all():
                additional_features.append({
                    'title': feature.title,
                    'description': feature.description,
                    'coverage_details': feature.coverage_details,
                    'icon': feature.icon
                })
        
        response_data['additional_features'] = additional_features
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error getting policy benefits for {policy_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to load policy benefits'
        })


# Error handling views
def session_expired_view(request):
    """Handle session expired errors"""
    return render(request, 'surveys/session_expired.html')


def session_error_view(request):
    """Handle general session errors"""
    return render(request, 'surveys/session_error.html')