"""
Simplified Session Management for Simple Surveys
Automatically handles survey modifications and generates new keys when needed.
"""

import uuid
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.sessions.models import Session

from .models import QuotationSession, SimpleSurveyResponse

logger = logging.getLogger(__name__)


class SimpleSessionManager:
    """
    Simplified session manager that automatically handles survey modifications.
    Key features:
    - Generates new session keys when survey is modified
    - Listens to survey changes and invalidates old sessions
    - Simple API with automatic error recovery
    """
    
    SESSION_LIFETIME_HOURS = 24
    
    @classmethod
    def get_or_create_session(cls, request, category):
        """
        Get or create a session for the given category.
        Always returns a valid session, creating one if needed.
        
        Args:
            request: Django request object
            category: Survey category ('health' or 'funeral')
            
        Returns:
            QuotationSession: Valid session instance
        """
        if category not in ['health', 'funeral']:
            raise ValueError(f"Invalid category: {category}")
        
        # Ensure Django session exists
        if not request.session.session_key:
            request.session.create()
        
        # Check if we have a valid session stored in Django session
        session_data_key = f'survey_session_{category}'
        stored_session_key = request.session.get(session_data_key)
        
        if stored_session_key:
            # Try to get existing session
            try:
                quotation_session = QuotationSession.objects.get(
                    session_key=stored_session_key,
                    category=category
                )
                
                if not quotation_session.is_expired():
                    logger.debug(f"Using existing session {stored_session_key[:8]} for {category}")
                    return quotation_session
                else:
                    logger.info(f"Session {stored_session_key[:8]} expired, creating new one")
                    
            except QuotationSession.DoesNotExist:
                logger.info(f"Stored session {stored_session_key[:8]} not found, creating new one")
        
        # Create new session
        return cls._create_new_session(request, category)
    
    @classmethod
    def _create_new_session(cls, request, category):
        """Create a new session and store it in Django session."""
        # Generate unique session key
        new_session_key = str(uuid.uuid4())
        
        try:
            with transaction.atomic():
                # Create new quotation session
                expires_at = timezone.now() + timedelta(hours=cls.SESSION_LIFETIME_HOURS)
                quotation_session = QuotationSession.objects.create(
                    session_key=new_session_key,
                    category=category,
                    expires_at=expires_at
                )
                
                # Store session key in Django session
                session_data_key = f'survey_session_{category}'
                request.session[session_data_key] = new_session_key
                request.session.save()
                
                logger.info(f"Created new session {new_session_key[:8]} for {category}")
                return quotation_session
                
        except Exception as e:
            logger.error(f"Error creating session for {category}: {e}")
            raise
    
    @classmethod
    def invalidate_session_on_modification(cls, request, category):
        """
        Invalidate current session when survey is modified.
        This forces creation of a new session for fresh results.
        
        Args:
            request: Django request object
            category: Survey category
        """
        session_data_key = f'survey_session_{category}'
        stored_session_key = request.session.get(session_data_key)
        
        if stored_session_key:
            try:
                # Mark old session as expired
                QuotationSession.objects.filter(
                    session_key=stored_session_key,
                    category=category
                ).update(expires_at=timezone.now())
                
                # Remove from Django session
                del request.session[session_data_key]
                request.session.save()
                
                logger.info(f"Invalidated session {stored_session_key[:8]} due to survey modification")
                
            except Exception as e:
                logger.error(f"Error invalidating session: {e}")
    
    @classmethod
    def get_session_key(cls, request, category):
        """
        Get the current session key for a category.
        
        Args:
            request: Django request object
            category: Survey category
            
        Returns:
            str: Session key or None if no session exists
        """
        session_data_key = f'survey_session_{category}'
        return request.session.get(session_data_key)
    
    @classmethod
    def ensure_fresh_session_for_results(cls, request, category):
        """
        Ensure we have a fresh session for generating results.
        This is called when user completes survey and wants quotes.
        
        Args:
            request: Django request object
            category: Survey category
            
        Returns:
            QuotationSession: Fresh session for results
        """
        # Always create a new session for results to avoid stale data
        cls.invalidate_session_on_modification(request, category)
        return cls.get_or_create_session(request, category)
    
    @classmethod
    def cleanup_expired_sessions(cls, batch_size=100):
        """
        Clean up expired sessions and their data.
        
        Args:
            batch_size: Number of sessions to process
            
        Returns:
            dict: Cleanup statistics
        """
        stats = {
            'sessions_deleted': 0,
            'responses_deleted': 0,
            'errors': []
        }
        
        try:
            # Get expired sessions
            expired_sessions = QuotationSession.objects.filter(
                expires_at__lt=timezone.now()
            )[:batch_size]
            
            for session in expired_sessions:
                try:
                    with transaction.atomic():
                        # Count and delete responses
                        response_count = SimpleSurveyResponse.objects.filter(
                            session_key=session.session_key,
                            category=session.category
                        ).count()
                        
                        SimpleSurveyResponse.objects.filter(
                            session_key=session.session_key,
                            category=session.category
                        ).delete()
                        
                        # Delete session
                        session.delete()
                        
                        stats['sessions_deleted'] += 1
                        stats['responses_deleted'] += response_count
                        
                        logger.debug(f"Cleaned up expired session {session.session_key[:8]}")
                        
                except Exception as e:
                    error_msg = f"Error cleaning up session {session.session_key[:8]}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            if stats['sessions_deleted'] > 0:
                logger.info(f"Cleaned up {stats['sessions_deleted']} expired sessions")
            
            return stats
            
        except Exception as e:
            error_msg = f"Error during cleanup: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
    
    @classmethod
    def extend_session(cls, request, category, hours=None):
        """
        Extend session expiry time.
        
        Args:
            request: Django request object
            category: Survey category
            hours: Hours to extend (default: SESSION_LIFETIME_HOURS)
            
        Returns:
            bool: True if extended successfully
        """
        if hours is None:
            hours = cls.SESSION_LIFETIME_HOURS
        
        session_key = cls.get_session_key(request, category)
        if not session_key:
            return False
        
        try:
            quotation_session = QuotationSession.objects.get(
                session_key=session_key,
                category=category
            )
            
            quotation_session.extend_expiry(hours)
            logger.info(f"Extended session {session_key[:8]} by {hours} hours")
            return True
            
        except QuotationSession.DoesNotExist:
            logger.warning(f"Attempted to extend non-existent session {session_key[:8]}")
            return False
        except Exception as e:
            logger.error(f"Error extending session {session_key[:8]}: {e}")
            return False


# Middleware to automatically handle session modifications
class SurveyModificationMiddleware:
    """
    Middleware that detects survey modifications and invalidates sessions.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is a survey modification request
        if self._is_survey_modification(request):
            category = self._extract_category(request)
            if category:
                SimpleSessionManager.invalidate_session_on_modification(request, category)
        
        response = self.get_response(request)
        return response
    
    def _is_survey_modification(self, request):
        """Check if this request modifies survey data."""
        if request.method != 'POST':
            return False
        
        # Check URL patterns that indicate survey modification
        survey_modification_patterns = [
            '/simple-surveys/save-response/',
            '/simple-surveys/feature-survey/',
            '/surveys/save-response/',
        ]
        
        return any(pattern in request.path for pattern in survey_modification_patterns)
    
    def _extract_category(self, request):
        """Extract category from request."""
        # Try to get category from URL
        if '/health/' in request.path:
            return 'health'
        elif '/funeral/' in request.path:
            return 'funeral'
        
        # Try to get from POST data
        return request.POST.get('category')


# Simple decorator for views that need sessions
def with_survey_session(category=None):
    """
    Decorator that ensures a valid survey session exists.
    Works with both function-based and class-based views.
    
    Args:
        category: Fixed category, or None to extract from view kwargs
    """
    def decorator(view_func):
        def wrapper(*args, **kwargs):
            # Determine if this is a class-based view method or function-based view
            if len(args) >= 2 and hasattr(args[0], '__class__') and hasattr(args[1], 'method'):
                # Class-based view: args[0] is self, args[1] is request
                view_instance = args[0]
                request = args[1]
                view_args = args[2:]
                is_class_based = True
            elif len(args) >= 1 and hasattr(args[0], 'method'):
                # Function-based view: args[0] is request
                view_instance = None
                request = args[0]
                view_args = args[1:]
                is_class_based = False
            else:
                raise ValueError("Unable to identify request object in view arguments")
            
            # Get category from decorator or view kwargs
            session_category = category or kwargs.get('category')
            
            if not session_category:
                raise ValueError("Category must be provided either in decorator or view kwargs")
            
            # Ensure session exists
            quotation_session = SimpleSessionManager.get_or_create_session(request, session_category)
            
            # Add to request for convenience
            request.survey_session = quotation_session
            request.survey_session_key = quotation_session.session_key
            
            # Call the original view function
            if is_class_based:
                return view_func(view_instance, request, *view_args, **kwargs)
            else:
                return view_func(request, *view_args, **kwargs)
        
        return wrapper
    return decorator