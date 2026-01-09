"""
Response Processor for Policy Comparison Surveys.
Converts survey responses to comparison criteria and generates dynamic weights.
"""

from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from django.db.models import Avg
from django.utils.translation import gettext_lazy as _
from comparison.models import ComparisonSession
from .models import SurveyResponse, SurveyQuestion
import logging
import json

logger = logging.getLogger(__name__)


class ResponseProcessor:
    """
    Processes survey responses and converts them to comparison engine criteria.
    Handles dynamic weight calculation and criteria mapping for different insurance categories.
    """
    
    def __init__(self, category_slug: str):
        """
        Initialize the response processor for a specific category.
        
        Args:
            category_slug: Slug of the policy category (health, funeral, etc.)
        """
        self.category_slug = category_slug
        self.mapping_rules = self._load_mapping_rules()
        
    def _load_mapping_rules(self) -> Dict[str, Any]:
        """
        Load category-specific mapping rules for converting survey responses to criteria.
        
        Returns:
            Dictionary containing mapping rules for the category
        """
        if self.category_slug == 'health':
            return self._get_health_mapping_rules()
        elif self.category_slug == 'funeral':
            return self._get_funeral_mapping_rules()
        else:
            # Default/generic mapping rules
            return self._get_default_mapping_rules()
    
    def _get_health_mapping_rules(self) -> Dict[str, Any]:
        """
        Get mapping rules for health insurance survey responses.
        
        Returns:
            Dictionary with health insurance specific mapping rules
        """
        return {
            # Direct field mappings (survey field -> policy field)
            'field_mappings': {
                'age': 'minimum_age',  # User age affects age eligibility scoring
                'monthly_budget': 'base_premium',
                'coverage_amount_preference': 'coverage_amount',
                'waiting_period_tolerance': 'waiting_period_days',
                'hospital_network_preference': 'hospital_networks',
                'chronic_medication_needed': 'chronic_medication_covered',
                'gp_visits_needed': 'gp_visits_per_year',
                'specialist_visits_needed': 'specialist_visits_per_year',
                'dental_cover_needed': 'includes_dental_cover',
                'optical_cover_needed': 'includes_optical_cover',
                'maternity_cover_needed': 'includes_maternity_cover',
                'mental_health_cover_needed': 'includes_mental_health_cover',
                'alternative_medicine_needed': 'includes_alternative_medicine',
                'hospital_cover_priority': 'includes_hospital_cover',
                'outpatient_cover_priority': 'includes_outpatient_cover'
            },
            
            # Weight calculation rules based on user priorities
            'priority_weights': {
                'very_high': 100,
                'high': 80,
                'medium': 60,
                'low': 40,
                'very_low': 20,
                'not_important': 0
            },
            
            # Confidence level adjustments
            'confidence_adjustments': {
                5: 1.0,    # Very confident - no adjustment
                4: 0.9,    # Confident - slight reduction
                3: 0.8,    # Neutral - moderate reduction
                2: 0.7,    # Not confident - significant reduction
                1: 0.5     # Very unsure - major reduction
            },
            
            # Special processing rules for complex responses
            'special_processing': {
                'health_conditions': {
                    'type': 'list_to_boolean',
                    'target_fields': ['chronic_conditions_covered', 'pre_existing_conditions_covered']
                },
                'family_size': {
                    'type': 'numeric_range',
                    'target_field': 'family_coverage_options'
                },
                'preferred_hospitals': {
                    'type': 'list_matching',
                    'target_field': 'hospital_networks'
                }
            }
        }
    
    def _get_funeral_mapping_rules(self) -> Dict[str, Any]:
        """
        Get mapping rules for funeral insurance survey responses.
        
        Returns:
            Dictionary with funeral insurance specific mapping rules
        """
        return {
            # Direct field mappings
            'field_mappings': {
                'monthly_budget': 'base_premium',
                'coverage_amount_preference': 'coverage_amount',
                'waiting_period_tolerance': 'waiting_period_days',
                'family_members_to_cover': 'family_coverage_size',
                'burial_preference': 'burial_cover_included',
                'cremation_preference': 'cremation_cover_included',
                'repatriation_needed': 'repatriation_cover_included',
                'memorial_service_needed': 'memorial_service_covered',
                'funeral_groceries_needed': 'funeral_groceries_covered',
                'tombstone_cover_needed': 'tombstone_cover_included',
                'inflation_protection_wanted': 'inflation_protection_included',
                'claim_payout_speed_importance': 'claim_processing_days'
            },
            
            # Priority weights
            'priority_weights': {
                'essential': 100,
                'very_important': 85,
                'important': 70,
                'somewhat_important': 50,
                'nice_to_have': 30,
                'not_needed': 0
            },
            
            # Confidence adjustments
            'confidence_adjustments': {
                5: 1.0,
                4: 0.9,
                3: 0.8,
                2: 0.7,
                1: 0.5
            },
            
            # Special processing
            'special_processing': {
                'service_preferences': {
                    'type': 'multi_choice_to_weights',
                    'target_fields': ['burial_cover_included', 'cremation_cover_included', 'memorial_service_covered']
                },
                'cultural_requirements': {
                    'type': 'text_to_boolean',
                    'target_field': 'cultural_requirements_covered'
                }
            }
        }
    
    def _get_default_mapping_rules(self) -> Dict[str, Any]:
        """
        Get default mapping rules for generic insurance categories.
        
        Returns:
            Dictionary with default mapping rules
        """
        return {
            'field_mappings': {
                'monthly_budget': 'base_premium',
                'coverage_amount_preference': 'coverage_amount',
                'waiting_period_tolerance': 'waiting_period_days'
            },
            'priority_weights': {
                'high': 80,
                'medium': 60,
                'low': 40
            },
            'confidence_adjustments': {
                5: 1.0,
                4: 0.9,
                3: 0.8,
                2: 0.7,
                1: 0.5
            },
            'special_processing': {}
        }
    
    def process_responses(self, session: ComparisonSession) -> Dict[str, Any]:
        """
        Process all survey responses for a session and generate comparison criteria.
        
        Args:
            session: ComparisonSession instance with survey responses
            
        Returns:
            Dictionary containing processed criteria, weights, and user profile
        """
        try:
            # Get all responses for this session
            responses = SurveyResponse.objects.filter(
                session=session,
                question__category__slug=self.category_slug
            ).select_related('question').order_by('question__display_order')
            
            if not responses.exists():
                logger.warning(f"No survey responses found for session {session.id}")
                return {
                    'success': False,
                    'criteria': {},
                    'weights': {},
                    'filters': {},
                    'user_profile': {},
                    'processed_responses': {},
                    'category': self.category_slug,
                    'total_responses': 0
                }
            
            # Process responses into structured data
            processed_data = self._structure_responses(responses)
            
            # Generate comparison criteria
            criteria = self._generate_criteria(processed_data)
            
            # Calculate dynamic weights
            weights = self._calculate_weights(processed_data)
            
            # Generate policy filters
            filters = self._generate_filters(processed_data)
            
            # Create user profile
            user_profile = self._create_user_profile(processed_data)
            
            return {
                'success': True,
                'criteria': criteria,
                'weights': weights,
                'filters': filters,
                'user_profile': user_profile,
                'processed_responses': processed_data,
                'category': self.category_slug,
                'total_responses': len(responses)
            }
            
        except Exception as e:
            logger.error(f"Error processing responses for session {session.id}: {str(e)}")
            return self._get_empty_criteria()
    
    def _get_empty_criteria(self) -> Dict[str, Any]:
        """
        Return empty criteria structure for error cases.
        
        Returns:
            Dictionary with empty criteria structure
        """
        return {
            'success': False,
            'criteria': {},
            'weights': {},
            'filters': {},
            'user_profile': {},
            'processed_responses': {},
            'category': self.category_slug,
            'total_responses': 0
        }
    
    def _structure_responses(self, responses: List[SurveyResponse]) -> Dict[str, Any]:
        """
        Structure raw survey responses into organized data.
        
        Args:
            responses: List of SurveyResponse objects
            
        Returns:
            Dictionary with structured response data
        """
        structured = {
            'responses_by_field': {},
            'responses_by_section': {},
            'confidence_levels': {},
            'priorities': {},
            'user_values': {}
        }
        
        for response in responses:
            field_name = response.question.field_name
            section = response.question.section
            
            # Store response by field name
            structured['responses_by_field'][field_name] = {
                'value': response.response_value,
                'confidence': response.confidence_level,
                'question_type': response.question.question_type,
                'weight_impact': float(response.question.weight_impact),
                'question_text': response.question.question_text
            }
            
            # Group by section
            if section not in structured['responses_by_section']:
                structured['responses_by_section'][section] = {}
            
            structured['responses_by_section'][section][field_name] = structured['responses_by_field'][field_name]
            
            # Store confidence levels
            structured['confidence_levels'][field_name] = response.confidence_level
            
            # Extract priorities from response values
            if self._is_priority_question(response.question, response.response_value):
                structured['priorities'][field_name] = response.response_value
            
            # Store user values for criteria generation
            structured['user_values'][field_name] = response.response_value
        
        return structured
    
    def _is_priority_question(self, question: SurveyQuestion, response_value: Any) -> bool:
        """
        Determine if a question response represents a priority level.
        
        Args:
            question: SurveyQuestion instance
            response_value: The response value
            
        Returns:
            Boolean indicating if this is a priority question
        """
        # Check if question text contains priority-related keywords
        priority_keywords = ['priority', 'importance', 'how important', 'rank', 'prefer']
        question_text_lower = question.question_text.lower()
        
        if any(keyword in question_text_lower for keyword in priority_keywords):
            return True
        
        # Check if response value matches priority scale values
        if isinstance(response_value, str):
            priority_values = ['very_high', 'high', 'medium', 'low', 'very_low', 'essential', 'important', 'not_important']
            if response_value.lower() in priority_values:
                return True
        
        # Check if it's a numeric scale (1-5, 1-10, etc.)
        if isinstance(response_value, (int, float)) and 1 <= response_value <= 10:
            return True
        
        return False
    
    def _generate_criteria(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comparison criteria from processed survey responses.
        
        Args:
            processed_data: Structured response data
            
        Returns:
            Dictionary with comparison criteria
        """
        criteria = {}
        field_mappings = self.mapping_rules.get('field_mappings', {})
        
        for survey_field, policy_field in field_mappings.items():
            if survey_field in processed_data['responses_by_field']:
                response_data = processed_data['responses_by_field'][survey_field]
                criteria[policy_field] = self._convert_response_to_criteria(
                    response_data['value'],
                    response_data['question_type'],
                    policy_field
                )
        
        # Handle special processing rules
        special_rules = self.mapping_rules.get('special_processing', {})
        for rule_name, rule_config in special_rules.items():
            if rule_name in processed_data['responses_by_field']:
                special_criteria = self._apply_special_processing(
                    processed_data['responses_by_field'][rule_name],
                    rule_config
                )
                criteria.update(special_criteria)
        
        return criteria
    
    def _convert_response_to_criteria(
        self,
        response_value: Any,
        question_type: str,
        policy_field: str
    ) -> Any:
        """
        Convert a survey response to comparison criteria format.
        
        Args:
            response_value: The survey response value
            question_type: Type of the survey question
            policy_field: Target policy field name
            
        Returns:
            Converted criteria value
        """
        if response_value is None:
            return None
        
        # Handle different question types
        if question_type == 'NUMBER':
            return float(response_value)
        
        elif question_type == 'RANGE':
            return float(response_value)
        
        elif question_type == 'BOOLEAN':
            return bool(response_value)
        
        elif question_type == 'CHOICE':
            # Convert choice to appropriate format
            if policy_field in ['base_premium', 'coverage_amount']:
                # Try to extract numeric value from choice
                return self._extract_numeric_from_choice(response_value)
            return response_value
        
        elif question_type == 'MULTI_CHOICE':
            # Return as list for multi-choice
            return response_value if isinstance(response_value, list) else [response_value]
        
        elif question_type == 'TEXT':
            return str(response_value)
        
        return response_value
    
    def _extract_numeric_from_choice(self, choice_value: str) -> Optional[float]:
        """
        Extract numeric value from choice text (e.g., "R500-R1000" -> 750).
        
        Args:
            choice_value: Choice text that may contain numeric values
            
        Returns:
            Extracted numeric value or None
        """
        import re
        
        if not isinstance(choice_value, str):
            return None
        
        # Look for numeric patterns
        numbers = re.findall(r'[\d,]+', choice_value.replace('R', '').replace(' ', ''))
        
        if len(numbers) == 1:
            # Single number
            return float(numbers[0].replace(',', ''))
        elif len(numbers) == 2:
            # Range - return midpoint
            try:
                min_val = float(numbers[0].replace(',', ''))
                max_val = float(numbers[1].replace(',', ''))
                return (min_val + max_val) / 2
            except ValueError:
                return None
        
        return None
    
    def _apply_special_processing(
        self,
        response_data: Dict[str, Any],
        rule_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply special processing rules for complex response types.
        
        Args:
            response_data: Response data dictionary
            rule_config: Special processing rule configuration
            
        Returns:
            Dictionary with processed criteria
        """
        criteria = {}
        processing_type = rule_config.get('type')
        
        if processing_type == 'list_to_boolean':
            # Convert list responses to boolean flags
            target_fields = rule_config.get('target_fields', [])
            response_list = response_data['value'] if isinstance(response_data['value'], list) else []
            
            for field in target_fields:
                # Check if any item in the list relates to this field
                criteria[field] = len(response_list) > 0
        
        elif processing_type == 'numeric_range':
            # Convert numeric response to range criteria
            target_field = rule_config.get('target_field')
            if target_field:
                value = response_data['value']
                if isinstance(value, (int, float)):
                    criteria[target_field] = {
                        'min': max(1, value - 1),
                        'max': value + 2
                    }
        
        elif processing_type == 'list_matching':
            # For list responses that need to match policy lists
            target_field = rule_config.get('target_field')
            if target_field:
                criteria[target_field] = response_data['value']
        
        elif processing_type == 'multi_choice_to_weights':
            # Convert multi-choice to individual field weights
            target_fields = rule_config.get('target_fields', [])
            selected_choices = response_data['value'] if isinstance(response_data['value'], list) else []
            
            for field in target_fields:
                # Check if this field is represented in the choices
                field_selected = any(choice for choice in selected_choices if field.replace('_', ' ') in choice.lower())
                criteria[field] = field_selected
        
        elif processing_type == 'text_to_boolean':
            # Convert text response to boolean
            target_field = rule_config.get('target_field')
            if target_field:
                text_value = str(response_data['value']).lower()
                criteria[target_field] = len(text_value.strip()) > 0 and text_value != 'none'
        
        return criteria
    
    def calculate_weights(self, responses: List[SurveyResponse]) -> Dict[str, float]:
        """
        Calculate dynamic weights based on user priorities and confidence levels.
        
        Args:
            responses: List of SurveyResponse objects
            
        Returns:
            Dictionary with field weights (0-100)
        """
        processed_data = self._structure_responses(responses)
        return self._calculate_weights(processed_data)
    
    def _calculate_weights(self, processed_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Internal method to calculate weights from processed data.
        
        Args:
            processed_data: Structured response data
            
        Returns:
            Dictionary with calculated weights
        """
        weights = {}
        priority_weights = self.mapping_rules.get('priority_weights', {})
        confidence_adjustments = self.mapping_rules.get('confidence_adjustments', {})
        field_mappings = self.mapping_rules.get('field_mappings', {})
        
        for survey_field, policy_field in field_mappings.items():
            if survey_field in processed_data['responses_by_field']:
                response_data = processed_data['responses_by_field'][survey_field]
                
                # Start with base weight from question
                base_weight = response_data.get('weight_impact', 50.0)
                
                # Adjust based on priority if this is a priority question
                if survey_field in processed_data['priorities']:
                    priority_value = processed_data['priorities'][survey_field]
                    priority_weight = self._get_priority_weight(priority_value, priority_weights)
                    if priority_weight is not None:
                        base_weight = priority_weight
                
                # Adjust based on confidence level
                confidence = response_data.get('confidence', 3)
                confidence_multiplier = confidence_adjustments.get(confidence, 0.8)
                
                # Calculate final weight
                final_weight = base_weight * confidence_multiplier
                weights[policy_field] = min(100.0, max(0.0, final_weight))
        
        # Normalize weights if they exceed reasonable totals
        total_weight = sum(weights.values())
        if total_weight > 500:  # Arbitrary threshold for normalization
            normalization_factor = 500 / total_weight
            weights = {field: weight * normalization_factor for field, weight in weights.items()}
        
        return weights
    
    def _get_priority_weight(self, priority_value: Any, priority_weights: Dict[str, int]) -> Optional[float]:
        """
        Convert priority value to weight.
        
        Args:
            priority_value: Priority value from survey response
            priority_weights: Mapping of priority levels to weights
            
        Returns:
            Weight value or None if not found
        """
        if isinstance(priority_value, str):
            return priority_weights.get(priority_value.lower())
        
        elif isinstance(priority_value, (int, float)):
            # Convert numeric scale to weight
            if 1 <= priority_value <= 5:
                # 5-point scale
                return priority_value * 20  # Convert to 0-100 scale
            elif 1 <= priority_value <= 10:
                # 10-point scale
                return priority_value * 10  # Convert to 0-100 scale
        
        return None
    
    def generate_filters(self, responses: List[SurveyResponse]) -> Dict[str, Any]:
        """
        Generate policy filters based on hard requirements from survey responses.
        
        Args:
            responses: List of SurveyResponse objects
            
        Returns:
            Dictionary with filter criteria for policy selection
        """
        processed_data = self._structure_responses(responses)
        return self._generate_filters(processed_data)
    
    def _generate_filters(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to generate filters from processed data.
        
        Args:
            processed_data: Structured response data
            
        Returns:
            Dictionary with filter criteria
        """
        filters = {}
        
        # Generate filters based on hard requirements
        for field_name, response_data in processed_data['responses_by_field'].items():
            value = response_data['value']
            confidence = response_data['confidence']
            
            # Only create filters for high-confidence responses
            if confidence >= 4:
                # Budget constraints (hard filter)
                if field_name == 'monthly_budget':
                    if isinstance(value, (int, float)):
                        filters['base_premium__lte'] = round(value * 1.1, 2)  # Allow 10% over budget
                    elif isinstance(value, str):
                        # Extract numeric value from choice string
                        numeric_value = self._extract_numeric_from_choice(value)
                        if numeric_value:
                            filters['base_premium__lte'] = round(numeric_value * 1.1, 2)
                
                # Age constraints
                elif field_name == 'age' and isinstance(value, (int, float)):
                    filters['minimum_age__lte'] = value
                    filters['maximum_age__gte'] = value
                
                # Boolean requirements
                elif response_data['question_type'] == 'BOOLEAN' and value is True:
                    # Map survey field to policy field
                    policy_field = self._get_policy_field_for_filter(field_name)
                    if policy_field:
                        filters[policy_field] = True
        
        return filters
    
    def _get_policy_field_for_filter(self, survey_field: str) -> Optional[str]:
        """
        Get the corresponding policy field name for filtering.
        
        Args:
            survey_field: Survey field name
            
        Returns:
            Policy field name or None
        """
        field_mappings = self.mapping_rules.get('field_mappings', {})
        return field_mappings.get(survey_field)
    
    def create_user_profile(self, responses: List[SurveyResponse]) -> Dict[str, Any]:
        """
        Create user profile for personalized explanations and recommendations.
        
        Args:
            responses: List of SurveyResponse objects
            
        Returns:
            Dictionary with user profile data
        """
        processed_data = self._structure_responses(responses)
        return self._create_user_profile(processed_data)
    
    def _create_user_profile(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to create user profile from processed data.
        
        Args:
            processed_data: Structured response data
            
        Returns:
            Dictionary with user profile information
        """
        profile = {
            'category': self.category_slug,
            'priorities': processed_data['priorities'],
            'confidence_levels': processed_data['confidence_levels'],
            'user_values': processed_data['user_values'],
            'sections_completed': list(processed_data['responses_by_section'].keys()),
            'total_responses': len(processed_data['responses_by_field']),
            'high_confidence_responses': len([
                r for r in processed_data['responses_by_field'].values()
                if r['confidence'] >= 4
            ]),
            'profile_strength': self._calculate_profile_strength(processed_data)
        }
        
        # Add category-specific profile data
        if self.category_slug == 'health':
            profile.update(self._create_health_profile(processed_data))
        elif self.category_slug == 'funeral':
            profile.update(self._create_funeral_profile(processed_data))
        
        return profile
    
    def _calculate_profile_strength(self, processed_data: Dict[str, Any]) -> float:
        """
        Calculate the strength/completeness of the user profile.
        
        Args:
            processed_data: Structured response data
            
        Returns:
            Profile strength score (0.0 to 1.0)
        """
        total_responses = len(processed_data['responses_by_field'])
        if total_responses == 0:
            return 0.0
        
        # Weight by confidence levels
        confidence_sum = sum(
            r['confidence'] for r in processed_data['responses_by_field'].values()
        )
        max_possible_confidence = total_responses * 5
        
        confidence_score = confidence_sum / max_possible_confidence if max_possible_confidence > 0 else 0
        
        # Weight by number of sections completed
        sections_completed = len(processed_data['responses_by_section'])
        expected_sections = 4  # Typical number of sections
        section_score = min(sections_completed / expected_sections, 1.0)
        
        # Combine scores
        return (confidence_score * 0.7) + (section_score * 0.3)
    
    def _create_health_profile(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create health insurance specific profile data.
        
        Args:
            processed_data: Structured response data
            
        Returns:
            Dictionary with health-specific profile data
        """
        health_profile = {}
        
        # Extract health-specific information
        responses = processed_data['responses_by_field']
        
        if 'age' in responses:
            health_profile['age_group'] = self._categorize_age(responses['age']['value'])
        
        if 'family_size' in responses:
            health_profile['family_type'] = self._categorize_family_size(responses['family_size']['value'])
        
        # Health priorities
        health_priorities = []
        priority_fields = ['hospital_cover_priority', 'outpatient_cover_priority', 'chronic_medication_needed']
        for field in priority_fields:
            if field in responses and responses[field]['value']:
                health_priorities.append(field.replace('_', ' ').title())
        
        health_profile['health_priorities'] = health_priorities
        
        return health_profile
    
    def _create_funeral_profile(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create funeral insurance specific profile data.
        
        Args:
            processed_data: Structured response data
            
        Returns:
            Dictionary with funeral-specific profile data
        """
        funeral_profile = {}
        
        responses = processed_data['responses_by_field']
        
        if 'family_members_to_cover' in responses:
            funeral_profile['coverage_scope'] = self._categorize_coverage_scope(
                responses['family_members_to_cover']['value']
            )
        
        # Service preferences
        service_preferences = []
        if 'burial_preference' in responses and responses['burial_preference']['value']:
            service_preferences.append('Burial')
        if 'cremation_preference' in responses and responses['cremation_preference']['value']:
            service_preferences.append('Cremation')
        
        funeral_profile['service_preferences'] = service_preferences
        
        return funeral_profile
    
    def _categorize_age(self, age: Any) -> str:
        """Categorize age into groups."""
        try:
            age_num = int(age)
            if age_num < 25:
                return 'Young Adult'
            elif age_num < 40:
                return 'Adult'
            elif age_num < 60:
                return 'Middle Age'
            else:
                return 'Senior'
        except (ValueError, TypeError):
            return 'Unknown'
    
    def _categorize_family_size(self, family_size: Any) -> str:
        """Categorize family size."""
        try:
            size = int(family_size)
            if size == 1:
                return 'Individual'
            elif size == 2:
                return 'Couple'
            elif size <= 4:
                return 'Small Family'
            else:
                return 'Large Family'
        except (ValueError, TypeError):
            return 'Unknown'
    
    def _categorize_coverage_scope(self, members: Any) -> str:
        """Categorize funeral coverage scope."""
        try:
            count = int(members)
            if count == 1:
                return 'Individual'
            elif count <= 4:
                return 'Small Family'
            elif count <= 6:
                return 'Extended Family'
            else:
                return 'Large Family'
        except (ValueError, TypeError):
            return 'Unknown'
    
    def _get_empty_criteria(self) -> Dict[str, Any]:
        """
        Return empty criteria structure for error cases.
        
        Returns:
            Dictionary with empty criteria structure
        """
        return {
            'criteria': {},
            'weights': {},
            'filters': {},
            'user_profile': {},
            'processed_responses': {},
            'category': self.category_slug,
            'total_responses': 0
        }