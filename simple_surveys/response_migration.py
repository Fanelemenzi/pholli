"""
Response Migration Handler for Simple Survey System.

This module handles the migration of existing user survey responses from the old
binary question format to the new benefit level and range-based format.

Requirements: 6.3, 6.4, 6.5, 6.6
"""

from typing import Dict, List, Any, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import logging

from .models import (
    SimpleSurvey, SimpleSurveyResponse, SimpleSurveyQuestion, QuotationSession,
    HOSPITAL_BENEFIT_CHOICES, OUT_HOSPITAL_BENEFIT_CHOICES,
    ANNUAL_LIMIT_FAMILY_RANGES, ANNUAL_LIMIT_MEMBER_RANGES
)

logger = logging.getLogger(__name__)


class ResponseMigrationHandler:
    """
    Handles migration of existing survey responses to new question format.
    
    This class provides functionality to:
    - Detect users with old format responses
    - Migrate responses where possible
    - Provide UI for users to update unmigrated responses
    - Handle mixed old/new response scenarios
    """
    
    def __init__(self, category: str):
        """
        Initialize migration handler for specific category.
        
        Args:
            category: Insurance category ('health' or 'funeral')
        """
        self.category = category
    
    def check_migration_status(self, session_key: str) -> Dict[str, Any]:
        """
        Check migration status for a user session.
        
        Args:
            session_key: User session identifier
            
        Returns:
            Dictionary with migration status information
            
        Requirements: 6.3, 6.4
        """
        try:
            # Get all responses for this session and category
            responses = SimpleSurveyResponse.objects.filter(
                session_key=session_key,
                category=self.category
            ).select_related('question')
            
            if not responses.exists():
                return {
                    'status': 'no_responses',
                    'needs_migration': False,
                    'can_auto_migrate': False,
                    'requires_user_input': False,
                    'message': 'No existing responses found'
                }
            
            # Check for old format questions
            old_format_fields = self._get_old_format_fields()
            new_format_fields = self._get_new_format_fields()
            
            old_responses = []
            new_responses = []
            mixed_responses = []
            
            for response in responses:
                field_name = response.question.field_name
                
                if field_name in old_format_fields:
                    old_responses.append(response)
                elif field_name in new_format_fields:
                    new_responses.append(response)
                else:
                    mixed_responses.append(response)
            
            # Determine migration status
            has_old = len(old_responses) > 0
            has_new = len(new_responses) > 0
            
            if has_old and not has_new:
                # Pure old format - can attempt auto-migration
                return {
                    'status': 'old_format',
                    'needs_migration': True,
                    'can_auto_migrate': True,
                    'requires_user_input': False,
                    'old_responses': len(old_responses),
                    'message': 'Responses in old format - can be automatically migrated'
                }
            elif has_old and has_new:
                # Mixed format - needs user review
                return {
                    'status': 'mixed_format',
                    'needs_migration': True,
                    'can_auto_migrate': False,
                    'requires_user_input': True,
                    'old_responses': len(old_responses),
                    'new_responses': len(new_responses),
                    'message': 'Mixed old and new format responses - user review required'
                }
            elif has_new and not has_old:
                # Pure new format - no migration needed
                return {
                    'status': 'new_format',
                    'needs_migration': False,
                    'can_auto_migrate': False,
                    'requires_user_input': False,
                    'new_responses': len(new_responses),
                    'message': 'Responses already in new format'
                }
            else:
                # Unknown format
                return {
                    'status': 'unknown_format',
                    'needs_migration': False,
                    'can_auto_migrate': False,
                    'requires_user_input': True,
                    'mixed_responses': len(mixed_responses),
                    'message': 'Unknown response format - manual review required'
                }
                
        except Exception as e:
            logger.error(f"Error checking migration status for session {session_key}: {e}")
            return {
                'status': 'error',
                'needs_migration': False,
                'can_auto_migrate': False,
                'requires_user_input': True,
                'message': f'Error checking migration status: {str(e)}'
            }
    
    def auto_migrate_responses(self, session_key: str) -> Dict[str, Any]:
        """
        Automatically migrate old format responses to new format.
        
        Args:
            session_key: User session identifier
            
        Returns:
            Dictionary with migration results
            
        Requirements: 6.1, 6.3
        """
        try:
            with transaction.atomic():
                # Get migration status first
                status = self.check_migration_status(session_key)
                
                if not status['can_auto_migrate']:
                    return {
                        'success': False,
                        'error': 'Cannot auto-migrate responses',
                        'status': status['status'],
                        'message': status['message']
                    }
                
                # Get old format responses
                old_responses = SimpleSurveyResponse.objects.filter(
                    session_key=session_key,
                    category=self.category,
                    question__field_name__in=self._get_old_format_fields()
                ).select_related('question')
                
                migrated_count = 0
                migration_log = []
                
                for response in old_responses:
                    field_name = response.question.field_name
                    old_value = response.response_value
                    
                    # Migrate based on field type
                    migration_result = self._migrate_single_response(
                        field_name, old_value, session_key
                    )
                    
                    if migration_result['success']:
                        migrated_count += 1
                        migration_log.append({
                            'field': field_name,
                            'old_value': old_value,
                            'new_field': migration_result['new_field'],
                            'new_value': migration_result['new_value']
                        })
                        
                        # Delete old response
                        response.delete()
                    else:
                        migration_log.append({
                            'field': field_name,
                            'old_value': old_value,
                            'error': migration_result['error']
                        })
                
                return {
                    'success': True,
                    'migrated_count': migrated_count,
                    'total_old_responses': len(old_responses),
                    'migration_log': migration_log,
                    'message': f'Successfully migrated {migrated_count} responses'
                }
                
        except Exception as e:
            logger.error(f"Error auto-migrating responses for session {session_key}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to auto-migrate responses'
            }
    
    def get_migration_form_data(self, session_key: str) -> Dict[str, Any]:
        """
        Get form data for user to review and update migrated responses.
        
        Args:
            session_key: User session identifier
            
        Returns:
            Dictionary with form data for user review
            
        Requirements: 6.4, 6.5
        """
        try:
            # Get current responses
            responses = SimpleSurveyResponse.objects.filter(
                session_key=session_key,
                category=self.category
            ).select_related('question')
            
            # Get migration status
            status = self.check_migration_status(session_key)
            
            # Build form data
            form_data = {}
            migration_suggestions = {}
            
            for response in responses:
                field_name = response.question.field_name
                form_data[field_name] = response.response_value
                
                # Add migration suggestions for old format fields
                if field_name in self._get_old_format_fields():
                    suggestion = self._get_migration_suggestion(field_name, response.response_value)
                    if suggestion:
                        migration_suggestions[field_name] = suggestion
            
            # Add suggested values for missing new format fields
            new_fields = self._get_new_format_fields()
            for field in new_fields:
                if field not in form_data:
                    # Try to infer from old responses
                    suggested_value = self._infer_new_field_value(field, form_data)
                    if suggested_value:
                        migration_suggestions[field] = {
                            'suggested_value': suggested_value,
                            'reason': 'Inferred from existing responses'
                        }
            
            return {
                'success': True,
                'form_data': form_data,
                'migration_suggestions': migration_suggestions,
                'migration_status': status,
                'requires_review': status['requires_user_input']
            }
            
        except Exception as e:
            logger.error(f"Error getting migration form data for session {session_key}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get migration form data'
            }
    
    def handle_mixed_responses(self, session_key: str, user_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle mixed old/new response scenarios for comparison engine.
        
        Args:
            session_key: User session identifier
            user_criteria: Processed user criteria from comparison adapter
            
        Returns:
            Dictionary with processed criteria handling mixed responses
            
        Requirements: 6.5
        """
        try:
            # Get migration status
            status = self.check_migration_status(session_key)
            
            if status['status'] not in ['mixed_format', 'old_format']:
                # No mixed responses to handle
                return {
                    'success': True,
                    'criteria': user_criteria,
                    'fallback_applied': False,
                    'message': 'No mixed responses detected'
                }
            
            # Apply fallback logic for missing new format fields
            enhanced_criteria = user_criteria.copy()
            fallback_applied = False
            fallback_details = []
            
            # Handle missing benefit level fields
            if 'in_hospital_benefit_level' not in enhanced_criteria:
                # Try to infer from old boolean responses or set default
                fallback_value = self._get_fallback_benefit_level('in_hospital', session_key)
                enhanced_criteria['in_hospital_benefit_level'] = fallback_value
                fallback_applied = True
                fallback_details.append(f"in_hospital_benefit_level set to {fallback_value}")
            
            if 'out_hospital_benefit_level' not in enhanced_criteria:
                fallback_value = self._get_fallback_benefit_level('out_hospital', session_key)
                enhanced_criteria['out_hospital_benefit_level'] = fallback_value
                fallback_applied = True
                fallback_details.append(f"out_hospital_benefit_level set to {fallback_value}")
            
            # Handle missing range fields
            if 'annual_limit_family_range' not in enhanced_criteria:
                fallback_value = self._get_fallback_range('family', enhanced_criteria)
                enhanced_criteria['annual_limit_family_range'] = fallback_value
                fallback_applied = True
                fallback_details.append(f"annual_limit_family_range set to {fallback_value}")
            
            if 'annual_limit_member_range' not in enhanced_criteria:
                fallback_value = self._get_fallback_range('member', enhanced_criteria)
                enhanced_criteria['annual_limit_member_range'] = fallback_value
                fallback_applied = True
                fallback_details.append(f"annual_limit_member_range set to {fallback_value}")
            
            # Adjust weights for fallback values
            if fallback_applied and 'weights' in enhanced_criteria:
                # Reduce weights for fallback values to avoid over-weighting uncertain data
                weights = enhanced_criteria['weights']
                if 'in_hospital_benefit_level' in weights:
                    weights['in_hospital_benefit_level'] = max(1, weights['in_hospital_benefit_level'] // 2)
                if 'out_hospital_benefit_level' in weights:
                    weights['out_hospital_benefit_level'] = max(1, weights['out_hospital_benefit_level'] // 2)
                if 'annual_limit_family_range' in weights:
                    weights['annual_limit_family_range'] = max(1, weights['annual_limit_family_range'] // 2)
                if 'annual_limit_member_range' in weights:
                    weights['annual_limit_member_range'] = max(1, weights['annual_limit_member_range'] // 2)
            
            # Log fallback application for monitoring
            if fallback_applied:
                logger.info(f"Applied fallback values for session {session_key}: {', '.join(fallback_details)}")
            
            return {
                'success': True,
                'criteria': enhanced_criteria,
                'fallback_applied': fallback_applied,
                'fallback_details': fallback_details,
                'message': 'Mixed responses handled with fallback values' if fallback_applied else 'No fallback needed'
            }
            
        except Exception as e:
            logger.error(f"Error handling mixed responses for session {session_key}: {e}")
            return {
                'success': False,
                'error': str(e),
                'criteria': user_criteria,
                'fallback_applied': False,
                'message': 'Failed to handle mixed responses'
            }
    
    def _get_old_format_fields(self) -> List[str]:
        """Get list of old format field names that need migration."""
        return [
            'wants_in_hospital_benefit',
            'wants_out_hospital_benefit',
            'currently_on_medical_aid'  # This field is removed entirely
        ]
    
    def _get_new_format_fields(self) -> List[str]:
        """Get list of new format field names."""
        return [
            'in_hospital_benefit_level',
            'out_hospital_benefit_level',
            'annual_limit_family_range',
            'annual_limit_member_range'
        ]
    
    def _migrate_single_response(self, field_name: str, old_value: Any, session_key: str) -> Dict[str, Any]:
        """
        Migrate a single response from old to new format.
        
        Args:
            field_name: Old field name
            old_value: Old response value
            session_key: User session identifier
            
        Returns:
            Dictionary with migration result
        """
        try:
            # Handle binary benefit fields
            if field_name == 'wants_in_hospital_benefit':
                new_field = 'in_hospital_benefit_level'
                new_value = 'basic' if old_value else 'no_cover'
                
                return self._create_new_response(session_key, new_field, new_value)
            
            elif field_name == 'wants_out_hospital_benefit':
                new_field = 'out_hospital_benefit_level'
                new_value = 'basic_visits' if old_value else 'no_cover'
                
                return self._create_new_response(session_key, new_field, new_value)
            
            elif field_name == 'currently_on_medical_aid':
                # This field is removed entirely - no migration needed
                return {
                    'success': True,
                    'new_field': None,
                    'new_value': None,
                    'message': 'Field removed - no migration needed'
                }
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown old format field: {field_name}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_new_response(self, session_key: str, field_name: str, value: Any) -> Dict[str, Any]:
        """
        Create a new response record for migrated data.
        
        Args:
            session_key: User session identifier
            field_name: New field name
            value: New response value
            
        Returns:
            Dictionary with creation result
        """
        try:
            # Get or create the question
            question = SimpleSurveyQuestion.objects.get(
                category=self.category,
                field_name=field_name
            )
            
            # Create or update the response
            response, created = SimpleSurveyResponse.objects.update_or_create(
                session_key=session_key,
                question=question,
                defaults={
                    'category': self.category,
                    'response_value': value
                }
            )
            
            return {
                'success': True,
                'new_field': field_name,
                'new_value': value,
                'created': created
            }
            
        except SimpleSurveyQuestion.DoesNotExist:
            return {
                'success': False,
                'error': f'Question not found for field: {field_name}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_migration_suggestion(self, field_name: str, old_value: Any) -> Optional[Dict[str, Any]]:
        """
        Get migration suggestion for an old format field.
        
        Args:
            field_name: Old field name
            old_value: Old response value
            
        Returns:
            Dictionary with migration suggestion or None
        """
        if field_name == 'wants_in_hospital_benefit':
            return {
                'new_field': 'in_hospital_benefit_level',
                'suggested_value': 'basic' if old_value else 'no_cover',
                'reason': 'Converted from yes/no to benefit level'
            }
        elif field_name == 'wants_out_hospital_benefit':
            return {
                'new_field': 'out_hospital_benefit_level',
                'suggested_value': 'basic_visits' if old_value else 'no_cover',
                'reason': 'Converted from yes/no to benefit level'
            }
        elif field_name == 'currently_on_medical_aid':
            return {
                'new_field': None,
                'suggested_value': None,
                'reason': 'This question has been removed'
            }
        
        return None
    
    def _infer_new_field_value(self, field_name: str, existing_data: Dict[str, Any]) -> Optional[str]:
        """
        Infer value for new format field based on existing responses.
        
        Args:
            field_name: New field name
            existing_data: Existing response data
            
        Returns:
            Inferred value or None
        """
        if field_name == 'annual_limit_family_range':
            # Try to infer from preferred_annual_limit_per_family
            if 'preferred_annual_limit_per_family' in existing_data:
                limit = existing_data['preferred_annual_limit_per_family']
                return self._map_limit_to_range(limit, 'family')
        
        elif field_name == 'annual_limit_member_range':
            # Try to infer from preferred_annual_limit
            if 'preferred_annual_limit' in existing_data:
                limit = existing_data['preferred_annual_limit']
                return self._map_limit_to_range(limit, 'member')
        
        return None
    
    def _map_limit_to_range(self, limit: Any, range_type: str) -> str:
        """
        Map a numeric limit to appropriate range selection.
        
        Args:
            limit: Numeric limit value
            range_type: 'family' or 'member'
            
        Returns:
            Range selection string
        """
        try:
            limit_value = float(limit)
            
            if range_type == 'family':
                if limit_value <= 50000:
                    return '10k-50k'
                elif limit_value <= 100000:
                    return '50k-100k'
                elif limit_value <= 250000:
                    return '100k-250k'
                elif limit_value <= 500000:
                    return '250k-500k'
                elif limit_value <= 1000000:
                    return '500k-1m'
                elif limit_value <= 2000000:
                    return '1m-2m'
                elif limit_value <= 5000000:
                    return '2m-5m'
                else:
                    return '5m-plus'
            
            else:  # member
                if limit_value <= 25000:
                    return '10k-25k'
                elif limit_value <= 50000:
                    return '25k-50k'
                elif limit_value <= 100000:
                    return '50k-100k'
                elif limit_value <= 200000:
                    return '100k-200k'
                elif limit_value <= 500000:
                    return '200k-500k'
                elif limit_value <= 1000000:
                    return '500k-1m'
                elif limit_value <= 2000000:
                    return '1m-2m'
                else:
                    return '2m-plus'
                    
        except (ValueError, TypeError):
            return 'not_sure'
    
    def _get_fallback_benefit_level(self, benefit_type: str, session_key: str = None) -> str:
        """
        Get fallback benefit level for missing responses.
        
        Args:
            benefit_type: 'in_hospital' or 'out_hospital'
            session_key: Optional session key to check for old responses
            
        Returns:
            Fallback benefit level
        """
        # Try to infer from old boolean responses if session_key provided
        if session_key:
            try:
                old_field = f'wants_{benefit_type}_benefit'
                old_response = SimpleSurveyResponse.objects.filter(
                    session_key=session_key,
                    category=self.category,
                    question__field_name=old_field
                ).first()
                
                if old_response:
                    # Convert old boolean to benefit level
                    if old_response.response_value:
                        return 'basic' if benefit_type == 'in_hospital' else 'basic_visits'
                    else:
                        return 'no_cover'
            except Exception as e:
                logger.warning(f"Could not infer from old responses: {e}")
        
        # Default to basic coverage for users who had existing surveys
        if benefit_type == 'in_hospital':
            return 'basic'
        else:
            return 'basic_visits'
    
    def _get_fallback_range(self, range_type: str, criteria: Dict[str, Any]) -> str:
        """
        Get fallback range selection based on available criteria.
        
        Args:
            range_type: 'family' or 'member'
            criteria: Available user criteria
            
        Returns:
            Fallback range selection
        """
        # Try to infer from household income
        if 'monthly_household_income' in criteria:
            income = criteria['monthly_household_income']
            try:
                monthly_income = float(income)
                # Rough estimate: annual coverage should be 2-4x monthly income
                estimated_annual = monthly_income * 3
                
                return self._map_limit_to_range(estimated_annual, range_type)
            except (ValueError, TypeError):
                pass
        
        # Default fallback based on range type
        if range_type == 'family':
            return '100k-250k'  # Mid-range family coverage
        else:
            return '50k-100k'   # Mid-range member coverage
    
    def get_user_migration_prompt(self, session_key: str) -> Dict[str, Any]:
        """
        Get user-friendly migration prompt information.
        
        Args:
            session_key: User session identifier
            
        Returns:
            Dictionary with user prompt information
            
        Requirements: 6.4, 6.6
        """
        try:
            status = self.check_migration_status(session_key)
            
            if not status['needs_migration']:
                return {
                    'show_prompt': False,
                    'message': 'No migration needed'
                }
            
            # Get old responses for context
            old_responses = SimpleSurveyResponse.objects.filter(
                session_key=session_key,
                category=self.category,
                question__field_name__in=self._get_old_format_fields()
            ).select_related('question')
            
            # Build user-friendly explanation
            old_answers = {}
            for response in old_responses:
                field_name = response.question.field_name
                if field_name == 'wants_in_hospital_benefit':
                    old_answers['hospital'] = 'Yes' if response.response_value else 'No'
                elif field_name == 'wants_out_hospital_benefit':
                    old_answers['out_hospital'] = 'Yes' if response.response_value else 'No'
                elif field_name == 'currently_on_medical_aid':
                    old_answers['medical_aid'] = 'Yes' if response.response_value else 'No'
            
            # Create migration explanation
            explanation = []
            if 'hospital' in old_answers:
                if old_answers['hospital'] == 'Yes':
                    explanation.append("Your 'Yes' to hospital benefits will become 'Basic hospital care'")
                else:
                    explanation.append("Your 'No' to hospital benefits will become 'No hospital cover'")
            
            if 'out_hospital' in old_answers:
                if old_answers['out_hospital'] == 'Yes':
                    explanation.append("Your 'Yes' to out-of-hospital benefits will become 'Basic clinic visits'")
                else:
                    explanation.append("Your 'No' to out-of-hospital benefits will become 'No out-of-hospital cover'")
            
            if 'medical_aid' in old_answers:
                explanation.append("The medical aid status question has been removed as it's no longer needed")
            
            return {
                'show_prompt': True,
                'status': status['status'],
                'can_auto_migrate': status.get('can_auto_migrate', False),
                'old_answers': old_answers,
                'explanation': explanation,
                'benefits': [
                    "More precise coverage matching",
                    "Better policy recommendations", 
                    "Clearer understanding of your needs",
                    "Improved comparison results"
                ],
                'message': self._get_migration_message(status['status'])
            }
            
        except Exception as e:
            logger.error(f"Error getting user migration prompt: {e}")
            return {
                'show_prompt': False,
                'error': str(e)
            }
    
    def _get_migration_message(self, status: str) -> str:
        """Get user-friendly migration message based on status."""
        messages = {
            'old_format': "We've improved our questions to better match you with policies. Your previous answers can be automatically updated.",
            'mixed_format': "Some of your answers are in our old format. Please review and update them to get better policy matches.",
            'unknown_format': "We need to review your previous answers to ensure they work with our improved system."
        }
        return messages.get(status, "Your responses need to be updated to our new format.")
    
    def create_migration_notification(self, session_key: str) -> Dict[str, Any]:
        """
        Create a notification for users about available migration.
        
        Args:
            session_key: User session identifier
            
        Returns:
            Dictionary with notification data
            
        Requirements: 6.6
        """
        try:
            prompt_data = self.get_user_migration_prompt(session_key)
            
            if not prompt_data['show_prompt']:
                return {'show_notification': False}
            
            return {
                'show_notification': True,
                'type': 'info' if prompt_data['can_auto_migrate'] else 'warning',
                'title': 'Survey Questions Updated',
                'message': prompt_data['message'],
                'actions': [
                    {
                        'text': 'Auto-Update' if prompt_data['can_auto_migrate'] else 'Review & Update',
                        'url': f'/simple_surveys/migrate/{self.category}/',
                        'primary': True
                    },
                    {
                        'text': 'Learn More',
                        'url': '#migration-details',
                        'primary': False
                    }
                ],
                'dismissible': True,
                'persistent': not prompt_data['can_auto_migrate']  # Keep showing if manual review needed
            }
            
        except Exception as e:
            logger.error(f"Error creating migration notification: {e}")
            return {'show_notification': False}