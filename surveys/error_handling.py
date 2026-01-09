"""
Comprehensive Error Handling and Recovery for Survey System.
Provides error handling for validation failures, session expiry, incomplete data,
and fallback mechanisms for survey processing failures.
"""

import logging
import traceback
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.conf import settings

from comparison.models import ComparisonSession
from policies.models import PolicyCategory
from .models import SurveyQuestion, SurveyResponse, SurveyTemplate
from .engine import SurveyEngine
from .session_manager import SurveySessionManager

logger = logging.getLogger(__name__)


class SurveyError(Exception):
    """Base exception for survey-related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code or 'SURVEY_ERROR'
        self.details = details or {}
        super().__init__(self.message)


class SurveyValidationError(SurveyError):
    """Exception for survey validation failures."""
    
    def __init__(self, message: str, field_errors: Dict = None, **kwargs):
        self.field_errors = field_errors or {}
        super().__init__(message, error_code='VALIDATION_ERROR', **kwargs)


class SurveySessionError(SurveyError):
    """Exception for survey session-related errors."""
    
    def __init__(self, message: str, session_key: str = None, **kwargs):
        self.session_key = session_key
        super().__init__(message, error_code='SESSION_ERROR', **kwargs)


class SurveyProcessingError(SurveyError):
    """Exception for survey processing failures."""
    
    def __init__(self, message: str, processing_stage: str = None, **kwargs):
        self.processing_stage = processing_stage
        super().__init__(message, error_code='PROCESSING_ERROR', **kwargs)


class SurveyErrorHandler:
    """
    Centralized error handling for survey operations.
    Provides consistent error responses and recovery mechanisms.
    """
    
    # Error severity levels
    SEVERITY_LOW = 'low'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_HIGH = 'high'
    SEVERITY_CRITICAL = 'critical'
    
    # Error categories
    CATEGORY_VALIDATION = 'validation'
    CATEGORY_SESSION = 'session'
    CATEGORY_PROCESSING = 'processing'
    CATEGORY_SYSTEM = 'system'
    
    def __init__(self):
        self.error_log = []
    
    def handle_validation_error(
        self,
        error: Union[ValidationError, SurveyValidationError, Exception],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle survey validation errors with detailed field-level feedback.
        
        Args:
            error: Validation error instance
            context: Additional context information
            
        Returns:
            Standardized error response dictionary
        """
        context = context or {}
        
        if isinstance(error, SurveyValidationError):
            error_response = {
                'success': False,
                'error_type': 'validation_error',
                'error_code': error.error_code,
                'message': error.message,
                'field_errors': error.field_errors,
                'details': error.details,
                'severity': self.SEVERITY_MEDIUM,
                'category': self.CATEGORY_VALIDATION,
                'recoverable': True,
                'recovery_suggestions': self._get_validation_recovery_suggestions(error)
            }
        elif isinstance(error, ValidationError):
            # Handle Django ValidationError
            field_errors = {}
            if hasattr(error, 'error_dict'):
                # Field-specific errors
                for field, errors in error.error_dict.items():
                    field_errors[field] = [str(e) for e in errors]
            elif hasattr(error, 'error_list'):
                # Non-field errors
                field_errors['__all__'] = [str(e) for e in error.error_list]
            else:
                field_errors['__all__'] = [str(error)]
            
            error_response = {
                'success': False,
                'error_type': 'validation_error',
                'error_code': 'DJANGO_VALIDATION_ERROR',
                'message': 'Validation failed',
                'field_errors': field_errors,
                'details': context,
                'severity': self.SEVERITY_MEDIUM,
                'category': self.CATEGORY_VALIDATION,
                'recoverable': True,
                'recovery_suggestions': self._get_generic_validation_recovery_suggestions()
            }
        else:
            # Generic exception
            error_response = {
                'success': False,
                'error_type': 'validation_error',
                'error_code': 'UNKNOWN_VALIDATION_ERROR',
                'message': str(error),
                'field_errors': {'__all__': [str(error)]},
                'details': context,
                'severity': self.SEVERITY_HIGH,
                'category': self.CATEGORY_VALIDATION,
                'recoverable': False,
                'recovery_suggestions': []
            }
        
        # Log the error
        self._log_error(error_response, error, context)
        
        return error_response
    
    def handle_session_error(
        self,
        error: Union[SurveySessionError, Exception],
        session_key: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle session-related errors with recovery options.
        
        Args:
            error: Session error instance
            session_key: Session key if available
            context: Additional context information
            
        Returns:
            Standardized error response dictionary
        """
        context = context or {}
        session_key = session_key or getattr(error, 'session_key', None)
        
        if isinstance(error, SurveySessionError):
            error_response = {
                'success': False,
                'error_type': 'session_error',
                'error_code': error.error_code,
                'message': error.message,
                'session_key': session_key,
                'details': error.details,
                'severity': self.SEVERITY_HIGH,
                'category': self.CATEGORY_SESSION,
                'recoverable': True,
                'recovery_suggestions': self._get_session_recovery_suggestions(error, session_key)
            }
        else:
            error_response = {
                'success': False,
                'error_type': 'session_error',
                'error_code': 'UNKNOWN_SESSION_ERROR',
                'message': str(error),
                'session_key': session_key,
                'details': context,
                'severity': self.SEVERITY_HIGH,
                'category': self.CATEGORY_SESSION,
                'recoverable': False,
                'recovery_suggestions': []
            }
        
        # Log the error
        self._log_error(error_response, error, context)
        
        return error_response
    
    def handle_processing_error(
        self,
        error: Union[SurveyProcessingError, Exception],
        processing_stage: str = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle survey processing errors with fallback options.
        
        Args:
            error: Processing error instance
            processing_stage: Stage where error occurred
            context: Additional context information
            
        Returns:
            Standardized error response dictionary
        """
        context = context or {}
        processing_stage = processing_stage or getattr(error, 'processing_stage', 'unknown')
        
        if isinstance(error, SurveyProcessingError):
            error_response = {
                'success': False,
                'error_type': 'processing_error',
                'error_code': error.error_code,
                'message': error.message,
                'processing_stage': processing_stage,
                'details': error.details,
                'severity': self.SEVERITY_HIGH,
                'category': self.CATEGORY_PROCESSING,
                'recoverable': True,
                'recovery_suggestions': self._get_processing_recovery_suggestions(error, processing_stage)
            }
        else:
            error_response = {
                'success': False,
                'error_type': 'processing_error',
                'error_code': 'UNKNOWN_PROCESSING_ERROR',
                'message': str(error),
                'processing_stage': processing_stage,
                'details': context,
                'severity': self.SEVERITY_CRITICAL,
                'category': self.CATEGORY_PROCESSING,
                'recoverable': True,
                'recovery_suggestions': self._get_generic_processing_recovery_suggestions()
            }
        
        # Log the error
        self._log_error(error_response, error, context)
        
        return error_response
    
    def handle_system_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Handle system-level errors with graceful degradation.
        
        Args:
            error: System error instance
            context: Additional context information
            
        Returns:
            Standardized error response dictionary
        """
        context = context or {}
        
        error_response = {
            'success': False,
            'error_type': 'system_error',
            'error_code': 'SYSTEM_ERROR',
            'message': 'A system error occurred. Please try again later.',
            'technical_message': str(error),
            'details': context,
            'severity': self.SEVERITY_CRITICAL,
            'category': self.CATEGORY_SYSTEM,
            'recoverable': False,
            'recovery_suggestions': self._get_system_recovery_suggestions()
        }
        
        # Log the error with full traceback
        self._log_error(error_response, error, context, include_traceback=True)
        
        return error_response
    
    def _get_validation_recovery_suggestions(self, error: SurveyValidationError) -> List[str]:
        """Get recovery suggestions for validation errors."""
        suggestions = []
        
        if error.field_errors:
            suggestions.append("Please correct the highlighted fields and try again")
            
            # Specific suggestions based on field types
            for field, errors in error.field_errors.items():
                for error_msg in errors:
                    if 'required' in error_msg.lower():
                        suggestions.append(f"The {field} field is required")
                    elif 'invalid' in error_msg.lower():
                        suggestions.append(f"Please enter a valid value for {field}")
                    elif 'length' in error_msg.lower():
                        suggestions.append(f"Check the length requirements for {field}")
        
        suggestions.append("You can skip optional questions and return to them later")
        suggestions.append("Use the help text provided with each question for guidance")
        
        return suggestions
    
    def _get_generic_validation_recovery_suggestions(self) -> List[str]:
        """Get generic validation recovery suggestions."""
        return [
            "Please review your responses and correct any errors",
            "Make sure all required fields are completed",
            "Check that numeric values are within the specified ranges",
            "Ensure text responses meet the minimum/maximum length requirements"
        ]
    
    def _get_session_recovery_suggestions(self, error: SurveySessionError, session_key: str) -> List[str]:
        """Get recovery suggestions for session errors."""
        suggestions = []
        
        if 'expired' in error.message.lower():
            suggestions.extend([
                "Your session has expired. You can start a new survey",
                "Consider creating an account to save your progress automatically",
                "Enable browser cookies to maintain your session longer"
            ])
        elif 'not found' in error.message.lower():
            suggestions.extend([
                "The survey session could not be found",
                "You may need to start a new survey",
                "Check if you have the correct survey link"
            ])
        else:
            suggestions.extend([
                "Try refreshing the page to restore your session",
                "Clear your browser cache and cookies if problems persist",
                "Start a new survey if the issue continues"
            ])
        
        return suggestions
    
    def _get_processing_recovery_suggestions(self, error: SurveyProcessingError, stage: str) -> List[str]:
        """Get recovery suggestions for processing errors."""
        suggestions = []
        
        if stage == 'response_processing':
            suggestions.extend([
                "Some of your responses may need to be reviewed",
                "Try completing any remaining required questions",
                "You can modify previous responses if needed"
            ])
        elif stage == 'comparison_generation':
            suggestions.extend([
                "The system will use basic comparison criteria",
                "Your survey responses have been saved",
                "You can view available policies without personalized ranking"
            ])
        else:
            suggestions.extend([
                "Your survey responses have been saved",
                "You can try completing the survey again",
                "Contact support if the problem persists"
            ])
        
        return suggestions
    
    def _get_generic_processing_recovery_suggestions(self) -> List[str]:
        """Get generic processing recovery suggestions."""
        return [
            "The system will fall back to basic comparison functionality",
            "Your survey responses have been preserved",
            "You can still view and compare available policies",
            "Try refreshing the page or completing the survey again"
        ]
    
    def _get_system_recovery_suggestions(self) -> List[str]:
        """Get recovery suggestions for system errors."""
        return [
            "Please try again in a few minutes",
            "Refresh the page to see if the issue is resolved",
            "Your progress has been automatically saved",
            "Contact support if the problem persists"
        ]
    
    def _log_error(
        self,
        error_response: Dict[str, Any],
        original_error: Exception,
        context: Dict[str, Any],
        include_traceback: bool = False
    ):
        """Log error details for monitoring and debugging."""
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'error_type': error_response['error_type'],
            'error_code': error_response['error_code'],
            'message': error_response['message'],
            'severity': error_response['severity'],
            'category': error_response['category'],
            'context': context,
            'original_error': str(original_error),
            'original_error_type': type(original_error).__name__
        }
        
        if include_traceback:
            log_entry['traceback'] = traceback.format_exc()
        
        # Add to internal error log
        self.error_log.append(log_entry)
        
        # Log to Django logger based on severity
        if error_response['severity'] == self.SEVERITY_CRITICAL:
            logger.critical(f"Survey Error: {log_entry}")
        elif error_response['severity'] == self.SEVERITY_HIGH:
            logger.error(f"Survey Error: {log_entry}")
        elif error_response['severity'] == self.SEVERITY_MEDIUM:
            logger.warning(f"Survey Error: {log_entry}")
        else:
            logger.info(f"Survey Error: {log_entry}")


class SurveyRecoveryManager:
    """
    Manages recovery operations for failed survey operations.
    Provides session recovery, data restoration, and fallback mechanisms.
    """
    
    def __init__(self):
        self.error_handler = SurveyErrorHandler()
    
    def recover_expired_session(
        self,
        session_key: str,
        category_slug: str,
        user=None
    ) -> Dict[str, Any]:
        """
        Attempt to recover data from an expired session.
        
        Args:
            session_key: Expired session key
            category_slug: Policy category slug
            user: User instance if authenticated
            
        Returns:
            Recovery result with new session information
        """
        try:
            # Try to find the expired session
            expired_session = ComparisonSession.objects.filter(
                session_key=session_key,
                category__slug=category_slug
            ).first()
            
            if not expired_session:
                return {
                    'success': False,
                    'error': 'Original session not found',
                    'recovery_type': 'create_new'
                }
            
            # Get existing responses
            existing_responses = SurveyResponse.objects.filter(
                session=expired_session
            ).select_related('question')
            
            if not existing_responses.exists():
                return {
                    'success': False,
                    'error': 'No responses found to recover',
                    'recovery_type': 'create_new'
                }
            
            # Create new session
            session_manager = SurveySessionManager()
            new_session = session_manager.create_survey_session(
                category_slug=category_slug,
                user=user
            )
            
            # Copy responses to new session
            recovered_count = 0
            with transaction.atomic():
                for old_response in existing_responses:
                    try:
                        SurveyResponse.objects.create(
                            session=new_session,
                            question=old_response.question,
                            response_value=old_response.response_value,
                            confidence_level=old_response.confidence_level
                        )
                        recovered_count += 1
                    except IntegrityError:
                        # Skip duplicate responses
                        continue
            
            # Update new session progress
            engine = SurveyEngine(category_slug)
            engine._update_session_progress(new_session)
            
            return {
                'success': True,
                'new_session_key': new_session.session_key,
                'recovered_responses': recovered_count,
                'recovery_type': 'session_restored',
                'message': f'Recovered {recovered_count} responses from your previous session'
            }
            
        except Exception as e:
            logger.error(f"Error recovering expired session {session_key}: {str(e)}")
            return {
                'success': False,
                'error': 'Recovery failed',
                'recovery_type': 'create_new',
                'details': str(e)
            }
    
    def handle_incomplete_survey_data(
        self,
        session: ComparisonSession,
        required_completion_percentage: float = 80.0
    ) -> Dict[str, Any]:
        """
        Handle incomplete survey data with graceful degradation.
        
        Args:
            session: ComparisonSession instance
            required_completion_percentage: Minimum completion percentage required
            
        Returns:
            Handling result with available options
        """
        try:
            engine = SurveyEngine(session.category.slug)
            completion_percentage = engine.calculate_completion_percentage(session)
            
            if completion_percentage >= required_completion_percentage:
                return {
                    'success': True,
                    'action': 'proceed_with_partial',
                    'completion_percentage': completion_percentage,
                    'message': 'Sufficient data available for comparison'
                }
            
            # Get section progress to identify missing areas
            from .flow_controller import SurveyFlowController
            flow_controller = SurveyFlowController(session.category.slug, session.session_key)
            section_progress = flow_controller.get_section_progress()
            
            # Identify critical missing sections
            critical_sections = []
            optional_sections = []
            
            for section_name, progress in section_progress.items():
                if progress['completion_percentage'] < 50:
                    if 'personal' in section_name.lower() or 'basic' in section_name.lower():
                        critical_sections.append(section_name)
                    else:
                        optional_sections.append(section_name)
            
            if critical_sections:
                return {
                    'success': False,
                    'action': 'require_completion',
                    'completion_percentage': completion_percentage,
                    'critical_sections': critical_sections,
                    'optional_sections': optional_sections,
                    'message': 'Critical sections need to be completed for accurate comparison'
                }
            else:
                return {
                    'success': True,
                    'action': 'proceed_with_basic',
                    'completion_percentage': completion_percentage,
                    'missing_sections': optional_sections,
                    'message': 'Basic comparison available with current responses'
                }
                
        except Exception as e:
            logger.error(f"Error handling incomplete survey data: {str(e)}")
            return {
                'success': False,
                'action': 'fallback_to_basic',
                'error': str(e),
                'message': 'Using basic comparison without survey data'
            }
    
    def implement_fallback_comparison(
        self,
        session: ComparisonSession,
        fallback_type: str = 'basic'
    ) -> Dict[str, Any]:
        """
        Implement fallback comparison when survey processing fails.
        
        Args:
            session: ComparisonSession instance
            fallback_type: Type of fallback ('basic', 'category_default', 'popular')
            
        Returns:
            Fallback implementation result
        """
        try:
            from comparison.engine import PolicyComparisonEngine
            
            # Create basic comparison criteria based on fallback type
            if fallback_type == 'basic':
                criteria = self._get_basic_comparison_criteria(session.category)
            elif fallback_type == 'category_default':
                criteria = self._get_category_default_criteria(session.category)
            elif fallback_type == 'popular':
                criteria = self._get_popular_choice_criteria(session.category)
            else:
                criteria = self._get_basic_comparison_criteria(session.category)
            
            # Update session with fallback criteria
            session.criteria = criteria
            session.save(update_fields=['criteria'])
            
            # Initialize comparison engine with fallback criteria
            engine = PolicyComparisonEngine(session.category.slug)
            
            return {
                'success': True,
                'fallback_type': fallback_type,
                'criteria': criteria,
                'message': f'Using {fallback_type} comparison criteria',
                'comparison_available': True
            }
            
        except Exception as e:
            logger.error(f"Error implementing fallback comparison: {str(e)}")
            return {
                'success': False,
                'fallback_type': fallback_type,
                'error': str(e),
                'message': 'Fallback comparison failed',
                'comparison_available': False
            }
    
    def _get_basic_comparison_criteria(self, category: PolicyCategory) -> Dict[str, Any]:
        """Get basic comparison criteria for a category."""
        if category.slug == 'health':
            return {
                'premium_weight': 0.3,
                'coverage_weight': 0.4,
                'deductible_weight': 0.2,
                'network_weight': 0.1,
                'max_premium': 1000,
                'min_coverage': 50000,
                'preferred_deductible': 'medium'
            }
        elif category.slug == 'funeral':
            return {
                'premium_weight': 0.4,
                'coverage_weight': 0.5,
                'waiting_period_weight': 0.1,
                'max_premium': 200,
                'min_coverage': 10000,
                'max_waiting_period': 24
            }
        else:
            return {
                'premium_weight': 0.5,
                'coverage_weight': 0.5,
                'max_premium': 500,
                'min_coverage': 25000
            }
    
    def _get_category_default_criteria(self, category: PolicyCategory) -> Dict[str, Any]:
        """Get category-specific default criteria."""
        # This would typically be configured by administrators
        # For now, return enhanced basic criteria
        criteria = self._get_basic_comparison_criteria(category)
        criteria['comparison_type'] = 'category_default'
        return criteria
    
    def _get_popular_choice_criteria(self, category: PolicyCategory) -> Dict[str, Any]:
        """Get criteria based on popular choices."""
        # This would analyze popular policy selections
        # For now, return basic criteria with popular adjustments
        criteria = self._get_basic_comparison_criteria(category)
        criteria['comparison_type'] = 'popular_choice'
        criteria['premium_weight'] = 0.6  # People often prioritize price
        criteria['coverage_weight'] = 0.4
        return criteria


# Global error handler instance
survey_error_handler = SurveyErrorHandler()
survey_recovery_manager = SurveyRecoveryManager()