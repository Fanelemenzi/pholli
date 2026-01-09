"""
Middleware for handling session validation and cleanup in simple surveys.
"""

from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
import logging

from .session_manager import SessionManager, SessionValidationError
from .models import QuotationSession

logger = logging.getLogger(__name__)


class SessionValidationMiddleware(MiddlewareMixin):
    """
    Middleware to validate and clean up expired sessions for simple survey views.
    
    This middleware:
    1. Validates sessions for simple survey URLs
    2. Cleans up expired sessions automatically
    3. Handles session validation errors gracefully
    """
    
    # URLs that require session validation
    PROTECTED_URLS = [
        '/simple-surveys/save-response/',
        '/simple-surveys/health/process/',
        '/simple-surveys/funeral/process/',
        '/simple-surveys/health/status/',
        '/simple-surveys/funeral/status/',
    ]
    
    # URLs that should create sessions if they don't exist
    SESSION_CREATION_URLS = [
        '/simple-surveys/health/',
        '/simple-surveys/funeral/',
    ]
    
    def process_request(self, request):
        """Process incoming request for session validation."""
        path = request.path
        
        # Skip non-survey URLs
        if not path.startswith('/simple-surveys/'):
            return None
        
        # Handle session creation URLs
        if any(path.startswith(url) for url in self.SESSION_CREATION_URLS):
            return self._handle_session_creation(request, path)
        
        # Handle protected URLs
        if any(path.startswith(url) for url in self.PROTECTED_URLS):
            return self._handle_protected_url(request, path)
        
        return None
    
    def _handle_session_creation(self, request, path):
        """Handle URLs that should create sessions."""
        try:
            # Extract category from path
            category = self._extract_category_from_path(path)
            if not category:
                return None
            
            # Ensure session exists
            if not request.session.session_key:
                request.session.create()
            
            # Clean up any expired sessions for this Django session
            self._cleanup_expired_sessions_for_django_session(request.session.session_key)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in session creation middleware: {e}")
            return None
    
    def _handle_protected_url(self, request, path):
        """Handle URLs that require valid sessions."""
        try:
            session_key = request.session.session_key
            
            # No session key means no session
            if not session_key:
                return self._handle_no_session(request, path)
            
            # Extract category from request data or path
            category = self._extract_category_from_request(request, path)
            if not category:
                return None  # Let the view handle category validation
            
            # Validate session
            validation_result = SessionManager.validate_session(session_key, category)
            
            if not validation_result['valid']:
                return self._handle_invalid_session(request, path, validation_result['error'])
            
            # Session is valid, add to request for convenience
            request.quotation_session = validation_result['session']
            
            return None
            
        except Exception as e:
            logger.error(f"Error in session validation middleware: {e}")
            return None
    
    def _extract_category_from_path(self, path):
        """Extract category from URL path."""
        if '/health/' in path:
            return 'health'
        elif '/funeral/' in path:
            return 'funeral'
        return None
    
    def _extract_category_from_request(self, request, path):
        """Extract category from request data or path."""
        # Try to get from path first
        category = self._extract_category_from_path(path)
        if category:
            return category
        
        # Try to get from POST data for AJAX requests
        if request.method == 'POST':
            try:
                import json
                if hasattr(request, 'body'):
                    data = json.loads(request.body)
                    return data.get('category')
            except (json.JSONDecodeError, AttributeError):
                pass
            
            # Try form data
            return request.POST.get('category')
        
        # Try GET parameters
        return request.GET.get('category')
    
    def _handle_no_session(self, request, path):
        """Handle requests with no session."""
        if request.headers.get('Content-Type') == 'application/json' or path.endswith('/'):
            # AJAX request or API endpoint
            return JsonResponse({
                'success': False,
                'error': 'No active session. Please start a new survey.',
                'redirect_url': '/simple-surveys/'
            }, status=400)
        else:
            # Regular request
            return redirect(reverse('simple_surveys:home'))
    
    def _handle_invalid_session(self, request, path, error):
        """Handle requests with invalid sessions."""
        logger.info(f"Invalid session for {path}: {error}")
        
        if request.headers.get('Content-Type') == 'application/json' or path.endswith('/'):
            # AJAX request or API endpoint
            return JsonResponse({
                'success': False,
                'error': f'Session validation failed: {error}',
                'redirect_url': '/simple-surveys/'
            }, status=400)
        else:
            # Regular request - redirect to home
            return redirect(reverse('simple_surveys:home'))
    
    def _cleanup_expired_sessions_for_django_session(self, session_key):
        """Clean up expired quotation sessions for a specific Django session."""
        try:
            expired_sessions = QuotationSession.objects.filter(
                session_key=session_key,
                expires_at__lte=timezone.now()
            )
            
            for session in expired_sessions:
                SessionManager._cleanup_expired_session(session)
                
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions for {session_key[:8]}: {e}")


class SessionExtensionMiddleware(MiddlewareMixin):
    """
    Middleware to automatically extend session expiry on activity.
    
    This middleware extends the session expiry time whenever a user
    makes a request to survey-related URLs, keeping active users' sessions alive.
    """
    
    # URLs that should extend session expiry
    ACTIVITY_URLS = [
        '/simple-surveys/save-response/',
        '/simple-surveys/health/',
        '/simple-surveys/funeral/',
        '/simple-surveys/health/status/',
        '/simple-surveys/funeral/status/',
    ]
    
    def process_response(self, request, response):
        """Extend session expiry after successful requests."""
        try:
            path = request.path
            
            # Only extend for survey URLs
            if not any(path.startswith(url) for url in self.ACTIVITY_URLS):
                return response
            
            # Only extend for successful responses
            if response.status_code >= 400:
                return response
            
            # Get session and category
            session_key = request.session.session_key
            if not session_key:
                return response
            
            category = self._extract_category_from_request(request, path)
            if not category:
                return response
            
            # Extend session expiry
            SessionManager.extend_session(session_key, category)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in session extension middleware: {e}")
            return response
    
    def _extract_category_from_request(self, request, path):
        """Extract category from request."""
        # Try path first
        if '/health/' in path:
            return 'health'
        elif '/funeral/' in path:
            return 'funeral'
        
        # Try request data
        if hasattr(request, 'quotation_session'):
            return request.quotation_session.category
        
        return None


class SessionCleanupMiddleware(MiddlewareMixin):
    """
    Middleware to periodically trigger session cleanup.
    
    This middleware triggers automatic cleanup of expired sessions
    on a subset of requests to avoid performance impact.
    """
    
    # Cleanup probability (1 in N requests will trigger cleanup)
    CLEANUP_PROBABILITY = 100
    
    def __init__(self, get_response):
        """Initialize middleware."""
        super().__init__(get_response)
        self._request_count = 0
    
    def process_request(self, request):
        """Periodically trigger session cleanup."""
        try:
            # Only cleanup on survey requests
            if not request.path.startswith('/simple-surveys/'):
                return None
            
            self._request_count += 1
            
            # Trigger cleanup based on probability
            if self._request_count % self.CLEANUP_PROBABILITY == 0:
                logger.info("Triggering periodic session cleanup")
                
                # Run cleanup in background (non-blocking)
                from threading import Thread
                cleanup_thread = Thread(
                    target=self._background_cleanup,
                    daemon=True
                )
                cleanup_thread.start()
            
            return None
            
        except Exception as e:
            logger.error(f"Error in session cleanup middleware: {e}")
            return None
    
    def _background_cleanup(self):
        """Run session cleanup in background."""
        try:
            stats = SessionManager.cleanup_expired_sessions(batch_size=50)
            
            if stats['quotation_sessions_deleted'] > 0:
                logger.info(
                    f"Background cleanup: {stats['quotation_sessions_deleted']} sessions, "
                    f"{stats['responses_deleted']} responses deleted"
                )
            
            if stats['errors']:
                logger.warning(f"Background cleanup errors: {len(stats['errors'])}")
                
        except Exception as e:
            logger.error(f"Error in background session cleanup: {e}")