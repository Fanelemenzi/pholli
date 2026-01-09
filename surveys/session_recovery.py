"""
Session Recovery Utilities for Survey System.
Handles session expiry, data recovery, and session restoration.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session

from comparison.models import ComparisonSession
from policies.models import PolicyCategory
from .models import SurveyResponse, SurveyQuestion
from .session_manager import SurveySessionManager
from .error_handling import SurveySessionError, survey_error_handler

logger = logging.getLogger(__name__)


class SessionRecoveryService:
    """
    Service for handling session recovery operations.
    Provides comprehensive session restoration and data recovery capabilities.
    """
    
    # Cache keys for session recovery data
    RECOVERY_CACHE_PREFIX = 'survey_recovery'
    RECOVERY_CACHE_TIMEOUT = 3600 * 24  # 24 hours
    
    def __init__(self):
        self.session_manager = SurveySessionManager()
    
    def check_session_validity(self, session_key: str, category_slug: str) -> Dict[str, Any]:
        """
        Check if a session is valid and provide recovery options if not.
        
        Args:
            session_key: Session key to check
            category_slug: Policy category slug
            
        Returns:
            Dictionary with session validity status and recovery options
        """
        try:
            # Try to get the session
            session = ComparisonSession.objects.filter(
                session_key=session_key,
                category__slug=category_slug
            ).first()
            
            if not session:
                return {
                    'is_valid': False,
                    'status': 'not_found',
                    'message': 'Session not found',
                    'recovery_options': ['create_new'],
                    'can_recover': False
                }
            
            # Check if session is expired
            if session.expires_at and session.expires_at < timezone.now():
                # Check if we can recover data
                recovery_data = self._assess_recovery_potential(session)
                
                return {
                    'is_valid': False,
                    'status': 'expired',
                    'message': 'Session has expired',
                    'expired_at': session.expires_at.isoformat(),
                    'recovery_options': recovery_data['recovery_options'],
                    'can_recover': recovery_data['can_recover'],
                    'recovery_data': recovery_data
                }
            
            # Check session status
            if session.status != ComparisonSession.Status.ACTIVE:
                return {
                    'is_valid': False,
                    'status': session.status.lower(),
                    'message': f'Session is {session.status.lower()}',
                    'recovery_options': ['create_new'],
                    'can_recover': False
                }
            
            # Session is valid
            return {
                'is_valid': True,
                'status': 'active',
                'message': 'Session is valid',
                'session': session,
                'expires_at': session.expires_at.isoformat() if session.expires_at else None
            }
            
        except Exception as e:
            logger.error(f"Error checking session validity for {session_key}: {str(e)}")
            return {
                'is_valid': False,
                'status': 'error',
                'message': 'Error checking session validity',
                'error': str(e),
                'recovery_options': ['create_new'],
                'can_recover': False
            }
    
    def _assess_recovery_potential(self, session: ComparisonSession) -> Dict[str, Any]:
        """
        Assess the potential for recovering data from an expired session.
        
        Args:
            session: Expired ComparisonSession instance
            
        Returns:
            Dictionary with recovery assessment
        """
        try:
            # Get existing responses
            responses = SurveyResponse.objects.filter(session=session)
            response_count = responses.count()
            
            if response_count == 0:
                return {
                    'can_recover': False,
                    'recovery_options': ['create_new'],
                    'reason': 'No responses to recover'
                }
            
            # Calculate how much data we have
            total_questions = SurveyQuestion.objects.filter(
                category=session.category,
                is_active=True
            ).count()
            
            completion_percentage = (response_count / total_questions * 100) if total_questions > 0 else 0
            
            # Determine recovery options based on data amount
            recovery_options = ['create_new']
            
            if completion_percentage > 10:  # At least 10% complete
                recovery_options.insert(0, 'recover_responses')
            
            if completion_percentage > 50:  # More than 50% complete
                recovery_options.insert(0, 'recover_and_continue')
            
            # Check how recently the session was active
            time_since_expiry = timezone.now() - session.expires_at
            recently_expired = time_since_expiry.total_seconds() < 3600  # Less than 1 hour
            
            return {
                'can_recover': response_count > 0,
                'recovery_options': recovery_options,
                'response_count': response_count,
                'completion_percentage': completion_percentage,
                'recently_expired': recently_expired,
                'time_since_expiry_hours': time_since_expiry.total_seconds() / 3600,
                'recommendation': self._get_recovery_recommendation(
                    completion_percentage, recently_expired, response_count
                )
            }
            
        except Exception as e:
            logger.error(f"Error assessing recovery potential: {str(e)}")
            return {
                'can_recover': False,
                'recovery_options': ['create_new'],
                'error': str(e)
            }
    
    def _get_recovery_recommendation(
        self, 
        completion_percentage: float, 
        recently_expired: bool, 
        response_count: int
    ) -> str:
        """Get recovery recommendation based on session data."""
        if completion_percentage > 75:
            return 'recover_and_continue'
        elif completion_percentage > 25 and recently_expired:
            return 'recover_responses'
        elif response_count > 5:
            return 'recover_responses'
        else:
            return 'create_new'
    
    def recover_session_data(
        self, 
        expired_session_key: str, 
        category_slug: str,
        user=None
    ) -> Dict[str, Any]:
        """
        Recover data from an expired session and create a new active session.
        
        Args:
            expired_session_key: Key of the expired session
            category_slug: Policy category slug
            user: User instance if authenticated
            
        Returns:
            Recovery result with new session information
        """
        try:
            # Find the expired session
            expired_session = ComparisonSession.objects.filter(
                session_key=expired_session_key,
                category__slug=category_slug
            ).first()
            
            if not expired_session:
                raise SurveySessionError(
                    "Original session not found",
                    session_key=expired_session_key
                )
            
            # Get existing responses
            existing_responses = SurveyResponse.objects.filter(
                session=expired_session
            ).select_related('question').order_by('created_at')
            
            if not existing_responses.exists():
                return {
                    'success': False,
                    'error': 'No responses found to recover',
                    'action': 'create_new_session'
                }
            
            # Create new session
            category = PolicyCategory.objects.get(slug=category_slug)
            new_session = ComparisonSession.objects.create(
                user=user,
                category=category,
                status=ComparisonSession.Status.ACTIVE,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
            # Copy responses to new session
            recovered_responses = []
            failed_responses = []
            
            with transaction.atomic():
                for old_response in existing_responses:
                    try:
                        new_response = SurveyResponse.objects.create(
                            session=new_session,
                            question=old_response.question,
                            response_value=old_response.response_value,
                            confidence_level=old_response.confidence_level
                        )
                        recovered_responses.append({
                            'question_id': old_response.question.id,
                            'question_text': old_response.question.question_text[:50] + '...',
                            'response_value': old_response.response_value,
                            'original_date': old_response.created_at.isoformat()
                        })
                    except Exception as e:
                        failed_responses.append({
                            'question_id': old_response.question.id,
                            'error': str(e)
                        })
                        logger.warning(f"Failed to recover response for question {old_response.question.id}: {str(e)}")
            
            # Update session progress
            from .engine import SurveyEngine
            engine = SurveyEngine(category_slug)
            completion_percentage = engine.calculate_completion_percentage(new_session)
            
            new_session.update_survey_progress(
                responses_count=len(recovered_responses),
                completion_percentage=completion_percentage
            )
            
            # Cache recovery information for user notification
            recovery_info = {
                'recovered_count': len(recovered_responses),
                'failed_count': len(failed_responses),
                'completion_percentage': completion_percentage,
                'recovery_timestamp': timezone.now().isoformat(),
                'original_session_key': expired_session_key
            }
            
            cache_key = f"{self.RECOVERY_CACHE_PREFIX}:{new_session.session_key}"
            cache.set(cache_key, recovery_info, self.RECOVERY_CACHE_TIMEOUT)
            
            return {
                'success': True,
                'new_session_key': new_session.session_key,
                'recovered_responses': recovered_responses,
                'failed_responses': failed_responses,
                'completion_percentage': completion_percentage,
                'recovery_info': recovery_info,
                'message': f'Successfully recovered {len(recovered_responses)} responses'
            }
            
        except Exception as e:
            error_response = survey_error_handler.handle_session_error(
                e, expired_session_key, {'category_slug': category_slug}
            )
            return error_response
    
    def get_recovery_info(self, session_key: str) -> Optional[Dict[str, Any]]:
        """
        Get recovery information for a session if it was recovered.
        
        Args:
            session_key: Session key to check for recovery info
            
        Returns:
            Recovery information dictionary or None
        """
        cache_key = f"{self.RECOVERY_CACHE_PREFIX}:{session_key}"
        return cache.get(cache_key)
    
    def clear_recovery_info(self, session_key: str):
        """Clear recovery information from cache."""
        cache_key = f"{self.RECOVERY_CACHE_PREFIX}:{session_key}"
        cache.delete(cache_key)
    
    def extend_session_expiry(
        self, 
        session_key: str, 
        hours: int = 24,
        reason: str = 'user_request'
    ) -> Dict[str, Any]:
        """
        Extend session expiry time.
        
        Args:
            session_key: Session key to extend
            hours: Number of hours to extend
            reason: Reason for extension
            
        Returns:
            Extension result
        """
        try:
            session = ComparisonSession.objects.get(session_key=session_key)
            
            old_expiry = session.expires_at
            new_expiry = timezone.now() + timedelta(hours=hours)
            
            session.expires_at = new_expiry
            session.save(update_fields=['expires_at', 'updated_at'])
            
            logger.info(f"Extended session {session_key} expiry from {old_expiry} to {new_expiry} (reason: {reason})")
            
            return {
                'success': True,
                'old_expiry': old_expiry.isoformat() if old_expiry else None,
                'new_expiry': new_expiry.isoformat(),
                'extended_hours': hours,
                'reason': reason
            }
            
        except ComparisonSession.DoesNotExist:
            return {
                'success': False,
                'error': 'Session not found'
            }
        except Exception as e:
            logger.error(f"Error extending session {session_key}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_expired_sessions(self, days_old: int = 7) -> Dict[str, Any]:
        """
        Clean up expired sessions older than specified days.
        
        Args:
            days_old: Number of days old to consider for cleanup
            
        Returns:
            Cleanup result statistics
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=days_old)
            
            # Find expired sessions to clean up
            expired_sessions = ComparisonSession.objects.filter(
                expires_at__lt=cutoff_date,
                status=ComparisonSession.Status.ACTIVE
            )
            
            session_count = expired_sessions.count()
            
            # Get response count before deletion
            response_count = SurveyResponse.objects.filter(
                session__in=expired_sessions
            ).count()
            
            # Mark sessions as expired (don't delete, for audit trail)
            updated_count = expired_sessions.update(
                status=ComparisonSession.Status.EXPIRED,
                updated_at=timezone.now()
            )
            
            logger.info(f"Cleaned up {updated_count} expired sessions with {response_count} responses")
            
            return {
                'success': True,
                'sessions_cleaned': updated_count,
                'responses_affected': response_count,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_session_backup(self, session: ComparisonSession) -> Dict[str, Any]:
        """
        Create a backup of session data for recovery purposes.
        
        Args:
            session: ComparisonSession to backup
            
        Returns:
            Backup creation result
        """
        try:
            # Get all responses for the session
            responses = SurveyResponse.objects.filter(
                session=session
            ).select_related('question')
            
            # Create backup data structure
            backup_data = {
                'session_key': session.session_key,
                'category_slug': session.category.slug,
                'user_id': session.user.id if session.user else None,
                'created_at': session.created_at.isoformat(),
                'expires_at': session.expires_at.isoformat() if session.expires_at else None,
                'status': session.status,
                'survey_completed': session.survey_completed,
                'completion_percentage': session.survey_completion_percentage,
                'responses': []
            }
            
            # Add response data
            for response in responses:
                backup_data['responses'].append({
                    'question_id': response.question.id,
                    'field_name': response.question.field_name,
                    'question_text': response.question.question_text,
                    'response_value': response.response_value,
                    'confidence_level': response.confidence_level,
                    'created_at': response.created_at.isoformat(),
                    'updated_at': response.updated_at.isoformat()
                })
            
            # Store backup in cache with extended timeout
            backup_key = f"session_backup:{session.session_key}:{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            cache.set(backup_key, backup_data, timeout=self.RECOVERY_CACHE_TIMEOUT * 7)  # 7 days
            
            return {
                'success': True,
                'backup_key': backup_key,
                'response_count': len(backup_data['responses']),
                'backup_timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating session backup: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def restore_from_backup(self, backup_key: str, user=None) -> Dict[str, Any]:
        """
        Restore session from backup data.
        
        Args:
            backup_key: Backup key to restore from
            user: User instance if authenticated
            
        Returns:
            Restoration result
        """
        try:
            # Get backup data from cache
            backup_data = cache.get(backup_key)
            if not backup_data:
                return {
                    'success': False,
                    'error': 'Backup data not found or expired'
                }
            
            # Create new session
            category = PolicyCategory.objects.get(slug=backup_data['category_slug'])
            new_session = ComparisonSession.objects.create(
                user=user,
                category=category,
                status=ComparisonSession.Status.ACTIVE,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
            # Restore responses
            restored_count = 0
            failed_count = 0
            
            with transaction.atomic():
                for response_data in backup_data['responses']:
                    try:
                        question = SurveyQuestion.objects.get(
                            id=response_data['question_id'],
                            category=category
                        )
                        
                        SurveyResponse.objects.create(
                            session=new_session,
                            question=question,
                            response_value=response_data['response_value'],
                            confidence_level=response_data['confidence_level']
                        )
                        restored_count += 1
                        
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to restore response: {str(e)}")
            
            # Update session progress
            from .engine import SurveyEngine
            engine = SurveyEngine(backup_data['category_slug'])
            completion_percentage = engine.calculate_completion_percentage(new_session)
            
            new_session.update_survey_progress(
                responses_count=restored_count,
                completion_percentage=completion_percentage
            )
            
            return {
                'success': True,
                'new_session_key': new_session.session_key,
                'restored_responses': restored_count,
                'failed_responses': failed_count,
                'completion_percentage': completion_percentage,
                'message': f'Restored {restored_count} responses from backup'
            }
            
        except Exception as e:
            logger.error(f"Error restoring from backup {backup_key}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class SessionExpiryHandler:
    """
    Handles session expiry notifications and automatic extensions.
    """
    
    def __init__(self):
        self.recovery_service = SessionRecoveryService()
    
    def check_session_expiry_warning(self, session: ComparisonSession) -> Dict[str, Any]:
        """
        Check if session is approaching expiry and needs warning.
        
        Args:
            session: ComparisonSession to check
            
        Returns:
            Warning information if session is approaching expiry
        """
        if not session.expires_at:
            return {'needs_warning': False}
        
        time_until_expiry = session.expires_at - timezone.now()
        minutes_until_expiry = time_until_expiry.total_seconds() / 60
        
        # Warning thresholds
        if minutes_until_expiry <= 5:
            return {
                'needs_warning': True,
                'urgency': 'critical',
                'minutes_remaining': int(minutes_until_expiry),
                'message': f'Your session will expire in {int(minutes_until_expiry)} minutes',
                'suggested_action': 'extend_session'
            }
        elif minutes_until_expiry <= 15:
            return {
                'needs_warning': True,
                'urgency': 'high',
                'minutes_remaining': int(minutes_until_expiry),
                'message': f'Your session will expire in {int(minutes_until_expiry)} minutes',
                'suggested_action': 'save_progress'
            }
        elif minutes_until_expiry <= 30:
            return {
                'needs_warning': True,
                'urgency': 'medium',
                'minutes_remaining': int(minutes_until_expiry),
                'message': f'Your session will expire in {int(minutes_until_expiry)} minutes',
                'suggested_action': 'continue_survey'
            }
        
        return {'needs_warning': False}
    
    def handle_session_expiry(self, session_key: str, category_slug: str) -> Dict[str, Any]:
        """
        Handle expired session with recovery options.
        
        Args:
            session_key: Expired session key
            category_slug: Policy category slug
            
        Returns:
            Expiry handling result with recovery options
        """
        validity_check = self.recovery_service.check_session_validity(session_key, category_slug)
        
        if validity_check['is_valid']:
            return {
                'action': 'continue',
                'message': 'Session is still valid'
            }
        
        if validity_check['status'] == 'expired' and validity_check['can_recover']:
            return {
                'action': 'offer_recovery',
                'recovery_options': validity_check['recovery_options'],
                'recovery_data': validity_check.get('recovery_data', {}),
                'message': 'Your session has expired, but we can recover your progress'
            }
        
        return {
            'action': 'create_new',
            'message': 'Your session has expired. Please start a new survey'
        }


# Global instances
session_recovery_service = SessionRecoveryService()
session_expiry_handler = SessionExpiryHandler()