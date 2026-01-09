"""
Survey Engine for Policy Comparison Surveys.
Manages question loading, response validation, and survey completion tracking.
Includes performance optimizations with caching and lazy loading.
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional, Union
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from .models import (
    SurveyTemplate, SurveyQuestion, SurveyResponse, 
    TemplateQuestion, QuestionDependency
)
from .caching import (
    SurveyCacheManager, LazyQuestionLoader, 
    ResponseProcessingCache, performance_optimizer
)
import logging
import json

logger = logging.getLogger(__name__)


class SurveyEngine:
    """
    Core survey engine for managing question loading and response validation.
    Handles different question types and provides survey completion tracking.
    """
    
    # Question type handlers mapping
    QUESTION_TYPE_HANDLERS = {
        'TEXT': '_handle_text_question',
        'NUMBER': '_handle_number_question', 
        'CHOICE': '_handle_choice_question',
        'MULTI_CHOICE': '_handle_multi_choice_question',
        'RANGE': '_handle_range_question',
        'BOOLEAN': '_handle_boolean_question'
    }
    
    def __init__(self, category_slug: str):
        """
        Initialize the survey engine for a specific category.
        
        Args:
            category_slug: Slug of the policy category (health, funeral, etc.)
        """
        self.category_slug = category_slug
        self.category = None
        self.template = None
        self.cache_manager = SurveyCacheManager()
        self.lazy_loader = LazyQuestionLoader(category_slug, self.cache_manager)
        self.response_cache = ResponseProcessingCache(self.cache_manager)
        self._load_category()
        self._load_template()
    
    def _load_category(self):
        """Load the policy category."""
        try:
            self.category = PolicyCategory.objects.get(slug=self.category_slug)
        except PolicyCategory.DoesNotExist:
            raise ValueError(f"Policy category '{self.category_slug}' not found")
    
    def _load_template(self):
        """Load the active survey template for the category."""
        try:
            self.template = SurveyTemplate.objects.get(
                category=self.category,
                is_active=True
            )
        except SurveyTemplate.DoesNotExist:
            logger.warning(f"No active survey template found for category '{self.category_slug}'")
            self.template = None
        except SurveyTemplate.MultipleObjectsReturned:
            # Get the most recent one
            self.template = SurveyTemplate.objects.filter(
                category=self.category,
                is_active=True
            ).order_by('-created_at').first()
    
    def get_survey_sections(self) -> List[Dict[str, Any]]:
        """
        Return organized survey sections with questions.
        
        Returns:
            List of dictionaries containing section information and questions
        """
        if not self.template:
            return []
        
        # Get all questions for this template, ordered by display_order
        template_questions = TemplateQuestion.objects.filter(
            template=self.template
        ).select_related('question').order_by('display_order')
        
        # Group questions by section
        sections = {}
        for tq in template_questions:
            question = tq.question
            if not question.is_active:
                continue
                
            section_name = question.section
            if section_name not in sections:
                sections[section_name] = {
                    'name': section_name,
                    'questions': []
                }
            
            # Prepare question data
            question_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'field_name': question.field_name,
                'choices': question.choices,
                'validation_rules': question.validation_rules,
                'help_text': question.help_text,
                'is_required': tq.is_required,  # Use template override if available
                'display_order': tq.display_order,
                'weight_impact': float(question.weight_impact)
            }
            
            sections[section_name]['questions'].append(question_data)
        
        # Convert to list and sort by first question's display order
        section_list = []
        for section_name, section_data in sections.items():
            if section_data['questions']:
                # Sort questions within section by display order
                section_data['questions'].sort(key=lambda q: q['display_order'])
                section_list.append(section_data)
        
        # Sort sections by the display order of their first question
        section_list.sort(key=lambda s: s['questions'][0]['display_order'] if s['questions'] else 0)
        
        return section_list
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific question by ID with validation rules.
        
        Args:
            question_id: ID of the question to retrieve
            
        Returns:
            Question data dictionary or None if not found
        """
        try:
            question = SurveyQuestion.objects.get(
                id=question_id,
                category=self.category,
                is_active=True
            )
            
            return {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'field_name': question.field_name,
                'choices': question.choices,
                'validation_rules': question.validation_rules,
                'help_text': question.help_text,
                'is_required': question.is_required,
                'weight_impact': float(question.weight_impact)
            }
        except SurveyQuestion.DoesNotExist:
            return None
    
    def validate_response(self, question_id: int, response: Any) -> Dict[str, Any]:
        """
        Validate user response against question rules.
        
        Args:
            question_id: ID of the question being answered
            response: User's response value
            
        Returns:
            Dictionary with validation result and any error messages
        """
        question_data = self.get_question_by_id(question_id)
        if not question_data:
            return {
                'is_valid': False,
                'errors': ['Question not found'],
                'cleaned_value': None
            }
        
        # Check if response is required
        if question_data['is_required'] and (response is None or response == ''):
            return {
                'is_valid': False,
                'errors': ['This question is required'],
                'cleaned_value': None
            }
        
        # If not required and empty, return valid
        if not question_data['is_required'] and (response is None or response == ''):
            return {
                'is_valid': True,
                'errors': [],
                'cleaned_value': None
            }
        
        # Validate based on question type
        question_type = question_data['question_type']
        handler_method = self.QUESTION_TYPE_HANDLERS.get(question_type)
        
        if not handler_method:
            return {
                'is_valid': False,
                'errors': [f'Unsupported question type: {question_type}'],
                'cleaned_value': None
            }
        
        try:
            return getattr(self, handler_method)(question_data, response)
        except Exception as e:
            logger.error(f"Error validating response for question {question_id}: {str(e)}")
            return {
                'is_valid': False,
                'errors': ['Validation error occurred'],
                'cleaned_value': None
            }
    
    def _handle_text_question(self, question_data: Dict, response: Any) -> Dict[str, Any]:
        """Handle TEXT question type validation."""
        if not isinstance(response, str):
            response = str(response) if response is not None else ''
        
        validation_rules = question_data.get('validation_rules', {})
        errors = []
        
        # Check minimum length
        min_length = validation_rules.get('min_length')
        if min_length and len(response) < min_length:
            errors.append(f'Response must be at least {min_length} characters long')
        
        # Check maximum length
        max_length = validation_rules.get('max_length')
        if max_length and len(response) > max_length:
            errors.append(f'Response must be no more than {max_length} characters long')
        
        # Check pattern if specified
        pattern = validation_rules.get('pattern')
        if pattern:
            import re
            if not re.match(pattern, response):
                pattern_description = validation_rules.get('pattern_description', 'Invalid format')
                errors.append(pattern_description)
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'cleaned_value': response.strip() if response else None
        }
    
    def _handle_number_question(self, question_data: Dict, response: Any) -> Dict[str, Any]:
        """Handle NUMBER question type validation."""
        validation_rules = question_data.get('validation_rules', {})
        errors = []
        
        # Convert to number
        try:
            if isinstance(response, str):
                # Handle decimal separator variations
                response = response.replace(',', '.')
            cleaned_value = Decimal(str(response))
        except (ValueError, TypeError, Exception):
            return {
                'is_valid': False,
                'errors': ['Please enter a valid number'],
                'cleaned_value': None
            }
        
        # Check minimum value
        min_value = validation_rules.get('min_value')
        if min_value is not None and cleaned_value < Decimal(str(min_value)):
            errors.append(f'Value must be at least {min_value}')
        
        # Check maximum value
        max_value = validation_rules.get('max_value')
        if max_value is not None and cleaned_value > Decimal(str(max_value)):
            errors.append(f'Value must be no more than {max_value}')
        
        # Check decimal places
        decimal_places = validation_rules.get('decimal_places')
        if decimal_places is not None:
            # Count decimal places
            decimal_part = str(cleaned_value).split('.')
            if len(decimal_part) > 1 and len(decimal_part[1]) > decimal_places:
                errors.append(f'Maximum {decimal_places} decimal places allowed')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'cleaned_value': float(cleaned_value) if len(errors) == 0 else None
        }
    
    def _handle_choice_question(self, question_data: Dict, response: Any) -> Dict[str, Any]:
        """Handle CHOICE (single choice) question type validation."""
        choices = question_data.get('choices', [])
        if not choices:
            return {
                'is_valid': False,
                'errors': ['No choices available for this question'],
                'cleaned_value': None
            }
        
        # Extract choice values (choices can be strings or objects with 'value' key)
        valid_choices = []
        for choice in choices:
            if isinstance(choice, dict):
                valid_choices.append(choice.get('value'))
            else:
                valid_choices.append(choice)
        
        if response not in valid_choices:
            return {
                'is_valid': False,
                'errors': ['Please select a valid option'],
                'cleaned_value': None
            }
        
        return {
            'is_valid': True,
            'errors': [],
            'cleaned_value': response
        }
    
    def _handle_multi_choice_question(self, question_data: Dict, response: Any) -> Dict[str, Any]:
        """Handle MULTI_CHOICE question type validation."""
        choices = question_data.get('choices', [])
        validation_rules = question_data.get('validation_rules', {})
        
        if not choices:
            return {
                'is_valid': False,
                'errors': ['No choices available for this question'],
                'cleaned_value': None
            }
        
        # Ensure response is a list
        if not isinstance(response, list):
            return {
                'is_valid': False,
                'errors': ['Multiple choice response must be a list'],
                'cleaned_value': None
            }
        
        # Extract valid choice values
        valid_choices = []
        for choice in choices:
            if isinstance(choice, dict):
                valid_choices.append(choice.get('value'))
            else:
                valid_choices.append(choice)
        
        errors = []
        
        # Check if all selected choices are valid
        for selected in response:
            if selected not in valid_choices:
                errors.append(f'Invalid choice: {selected}')
        
        # Check minimum selections
        min_selections = validation_rules.get('min_selections')
        if min_selections and len(response) < min_selections:
            errors.append(f'Please select at least {min_selections} option(s)')
        
        # Check maximum selections
        max_selections = validation_rules.get('max_selections')
        if max_selections and len(response) > max_selections:
            errors.append(f'Please select no more than {max_selections} option(s)')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'cleaned_value': response if len(errors) == 0 else None
        }
    
    def _handle_range_question(self, question_data: Dict, response: Any) -> Dict[str, Any]:
        """Handle RANGE (slider) question type validation."""
        validation_rules = question_data.get('validation_rules', {})
        
        # Convert to number
        try:
            cleaned_value = float(response)
        except (ValueError, TypeError):
            return {
                'is_valid': False,
                'errors': ['Please enter a valid number'],
                'cleaned_value': None
            }
        
        errors = []
        
        # Check range bounds
        min_value = validation_rules.get('min_value', 0)
        max_value = validation_rules.get('max_value', 100)
        
        if cleaned_value < min_value:
            errors.append(f'Value must be at least {min_value}')
        
        if cleaned_value > max_value:
            errors.append(f'Value must be no more than {max_value}')
        
        # Check step if specified
        step = validation_rules.get('step')
        if step and (cleaned_value - min_value) % step != 0:
            errors.append(f'Value must be in increments of {step}')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'cleaned_value': cleaned_value if len(errors) == 0 else None
        }
    
    def _handle_boolean_question(self, question_data: Dict, response: Any) -> Dict[str, Any]:
        """Handle BOOLEAN (yes/no) question type validation."""
        # Convert various boolean representations
        if isinstance(response, bool):
            cleaned_value = response
        elif isinstance(response, str):
            response_lower = response.lower().strip()
            if response_lower in ['true', 'yes', 'y', '1']:
                cleaned_value = True
            elif response_lower in ['false', 'no', 'n', '0']:
                cleaned_value = False
            else:
                return {
                    'is_valid': False,
                    'errors': ['Please select Yes or No'],
                    'cleaned_value': None
                }
        elif isinstance(response, (int, float)):
            cleaned_value = bool(response)
        else:
            return {
                'is_valid': False,
                'errors': ['Please select Yes or No'],
                'cleaned_value': None
            }
        
        return {
            'is_valid': True,
            'errors': [],
            'cleaned_value': cleaned_value
        }
    
    def save_response(
        self, 
        session: ComparisonSession, 
        question_id: int, 
        response: Any,
        confidence_level: int = 3
    ) -> Dict[str, Any]:
        """
        Save validated response to database.
        
        Args:
            session: ComparisonSession instance
            question_id: ID of the question being answered
            response: User's response value
            confidence_level: User's confidence in their answer (1-5)
            
        Returns:
            Dictionary with save result and any error messages
        """
        # Validate the response first
        validation_result = self.validate_response(question_id, response)
        
        if not validation_result['is_valid']:
            return {
                'success': False,
                'errors': validation_result['errors']
            }
        
        try:
            # Get the question
            question = SurveyQuestion.objects.get(
                id=question_id,
                category=self.category,
                is_active=True
            )
            
            # Validate confidence level
            if not (1 <= confidence_level <= 5):
                confidence_level = 3  # Default to neutral
            
            # Save or update the response
            survey_response, created = SurveyResponse.objects.update_or_create(
                session=session,
                question=question,
                defaults={
                    'response_value': validation_result['cleaned_value'],
                    'confidence_level': confidence_level
                }
            )
            
            # Update session progress
            self._update_session_progress(session)
            
            return {
                'success': True,
                'response_id': survey_response.id,
                'created': created,
                'errors': []
            }
            
        except SurveyQuestion.DoesNotExist:
            return {
                'success': False,
                'errors': ['Question not found']
            }
        except Exception as e:
            logger.error(f"Error saving response for question {question_id}: {str(e)}")
            return {
                'success': False,
                'errors': ['Failed to save response']
            }
    
    def calculate_completion_percentage(self, session: ComparisonSession) -> float:
        """
        Calculate survey completion percentage for a session.
        
        Args:
            session: ComparisonSession instance
            
        Returns:
            Completion percentage (0.0 to 100.0)
        """
        if not self.template:
            return 0.0
        
        # Get total number of questions in the template
        total_questions = TemplateQuestion.objects.filter(
            template=self.template,
            question__is_active=True
        ).count()
        
        if total_questions == 0:
            return 100.0  # No questions = 100% complete
        
        # Get number of answered questions for this session
        answered_questions = SurveyResponse.objects.filter(
            session=session,
            question__category=self.category,
            question__is_active=True
        ).count()
        
        # Calculate percentage
        completion_percentage = (answered_questions / total_questions) * 100
        return min(100.0, max(0.0, completion_percentage))
    
    def _update_session_progress(self, session: ComparisonSession):
        """Update session progress tracking."""
        completion_percentage = self.calculate_completion_percentage(session)
        responses_count = SurveyResponse.objects.filter(
            session=session,
            question__category=self.category
        ).count()
        
        session.update_survey_progress(
            responses_count=responses_count,
            completion_percentage=completion_percentage
        )
    
    def get_session_responses(self, session: ComparisonSession) -> Dict[str, Any]:
        """
        Get all responses for a session organized by section.
        
        Args:
            session: ComparisonSession instance
            
        Returns:
            Dictionary with responses organized by section
        """
        responses = SurveyResponse.objects.filter(
            session=session,
            question__category=self.category
        ).select_related('question').order_by('question__display_order')
        
        # Organize by section
        sections = {}
        for response in responses:
            section_name = response.question.section
            if section_name not in sections:
                sections[section_name] = []
            
            sections[section_name].append({
                'question_id': response.question.id,
                'field_name': response.question.field_name,
                'question_text': response.question.question_text,
                'question_type': response.question.question_type,
                'response_value': response.response_value,
                'confidence_level': response.confidence_level,
                'created_at': response.created_at,
                'updated_at': response.updated_at
            })
        
        return sections
    
    def check_conditional_questions(
        self, 
        session: ComparisonSession, 
        parent_question_id: int, 
        parent_response: Any
    ) -> List[int]:
        """
        Check which conditional questions should be shown based on parent response.
        
        Args:
            session: ComparisonSession instance
            parent_question_id: ID of the parent question
            parent_response: Response value for the parent question
            
        Returns:
            List of question IDs that should be shown
        """
        dependencies = QuestionDependency.objects.filter(
            parent_question_id=parent_question_id,
            is_active=True
        )
        
        questions_to_show = []
        for dependency in dependencies:
            if dependency.evaluate_condition(parent_response):
                questions_to_show.append(dependency.child_question.id)
        
        return questions_to_show
    
    def get_survey_summary(self, session: ComparisonSession) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the survey state for a session.
        
        Args:
            session: ComparisonSession instance
            
        Returns:
            Dictionary with survey summary information
        """
        completion_percentage = self.calculate_completion_percentage(session)
        responses = self.get_session_responses(session)
        
        # Count responses by section
        section_stats = {}
        total_responses = 0
        
        for section_name, section_responses in responses.items():
            section_stats[section_name] = {
                'responses_count': len(section_responses),
                'latest_response': max(
                    (r['updated_at'] for r in section_responses),
                    default=None
                )
            }
            total_responses += len(section_responses)
        
        return {
            'completion_percentage': completion_percentage,
            'total_responses': total_responses,
            'sections': section_stats,
            'is_completed': completion_percentage >= 100.0,
            'category': self.category_slug,
            'template_name': self.template.name if self.template else None,
            'last_updated': session.updated_at
        }