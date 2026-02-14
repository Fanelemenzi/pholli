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
from .models import SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession


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
    """Display survey results"""
    def get(self, request, category):
        # Render survey results with sample data
        context = {
            'category': category,
            'category_display': category.title(),
            'quotations': [],  # Will be populated by actual comparison engine
            'total_quotations': 0,
            'message': 'Survey processing complete. Results will be displayed here.',
            'metadata': {
                'total_policies_evaluated': 0,
                'fallback_used': False
            }
        }
        return render(request, 'surveys/simple_survey_results.html', context)


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
    # This could integrate with the policies app
    return JsonResponse({'benefits': [], 'policy_id': policy_id})


# Error handling views
def session_expired_view(request):
    """Handle session expired errors"""
    return render(request, 'surveys/session_expired.html')


def session_error_view(request):
    """Handle general session errors"""
    return render(request, 'surveys/session_error.html')