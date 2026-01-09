"""
Survey Session Management

This module provides session management functionality for survey responses,
supporting both anonymous and authenticated users with auto-save, recovery,
and progress tracking capabilities.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings

from comparison.models import ComparisonSession
from surveys.models import SurveyResponse, SurveyQuestion, SurveyTemplate
from policies.models import PolicyCategory


class SurveySessionManager:
    """
    Manages survey sessions for both anonymous and authenticated users.
    Provides auto-save, recovery, and progress tracking functionality.
    """
    
    # Session keys for storing survey data
    SURVEY_DATA_KEY = 'survey_data'
    SURVEY_PROGRESS_KEY = 'survey_progress'
    SURVEY_METADATA_KEY = 'survey_metadata'
    
    # Default session expiry (7 days for survey sessions)
    DEFAULT_SESSION_EXPIRY_DAYS = 7
    
    def __init__(self, request=None, session_key=None):
        """
        Initialize session manager.
        
        Args:
            request: Django request object (for authenticated users)
            session_key: Session key for anonymous users
        """
        self.request = request
        self.session_key = session_key
        self.user = getattr(request, 'user', None) if request else None
        self.is_authenticated = self.user and self.user.is_authenticated
        
        # Initialize session store for anonymous users
        if not self.is_authenticated:
            self.session_store = SessionStore(session_key=session_key)
            if not session_key:
                self.session_store.create()
                self.session_key = self.session_store.session_key
    
    def create_survey_session(self, category_slug: str, **kwargs) -> ComparisonSession:
        """
        Create a new survey session for the given category.
        
        Args:
            category_slug: Policy category slug
            **kwargs: Additional session parameters
            
        Returns:
            ComparisonSession: Created session instance
            
        Raises:
            ValidationError: If category doesn't exist or session creation fails
        """
        try:
            category = PolicyCategory.objects.get(slug=category_slug)
        except PolicyCategory.DoesNotExist:
            raise ValidationError(f"Policy category '{category_slug}' does not exist")
        
        # Generate unique session key if not provided
        if not self.session_key:
            self.session_key = str(uuid.uuid4())
        
        # Set session expiry
        expires_at = timezone.now() + timedelta(days=self.DEFAULT_SESSION_EXPIRY_DAYS)
        
        # Create comparison session
        session_data = {
            'user': self.user if self.is_authenticated else None,
            'session_key': self.session_key,
            'category': category,
            'expires_at': expires_at,
            **kwargs
        }
        
        session = ComparisonSession.objects.create(**session_data)
        
        # Initialize session metadata
        self._initialize_session_metadata(session, category)
        
        return session
    
    def get_or_create_survey_session(self, category_slug: str, **kwargs) -> ComparisonSession:
        """
        Get existing survey session or create a new one.
        
        Args:
            category_slug: Policy category slug
            **kwargs: Additional session parameters
            
        Returns:
            ComparisonSession: Existing or newly created session
        """
        # Try to get existing active session
        session = self.get_active_survey_session(category_slug)
        
        if session:
            # Check if session is expired
            if session.expires_at and session.expires_at < timezone.now():
                # Mark as expired and create new session
                session.status = ComparisonSession.Status.EXPIRED
                session.save()
                return self.create_survey_session(category_slug, **kwargs)
            return session
        
        # Create new session
        return self.create_survey_session(category_slug, **kwargs)
    
    def get_active_survey_session(self, category_slug: str) -> Optional[ComparisonSession]:
        """
        Get active survey session for the given category.
        
        Args:
            category_slug: Policy category slug
            
        Returns:
            ComparisonSession or None: Active session if exists
        """
        try:
            category = PolicyCategory.objects.get(slug=category_slug)
        except PolicyCategory.DoesNotExist:
            return None
        
        # Query based on user type
        if self.is_authenticated:
            sessions = ComparisonSession.objects.filter(
                user=self.user,
                category=category,
                status=ComparisonSession.Status.ACTIVE
            )
        else:
            sessions = ComparisonSession.objects.filter(
                session_key=self.session_key,
                category=category,
                status=ComparisonSession.Status.ACTIVE
            )
        
        return sessions.first()
    
    def save_survey_response(
        self,
        session: ComparisonSession,
        question_id: int,
        response_value: Any,
        confidence_level: int = 3,
        auto_save: bool = True
    ) -> SurveyResponse:
        """
        Save or update a survey response.
        
        Args:
            session: ComparisonSession instance
            question_id: ID of the question being answered
            response_value: User's response value
            confidence_level: User's confidence level (1-5)
            auto_save: Whether this is an auto-save operation
            
        Returns:
            SurveyResponse: Created or updated response
            
        Raises:
            ValidationError: If question doesn't exist or validation fails
        """
        try:
            question = SurveyQuestion.objects.get(
                id=question_id,
                category=session.category,
                is_active=True
            )
        except SurveyQuestion.DoesNotExist:
            raise ValidationError(f"Question with ID {question_id} does not exist")
        
        # Validate response value
        self._validate_response_value(question, response_value)
        
        # Create or update response
        response, created = SurveyResponse.objects.update_or_create(
            session=session,
            question=question,
            defaults={
                'response_value': response_value,
                'confidence_level': confidence_level,
                'updated_at': timezone.now()
            }
        )
        
        # Update session progress
        if not auto_save:  # Only update progress for manual saves
            self._update_session_progress(session)
        
        # Store in session for anonymous users
        if not self.is_authenticated:
            self._store_response_in_session(session, response)
        
        return response
    
    def auto_save_responses(self, session: ComparisonSession, responses_data: List[Dict]) -> List[SurveyResponse]:
        """
        Auto-save multiple survey responses.
        
        Args:
            session: ComparisonSession instance
            responses_data: List of response data dictionaries
            
        Returns:
            List[SurveyResponse]: List of saved responses
        """
        saved_responses = []
        
        with transaction.atomic():
            for response_data in responses_data:
                try:
                    response = self.save_survey_response(
                        session=session,
                        question_id=response_data['question_id'],
                        response_value=response_data['response_value'],
                        confidence_level=response_data.get('confidence_level', 3),
                        auto_save=True
                    )
                    saved_responses.append(response)
                except ValidationError:
                    # Skip invalid responses in auto-save
                    continue
            
            # Update progress after all auto-saves
            self._update_session_progress(session)
        
        return saved_responses
    
    def recover_session_data(self, session: ComparisonSession) -> Dict:
        """
        Recover session data for incomplete surveys.
        
        Args:
            session: ComparisonSession instance
            
        Returns:
            Dict: Recovered session data including responses and progress
        """
        # Get existing responses
        responses = SurveyResponse.objects.filter(session=session).select_related('question')
        
        # Build response data
        response_data = {}
        for response in responses:
            response_data[response.question.field_name] = {
                'question_id': response.question.id,
                'response_value': response.response_value,
                'confidence_level': response.confidence_level,
                'updated_at': response.updated_at.isoformat()
            }
        
        # Get session progress
        progress_data = self.get_session_progress(session)
        
        # Get session metadata
        metadata = self._get_session_metadata(session)
        
        return {
            'session_id': session.id,
            'session_key': session.session_key,
            'category': session.category.slug,
            'responses': response_data,
            'progress': progress_data,
            'metadata': metadata,
            'last_updated': session.updated_at.isoformat(),
            'expires_at': session.expires_at.isoformat() if session.expires_at else None
        }
    
    def get_session_progress(self, session: ComparisonSession) -> Dict:
        """
        Get detailed progress information for a survey session.
        
        Args:
            session: ComparisonSession instance
            
        Returns:
            Dict: Progress information including completion percentage and section status
        """
        # Get survey template for this category
        try:
            template = SurveyTemplate.objects.get(
                category=session.category,
                is_active=True
            )
        except SurveyTemplate.DoesNotExist:
            return {
                'completion_percentage': 0.0,
                'total_questions': 0,
                'answered_questions': 0,
                'sections': {},
                'is_complete': False
            }
        
        # Get all questions for this template
        questions = SurveyQuestion.objects.filter(
            category=session.category,
            is_active=True
        ).order_by('section', 'display_order')
        
        # Get answered questions
        answered_questions = set(
            SurveyResponse.objects.filter(session=session)
            .values_list('question_id', flat=True)
        )
        
        # Calculate section progress
        sections = {}
        for question in questions:
            section = question.section
            if section not in sections:
                sections[section] = {
                    'total_questions': 0,
                    'answered_questions': 0,
                    'completion_percentage': 0.0,
                    'is_complete': False
                }
            
            sections[section]['total_questions'] += 1
            if question.id in answered_questions:
                sections[section]['answered_questions'] += 1
        
        # Calculate section completion percentages
        for section_data in sections.values():
            if section_data['total_questions'] > 0:
                section_data['completion_percentage'] = (
                    section_data['answered_questions'] / section_data['total_questions'] * 100
                )
                section_data['is_complete'] = section_data['completion_percentage'] >= 100.0
        
        # Calculate overall progress
        total_questions = questions.count()
        answered_count = len(answered_questions)
        completion_percentage = (answered_count / total_questions * 100) if total_questions > 0 else 0.0
        
        return {
            'completion_percentage': round(completion_percentage, 2),
            'total_questions': total_questions,
            'answered_questions': answered_count,
            'sections': sections,
            'is_complete': completion_percentage >= 100.0
        }
    
    def validate_session_data(self, session: ComparisonSession) -> Dict:
        """
        Validate all responses in a survey session.
        
        Args:
            session: ComparisonSession instance
            
        Returns:
            Dict: Validation results including errors and warnings
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'invalid_responses': []
        }
        
        # Get all questions for this category
        questions = SurveyQuestion.objects.filter(
            category=session.category,
            is_active=True
        )
        
        # Get all responses for this session
        responses = {
            r.question_id: r for r in 
            SurveyResponse.objects.filter(session=session).select_related('question')
        }
        
        # Validate each question
        for question in questions:
            if question.is_required and question.id not in responses:
                validation_results['missing_required'].append({
                    'question_id': question.id,
                    'question_text': question.question_text,
                    'section': question.section
                })
                validation_results['is_valid'] = False
            elif question.id in responses:
                # Validate response value
                response = responses[question.id]
                try:
                    self._validate_response_value(question, response.response_value)
                except ValidationError as e:
                    validation_results['invalid_responses'].append({
                        'question_id': question.id,
                        'question_text': question.question_text,
                        'error': str(e)
                    })
                    validation_results['is_valid'] = False
        
        return validation_results
    
    def extend_session_expiry(self, session: ComparisonSession, days: int = None) -> ComparisonSession:
        """
        Extend session expiry time.
        
        Args:
            session: ComparisonSession instance
            days: Number of days to extend (default: DEFAULT_SESSION_EXPIRY_DAYS)
            
        Returns:
            ComparisonSession: Updated session
        """
        if days is None:
            days = self.DEFAULT_SESSION_EXPIRY_DAYS
        
        session.expires_at = timezone.now() + timedelta(days=days)
        session.save(update_fields=['expires_at', 'updated_at'])
        
        return session
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired anonymous survey sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        expired_sessions = ComparisonSession.objects.filter(
            user__isnull=True,  # Anonymous sessions only
            expires_at__lt=timezone.now(),
            status=ComparisonSession.Status.ACTIVE
        )
        
        count = expired_sessions.count()
        expired_sessions.update(status=ComparisonSession.Status.EXPIRED)
        
        return count
    
    def _initialize_session_metadata(self, session: ComparisonSession, category: PolicyCategory):
        """Initialize session metadata for tracking."""
        metadata = {
            'created_at': timezone.now().isoformat(),
            'category_slug': category.slug,
            'user_agent': getattr(self.request, 'META', {}).get('HTTP_USER_AGENT', '') if self.request else '',
            'ip_address': self._get_client_ip() if self.request else '',
            'auto_save_enabled': True,
            'last_auto_save': None
        }
        
        if not self.is_authenticated:
            self.session_store[self.SURVEY_METADATA_KEY] = metadata
            self.session_store.save()
    
    def _update_session_progress(self, session: ComparisonSession):
        """Update session progress tracking."""
        progress_data = self.get_session_progress(session)
        
        # Update ComparisonSession fields
        session.update_survey_progress(
            responses_count=progress_data['answered_questions'],
            completion_percentage=progress_data['completion_percentage']
        )
        
        # Store progress in session for anonymous users
        if not self.is_authenticated:
            self.session_store[self.SURVEY_PROGRESS_KEY] = progress_data
            self.session_store.save()
    
    def _store_response_in_session(self, session: ComparisonSession, response: SurveyResponse):
        """Store response data in session for anonymous users."""
        if self.is_authenticated:
            return
        
        # Get existing survey data
        survey_data = self.session_store.get(self.SURVEY_DATA_KEY, {})
        
        # Update with new response
        survey_data[response.question.field_name] = {
            'question_id': response.question.id,
            'response_value': response.response_value,
            'confidence_level': response.confidence_level,
            'updated_at': timezone.now().isoformat()
        }
        
        # Save back to session
        self.session_store[self.SURVEY_DATA_KEY] = survey_data
        
        # Update metadata
        metadata = self.session_store.get(self.SURVEY_METADATA_KEY, {})
        metadata['last_auto_save'] = timezone.now().isoformat()
        self.session_store[self.SURVEY_METADATA_KEY] = metadata
        
        self.session_store.save()
    
    def _validate_response_value(self, question: SurveyQuestion, response_value: Any):
        """Validate response value against question rules."""
        validation_rules = question.validation_rules or {}
        
        # Check required
        if question.is_required and (response_value is None or response_value == ''):
            raise ValidationError(f"Response is required for question: {question.question_text}")
        
        # Type-specific validation
        if question.question_type == SurveyQuestion.QuestionType.NUMBER:
            try:
                value = float(response_value)
                if 'min_value' in validation_rules and value < validation_rules['min_value']:
                    raise ValidationError(f"Value must be at least {validation_rules['min_value']}")
                if 'max_value' in validation_rules and value > validation_rules['max_value']:
                    raise ValidationError(f"Value must be at most {validation_rules['max_value']}")
            except (ValueError, TypeError):
                raise ValidationError("Response must be a valid number")
        
        elif question.question_type == SurveyQuestion.QuestionType.CHOICE:
            if response_value not in [choice['value'] for choice in question.choices]:
                raise ValidationError("Invalid choice selected")
        
        elif question.question_type == SurveyQuestion.QuestionType.MULTI_CHOICE:
            if not isinstance(response_value, list):
                raise ValidationError("Multi-choice response must be a list")
            valid_choices = [choice['value'] for choice in question.choices]
            for value in response_value:
                if value not in valid_choices:
                    raise ValidationError(f"Invalid choice: {value}")
        
        elif question.question_type == SurveyQuestion.QuestionType.RANGE:
            try:
                value = float(response_value)
                min_val = validation_rules.get('min_value', 0)
                max_val = validation_rules.get('max_value', 100)
                if not (min_val <= value <= max_val):
                    raise ValidationError(f"Value must be between {min_val} and {max_val}")
            except (ValueError, TypeError):
                raise ValidationError("Range response must be a valid number")
        
        elif question.question_type == SurveyQuestion.QuestionType.BOOLEAN:
            if not isinstance(response_value, bool):
                raise ValidationError("Boolean response must be true or false")
        
        elif question.question_type == SurveyQuestion.QuestionType.TEXT:
            if isinstance(response_value, str):
                min_length = validation_rules.get('min_length', 0)
                max_length = validation_rules.get('max_length', 1000)
                if len(response_value) < min_length:
                    raise ValidationError(f"Response must be at least {min_length} characters")
                if len(response_value) > max_length:
                    raise ValidationError(f"Response must be at most {max_length} characters")
    
    def _get_session_metadata(self, session: ComparisonSession) -> Dict:
        """Get session metadata."""
        if self.is_authenticated:
            return {
                'user_id': self.user.id,
                'username': self.user.username,
                'session_type': 'authenticated'
            }
        else:
            return self.session_store.get(self.SURVEY_METADATA_KEY, {})
    
    def _get_client_ip(self) -> str:
        """Get client IP address from request."""
        if not self.request:
            return ''
        
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip or ''


class SurveyAutoSaveManager:
    """
    Manages auto-save functionality for survey responses.
    Handles periodic saving and recovery of survey data.
    """
    
    def __init__(self, session_manager: SurveySessionManager):
        self.session_manager = session_manager
    
    def enable_auto_save(self, session: ComparisonSession, interval_seconds: int = 30):
        """
        Enable auto-save for a survey session.
        
        Args:
            session: ComparisonSession instance
            interval_seconds: Auto-save interval in seconds
        """
        # This would typically be implemented with JavaScript on the frontend
        # Here we just mark the session as auto-save enabled
        metadata = self.session_manager._get_session_metadata(session)
        metadata['auto_save_enabled'] = True
        metadata['auto_save_interval'] = interval_seconds
        
        if not self.session_manager.is_authenticated:
            self.session_manager.session_store[SurveySessionManager.SURVEY_METADATA_KEY] = metadata
            self.session_manager.session_store.save()
    
    def save_draft_responses(self, session: ComparisonSession, draft_data: Dict) -> Dict:
        """
        Save draft responses (partial/incomplete responses).
        
        Args:
            session: ComparisonSession instance
            draft_data: Dictionary of draft response data
            
        Returns:
            Dict: Save results including success/failure status
        """
        results = {
            'saved_count': 0,
            'failed_count': 0,
            'errors': []
        }
        
        for field_name, response_data in draft_data.items():
            try:
                self.session_manager.save_survey_response(
                    session=session,
                    question_id=response_data['question_id'],
                    response_value=response_data['response_value'],
                    confidence_level=response_data.get('confidence_level', 3),
                    auto_save=True
                )
                results['saved_count'] += 1
            except Exception as e:
                results['failed_count'] += 1
                results['errors'].append({
                    'field_name': field_name,
                    'error': str(e)
                })
        
        return results