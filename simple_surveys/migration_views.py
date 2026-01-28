"""
Migration Views for Simple Survey System.

This module provides views for handling response migration from old to new format.
Allows users to review and update their responses when migration is needed.

Requirements: 6.4, 6.5, 6.6
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.utils import timezone
import json
import logging

from .models import SimpleSurveyResponse, SimpleSurveyQuestion, QuotationSession
from .forms import HealthSurveyForm, FuneralSurveyForm
from .response_migration import ResponseMigrationHandler
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class ResponseMigrationView(View):
    """
    View for handling response migration from old to new format.
    
    Provides interface for users to review and update their responses
    when migration from old binary questions to new benefit levels is needed.
    """
    
    def get(self, request, category):
        """Display migration review form for user responses"""
        # Validate category
        if category not in ['health', 'funeral']:
            raise Http404("Invalid survey category")
        
        # Get session key
        session_key = request.session.session_key
        if not session_key:
            # No session - redirect to survey
            return redirect('simple_surveys:feature_survey', category=category)
        
        # Initialize migration handler
        migration_handler = ResponseMigrationHandler(category)
        
        # Check migration status
        status = migration_handler.check_migration_status(session_key)
        
        if status['status'] == 'no_responses':
            # No responses to migrate - redirect to survey
            return redirect('simple_surveys:feature_survey', category=category)
        
        if status['status'] == 'new_format':
            # Already in new format - redirect to results
            return redirect('simple_surveys:feature_results', category=category)
        
        # Get migration form data
        form_data_result = migration_handler.get_migration_form_data(session_key)
        
        if not form_data_result['success']:
            messages.error(request, f"Error loading migration data: {form_data_result['message']}")
            return redirect('simple_surveys:feature_survey', category=category)
        
        # Create form with existing data and suggestions
        form_data = form_data_result['form_data']
        suggestions = form_data_result['migration_suggestions']
        
        # Create appropriate form based on category
        if category == 'health':
            form = HealthSurveyForm(initial=form_data)
        else:
            form = FuneralSurveyForm(initial=form_data)
        
        # Add suggestion data to form fields
        for field_name, suggestion in suggestions.items():
            if field_name in form.fields:
                field = form.fields[field_name]
                if 'suggested_value' in suggestion:
                    field.initial = suggestion['suggested_value']
                if 'reason' in suggestion:
                    field.help_text = f"{field.help_text or ''} (Suggested: {suggestion['reason']})".strip()
        
        context = {
            'category': category,
            'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
            'form': form,
            'migration_status': status,
            'suggestions': suggestions,
            'is_migration': True,
            'can_auto_migrate': status.get('can_auto_migrate', False),
        }
        
        return render(request, 'surveys/migration_review_form.html', context)
    
    def post(self, request, category):
        """Process migration review form submission"""
        # Validate category
        if category not in ['health', 'funeral']:
            raise Http404("Invalid survey category")
        
        # Get session key
        session_key = request.session.session_key
        if not session_key:
            return JsonResponse({'success': False, 'error': 'No session found'})
        
        # Check if this is an auto-migration request
        if request.POST.get('action') == 'auto_migrate':
            return self._handle_auto_migration(request, category, session_key)
        
        # Handle manual form submission
        return self._handle_manual_migration(request, category, session_key)
    
    def _handle_auto_migration(self, request, category: str, session_key: str) -> JsonResponse:
        """
        Handle automatic migration of responses.
        
        Args:
            request: HTTP request
            category: Insurance category
            session_key: User session key
            
        Returns:
            JSON response with migration results
        """
        try:
            migration_handler = ResponseMigrationHandler(category)
            
            # Attempt auto-migration
            result = migration_handler.auto_migrate_responses(session_key)
            
            if result['success']:
                messages.success(
                    request, 
                    f"Successfully migrated {result['migrated_count']} responses to new format"
                )
                
                return JsonResponse({
                    'success': True,
                    'migrated_count': result['migrated_count'],
                    'redirect_url': f'/simple_surveys/{category}/results/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Auto-migration failed'),
                    'message': result.get('message', '')
                })
                
        except Exception as e:
            logger.error(f"Error in auto-migration for session {session_key}: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    def _handle_manual_migration(self, request, category: str, session_key: str):
        """
        Handle manual form submission for migration.
        
        Args:
            request: HTTP request
            category: Insurance category
            session_key: User session key
            
        Returns:
            HTTP response (redirect or form with errors)
        """
        try:
            # Create appropriate form based on category
            if category == 'health':
                form = HealthSurveyForm(request.POST)
            else:
                form = FuneralSurveyForm(request.POST)
            
            if form.is_valid():
                # Save responses in new format
                self._save_migrated_responses(session_key, category, form.cleaned_data)
                
                # Clear old responses
                self._clear_old_responses(session_key, category)
                
                messages.success(request, "Your responses have been updated to the new format")
                return redirect('simple_surveys:feature_results', category=category)
            
            else:
                # Form has errors - redisplay with migration context
                migration_handler = ResponseMigrationHandler(category)
                status = migration_handler.check_migration_status(session_key)
                form_data_result = migration_handler.get_migration_form_data(session_key)
                
                context = {
                    'category': category,
                    'category_display': 'Health Insurance' if category == 'health' else 'Funeral Insurance',
                    'form': form,
                    'migration_status': status,
                    'suggestions': form_data_result.get('migration_suggestions', {}),
                    'is_migration': True,
                    'can_auto_migrate': status.get('can_auto_migrate', False),
                }
                
                return render(request, 'surveys/migration_review_form.html', context)
                
        except Exception as e:
            logger.error(f"Error in manual migration for session {session_key}: {e}")
            messages.error(request, f"Error updating responses: {str(e)}")
            return redirect('simple_surveys:feature_survey', category=category)
    
    def _save_migrated_responses(self, session_key: str, category: str, form_data: dict):
        """
        Save migrated responses in new format.
        
        Args:
            session_key: User session key
            category: Insurance category
            form_data: Cleaned form data
        """
        # Get all questions for this category
        questions = SimpleSurveyQuestion.objects.filter(category=category)
        question_map = {q.field_name: q for q in questions}
        
        # Save each response
        for field_name, value in form_data.items():
            if field_name in question_map and value is not None:
                question = question_map[field_name]
                
                # Create or update response
                SimpleSurveyResponse.objects.update_or_create(
                    session_key=session_key,
                    question=question,
                    defaults={
                        'category': category,
                        'response_value': value
                    }
                )
    
    def _clear_old_responses(self, session_key: str, category: str):
        """
        Clear old format responses that are no longer needed.
        
        Args:
            session_key: User session key
            category: Insurance category
        """
        old_fields = [
            'wants_in_hospital_benefit',
            'wants_out_hospital_benefit',
            'currently_on_medical_aid'
        ]
        
        # Delete old responses
        SimpleSurveyResponse.objects.filter(
            session_key=session_key,
            category=category,
            question__field_name__in=old_fields
        ).delete()


@require_http_methods(["GET"])
def check_migration_status(request, category):
    """
    AJAX endpoint to check migration status for a session.
    
    Args:
        request: HTTP request
        category: Insurance category
        
    Returns:
        JSON response with migration status
    """
    if category not in ['health', 'funeral']:
        return JsonResponse({'success': False, 'error': 'Invalid category'})
    
    session_key = request.session.session_key
    if not session_key:
        return JsonResponse({
            'success': True,
            'status': 'no_session',
            'needs_migration': False
        })
    
    try:
        migration_handler = ResponseMigrationHandler(category)
        status = migration_handler.check_migration_status(session_key)
        
        return JsonResponse({
            'success': True,
            **status
        })
        
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_migration_notification(request, category):
    """
    AJAX endpoint to get migration notification for display in UI.
    
    Args:
        request: HTTP request
        category: Insurance category
        
    Returns:
        JSON response with notification data
    """
    if category not in ['health', 'funeral']:
        return JsonResponse({'success': False, 'error': 'Invalid category'})
    
    session_key = request.session.session_key
    if not session_key:
        return JsonResponse({
            'success': True,
            'show_notification': False
        })
    
    try:
        migration_handler = ResponseMigrationHandler(category)
        notification = migration_handler.create_migration_notification(session_key)
        
        return JsonResponse({
            'success': True,
            **notification
        })
        
    except Exception as e:
        logger.error(f"Error getting migration notification: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
@require_POST
@csrf_exempt
def migrate_responses_ajax(request, category):
    """
    AJAX endpoint for automatic response migration.
    
    Args:
        request: HTTP request
        category: Insurance category
        
    Returns:
        JSON response with migration results
    """
    if category not in ['health', 'funeral']:
        return JsonResponse({'success': False, 'error': 'Invalid category'})
    
    session_key = request.session.session_key
    if not session_key:
        return JsonResponse({'success': False, 'error': 'No session found'})
    
    try:
        migration_handler = ResponseMigrationHandler(category)
        result = migration_handler.auto_migrate_responses(session_key)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in AJAX migration: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })