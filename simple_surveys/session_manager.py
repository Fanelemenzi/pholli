"""
Session management utilities for simple surveys.
Handles session creation, validation, expiry, and cleanup.
"""

from django.utils import timezone
from django.contrib.sessions.models import Session
from django.db import transaction
from datetime import timedelta
import logging

from .models import QuotationSession, SimpleSurveyResponse

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages survey sessions with 24-hour expiry and automatic cleanup.
    Handles session creation, validation, and data cleanup for anonymous users.
    """
    
    SESSION_LIFETIME_HOURS = 24
    
    @classmethod
    def create_or_get_session(cls, request, category):
        """
        Create or get an active session for the given category.
        
        Args:
            request: Django request object
            category: Survey category ('health' or 'funeral')
            
        Returns:
            tuple: (QuotationSession, created_flag)
            
        Raises:
            ValueError: If category is invalid
        """
        if category not in ['health', 'funeral']:
            raise ValueError(f"Invalid category: {category}")
        
        # Ensure Django session exists
        if not request.session.session_key:
            request.session.create()
        
        session_key = request.session.session_key
        
        try:
            with transaction.atomic():
                # Try to get existing active session
                quotation_session = QuotationSession.objects.filter(
                    session_key=session_key,
                    category=category
                ).first()
                
                if quotation_session:
                    if quotation_session.is_expired():
                        # Session expired, clean it up and create new one
                        cls._cleanup_expired_session(quotation_session)
                        quotation_session = cls._create_new_session(session_key, category)
                        created = True
                    else:
                        # Extend expiry for active session
                        quotation_session.extend_expiry(cls.SESSION_LIFETIME_HOURS)
                        created = False
                else:
                    # Create new session
                    quotation_session = cls._create_new_session(session_key, category)
                    created = True
                
                return quotation_session, created
                
        except Exception as e:
            logger.error(f"Error creating/getting session for {category}: {e}")
            raise
    
    @classmethod
    def _create_new_session(cls, session_key, category):
        """Create a new quotation session with proper expiry."""
        expires_at = timezone.now() + timedelta(hours=cls.SESSION_LIFETIME_HOURS)
        return QuotationSession.objects.create(
            session_key=session_key,
            category=category,
            expires_at=expires_at
        )
    
    @classmethod
    def validate_session(cls, session_key, category=None):
        """
        Validate that a session exists and is not expired.
        
        Args:
            session_key: Session key to validate
            category: Optional category to validate against
            
        Returns:
            dict: Validation result with 'valid' flag and 'session' if valid
        """
        try:
            # Check if Django session exists
            try:
                django_session = Session.objects.get(session_key=session_key)
                if django_session.expire_date < timezone.now():
                    return {
                        'valid': False,
                        'error': 'Django session expired',
                        'session': None
                    }
            except Session.DoesNotExist:
                return {
                    'valid': False,
                    'error': 'Django session not found',
                    'session': None
                }
            
            # Check quotation session
            quotation_sessions = QuotationSession.objects.filter(session_key=session_key)
            
            if category:
                quotation_sessions = quotation_sessions.filter(category=category)
            
            quotation_session = quotation_sessions.first()
            
            if not quotation_session:
                return {
                    'valid': False,
                    'error': 'Quotation session not found',
                    'session': None
                }
            
            if quotation_session.is_expired():
                return {
                    'valid': False,
                    'error': 'Quotation session expired',
                    'session': quotation_session
                }
            
            return {
                'valid': True,
                'error': None,
                'session': quotation_session
            }
            
        except Exception as e:
            logger.error(f"Error validating session {session_key}: {e}")
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}',
                'session': None
            }
    
    @classmethod
    def cleanup_expired_sessions(cls, batch_size=100):
        """
        Clean up expired sessions and their associated data.
        
        Args:
            batch_size: Number of sessions to process in each batch
            
        Returns:
            dict: Cleanup statistics
        """
        stats = {
            'quotation_sessions_deleted': 0,
            'responses_deleted': 0,
            'django_sessions_deleted': 0,
            'errors': []
        }
        
        try:
            # Get expired quotation sessions in batches
            expired_sessions = QuotationSession.objects.expired_sessions()[:batch_size]
            
            for session in expired_sessions:
                try:
                    with transaction.atomic():
                        # Count responses before deletion
                        response_count = SimpleSurveyResponse.objects.filter(
                            session_key=session.session_key,
                            category=session.category
                        ).count()
                        
                        # Delete associated responses
                        SimpleSurveyResponse.objects.filter(
                            session_key=session.session_key,
                            category=session.category
                        ).delete()
                        
                        # Delete quotation session
                        session.delete()
                        
                        stats['quotation_sessions_deleted'] += 1
                        stats['responses_deleted'] += response_count
                        
                        logger.info(f"Cleaned up expired session {session.session_key[:8]} "
                                  f"with {response_count} responses")
                        
                except Exception as e:
                    error_msg = f"Error cleaning up session {session.session_key[:8]}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Clean up expired Django sessions
            try:
                expired_django_sessions = Session.objects.filter(
                    expire_date__lt=timezone.now()
                )
                
                # Count before deletion
                django_count = expired_django_sessions.count()
                
                # Delete in batches to avoid issues with limit/offset
                session_keys = list(expired_django_sessions.values_list('session_key', flat=True)[:batch_size])
                if session_keys:
                    Session.objects.filter(session_key__in=session_keys).delete()
                    stats['django_sessions_deleted'] = len(session_keys)
                
                if stats['django_sessions_deleted'] > 0:
                    logger.info(f"Cleaned up {stats['django_sessions_deleted']} expired Django sessions")
                    
            except Exception as e:
                error_msg = f"Error cleaning up Django sessions: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
            
            return stats
            
        except Exception as e:
            error_msg = f"Error during session cleanup: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
    
    @classmethod
    def _cleanup_expired_session(cls, quotation_session):
        """Clean up a single expired session and its data."""
        try:
            with transaction.atomic():
                # Delete associated responses
                SimpleSurveyResponse.objects.filter(
                    session_key=quotation_session.session_key,
                    category=quotation_session.category
                ).delete()
                
                # Delete the session
                quotation_session.delete()
                
                logger.info(f"Cleaned up expired session {quotation_session.session_key[:8]}")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired session {quotation_session.session_key[:8]}: {e}")
            raise
    
    @classmethod
    def get_session_stats(cls):
        """
        Get statistics about current sessions.
        
        Returns:
            dict: Session statistics
        """
        try:
            now = timezone.now()
            
            # Quotation session stats
            total_quotation_sessions = QuotationSession.objects.count()
            active_quotation_sessions = QuotationSession.objects.active_sessions().count()
            expired_quotation_sessions = QuotationSession.objects.expired_sessions().count()
            completed_sessions = QuotationSession.objects.completed_sessions().count()
            
            # Response stats
            total_responses = SimpleSurveyResponse.objects.count()
            
            # Django session stats
            total_django_sessions = Session.objects.count()
            expired_django_sessions = Session.objects.filter(expire_date__lt=now).count()
            
            return {
                'quotation_sessions': {
                    'total': total_quotation_sessions,
                    'active': active_quotation_sessions,
                    'expired': expired_quotation_sessions,
                    'completed': completed_sessions
                },
                'responses': {
                    'total': total_responses
                },
                'django_sessions': {
                    'total': total_django_sessions,
                    'expired': expired_django_sessions
                },
                'timestamp': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    @classmethod
    def cleanup_expired_sessions_for_django_session(cls, session_key):
        """
        Clean up expired quotation sessions for a specific Django session.
        
        Args:
            session_key: Django session key to clean up
        """
        try:
            expired_sessions = QuotationSession.objects.filter(
                session_key=session_key,
                expires_at__lte=timezone.now()
            )
            
            for session in expired_sessions:
                cls._cleanup_expired_session(session)
                
            logger.info(f"Cleaned up {expired_sessions.count()} expired sessions for Django session {session_key[:8]}")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions for Django session {session_key[:8]}: {e}")
            raise
    
    @classmethod
    def extend_session(cls, session_key, category, hours=None):
        """
        Extend the expiry time for a session.
        
        Args:
            session_key: Session key to extend
            category: Session category
            hours: Hours to extend (default: SESSION_LIFETIME_HOURS)
            
        Returns:
            bool: True if extended successfully, False otherwise
        """
        if hours is None:
            hours = cls.SESSION_LIFETIME_HOURS
        
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


class SessionValidationError(Exception):
    """Exception raised when session validation fails."""
    pass


def require_valid_session(category=None):
    """
    Decorator to require a valid session for a view.
    
    Args:
        category: Optional category to validate against
        
    Usage:
        @require_valid_session('health')
        def my_view(request):
            # Session is guaranteed to be valid
            pass
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            session_key = request.session.session_key
            
            if not session_key:
                raise SessionValidationError("No active session")
            
            validation_result = SessionManager.validate_session(session_key, category)
            
            if not validation_result['valid']:
                raise SessionValidationError(validation_result['error'])
            
            # Add session to request for convenience
            request.quotation_session = validation_result['session']
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator