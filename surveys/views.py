from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.urls import reverse
from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from .models import SurveyQuestion, SurveyResponse
from .forms import SurveyResponseForm
import logging
import uuid

logger = logging.getLogger(__name__)


def direct_survey_view(request, category_slug):
    """
    Direct survey access that creates a new session and starts the survey.
    """
    try:
        # Get the category
        category = get_object_or_404(PolicyCategory, slug=category_slug)
        
        # Create a new session
        session_key = f"survey_{category_slug}_{uuid.uuid4().hex[:12]}"
        session = ComparisonSession.objects.create(
            session_key=session_key,
            category=category,
            status=ComparisonSession.Status.ACTIVE
        )
        
        # Redirect to survey form with session
        survey_url = reverse('surveys:survey_form', kwargs={'category_slug': category_slug}) + f"?session={session_key}"
        return redirect(survey_url)
        
    except Exception as e:
        logger.error(f"Error in direct_survey_view for {category_slug}: {str(e)}")
        messages.error(request, f'Unable to start {category_slug} survey. Please try again.')
        return redirect('home')


def survey_form_view(request, category_slug):
    """
    Display the survey form for a specific insurance category.
    """
    try:
        # Get session key from query parameters
        session_key = request.GET.get('session')
        if not session_key:
            messages.error(request, 'No survey session found. Starting new survey.')
            return redirect('surveys:direct_survey', category_slug=category_slug)
        
        # Get category and session
        category = get_object_or_404(PolicyCategory, slug=category_slug)
        session = get_object_or_404(ComparisonSession, session_key=session_key, category=category)
        
        # Get the next unanswered question
        answered_questions = SurveyResponse.objects.filter(session=session).values_list('question_id', flat=True)
        current_question = SurveyQuestion.objects.filter(
            category=category,
            is_active=True
        ).exclude(id__in=answered_questions).order_by('display_order').first()
        
        # If no more questions, redirect to completion
        if not current_question:
            completion_url = reverse('surveys:survey_completion', kwargs={'category_slug': category_slug}) + f"?session={session_key}"
            return redirect(completion_url)
        
        # Handle form submission
        if request.method == 'POST':
            form = SurveyResponseForm(current_question, request.POST)
            if form.is_valid():
                # Save the response
                response = form.save(session)
                if response:
                    messages.success(request, 'Response saved successfully!')
                    # Redirect to next question
                    next_url = reverse('surveys:survey_form', kwargs={'category_slug': category_slug}) + f"?session={session_key}"
                    return redirect(next_url)
                else:
                    messages.error(request, 'Failed to save response. Please try again.')
        else:
            form = SurveyResponseForm(current_question)
        
        # Calculate progress
        total_questions = SurveyQuestion.objects.filter(category=category, is_active=True).count()
        answered_count = len(answered_questions)
        completion_percentage = float((answered_count / total_questions * 100)) if total_questions > 0 else 0.0
        
        context = {
            'category': category,
            'category_slug': category_slug,
            'session_key': session_key,
            'current_question': current_question,
            'form': form,
            'completion_percentage': completion_percentage,
            'answered_count': answered_count,
            'total_questions': total_questions,
        }
        
        return render(request, 'surveys/survey_form.html', context)
        
    except Exception as e:
        logger.error(f"Error in survey_form_view for {category_slug}: {str(e)}")
        messages.error(request, 'An error occurred while loading the survey. Please try again.')
        return redirect('surveys:direct_survey', category_slug=category_slug)


def survey_completion_view(request, category_slug):
    """
    Handle survey completion.
    """
    try:
        session_key = request.GET.get('session')
        if not session_key:
            messages.error(request, 'No survey session found.')
            return redirect('home')
        
        category = get_object_or_404(PolicyCategory, slug=category_slug)
        session = get_object_or_404(ComparisonSession, session_key=session_key, category=category)
        
        # Mark session as completed
        session.survey_completed = True
        session.status = ComparisonSession.Status.COMPLETED
        session.save()
        
        context = {
            'category': category,
            'category_slug': category_slug,
            'session_key': session_key,
            'completion_result': {
                'completion_time': 'Just now',
                'results_url': f'/surveys/results/?session={session_key}'
            }
        }
        
        return render(request, 'surveys/survey_completion.html', context)
        
    except Exception as e:
        logger.error(f"Error completing survey for {category_slug}: {str(e)}")
        messages.error(request, 'An error occurred while completing the survey.')
        return redirect('home')


def survey_results_view(request):
    """
    Display survey results and policy recommendations.
    """
    session_key = request.GET.get('session')
    
    if not session_key:
        messages.error(request, 'No survey session specified.')
        return redirect('home')
    
    try:
        session = get_object_or_404(ComparisonSession, session_key=session_key)
        
        # Get survey responses
        responses = SurveyResponse.objects.filter(session=session).select_related('question')
        total_responses = responses.count()
        total_questions = SurveyQuestion.objects.filter(category=session.category, is_active=True).count()
        completion_percentage = (total_responses / total_questions * 100) if total_questions > 0 else 0
        
        context = {
            'session_key': session_key,
            'session': session,
            'category': session.category,
            'responses': responses,
            'survey_summary': {
                'completion_percentage': completion_percentage,
                'total_responses': total_responses,
                'total_questions': total_questions,
            },
        }
        
        return render(request, 'surveys/survey_results.html', context)
        
    except Exception as e:
        logger.error(f"Error loading survey results for session {session_key}: {str(e)}")
        messages.error(request, 'An error occurred while loading survey results.')
        return redirect('home')


def survey_progress_view(request, session_key):
    """
    Get survey progress for a session (JSON response).
    """
    try:
        session = get_object_or_404(ComparisonSession, session_key=session_key)
        
        # Calculate progress
        total_responses = SurveyResponse.objects.filter(session=session).count()
        total_questions = SurveyQuestion.objects.filter(
            category=session.category,
            is_active=True
        ).count()
        
        completion_percentage = 0
        if total_questions > 0:
            completion_percentage = min(100, (total_responses / total_questions) * 100)
        
        return JsonResponse({
            'session_key': session_key,
            'completion_percentage': float(completion_percentage),
            'total_responses': total_responses,
            'total_questions': total_questions,
            'survey_completed': session.survey_completed
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
