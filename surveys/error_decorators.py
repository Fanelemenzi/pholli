"""
Error Handling Decorators for Survey Views and Functions.
Provides consistent error handling across survey operations.
"""

import functools
import logging
from typing import Callable, Any, Dict, Optional
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.core.exceptions import ValidationError

from .error_handling import (
    SurveyError, SurveyValidationError, SurveySessionError, 
    SurveyProcessingError, survey_error_handler
)
from .session_recovery import session_recovery_service

logger = logging.getLogger(__name__)


def handle_survey_errors(
    fallback_redirect: str = None,
    return_json: bool = False,
    log_errors: bool = True
):
    """
    Decorator to handle survey-related errors with appropriate responses.
    
    Args:
        fallback_redirect: URL name to redirect to on error
        return_json: Whether to return JSON responses for AJAX requests
        log_errors: Whether to log errors
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
                
            except SurveyValidationError as e:
                error_response = survey_error_handler.handle_validation_error(e)
                return _handle_error_response(
                    error_response, args, fallback_redirect, return_json
                )
                
            except SurveySessionError as e:
                error_response = survey_error_handler.handle_session_error(e)
                return _handle_error_response(
                    error_response, args, fallback_redirect, return_json
                )
                
            except SurveyProcessingError as e:
                error_response = survey_error_handler.handle_processing_error(e)
                return _handle_error_response(
                    error_response, args, fallback_redirect, return_json
                )
                
            except ValidationError as e:
                error_response = survey_error_handler.handle_validation_error(e)
                return _handle_error_response(
                    error_response, args, fallback_redirect, return_json
                )
                
            except Exception as e:
                if log_errors:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                
                error_response = survey_error_handler.handle_system_error(e)
                return _handle_error_response(
                    error_response, args, fallback_redirect, return_json
                )
                
        return wrapper
    return decorator


def _handle_error_response(
    error_response: Dict[str, Any],
    view_args: tuple,
    fallback_redirect: str,
    return_json: bool
) -> HttpResponse:
    """Handle error response based on request type and configuration."""
    
    # Extract request from view args (assuming first arg is request for view functions)
    request = None
    if view_args and hasattr(view_args[0], 'META'):
        request = view_args[0]
    
    # Check if this is an AJAX request
    is_ajax = False
    if request:
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.content_type == 'application/json' or
            'application/json' in request.headers.get('Accept', '')
        )
    
    # Return JSON response for AJAX requests or if explicitly requested
    if is_ajax or return_json:
        return JsonResponse(error_response, status=400 if error_response.get('recoverable') else 500)
    
    # For regular requests, add message and redirect
    if request:
        if error_response.get('severity') == 'critical':
            messages.error(request, error_response['message'])
        elif error_response.get('severity') == 'high':
            messages.warning(request, error_response['message'])
        else:
            messages.info(request, error_response['message'])
        
        # Add recovery suggestions as info messages
        for suggestion in error_response.get('recovery_suggestions', []):
            messages.info(request, suggestion)
    
    # Determine redirect URL
    if fallback_redirect:
        return redirect(fallback_redirect)
    elif error_response.get('error_type') == 'session_error':
        return redirect('home')
    else:
        return redirect('home')


def handle_session_expiry(
    recovery_enabled: bool = True,
    extend_on_activity: bool = True
):
    """
    Decorator to handle session expiry with recovery options.
    
    Args:
        recovery_enabled: Whether to offer session recovery
        extend_on_activity: Whether to extend session on user activity
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            request = args[0] if args and hasattr(args[0], 'META') else None
            
            # Extract session key from request or kwargs
            session_key = None
            category_slug = None
            
            if request:
                session_key = request.GET.get('session') or request.POST.get('session_key')
                category_slug = kwargs.get('category_slug')
            
            if session_key and category_slug:
                # Check session validity
                validity_check = session_recovery_service.check_session_validity(
                    session_key, category_slug
                )
                
                if not validity_check['is_valid']:
                    if validity_check['status'] == 'expired' and recovery_enabled:
                        # Offer recovery options
                        return _handle_session_expiry(
                            request, session_key, category_slug, validity_check
                        )
                    else:
                        # Session invalid, redirect to start
                        if request:
                            messages.error(request, validity_check['message'])
                        return redirect('home')
                
                # Extend session if configured
                if extend_on_activity and validity_check.get('session'):
                    session_recovery_service.extend_session_expiry(session_key, hours=1)
            
            return func(*args, **kwargs)
            
        return wrapper
    return decorator


def _handle_session_expiry(
    request,
    session_key: str,
    category_slug: str,
    validity_check: Dict[str, Any]
) -> HttpResponse:
    """Handle session expiry with recovery options."""
    
    # Check if this is an AJAX request
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.content_type == 'application/json'
    )
    
    recovery_data = validity_check.get('recovery_data', {})
    
    if is_ajax:
        return JsonResponse({
            'success': False,
            'error_type': 'session_expired',
            'message': 'Your session has expired',
            'recovery_options': validity_check.get('recovery_options', []),
            'recovery_data': recovery_data,
            'can_recover': validity_check.get('can_recover', False)
        })
    
    # For regular requests, show recovery options
    if recovery_data.get('can_recover'):
        messages.warning(
            request,
            f"Your session expired, but we can recover {recovery_data.get('response_count', 0)} responses."
        )
        
        # Store recovery info in session for recovery page
        request.session['recovery_info'] = {
            'expired_session_key': session_key,
            'category_slug': category_slug,
            'recovery_data': recovery_data
        }
        
        return redirect('surveys:session_recovery')
    else:
        messages.error(request, 'Your session has expired. Please start a new survey.')
        return redirect('home')


def validate_survey_data(
    required_fields: list = None,
    validate_session: bool = True
):
    """
    Decorator to validate survey data before processing.
    
    Args:
        required_fields: List of required fields in request data
        validate_session: Whether to validate session existence
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            request = args[0] if args and hasattr(args[0], 'META') else None
            
            if not request:
                return func(*args, **kwargs)
            
            # Validate required fields
            if required_fields:
                missing_fields = []
                
                if request.method == 'POST':
                    data = request.POST
                elif request.method == 'GET':
                    data = request.GET
                else:
                    try:
                        import json
                        data = json.loads(request.body)
                    except:
                        data = {}
                
                for field in required_fields:
                    if field not in data or not data[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    error = SurveyValidationError(
                        "Missing required fields",
                        field_errors={field: ["This field is required"] for field in missing_fields}
                    )
                    error_response = survey_error_handler.handle_validation_error(error)
                    
                    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    if is_ajax:
                        return JsonResponse(error_response, status=400)
                    else:
                        for field in missing_fields:
                            messages.error(request, f"Missing required field: {field}")
                        return redirect('home')
            
            # Validate session if required
            if validate_session:
                session_key = (
                    request.GET.get('session') or 
                    request.POST.get('session_key') or
                    getattr(request, 'session_key', None)
                )
                
                if not session_key:
                    error = SurveySessionError("No session key provided")
                    error_response = survey_error_handler.handle_session_error(error)
                    
                    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    if is_ajax:
                        return JsonResponse(error_response, status=400)
                    else:
                        messages.error(request, "No active survey session found")
                        return redirect('home')
            
            return func(*args, **kwargs)
            
        return wrapper
    return decorator


def with_graceful_degradation(
    fallback_function: Callable = None,
    enable_fallback: bool = True
):
    """
    Decorator to provide graceful degradation for survey operations.
    
    Args:
        fallback_function: Function to call if main function fails
        enable_fallback: Whether to enable fallback mechanisms
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                logger.warning(f"Function {func.__name__} failed, attempting graceful degradation: {str(e)}")
                
                if enable_fallback and fallback_function:
                    try:
                        return fallback_function(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback function also failed: {str(fallback_error)}")
                
                # If no fallback or fallback failed, handle as system error
                error_response = survey_error_handler.handle_system_error(e)
                
                # Try to extract request from args
                request = None
                if args and hasattr(args[0], 'META'):
                    request = args[0]
                
                if request:
                    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    if is_ajax:
                        return JsonResponse(error_response, status=500)
                    else:
                        messages.error(request, error_response['message'])
                        return redirect('home')
                
                # Re-raise if we can't handle gracefully
                raise e
                
        return wrapper
    return decorator


def log_survey_activity(
    activity_type: str = 'survey_action',
    include_user: bool = True,
    include_session: bool = True
):
    """
    Decorator to log survey activities for monitoring and debugging.
    
    Args:
        activity_type: Type of activity being logged
        include_user: Whether to include user information
        include_session: Whether to include session information
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = timezone.now()
            
            # Extract context information
            context = {
                'function': func.__name__,
                'activity_type': activity_type,
                'start_time': start_time.isoformat()
            }
            
            # Extract request and session info
            request = None
            if args and hasattr(args[0], 'META'):
                request = args[0]
                
                if include_user and hasattr(request, 'user'):
                    context['user_id'] = request.user.id if request.user.is_authenticated else None
                    context['is_authenticated'] = request.user.is_authenticated
                
                if include_session:
                    session_key = (
                        request.GET.get('session') or 
                        request.POST.get('session_key') or
                        kwargs.get('session_key')
                    )
                    if session_key:
                        context['session_key'] = session_key
                    
                    category_slug = kwargs.get('category_slug')
                    if category_slug:
                        context['category_slug'] = category_slug
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful completion
                end_time = timezone.now()
                duration = (end_time - start_time).total_seconds()
                
                context.update({
                    'status': 'success',
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration
                })
                
                logger.info(f"Survey activity completed: {context}")
                
                return result
                
            except Exception as e:
                # Log error
                end_time = timezone.now()
                duration = (end_time - start_time).total_seconds()
                
                context.update({
                    'status': 'error',
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration
                })
                
                logger.error(f"Survey activity failed: {context}")
                
                # Re-raise the exception
                raise e
                
        return wrapper
    return decorator