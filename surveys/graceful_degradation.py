"""
Graceful Degradation Utilities for Survey System.
Provides fallback mechanisms when survey processing fails or data is incomplete.
"""

import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from comparison.models import ComparisonSession
from policies.models import PolicyCategory
from .models import SurveyResponse, SurveyQuestion
from .error_handling import SurveyProcessingError, survey_error_handler

logger = logging.getLogger(__name__)


class GracefulDegradationManager:
    """
    Manages graceful degradation when survey processing fails.
    Provides fallback comparison mechanisms and partial data handling.
    """
    
    def __init__(self):
        self.fallback_cache_timeout = 3600  # 1 hour
    
    def handle_incomplete_survey_data(
        self,
        session: ComparisonSession,
        minimum_completion_threshold: float = 30.0
    ) -> Dict[str, Any]:
        """
        Handle incomplete survey data with appropriate fallback strategies.
        
        Args:
            session: ComparisonSession with incomplete data
            minimum_completion_threshold: Minimum completion percentage to proceed
            
        Returns:
            Handling strategy and available options
        """
        try:
            # Calculate current completion
            from .engine import SurveyEngine
            engine = SurveyEngine(session.category.slug)
            completion_percentage = engine.calculate_completion_percentage(session)
            
            # Get response analysis
            response_analysis = self._analyze_existing_responses(session)
            
            # Determine handling strategy based on completion and data quality
            if completion_percentage >= minimum_completion_threshold:
                if response_analysis['has_critical_data']:
                    return {
                        'strategy': 'proceed_with_partial',
                        'success': True,
                        'completion_percentage': completion_percentage,
                        'data_quality': response_analysis,
                        'message': 'Sufficient data available for personalized comparison',
                        'comparison_type': 'partial_personalized'
                    }
                else:
                    return {
                        'strategy': 'enhanced_basic',
                        'success': True,
                        'completion_percentage': completion_percentage,
                        'data_quality': response_analysis,
                        'message': 'Using enhanced basic comparison with available data',
                        'comparison_type': 'enhanced_basic'
                    }
            else:
                # Very low completion - offer options
                return {
                    'strategy': 'offer_options',
                    'success': False,
                    'completion_percentage': completion_percentage,
                    'data_quality': response_analysis,
                    'options': [
                        {
                            'type': 'continue_survey',
                            'message': 'Complete more questions for better recommendations',
                            'recommended': completion_percentage > 10
                        },
                        {
                            'type': 'basic_comparison',
                            'message': 'View basic comparison without personalization',
                            'recommended': True
                        },
                        {
                            'type': 'category_defaults',
                            'message': 'Use popular choices for your category',
                            'recommended': False
                        }
                    ],
                    'message': 'More information needed for personalized recommendations'
                }
                
        except Exception as e:
            logger.error(f"Error handling incomplete survey data: {str(e)}")
            return self._get_emergency_fallback(session, str(e))
    
    def _analyze_existing_responses(self, session: ComparisonSession) -> Dict[str, Any]:
        """
        Analyze existing responses to determine data quality and completeness.
        
        Args:
            session: ComparisonSession to analyze
            
        Returns:
            Analysis results including data quality metrics
        """
        try:
            responses = SurveyResponse.objects.filter(
                session=session
            ).select_related('question')
            
            if not responses.exists():
                return {
                    'has_critical_data': False,
                    'sections_completed': [],
                    'critical_sections_missing': [],
                    'response_count': 0,
                    'confidence_average': 0
                }
            
            # Analyze by section
            sections = {}
            total_confidence = 0
            confidence_count = 0
            
            for response in responses:
                section = response.question.section
                if section not in sections:
                    sections[section] = {
                        'responses': 0,
                        'total_weight': 0,
                        'avg_confidence': 0
                    }
                
                sections[section]['responses'] += 1
                sections[section]['total_weight'] += float(response.question.weight_impact)
                total_confidence += response.confidence_level
                confidence_count += 1
            
            # Determine critical sections based on category
            critical_sections = self._get_critical_sections(session.category.slug)
            completed_critical = [s for s in critical_sections if s in sections]
            missing_critical = [s for s in critical_sections if s not in sections]
            
            # Calculate average confidence
            avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0
            
            return {
                'has_critical_data': len(completed_critical) >= len(critical_sections) * 0.6,
                'sections_completed': list(sections.keys()),
                'critical_sections_completed': completed_critical,
                'critical_sections_missing': missing_critical,
                'response_count': responses.count(),
                'confidence_average': avg_confidence,
                'section_analysis': sections
            }
            
        except Exception as e:
            logger.error(f"Error analyzing responses: {str(e)}")
            return {
                'has_critical_data': False,
                'sections_completed': [],
                'critical_sections_missing': [],
                'response_count': 0,
                'confidence_average': 0,
                'error': str(e)
            }
    
    def _get_critical_sections(self, category_slug: str) -> List[str]:
        """Get critical sections for a category."""
        if category_slug == 'health':
            return ['Personal Information', 'Health Status', 'Coverage Preferences']
        elif category_slug == 'funeral':
            return ['Family Structure', 'Coverage Requirements', 'Budget & Payment']
        else:
            return ['Personal Information', 'Coverage Preferences']
    
    def implement_fallback_comparison(
        self,
        session: ComparisonSession,
        fallback_type: str = 'basic',
        available_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Implement fallback comparison when survey processing fails.
        
        Args:
            session: ComparisonSession instance
            fallback_type: Type of fallback to implement
            available_data: Any available survey data to incorporate
            
        Returns:
            Fallback implementation result
        """
        try:
            # Generate fallback criteria based on type and available data
            if fallback_type == 'partial_personalized' and available_data:
                criteria = self._generate_partial_personalized_criteria(session, available_data)
            elif fallback_type == 'enhanced_basic':
                criteria = self._generate_enhanced_basic_criteria(session, available_data)
            elif fallback_type == 'category_defaults':
                criteria = self._generate_category_default_criteria(session.category)
            else:
                criteria = self._generate_basic_criteria(session.category)
            
            # Update session with fallback criteria
            session.criteria = criteria
            session.fallback_mode = True
            session.fallback_type = fallback_type
            session.save(update_fields=['criteria', 'fallback_mode', 'fallback_type'])
            
            # Cache fallback information for user notification
            fallback_info = {
                'type': fallback_type,
                'timestamp': timezone.now().isoformat(),
                'criteria_count': len(criteria),
                'has_survey_data': bool(available_data),
                'message': self._get_fallback_message(fallback_type)
            }
            
            cache_key = f"fallback_info:{session.session_key}"
            cache.set(cache_key, fallback_info, self.fallback_cache_timeout)
            
            return {
                'success': True,
                'fallback_type': fallback_type,
                'criteria': criteria,
                'fallback_info': fallback_info,
                'comparison_available': True,
                'message': fallback_info['message']
            }
            
        except Exception as e:
            logger.error(f"Error implementing fallback comparison: {str(e)}")
            return self._get_emergency_fallback(session, str(e))
    
    def _generate_partial_personalized_criteria(
        self,
        session: ComparisonSession,
        available_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate criteria using partial survey data."""
        try:
            # Start with basic criteria
            criteria = self._generate_basic_criteria(session.category)
            
            # Get existing responses to personalize
            responses = SurveyResponse.objects.filter(
                session=session
            ).select_related('question')
            
            # Process responses to adjust criteria
            for response in responses:
                field_name = response.question.field_name
                response_value = response.response_value
                confidence = response.confidence_level
                weight_impact = float(response.question.weight_impact)
                
                # Adjust criteria based on response
                if field_name == 'budget_range' and isinstance(response_value, (int, float)):
                    criteria['max_premium'] = response_value
                    criteria['premium_weight'] = min(0.6, criteria.get('premium_weight', 0.3) + 0.1)
                
                elif field_name == 'coverage_priority' and response_value:
                    if 'high' in str(response_value).lower():
                        criteria['coverage_weight'] = 0.5
                        criteria['min_coverage'] = criteria.get('min_coverage', 50000) * 1.2
                
                elif field_name == 'deductible_preference':
                    criteria['preferred_deductible'] = response_value
                    criteria['deductible_weight'] = weight_impact * 0.1
                
                # Adjust weights based on confidence
                confidence_multiplier = confidence / 5.0  # Normalize to 0-1
                for key in criteria:
                    if key.endswith('_weight'):
                        criteria[key] = criteria[key] * (0.8 + 0.4 * confidence_multiplier)
            
            # Normalize weights
            total_weight = sum(v for k, v in criteria.items() if k.endswith('_weight'))
            if total_weight > 1.0:
                for key in criteria:
                    if key.endswith('_weight'):
                        criteria[key] = criteria[key] / total_weight
            
            criteria['personalization_level'] = 'partial'
            criteria['data_sources'] = ['survey_partial', 'category_defaults']
            
            return criteria
            
        except Exception as e:
            logger.error(f"Error generating partial personalized criteria: {str(e)}")
            return self._generate_basic_criteria(session.category)
    
    def _generate_enhanced_basic_criteria(
        self,
        session: ComparisonSession,
        available_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate enhanced basic criteria with any available data."""
        criteria = self._generate_basic_criteria(session.category)
        
        # Enhance with category-specific intelligence
        if session.category.slug == 'health':
            criteria.update({
                'hospital_network_weight': 0.15,
                'day_to_day_weight': 0.25,
                'chronic_condition_weight': 0.1,
                'family_coverage_weight': 0.1
            })
        elif session.category.slug == 'funeral':
            criteria.update({
                'waiting_period_weight': 0.15,
                'payout_speed_weight': 0.1,
                'family_size_weight': 0.1,
                'repatriation_weight': 0.05
            })
        
        criteria['personalization_level'] = 'enhanced_basic'
        criteria['data_sources'] = ['category_intelligence', 'popular_choices']
        
        return criteria
    
    def _generate_category_default_criteria(self, category: PolicyCategory) -> Dict[str, Any]:
        """Generate default criteria for a category."""
        criteria = self._generate_basic_criteria(category)
        
        # Add category-specific defaults based on popular choices
        # This would typically come from analytics data
        if category.slug == 'health':
            criteria.update({
                'preferred_hospital_type': 'private',
                'preferred_excess': 'medium',
                'day_to_day_priority': 'medium'
            })
        elif category.slug == 'funeral':
            criteria.update({
                'preferred_coverage_amount': 25000,
                'preferred_waiting_period': 12,
                'family_coverage': True
            })
        
        criteria['personalization_level'] = 'category_default'
        criteria['data_sources'] = ['category_defaults', 'popular_choices']
        
        return criteria
    
    def _generate_basic_criteria(self, category: PolicyCategory) -> Dict[str, Any]:
        """Generate basic comparison criteria."""
        if category.slug == 'health':
            return {
                'premium_weight': 0.35,
                'coverage_weight': 0.40,
                'deductible_weight': 0.15,
                'network_weight': 0.10,
                'max_premium': 800,
                'min_coverage': 100000,
                'preferred_deductible': 'medium',
                'personalization_level': 'basic',
                'data_sources': ['system_defaults']
            }
        elif category.slug == 'funeral':
            return {
                'premium_weight': 0.45,
                'coverage_weight': 0.40,
                'waiting_period_weight': 0.15,
                'max_premium': 150,
                'min_coverage': 15000,
                'max_waiting_period': 24,
                'personalization_level': 'basic',
                'data_sources': ['system_defaults']
            }
        else:
            return {
                'premium_weight': 0.50,
                'coverage_weight': 0.50,
                'max_premium': 500,
                'min_coverage': 50000,
                'personalization_level': 'basic',
                'data_sources': ['system_defaults']
            }
    
    def _get_fallback_message(self, fallback_type: str) -> str:
        """Get user-friendly message for fallback type."""
        messages = {
            'partial_personalized': 'Using your available responses for personalized recommendations',
            'enhanced_basic': 'Using enhanced comparison based on your category preferences',
            'category_defaults': 'Using popular choices for your insurance category',
            'basic': 'Using basic comparison to show all available options'
        }
        return messages.get(fallback_type, 'Using alternative comparison method')
    
    def _get_emergency_fallback(self, session: ComparisonSession, error: str) -> Dict[str, Any]:
        """Get emergency fallback when all else fails."""
        try:
            # Minimal basic criteria
            criteria = {
                'premium_weight': 0.6,
                'coverage_weight': 0.4,
                'max_premium': 1000,
                'min_coverage': 25000,
                'personalization_level': 'emergency',
                'data_sources': ['emergency_fallback']
            }
            
            session.criteria = criteria
            session.fallback_mode = True
            session.fallback_type = 'emergency'
            session.save(update_fields=['criteria', 'fallback_mode', 'fallback_type'])
            
            return {
                'success': True,
                'fallback_type': 'emergency',
                'criteria': criteria,
                'comparison_available': True,
                'message': 'Using basic comparison due to technical issues',
                'error': error
            }
            
        except Exception as e:
            logger.critical(f"Emergency fallback failed: {str(e)}")
            return {
                'success': False,
                'fallback_type': 'failed',
                'comparison_available': False,
                'message': 'Comparison temporarily unavailable',
                'error': str(e)
            }
    
    def get_fallback_info(self, session_key: str) -> Optional[Dict[str, Any]]:
        """Get fallback information for a session."""
        cache_key = f"fallback_info:{session_key}"
        return cache.get(cache_key)
    
    def clear_fallback_info(self, session_key: str):
        """Clear fallback information from cache."""
        cache_key = f"fallback_info:{session_key}"
        cache.delete(cache_key)
    
    def validate_fallback_criteria(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate fallback criteria to ensure they're usable.
        
        Args:
            criteria: Criteria dictionary to validate
            
        Returns:
            Validation result
        """
        try:
            required_fields = ['premium_weight', 'coverage_weight']
            missing_fields = [field for field in required_fields if field not in criteria]
            
            if missing_fields:
                return {
                    'is_valid': False,
                    'errors': [f'Missing required field: {field}' for field in missing_fields]
                }
            
            # Check weight values
            weight_fields = [k for k in criteria.keys() if k.endswith('_weight')]
            total_weight = sum(criteria[field] for field in weight_fields)
            
            if total_weight <= 0:
                return {
                    'is_valid': False,
                    'errors': ['Total weight must be greater than 0']
                }
            
            # Check for reasonable values
            warnings = []
            if total_weight > 1.2:
                warnings.append('Total weights exceed 1.0 - will be normalized')
            
            if criteria.get('max_premium', 0) <= 0:
                warnings.append('Max premium should be greater than 0')
            
            return {
                'is_valid': True,
                'errors': [],
                'warnings': warnings,
                'total_weight': total_weight
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f'Validation error: {str(e)}']
            }


# Global instance
graceful_degradation_manager = GracefulDegradationManager()