"""
Survey Flow Controller for Policy Comparison Surveys.
Manages question progression, survey completion, and user navigation.
"""

from typing import Dict, Any, Optional, List, Tuple
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from django.http import Http404
from comparison.models import ComparisonSession
from policies.models import PolicyCategory
from .models import SurveyQuestion, SurveyResponse, QuestionDependency
from .engine import SurveyEngine
from .response_processor import ResponseProcessor
import logging
import uuid

logger = logging.getLogger(__name__)


class SurveyFlowController:
    """
    Controls the flow of survey questions and manages user progression through surveys.
    Handles navigation, conditional logic, and completion processing.
    """
    
    def __init__(self, category_slug: str, session_key: Optional[str] = None):
        """
        Initialize the survey flow controller.
        
        Args:
            category_slug: Policy category slug (health, funeral, etc.)
            session_key: Existing session key or None to create new session
        """
        self.category_slug = category_slug
        self.session_key = session_key
        self.category = None
        self.session = None
        self.engine = None
        
        self._load_category()
        self._load_or_create_session()
        self._initialize_engine()
    
    def _load_category(self):
        """Load and validate the policy category."""
        try:
            self.category = PolicyCategory.objects.get(slug=self.category_slug)
        except PolicyCategory.DoesNotExist:
            raise Http404(f"Policy category '{self.category_slug}' not found")
    
    def _load_or_create_session(self):
        """Load existing session or create a new one."""
        if self.session_key:
            try:
                self.session = ComparisonSession.objects.get(
                    session_key=self.session_key,
                    category=self.category
                )
                return
            except ComparisonSession.DoesNotExist:
                logger.warning(f"Session {self.session_key} not found, creating new session")
        
        # Create new session
        self.session_key = self._generate_session_key()
        self.session = ComparisonSession.objects.create(
            session_key=self.session_key,
            category=self.category,
            status=ComparisonSession.Status.ACTIVE,
            expires_at=timezone.now() + timezone.timedelta(hours=24)  # 24 hour expiry
        )
    
    def _generate_session_key(self) -> str:
        """Generate a unique session key."""
        return f"survey_{self.category_slug}_{uuid.uuid4().hex[:12]}"
    
    def _initialize_engine(self):
        """Initialize the survey engine."""
        self.engine = SurveyEngine(self.category_slug)
    
    def get_survey_start_url(self) -> str:
        """Get the URL to start the survey."""
        return reverse('surveys:survey_form', kwargs={
            'category_slug': self.category_slug
        }) + f"?session={self.session_key}"
    
    def get_current_section_and_question(self) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Get the current section and next unanswered question.
        
        Returns:
            Tuple of (section_name, question_data) or (None, None) if survey is complete
        """
        sections = self.engine.get_survey_sections()
        if not sections:
            return None, None
        
        # Get answered question IDs
        answered_question_ids = set(
            SurveyResponse.objects.filter(
                session=self.session,
                question__category=self.category
            ).values_list('question_id', flat=True)
        )
        
        # Find first unanswered question
        for section in sections:
            for question in section['questions']:
                question_id = question['id']
                
                # Skip if already answered
                if question_id in answered_question_ids:
                    continue
                
                # Check conditional logic
                if self._should_show_question(question_id):
                    return section['name'], question
        
        # All questions answered
        return None, None
    
    def _should_show_question(self, question_id: int) -> bool:
        """
        Check if a question should be shown based on conditional logic.
        
        Args:
            question_id: ID of the question to check
            
        Returns:
            True if question should be shown, False otherwise
        """
        # Get dependencies for this question
        dependencies = QuestionDependency.objects.filter(
            child_question_id=question_id,
            is_active=True
        )
        
        if not dependencies.exists():
            return True  # No dependencies, always show
        
        # Check all dependencies - all must be satisfied
        for dependency in dependencies:
            parent_response = self._get_response_value(dependency.parent_question_id)
            if parent_response is None:
                return False  # Parent not answered yet
            
            if not dependency.evaluate_condition(parent_response):
                return False  # Condition not met
        
        return True  # All conditions satisfied
    
    def _get_response_value(self, question_id: int) -> Any:
        """Get the response value for a specific question."""
        try:
            response = SurveyResponse.objects.get(
                session=self.session,
                question_id=question_id
            )
            return response.response_value
        except SurveyResponse.DoesNotExist:
            return None
    
    def get_section_progress(self) -> Dict[str, Any]:
        """
        Get progress information for all sections.
        
        Returns:
            Dictionary with section progress information
        """
        sections = self.engine.get_survey_sections()
        progress = {}
        
        # Get answered question IDs
        answered_question_ids = set(
            SurveyResponse.objects.filter(
                session=self.session,
                question__category=self.category
            ).values_list('question_id', flat=True)
        )
        
        for section in sections:
            section_name = section['name']
            total_questions = len(section['questions'])
            
            # Count answered questions in this section (considering conditional logic)
            answered_in_section = 0
            visible_questions = 0
            
            for question in section['questions']:
                question_id = question['id']
                
                # Check if question should be visible
                if self._should_show_question(question_id):
                    visible_questions += 1
                    if question_id in answered_question_ids:
                        answered_in_section += 1
            
            completion_percentage = 0
            if visible_questions > 0:
                completion_percentage = (answered_in_section / visible_questions) * 100
            
            progress[section_name] = {
                'total_questions': total_questions,
                'visible_questions': visible_questions,
                'answered_questions': answered_in_section,
                'completion_percentage': completion_percentage,
                'is_complete': completion_percentage >= 100
            }
        
        return progress
    
    def submit_response(
        self, 
        question_id: int, 
        response_value: Any, 
        confidence_level: int = 3
    ) -> Dict[str, Any]:
        """
        Submit a response to a question and handle progression logic.
        
        Args:
            question_id: ID of the question being answered
            response_value: User's response
            confidence_level: User's confidence level (1-5)
            
        Returns:
            Dictionary with submission result and next step information
        """
        # Save the response using the engine
        save_result = self.engine.save_response(
            self.session, 
            question_id, 
            response_value, 
            confidence_level
        )
        
        if not save_result['success']:
            return {
                'success': False,
                'errors': save_result['errors'],
                'next_action': None
            }
        
        # Check if this response triggers any conditional questions
        triggered_questions = self.engine.check_conditional_questions(
            self.session, 
            question_id, 
            response_value
        )
        
        # Get next question/section
        next_section, next_question = self.get_current_section_and_question()
        
        # Determine next action
        next_action = self._determine_next_action(next_section, next_question)
        
        return {
            'success': True,
            'errors': [],
            'response_id': save_result['response_id'],
            'triggered_questions': triggered_questions,
            'next_section': next_section,
            'next_question': next_question,
            'next_action': next_action,
            'completion_percentage': self.engine.calculate_completion_percentage(self.session)
        }
    
    def _determine_next_action(
        self, 
        next_section: Optional[str], 
        next_question: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Determine what action should be taken next in the survey flow.
        
        Args:
            next_section: Name of next section or None
            next_question: Next question data or None
            
        Returns:
            Dictionary describing the next action
        """
        if next_question is None:
            # Survey is complete
            return {
                'type': 'complete_survey',
                'url': reverse('surveys:survey_completion', kwargs={
                    'category_slug': self.category_slug
                }) + f"?session={self.session_key}",
                'message': 'Survey completed! Processing your responses...'
            }
        
        # Continue to next question
        return {
            'type': 'next_question',
            'section': next_section,
            'question_id': next_question['id'],
            'url': reverse('surveys:survey_form', kwargs={
                'category_slug': self.category_slug
            }) + f"?session={self.session_key}&question={next_question['id']}",
            'message': f'Continue to next question in {next_section}'
        }
    
    def navigate_to_section(self, section_name: str) -> Dict[str, Any]:
        """
        Navigate to a specific section of the survey.
        
        Args:
            section_name: Name of the section to navigate to
            
        Returns:
            Dictionary with navigation result and first question in section
        """
        sections = self.engine.get_survey_sections()
        target_section = None
        
        # Find the target section
        for section in sections:
            if section['name'] == section_name:
                target_section = section
                break
        
        if not target_section:
            return {
                'success': False,
                'error': f'Section "{section_name}" not found',
                'question': None
            }
        
        # Get answered question IDs
        answered_question_ids = set(
            SurveyResponse.objects.filter(
                session=self.session,
                question__category=self.category
            ).values_list('question_id', flat=True)
        )
        
        # Find first unanswered question in section
        for question in target_section['questions']:
            question_id = question['id']
            
            # Skip if already answered
            if question_id in answered_question_ids:
                continue
            
            # Check conditional logic
            if self._should_show_question(question_id):
                return {
                    'success': True,
                    'section': section_name,
                    'question': question,
                    'url': reverse('surveys:survey_form', kwargs={
                        'category_slug': self.category_slug
                    }) + f"?session={self.session_key}&question={question_id}"
                }
        
        # All questions in section are answered
        return {
            'success': True,
            'section': section_name,
            'question': None,
            'message': f'All questions in "{section_name}" are completed'
        }
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific question by ID with validation.
        
        Args:
            question_id: ID of the question to retrieve
            
        Returns:
            Question data or None if not found/not accessible
        """
        question_data = self.engine.get_question_by_id(question_id)
        if not question_data:
            return None
        
        # Check if question should be shown based on conditional logic
        if not self._should_show_question(question_id):
            return None
        
        # Add current response if exists
        current_response = self._get_response_value(question_id)
        question_data['current_response'] = current_response
        
        return question_data
    
    def complete_survey(self) -> Dict[str, Any]:
        """
        Mark the survey as complete and trigger comparison processing.
        
        Returns:
            Dictionary with completion result and comparison processing status
        """
        try:
            with transaction.atomic():
                # Check if survey is actually complete
                completion_percentage = self.engine.calculate_completion_percentage(self.session)
                
                if completion_percentage < 100.0:
                    return {
                        'success': False,
                        'error': 'Survey is not complete',
                        'completion_percentage': completion_percentage
                    }
                
                # Process responses and generate user profile
                processor = ResponseProcessor(self.category_slug)
                processing_result = processor.process_responses(self.session)
                
                if not processing_result.get('success', False):
                    return {
                        'success': False,
                        'error': 'Failed to process survey responses',
                        'details': ['Response processing failed or returned no data']
                    }
                
                # Mark survey as completed
                self.session.mark_survey_completed(processing_result['user_profile'])
                
                # Update session criteria with processed data
                self.session.criteria.update(processing_result['criteria'])
                self.session.save(update_fields=['criteria'])
                
                return {
                    'success': True,
                    'user_profile': processing_result['user_profile'],
                    'comparison_criteria': processing_result['criteria'],
                    'results_url': reverse('comparison:enhanced_results', kwargs={'session_key': self.session_key}),
                    'message': 'Survey completed successfully! Your personalized recommendations are ready.'
                }
                
        except Exception as e:
            logger.error(f"Error completing survey for session {self.session_key}: {str(e)}")
            return {
                'success': False,
                'error': 'An error occurred while completing the survey',
                'details': str(e)
            }
    
    def restart_survey(self, preserve_responses: bool = False) -> Dict[str, Any]:
        """
        Restart the survey, optionally preserving existing responses.
        
        Args:
            preserve_responses: If True, keep existing responses; if False, clear all
            
        Returns:
            Dictionary with restart result and new survey URL
        """
        try:
            with transaction.atomic():
                if not preserve_responses:
                    # Delete all responses for this session
                    SurveyResponse.objects.filter(
                        session=self.session,
                        question__category=self.category
                    ).delete()
                
                # Reset survey data in session
                self.session.reset_survey_data()
                
                # Get first question
                sections = self.engine.get_survey_sections()
                if sections and sections[0]['questions']:
                    first_question = sections[0]['questions'][0]
                    start_url = reverse('surveys:survey_form', kwargs={
                        'category_slug': self.category_slug
                    }) + f"?session={self.session_key}&question={first_question['id']}"
                else:
                    start_url = self.get_survey_start_url()
                
                return {
                    'success': True,
                    'session_key': self.session_key,
                    'start_url': start_url,
                    'message': 'Survey restarted successfully' + (
                        ' (responses preserved)' if preserve_responses else ' (all responses cleared)'
                    )
                }
                
        except Exception as e:
            logger.error(f"Error restarting survey for session {self.session_key}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to restart survey',
                'details': str(e)
            }
    
    def modify_response(self, question_id: int, new_response: Any, confidence_level: int = 3) -> Dict[str, Any]:
        """
        Modify an existing response and handle any cascading effects.
        
        Args:
            question_id: ID of the question to modify
            new_response: New response value
            confidence_level: New confidence level
            
        Returns:
            Dictionary with modification result and affected questions
        """
        try:
            with transaction.atomic():
                # Check if response exists
                try:
                    existing_response = SurveyResponse.objects.get(
                        session=self.session,
                        question_id=question_id
                    )
                except SurveyResponse.DoesNotExist:
                    return {
                        'success': False,
                        'error': 'Response not found'
                    }
                
                # Get questions that depend on this one
                dependent_questions = QuestionDependency.objects.filter(
                    parent_question_id=question_id,
                    is_active=True
                ).values_list('child_question_id', flat=True)
                
                # Save the new response
                save_result = self.engine.save_response(
                    self.session,
                    question_id,
                    new_response,
                    confidence_level
                )
                
                if not save_result['success']:
                    return save_result
                
                # Check if dependent questions should be removed
                affected_questions = []
                for dep_question_id in dependent_questions:
                    if not self._should_show_question(dep_question_id):
                        # Remove response for dependent question
                        SurveyResponse.objects.filter(
                            session=self.session,
                            question_id=dep_question_id
                        ).delete()
                        affected_questions.append(dep_question_id)
                
                # Update session progress
                self.engine._update_session_progress(self.session)
                
                return {
                    'success': True,
                    'response_id': save_result['response_id'],
                    'affected_questions': affected_questions,
                    'completion_percentage': self.engine.calculate_completion_percentage(self.session),
                    'message': 'Response updated successfully'
                }
                
        except Exception as e:
            logger.error(f"Error modifying response for question {question_id}: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to modify response',
                'details': str(e)
            }
    
    def get_survey_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the current survey state.
        
        Returns:
            Dictionary with complete survey status and progress information
        """
        summary = self.engine.get_survey_summary(self.session)
        
        # Add flow-specific information
        current_section, current_question = self.get_current_section_and_question()
        section_progress = self.get_section_progress()
        
        summary.update({
            'session_key': self.session_key,
            'current_section': current_section,
            'current_question_id': current_question['id'] if current_question else None,
            'section_progress': section_progress,
            'can_complete': summary['completion_percentage'] >= 100.0,
            'survey_url': self.get_survey_start_url()
        })
        
        return summary
    
    def validate_session(self) -> bool:
        """
        Validate that the session is still valid and active.
        
        Returns:
            True if session is valid, False otherwise
        """
        if not self.session:
            return False
        
        # Check if session is expired
        if self.session.expires_at and self.session.expires_at < timezone.now():
            return False
        
        # Check if session is active
        if self.session.status != ComparisonSession.Status.ACTIVE:
            return False
        
        return True
    
    def extend_session(self, hours: int = 24) -> bool:
        """
        Extend the session expiry time.
        
        Args:
            hours: Number of hours to extend the session
            
        Returns:
            True if extended successfully, False otherwise
        """
        try:
            self.session.expires_at = timezone.now() + timezone.timedelta(hours=hours)
            self.session.save(update_fields=['expires_at'])
            return True
        except Exception as e:
            logger.error(f"Error extending session {self.session_key}: {str(e)}")
            return False