"""
System integration utilities for ensuring consistency across all modules.
Handles cross-module validation, feature synchronization, and data consistency.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from typing import Dict, List, Any, Optional, Tuple
import logging

from .models import BasePolicy, PolicyFeatures, AdditionalFeatures
from simple_surveys.models import SimpleSurvey, SimpleSurveyQuestion, SimpleSurveyResponse
from comparison.models import FeatureComparisonResult, ComparisonSession

logger = logging.getLogger(__name__)


class FeatureSynchronizationManager:
    """
    Manages synchronization of features across policies, surveys, and comparisons.
    Ensures consistency when feature definitions change.
    """
    
    # Standard feature mappings between models
    HEALTH_FEATURE_MAPPING = {
        'annual_limit_per_member': {
            'policy_field': 'annual_limit_per_member',
            'survey_field': 'preferred_annual_limit',
            'display_name': 'Annual Limit per Member',
            'data_type': 'decimal',
            'validation_rules': {'min': 0}
        },
        'monthly_household_income': {
            'policy_field': 'monthly_household_income',
            'survey_field': 'household_income',
            'display_name': 'Monthly Household Income',
            'data_type': 'decimal',
            'validation_rules': {'min': 0}
        },
        'in_hospital_benefit': {
            'policy_field': 'in_hospital_benefit',
            'survey_field': 'wants_in_hospital_benefit',
            'display_name': 'In-Hospital Benefits',
            'data_type': 'boolean',
            'validation_rules': {}
        },
        'out_hospital_benefit': {
            'policy_field': 'out_hospital_benefit',
            'survey_field': 'wants_out_hospital_benefit',
            'display_name': 'Out-of-Hospital Benefits',
            'data_type': 'boolean',
            'validation_rules': {}
        },
        'chronic_medication_availability': {
            'policy_field': 'chronic_medication_availability',
            'survey_field': 'needs_chronic_medication',
            'display_name': 'Chronic Medication Coverage',
            'data_type': 'boolean',
            'validation_rules': {}
        }
    }
    
    FUNERAL_FEATURE_MAPPING = {
        'cover_amount': {
            'policy_field': 'cover_amount',
            'survey_field': 'preferred_cover_amount',
            'display_name': 'Cover Amount',
            'data_type': 'decimal',
            'validation_rules': {'min': 0}
        },
        'marital_status_requirement': {
            'policy_field': 'marital_status_requirement',
            'survey_field': 'marital_status',
            'display_name': 'Marital Status',
            'data_type': 'string',
            'validation_rules': {}
        },
        'gender_requirement': {
            'policy_field': 'gender_requirement',
            'survey_field': 'gender',
            'display_name': 'Gender',
            'data_type': 'string',
            'validation_rules': {}
        }
    }
    
    @classmethod
    def get_feature_mapping(cls, insurance_type: str) -> Dict[str, Dict[str, Any]]:
        """Get feature mapping for a specific insurance type."""
        if insurance_type == 'HEALTH':
            return cls.HEALTH_FEATURE_MAPPING
        elif insurance_type == 'FUNERAL':
            return cls.FUNERAL_FEATURE_MAPPING
        else:
            return {}
    
    @classmethod
    def validate_feature_consistency(cls, insurance_type: str) -> List[str]:
        """
        Validate that features are consistently defined across all modules.
        
        Returns:
            List of validation errors found
        """
        errors = []
        feature_mapping = cls.get_feature_mapping(insurance_type)
        
        if not feature_mapping:
            errors.append(f"No feature mapping found for insurance type: {insurance_type}")
            return errors
        
        # Check PolicyFeatures model fields
        policy_features_fields = [f.name for f in PolicyFeatures._meta.get_fields()]
        
        # Check SimpleSurvey model fields
        simple_survey_fields = [f.name for f in SimpleSurvey._meta.get_fields()]
        
        for feature_code, mapping in feature_mapping.items():
            policy_field = mapping['policy_field']
            survey_field = mapping['survey_field']
            
            # Validate policy field exists
            if policy_field not in policy_features_fields:
                errors.append(f"Policy field '{policy_field}' not found in PolicyFeatures model")
            
            # Validate survey field exists
            if survey_field not in simple_survey_fields:
                errors.append(f"Survey field '{survey_field}' not found in SimpleSurvey model")
        
        return errors
    
    @classmethod
    def synchronize_survey_questions(cls, insurance_type: str) -> Dict[str, Any]:
        """
        Synchronize survey questions with current feature definitions.
        
        Returns:
            Dictionary with synchronization results
        """
        results = {
            'created': 0,
            'updated': 0,
            'errors': []
        }
        
        feature_mapping = cls.get_feature_mapping(insurance_type)
        category = insurance_type.lower()
        
        try:
            with transaction.atomic():
                for feature_code, mapping in feature_mapping.items():
                    field_name = mapping['survey_field']
                    display_name = mapping['display_name']
                    data_type = mapping['data_type']
                    validation_rules = mapping['validation_rules']
                    
                    # Determine input type based on data type
                    input_type = 'text'
                    if data_type == 'decimal':
                        input_type = 'number'
                    elif data_type == 'boolean':
                        input_type = 'radio'
                    
                    # Create or update survey question
                    question, created = SimpleSurveyQuestion.objects.get_or_create(
                        category=category,
                        field_name=field_name,
                        defaults={
                            'question_text': f"What is your preference for {display_name}?",
                            'input_type': input_type,
                            'is_required': True,
                            'display_order': len(feature_mapping) * 10,
                            'validation_rules': validation_rules,
                            'choices': [] if data_type != 'boolean' else [
                                ['true', 'Yes'],
                                ['false', 'No']
                            ]
                        }
                    )
                    
                    if created:
                        results['created'] += 1
                        logger.info(f"Created survey question for {field_name}")
                    else:
                        # Update existing question if needed
                        updated = False
                        if question.validation_rules != validation_rules:
                            question.validation_rules = validation_rules
                            updated = True
                        
                        if updated:
                            question.save()
                            results['updated'] += 1
                            logger.info(f"Updated survey question for {field_name}")
        
        except Exception as e:
            results['errors'].append(f"Error synchronizing survey questions: {str(e)}")
            logger.error(f"Error synchronizing survey questions: {str(e)}")
        
        return results


class CrossModuleValidator:
    """
    Validates data consistency across policies, surveys, and comparison modules.
    """
    
    @classmethod
    def validate_policy_features(cls, policy: BasePolicy) -> List[str]:
        """
        Validate that a policy has complete and consistent feature data.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            policy_features = policy.get_policy_features()
            if not policy_features:
                errors.append("Policy has no associated PolicyFeatures record")
                return errors
            
            insurance_type = policy_features.insurance_type
            feature_mapping = FeatureSynchronizationManager.get_feature_mapping(insurance_type)
            
            # Check required features are present
            for feature_code, mapping in feature_mapping.items():
                field_name = mapping['policy_field']
                field_value = getattr(policy_features, field_name, None)
                
                if field_value is None:
                    errors.append(f"Required feature '{mapping['display_name']}' is missing")
                else:
                    # Validate field value based on data type and rules
                    validation_errors = cls._validate_field_value(
                        field_value, 
                        mapping['data_type'], 
                        mapping['validation_rules'],
                        mapping['display_name']
                    )
                    errors.extend(validation_errors)
        
        except Exception as e:
            errors.append(f"Error validating policy features: {str(e)}")
        
        return errors
    
    @classmethod
    def validate_survey_completeness(cls, survey: SimpleSurvey) -> List[str]:
        """
        Validate that a survey has complete data for its insurance type.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            insurance_type = survey.insurance_type
            feature_mapping = FeatureSynchronizationManager.get_feature_mapping(insurance_type)
            
            # Check required survey fields are present
            for feature_code, mapping in feature_mapping.items():
                field_name = mapping['survey_field']
                field_value = getattr(survey, field_name, None)
                
                if field_value is None:
                    errors.append(f"Required survey field '{mapping['display_name']}' is missing")
                else:
                    # Validate field value
                    validation_errors = cls._validate_field_value(
                        field_value,
                        mapping['data_type'],
                        mapping['validation_rules'],
                        mapping['display_name']
                    )
                    errors.extend(validation_errors)
        
        except Exception as e:
            errors.append(f"Error validating survey completeness: {str(e)}")
        
        return errors
    
    @classmethod
    def validate_comparison_consistency(cls, comparison_result: FeatureComparisonResult) -> List[str]:
        """
        Validate that comparison results are consistent with policy and survey data.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            survey = comparison_result.survey
            policy = comparison_result.policy
            
            # Validate survey and policy have same insurance type
            policy_features = policy.get_policy_features()
            if not policy_features:
                errors.append("Policy has no associated features for comparison")
                return errors
            
            if survey.insurance_type != policy_features.insurance_type:
                errors.append(
                    f"Insurance type mismatch: survey is {survey.insurance_type}, "
                    f"policy is {policy_features.insurance_type}"
                )
            
            # Validate feature scores are within expected range
            if not (0 <= comparison_result.overall_compatibility_score <= 100):
                errors.append("Overall compatibility score must be between 0 and 100")
            
            # Validate feature matches and mismatches are consistent
            total_features = len(comparison_result.feature_matches) + len(comparison_result.feature_mismatches)
            expected_features = len(FeatureSynchronizationManager.get_feature_mapping(survey.insurance_type))
            
            if total_features > expected_features:
                errors.append(f"Too many features in comparison result: {total_features} > {expected_features}")
        
        except Exception as e:
            errors.append(f"Error validating comparison consistency: {str(e)}")
        
        return errors
    
    @classmethod
    def _validate_field_value(cls, value: Any, data_type: str, validation_rules: Dict, field_name: str) -> List[str]:
        """
        Validate a field value against its data type and validation rules.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            if data_type == 'decimal':
                if not isinstance(value, (int, float)) and value is not None:
                    errors.append(f"{field_name} must be a number")
                elif value is not None:
                    if 'min' in validation_rules and value < validation_rules['min']:
                        errors.append(f"{field_name} must be at least {validation_rules['min']}")
                    if 'max' in validation_rules and value > validation_rules['max']:
                        errors.append(f"{field_name} must be at most {validation_rules['max']}")
            
            elif data_type == 'boolean':
                if value is not None and not isinstance(value, bool):
                    errors.append(f"{field_name} must be true or false")
            
            elif data_type == 'string':
                if value is not None and not isinstance(value, str):
                    errors.append(f"{field_name} must be text")
                elif value is not None:
                    if 'max_length' in validation_rules and len(value) > validation_rules['max_length']:
                        errors.append(f"{field_name} must be no more than {validation_rules['max_length']} characters")
        
        except Exception as e:
            errors.append(f"Error validating {field_name}: {str(e)}")
        
        return errors


class SystemIntegrationManager:
    """
    Main manager for system integration tasks.
    Coordinates validation, synchronization, and consistency checks.
    """
    
    @classmethod
    def perform_full_system_check(cls) -> Dict[str, Any]:
        """
        Perform a comprehensive system integration check.
        
        Returns:
            Dictionary with check results
        """
        results = {
            'timestamp': timezone.now().isoformat(),
            'health_policies': {'total': 0, 'valid': 0, 'errors': []},
            'funeral_policies': {'total': 0, 'valid': 0, 'errors': []},
            'health_surveys': {'total': 0, 'valid': 0, 'errors': []},
            'funeral_surveys': {'total': 0, 'valid': 0, 'errors': []},
            'comparison_results': {'total': 0, 'valid': 0, 'errors': []},
            'feature_consistency': {'health': [], 'funeral': []},
            'synchronization_needed': False,
            'overall_status': 'unknown'
        }
        
        try:
            # Check feature consistency
            results['feature_consistency']['health'] = FeatureSynchronizationManager.validate_feature_consistency('HEALTH')
            results['feature_consistency']['funeral'] = FeatureSynchronizationManager.validate_feature_consistency('FUNERAL')
            
            # Check health policies
            health_policies = BasePolicy.objects.filter(policy_features__insurance_type='HEALTH')
            results['health_policies']['total'] = health_policies.count()
            
            for policy in health_policies:
                errors = CrossModuleValidator.validate_policy_features(policy)
                if not errors:
                    results['health_policies']['valid'] += 1
                else:
                    results['health_policies']['errors'].extend([
                        f"Policy {policy.name}: {error}" for error in errors
                    ])
            
            # Check funeral policies
            funeral_policies = BasePolicy.objects.filter(policy_features__insurance_type='FUNERAL')
            results['funeral_policies']['total'] = funeral_policies.count()
            
            for policy in funeral_policies:
                errors = CrossModuleValidator.validate_policy_features(policy)
                if not errors:
                    results['funeral_policies']['valid'] += 1
                else:
                    results['funeral_policies']['errors'].extend([
                        f"Policy {policy.name}: {error}" for error in errors
                    ])
            
            # Check health surveys
            health_surveys = SimpleSurvey.objects.filter(insurance_type='HEALTH')
            results['health_surveys']['total'] = health_surveys.count()
            
            for survey in health_surveys:
                errors = CrossModuleValidator.validate_survey_completeness(survey)
                if not errors:
                    results['health_surveys']['valid'] += 1
                else:
                    results['health_surveys']['errors'].extend([
                        f"Survey {survey.id}: {error}" for error in errors
                    ])
            
            # Check funeral surveys
            funeral_surveys = SimpleSurvey.objects.filter(insurance_type='FUNERAL')
            results['funeral_surveys']['total'] = funeral_surveys.count()
            
            for survey in funeral_surveys:
                errors = CrossModuleValidator.validate_survey_completeness(survey)
                if not errors:
                    results['funeral_surveys']['valid'] += 1
                else:
                    results['funeral_surveys']['errors'].extend([
                        f"Survey {survey.id}: {error}" for error in errors
                    ])
            
            # Check comparison results
            comparison_results = FeatureComparisonResult.objects.all()
            results['comparison_results']['total'] = comparison_results.count()
            
            for comp_result in comparison_results:
                errors = CrossModuleValidator.validate_comparison_consistency(comp_result)
                if not errors:
                    results['comparison_results']['valid'] += 1
                else:
                    results['comparison_results']['errors'].extend([
                        f"Comparison {comp_result.id}: {error}" for error in errors
                    ])
            
            # Determine if synchronization is needed
            total_errors = (
                len(results['feature_consistency']['health']) +
                len(results['feature_consistency']['funeral']) +
                len(results['health_policies']['errors']) +
                len(results['funeral_policies']['errors']) +
                len(results['health_surveys']['errors']) +
                len(results['funeral_surveys']['errors']) +
                len(results['comparison_results']['errors'])
            )
            
            results['synchronization_needed'] = total_errors > 0
            
            # Determine overall status
            if total_errors == 0:
                results['overall_status'] = 'healthy'
            elif total_errors < 10:
                results['overall_status'] = 'warning'
            else:
                results['overall_status'] = 'critical'
        
        except Exception as e:
            results['overall_status'] = 'error'
            results['system_error'] = str(e)
            logger.error(f"Error performing system check: {str(e)}")
        
        return results
    
    @classmethod
    def synchronize_all_features(cls) -> Dict[str, Any]:
        """
        Synchronize features across all modules.
        
        Returns:
            Dictionary with synchronization results
        """
        results = {
            'health_sync': {},
            'funeral_sync': {},
            'overall_success': False
        }
        
        try:
            with transaction.atomic():
                # Synchronize health features
                results['health_sync'] = FeatureSynchronizationManager.synchronize_survey_questions('HEALTH')
                
                # Synchronize funeral features
                results['funeral_sync'] = FeatureSynchronizationManager.synchronize_survey_questions('FUNERAL')
                
                # Check if synchronization was successful
                health_errors = results['health_sync'].get('errors', [])
                funeral_errors = results['funeral_sync'].get('errors', [])
                
                results['overall_success'] = len(health_errors) == 0 and len(funeral_errors) == 0
                
                if results['overall_success']:
                    logger.info("Feature synchronization completed successfully")
                else:
                    logger.warning(f"Feature synchronization completed with errors: {health_errors + funeral_errors}")
        
        except Exception as e:
            results['overall_success'] = False
            results['system_error'] = str(e)
            logger.error(f"Error during feature synchronization: {str(e)}")
        
        return results
    
    @classmethod
    def validate_system_integrity(cls) -> Tuple[bool, List[str]]:
        """
        Validate overall system integrity.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Check feature consistency
            health_errors = FeatureSynchronizationManager.validate_feature_consistency('HEALTH')
            funeral_errors = FeatureSynchronizationManager.validate_feature_consistency('FUNERAL')
            
            errors.extend([f"Health feature consistency: {error}" for error in health_errors])
            errors.extend([f"Funeral feature consistency: {error}" for error in funeral_errors])
            
            # Check that we have the required models
            required_models = [BasePolicy, PolicyFeatures, SimpleSurvey, FeatureComparisonResult]
            for model in required_models:
                try:
                    model.objects.first()  # Test model access
                except Exception as e:
                    errors.append(f"Model {model.__name__} is not accessible: {str(e)}")
            
            # Check that insurance types are consistent
            policy_types = set(PolicyFeatures.objects.values_list('insurance_type', flat=True).distinct())
            survey_types = set(SimpleSurvey.objects.values_list('insurance_type', flat=True).distinct())
            
            expected_types = {'HEALTH', 'FUNERAL'}
            
            if policy_types - expected_types:
                errors.append(f"Unexpected policy insurance types: {policy_types - expected_types}")
            
            if survey_types - expected_types:
                errors.append(f"Unexpected survey insurance types: {survey_types - expected_types}")
        
        except Exception as e:
            errors.append(f"System integrity check failed: {str(e)}")
        
        return len(errors) == 0, errors


# Import timezone here to avoid circular imports
from django.utils import timezone