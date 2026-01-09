"""
Simple Survey Engine for question delivery and response handling.

This module provides the core SimpleSurveyEngine class that handles:
- Loading questions for a specific category
- Validating user responses
- Saving responses immediately to the database
- Converting responses to quotation criteria
"""

from typing import List, Dict, Any, Optional
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession
import logging

logger = logging.getLogger(__name__)


class SimpleSurveyEngine:
    """
    Core engine for handling survey questions and responses.
    
    Provides functionality to:
    - Load questions for health or funeral insurance categories
    - Validate responses based on question type and rules
    - Save responses immediately to database
    - Process responses into quotation criteria
    """
    
    def __init__(self, category: str):
        """
        Initialize the survey engine for a specific category.
        
        Args:
            category: Either 'health' or 'funeral'
        
        Raises:
            ValueError: If category is not valid
        """
        if category not in ['health', 'funeral']:
            raise ValueError(f"Invalid category: {category}. Must be 'health' or 'funeral'")
        
        self.category = category
        self.questions = self._load_questions()
        logger.info(f"SimpleSurveyEngine initialized for category: {category}")
    
    def _load_questions(self) -> List[SimpleSurveyQuestion]:
        """
        Load all questions for the category from database.
        
        Returns:
            List of SimpleSurveyQuestion objects ordered by display_order
        """
        try:
            questions = SimpleSurveyQuestion.objects.for_category(self.category)
            logger.debug(f"Loaded {questions.count()} questions for category: {self.category}")
            return list(questions)
        except Exception as e:
            logger.error(f"Error loading questions for category {self.category}: {e}")
            return []
    
    def get_questions(self) -> List[Dict[str, Any]]:
        """
        Return all questions for the category as serialized dictionaries.
        
        Returns:
            List of question dictionaries with all necessary fields for frontend
        """
        return [self._serialize_question(question) for question in self.questions]
    
    def _serialize_question(self, question: SimpleSurveyQuestion) -> Dict[str, Any]:
        """
        Convert a SimpleSurveyQuestion model to a dictionary for JSON serialization.
        
        Args:
            question: SimpleSurveyQuestion instance
            
        Returns:
            Dictionary with question data for frontend consumption
        """
        return {
            'id': question.id,
            'question_text': question.question_text,
            'field_name': question.field_name,
            'input_type': question.input_type,
            'choices': question.get_choices_list(),
            'is_required': question.is_required,
            'display_order': question.display_order,
            'validation_rules': question.validation_rules,
            'category': question.category
        }
    
    def _get_question(self, question_id: int) -> Optional[SimpleSurveyQuestion]:
        """
        Get a specific question by ID.
        
        Args:
            question_id: ID of the question to retrieve
            
        Returns:
            SimpleSurveyQuestion instance or None if not found
        """
        try:
            return next((q for q in self.questions if q.id == question_id), None)
        except Exception as e:
            logger.error(f"Error getting question {question_id}: {e}")
            return None
    
    def validate_response(self, question_id: int, response: Any) -> Dict[str, Any]:
        """
        Validate a response for a specific question.
        
        Args:
            question_id: ID of the question being answered
            response: The user's response value
            
        Returns:
            Dictionary with validation results:
            {
                'is_valid': bool,
                'errors': List[str],
                'cleaned_value': Any (processed response value)
            }
        """
        question = self._get_question(question_id)
        if not question:
            return {
                'is_valid': False,
                'errors': ['Question not found'],
                'cleaned_value': None
            }
        
        try:
            # Use the model's validation method
            errors = question.validate_response(response)
            
            # Clean the response value based on input type
            cleaned_value = self._clean_response_value(question, response)
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'cleaned_value': cleaned_value
            }
            
        except Exception as e:
            logger.error(f"Error validating response for question {question_id}: {e}")
            return {
                'is_valid': False,
                'errors': ['Validation error occurred'],
                'cleaned_value': None
            }
    
    def _clean_response_value(self, question: SimpleSurveyQuestion, response: Any) -> Any:
        """
        Clean and normalize response value based on question type.
        
        Args:
            question: SimpleSurveyQuestion instance
            response: Raw response value
            
        Returns:
            Cleaned response value appropriate for the question type
        """
        if response is None or response == '':
            return None
        
        try:
            if question.input_type == 'number':
                # Convert to appropriate numeric type
                if '.' in str(response):
                    return float(response)
                else:
                    return int(response)
            
            elif question.input_type == 'checkbox':
                # Ensure checkbox responses are lists
                if isinstance(response, list):
                    return response
                elif isinstance(response, str):
                    # Handle comma-separated values
                    return [item.strip() for item in response.split(',') if item.strip()]
                else:
                    return [response]
            
            elif question.input_type in ['text', 'select', 'radio']:
                # Convert to string and strip whitespace
                return str(response).strip()
            
            else:
                return response
                
        except Exception as e:
            logger.warning(f"Error cleaning response value for question {question.id}: {e}")
            return response
    
    def save_response(self, session_key: str, question_id: int, response: Any) -> Dict[str, Any]:
        """
        Validate and save a response immediately to the database.
        
        Args:
            session_key: Session identifier for the user
            question_id: ID of the question being answered
            response: The user's response value
            
        Returns:
            Dictionary with save results:
            {
                'success': bool,
                'errors': List[str],
                'response_id': int (if successful)
            }
        """
        # First validate the response
        validation_result = self.validate_response(question_id, response)
        
        if not validation_result['is_valid']:
            return {
                'success': False,
                'errors': validation_result['errors'],
                'response_id': None
            }
        
        try:
            # Save or update the response
            response_obj, created = SimpleSurveyResponse.objects.update_or_create(
                session_key=session_key,
                question_id=question_id,
                defaults={
                    'category': self.category,
                    'response_value': validation_result['cleaned_value']
                }
            )
            
            action = "created" if created else "updated"
            logger.info(f"Response {action} for session {session_key[:8]}, question {question_id}")
            
            return {
                'success': True,
                'errors': [],
                'response_id': response_obj.id
            }
            
        except Exception as e:
            logger.error(f"Error saving response for session {session_key}, question {question_id}: {e}")
            return {
                'success': False,
                'errors': ['Failed to save response'],
                'response_id': None
            }
    
    def get_session_responses(self, session_key: str) -> Dict[str, Any]:
        """
        Get all responses for a session.
        
        Args:
            session_key: Session identifier
            
        Returns:
            Dictionary with session response data
        """
        try:
            responses = SimpleSurveyResponse.objects.for_session_category(
                session_key, self.category
            )
            
            response_data = {}
            for response in responses:
                response_data[response.question.field_name] = {
                    'question_id': response.question.id,
                    'value': response.response_value,
                    'display_value': response.get_display_value(),
                    'updated_at': response.updated_at.isoformat()
                }
            
            return {
                'session_key': session_key,
                'category': self.category,
                'responses': response_data,
                'total_responses': len(response_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting session responses for {session_key}: {e}")
            return {
                'session_key': session_key,
                'category': self.category,
                'responses': {},
                'total_responses': 0
            }
    
    def process_responses(self, session_key: str) -> Dict[str, Any]:
        """
        Convert session responses to quotation criteria format.
        
        Args:
            session_key: Session identifier
            
        Returns:
            Dictionary with processed criteria for quotation engine
        """
        try:
            responses = SimpleSurveyResponse.objects.for_session_category(
                session_key, self.category
            )
            
            criteria = {}
            for response in responses:
                field_name = response.question.field_name
                criteria[field_name] = response.response_value
            
            # Add metadata
            criteria['_metadata'] = {
                'category': self.category,
                'session_key': session_key,
                'processed_at': timezone.now().isoformat(),
                'total_responses': len(responses)  # Count actual responses, not criteria dict
            }
            
            logger.info(f"Processed {len(criteria)-1} responses for session {session_key[:8]}")
            return criteria
            
        except Exception as e:
            logger.error(f"Error processing responses for session {session_key}: {e}")
            return {
                '_metadata': {
                    'category': self.category,
                    'session_key': session_key,
                    'processed_at': timezone.now().isoformat(),
                    'error': str(e)
                }
            }
    
    def is_survey_complete(self, session_key: str) -> bool:
        """
        Check if all required questions have been answered for a session.
        
        Args:
            session_key: Session identifier
            
        Returns:
            True if all required questions are answered, False otherwise
        """
        try:
            # Get count of required questions
            required_count = SimpleSurveyQuestion.objects.filter(
                category=self.category,
                is_required=True
            ).count()
            
            # Get count of answered required questions
            answered_count = SimpleSurveyResponse.objects.filter(
                session_key=session_key,
                category=self.category,
                question__is_required=True
            ).count()
            
            is_complete = answered_count >= required_count
            logger.debug(f"Survey completion check for {session_key[:8]}: {answered_count}/{required_count} = {is_complete}")
            
            return is_complete
            
        except Exception as e:
            logger.error(f"Error checking survey completion for session {session_key}: {e}")
            return False
    
    def get_completion_status(self, session_key: str) -> Dict[str, Any]:
        """
        Get detailed completion status for a session.
        
        Args:
            session_key: Session identifier
            
        Returns:
            Dictionary with completion details
        """
        try:
            total_questions = len(self.questions)
            required_questions = sum(1 for q in self.questions if q.is_required)
            
            responses = SimpleSurveyResponse.objects.for_session_category(
                session_key, self.category
            )
            
            answered_total = responses.count()
            answered_required = responses.filter(question__is_required=True).count()
            
            is_complete = answered_required >= required_questions
            
            return {
                'session_key': session_key,
                'category': self.category,
                'is_complete': is_complete,
                'total_questions': total_questions,
                'required_questions': required_questions,
                'answered_total': answered_total,
                'answered_required': answered_required,
                'completion_percentage': int((answered_required / required_questions) * 100) if required_questions > 0 else 100
            }
            
        except Exception as e:
            logger.error(f"Error getting completion status for session {session_key}: {e}")
            return {
                'session_key': session_key,
                'category': self.category,
                'is_complete': False,
                'error': str(e)
            }