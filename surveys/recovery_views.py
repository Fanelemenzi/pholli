"""
Session Recovery Views for Survey System.
Handles session expiry recovery and data restoration.
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

from .session_recovery import session_recovery_service, session_expiry_handler
from .error_handling import survey_error_handler
from .error_decorators import handle_survey_errors
import json
import logging

logger = logging.getLogger(__name__)


@handle_survey_errors(fallback_redirect='surveys:category_selection')
def session_recovery_view(request):
    """
    Display session recovery options when a session has expired.
    """
    # Get recovery info from session
    recovery_info = request.session.get('recovery_info')
    
    if not recovery_info:
        messages.error(request, 'No recovery information available.')
        return redirect('surveys:category_selection')
    
    expired_session_key = recovery_info['expired_session_key']
    category_slug = recovery_info['category_slug']
    recovery_data = recovery_info['recovery_data']
    
    # Check if recovery is still possible
    validity_check = session_recovery_service.check_session_validity(
        expired_session_key, category_slug
    )
    
    context = {
        'expired_session_key': expired_session_key,
        'category_slug': category_slug,
        'recovery_data': recovery_data,
        'validity_check': validity_check,
        'recovery_options': validity_check.get('recovery_options', [])
    }
    
    return render(request, 'surveys/session_recovery.html', context)


@require_POST
@handle_survey_errors(return_json=True)
def recover_session_ajax(request):
    """
    AJAX endpoint to recover an expired session.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    expired_session_key = data.get('expired_session_key')
    category_slug = data.get('category_slug')
    recovery_type = data.get('recovery_type', 'recover_responses')
    
    if not all([expired_session_key, category_slug]):
        return JsonResponse({
            'success': False,
            'error': 'Missing required parameters'
        }, status=400)
    
    # Perform recovery based on type
    if recovery_type == 'recover_and_continue':
        result = session_recovery_service.recover_session_data(
            expired_session_key, category_slug, request.user if request.user.is_authenticated else None
        )
    elif recovery_type == 'recover_responses':
        result = session_recovery_service.recover_session_data(
            expired_session_key, category_slug, request.user if request.user.is_authenticated else None
        )
    elif recovery_type == 'create_new':
        # Create new session without recovery
        from .session_manager import SurveySessionManager
        session_manager = SurveySessionManager(request)
        new_session = session_manager.create_survey_session(category_slug)
        
        result = {
            'success': True,
            'new_session_key': new_session.session_key,
            'recovered_responses': 0,
            'message': 'New survey session created'
        }
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid recovery type'
        }, status=400)
    
    # Clear recovery info from session if successful
    if result.get('success'):
        if 'recovery_info' in request.session:
            del request.session['recovery_info']
    
    return JsonResponse(result)


@require_http_methods(["GET"])
@handle_survey_errors(return_json=True)
def check_session_status_ajax(request):
    """
    AJAX endpoint to check session status and expiry warnings.
    """
    session_key = request.GET.get('session_key')
    category_slug = request.GET.get('category_slug')
    
    if not all([session_key, category_slug]):
        return JsonResponse({
            'success': False,
            'error': 'Missing required parameters'
        }, status=400)
    
    # Check session validity
    validity_check = session_recovery_service.check_session_validity(
        session_key, category_slug
    )
    
    response_data = {
        'success': True,
        'is_valid': validity_check['is_valid'],
        'status': validity_check['status'],
        'message': validity_check['message']
    }
    
    # Add expiry warning if session is valid
    if validity_check['is_valid'] and validity_check.get('session'):
        expiry_warning = session_expiry_handler.check_session_expiry_warning(
            validity_check['session']
        )
        response_data['expiry_warning'] = expiry_warning
    
    # Add recovery options if session is invalid
    if not validity_check['is_valid']:
        response_data.update({
            'recovery_options': validity_check.get('recovery_options', []),
            'can_recover': validity_check.get('can_recover', False),
            'recovery_data': validity_check.get('recovery_data', {})
        })
    
    return JsonResponse(response_data)


@require_POST
@handle_survey_errors(return_json=True)
def extend_session_ajax(request):
    """
    AJAX endpoint to extend session expiry.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    session_key = data.get('session_key')
    hours = data.get('hours', 1)
    reason = data.get('reason', 'user_request')
    
    if not session_key:
        return JsonResponse({
            'success': False,
            'error': 'Session key is required'
        }, status=400)
    
    # Extend session
    result = session_recovery_service.extend_session_expiry(
        session_key, hours, reason
    )
    
    return JsonResponse(result)


@handle_survey_errors(fallback_redirect='surveys:category_selection')
def session_expired_view(request):
    """
    Display session expired page with recovery options.
    """
    session_key = request.GET.get('session')
    category_slug = request.GET.get('category')
    
    context = {
        'session_key': session_key,
        'category_slug': category_slug
    }
    
    # Check if recovery is possible
    if session_key and category_slug:
        validity_check = session_recovery_service.check_session_validity(
            session_key, category_slug
        )
        context['validity_check'] = validity_check
        context['can_recover'] = validity_check.get('can_recover', False)
        context['recovery_data'] = validity_check.get('recovery_data', {})
    
    return render(request, 'surveys/session_expired.html', context)


@require_POST
@handle_survey_errors(fallback_redirect='surveys:category_selection')
def handle_session_expiry_form(request):
    """
    Handle form submission for session expiry recovery.
    """
    action = request.POST.get('action')
    expired_session_key = request.POST.get('expired_session_key')
    category_slug = request.POST.get('category_slug')
    
    if not all([action, expired_session_key, category_slug]):
        messages.error(request, 'Missing required information for recovery.')
        return redirect('surveys:category_selection')
    
    if action == 'recover':
        # Attempt to recover session data
        result = session_recovery_service.recover_session_data(
            expired_session_key, 
            category_slug, 
            request.user if request.user.is_authenticated else None
        )
        
        if result['success']:
            messages.success(request, result['message'])
            return redirect('surveys:survey_form', category_slug=category_slug) + f"?session={result['new_session_key']}"
        else:
            messages.error(request, f"Recovery failed: {result.get('error', 'Unknown error')}")
            return redirect('surveys:category_selection')
    
    elif action == 'new_session':
        # Create new session
        messages.info(request, 'Starting a new survey session.')
        return redirect('surveys:survey_form', category_slug=category_slug)
    
    else:
        messages.error(request, 'Invalid action specified.')
        return redirect('surveys:category_selection')


@require_http_methods(["GET"])
@handle_survey_errors(return_json=True)
def get_recovery_info_ajax(request):
    """
    AJAX endpoint to get recovery information for a session.
    """
    session_key = request.GET.get('session_key')
    
    if not session_key:
        return JsonResponse({
            'success': False,
            'error': 'Session key is required'
        }, status=400)
    
    # Get recovery info from cache
    recovery_info = session_recovery_service.get_recovery_info(session_key)
    
    if recovery_info:
        return JsonResponse({
            'success': True,
            'recovery_info': recovery_info,
            'has_recovery_info': True
        })
    else:
        return JsonResponse({
            'success': True,
            'recovery_info': None,
            'has_recovery_info': False
        })


@require_POST
@handle_survey_errors(return_json=True)
def clear_recovery_info_ajax(request):
    """
    AJAX endpoint to clear recovery information.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    session_key = data.get('session_key')
    
    if not session_key:
        return JsonResponse({
            'success': False,
            'error': 'Session key is required'
        }, status=400)
    
    # Clear recovery info
    session_recovery_service.clear_recovery_info(session_key)
    
    return JsonResponse({
        'success': True,
        'message': 'Recovery information cleared'
    })


@handle_survey_errors(fallback_redirect='surveys:category_selection')
def error_fallback_view(request):
    """
    Fallback view for when survey operations fail.
    Provides basic comparison options.
    """
    category_slug = request.GET.get('category', 'health')
    error_type = request.GET.get('error_type', 'unknown')
    
    # Get fallback information if available
    from .graceful_degradation import graceful_degradation_manager
    
    context = {
        'category_slug': category_slug,
        'error_type': error_type,
        'fallback_options': [
            {
                'type': 'basic_comparison',
                'title': 'Basic Comparison',
                'description': 'View all available policies with standard comparison',
                'url': reverse('comparison:basic_comparison', kwargs={'category_slug': category_slug})
            },
            {
                'type': 'new_survey',
                'title': 'Start New Survey',
                'description': 'Begin a new personalized survey',
                'url': reverse('surveys:survey_form', kwargs={'category_slug': category_slug})
            },
            {
                'type': 'category_selection',
                'title': 'Choose Category',
                'description': 'Select a different insurance category',
                'url': reverse('surveys:category_selection')
            }
        ]
    }
    
    return render(request, 'surveys/error_fallback.html', context)