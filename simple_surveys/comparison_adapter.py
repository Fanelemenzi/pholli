"""
Comparison Adapter for Simple Survey System.

This module provides the adapter layer between the simplified survey system
and the existing PolicyComparisonEngine. It converts simple survey responses
into the format expected by the comparison engine and simplifies the scoring
algorithm by removing complex survey context features.
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import models
from comparison.engine import PolicyComparisonEngine
from comparison.models import ComparisonSession, ComparisonCriteria
from policies.models import BasePolicy, PolicyCategory
from .models import SimpleSurveyResponse, QuotationSession
from .engine import SimpleSurveyEngine
from .response_migration import ResponseMigrationHandler
import logging
import uuid

logger = logging.getLogger(__name__)


class SimpleSurveyComparisonAdapter:
    """
    Adapter class that bridges the simple survey system with the existing comparison engine.
    
    This adapter:
    - Converts simple survey responses to comparison engine format
    - Creates simplified comparison sessions
    - Removes complex survey context features for streamlined processing
    - Provides a clean interface for generating quotations from survey data
    """
    
    def __init__(self, category: str):
        """
        Initialize the adapter for a specific insurance category.
        
        Args:
            category: Insurance category ('health' or 'funeral')
        """
        self.category = category
        self.survey_engine = SimpleSurveyEngine(category)
        # Use simplified comparison engine instead of standard one
        self.comparison_engine = SimplifiedPolicyComparisonEngine(category)
        
    def generate_quotations(
        self, 
        session_key: str, 
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Generate policy quotations from simple survey responses.
        
        Args:
            session_key: Session identifier containing survey responses
            max_results: Maximum number of policy results to return
            
        Returns:
            Dictionary with quotation results and metadata
        """
        try:
            # Get survey responses and convert to criteria
            criteria = self._convert_survey_responses_to_criteria(session_key)
            if not criteria:
                return {
                    'success': False,
                    'error': 'No survey responses found for session',
                    'session_key': session_key
                }
            
            # Get eligible policies for the category
            policy_ids = self._get_eligible_policy_ids(criteria)
            if not policy_ids:
                return {
                    'success': False,
                    'error': 'No eligible policies found for your criteria',
                    'session_key': session_key,
                    'criteria': criteria
                }
            
            # Limit to max_results for performance
            if len(policy_ids) > max_results * 2:
                # Get more than needed for better selection
                policy_ids = policy_ids[:max_results * 2]
            
            # Use comparison engine with simplified criteria
            comparison_result = self.comparison_engine.compare_policies(
                policy_ids=policy_ids,
                user_criteria=criteria,
                session_key=session_key
            )
            
            if not comparison_result.get('success'):
                return {
                    'success': False,
                    'error': comparison_result.get('error', 'Comparison failed'),
                    'session_key': session_key
                }
            
            # Simplify and limit results
            simplified_results = self._simplify_comparison_results(
                comparison_result, max_results
            )
            
            # Update quotation session
            self._update_quotation_session(session_key, criteria, simplified_results)
            
            return {
                'success': True,
                'session_key': session_key,
                'category': self.category,
                'total_policies_evaluated': len(policy_ids),
                'results_returned': len(simplified_results['policies']),
                'best_match': simplified_results['best_match'],
                'policies': simplified_results['policies'],
                'summary': simplified_results['summary'],
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating quotations for session {session_key}: {e}")
            return {
                'success': False,
                'error': f'Failed to generate quotations: {str(e)}',
                'session_key': session_key
            }
    
    def _convert_survey_responses_to_criteria(self, session_key: str) -> Dict[str, Any]:
        """
        Convert simple survey responses to comparison engine criteria format.
        
        Args:
            session_key: Session identifier
            
        Returns:
            Dictionary with criteria in comparison engine format
        """
        try:
            # Get processed responses from survey engine
            processed_responses = self.survey_engine.process_responses(session_key)
            
            if '_metadata' in processed_responses:
                # Remove metadata for criteria processing
                metadata = processed_responses.pop('_metadata')
                if 'error' in metadata:
                    logger.error(f"Error in survey responses: {metadata['error']}")
                    return {}
            
            # Convert to comparison engine format
            criteria = {}
            
            # Map survey fields to comparison criteria
            field_mappings = self._get_field_mappings()
            
            for survey_field, response_value in processed_responses.items():
                if survey_field in field_mappings:
                    comparison_field = field_mappings[survey_field]
                    criteria[comparison_field] = self._convert_response_value(
                        survey_field, response_value
                    )
            
            # Add default weights for criteria not specified
            criteria['weights'] = self._get_default_weights(criteria)
            
            # Add category-specific processing
            criteria = self._apply_category_specific_processing(criteria)
            
            # Handle mixed old/new response scenarios using migration handler
            migration_handler = ResponseMigrationHandler(self.category)
            migration_result = migration_handler.handle_mixed_responses(session_key, criteria)
            
            if migration_result['success']:
                criteria = migration_result['criteria']
                if migration_result['fallback_applied']:
                    logger.info(f"Applied fallback values for mixed responses in session {session_key}")
            else:
                logger.warning(f"Failed to handle mixed responses for session {session_key}: {migration_result['message']}")
            
            logger.info(f"Converted {len(processed_responses)} survey responses to {len(criteria)} criteria")
            return criteria
            
        except Exception as e:
            logger.error(f"Error converting survey responses to criteria: {e}")
            return {}
    
    def _get_field_mappings(self) -> Dict[str, str]:
        """
        Get mapping from survey field names to comparison engine field names.
        
        Returns:
            Dictionary mapping survey fields to comparison fields
        """
        if self.category == 'health':
            return {
                'age': 'age',
                'location': 'location',
                'family_size': 'family_size',
                'health_status': 'health_status',
                'chronic_conditions': 'chronic_conditions',
                'coverage_priority': 'coverage_priority',
                'monthly_budget': 'base_premium',
                'preferred_deductible': 'deductible_amount',
                # Updated health policy fields - benefit levels instead of boolean
                'preferred_annual_limit_per_family': 'annual_limit_per_family',
                'household_income': 'monthly_household_income',
                'wants_ambulance_coverage': 'ambulance_coverage',
                'in_hospital_benefit_level': 'in_hospital_benefit_level',
                'out_hospital_benefit_level': 'out_hospital_benefit_level',
                'annual_limit_family_range': 'annual_limit_family_range',
                'annual_limit_member_range': 'annual_limit_member_range',
                'needs_chronic_medication': 'chronic_medication_availability'
                # Removed: currently_on_medical_aid (no longer used)
                # Removed: wants_in_hospital_benefit, wants_out_hospital_benefit (replaced by benefit levels)
            }
        elif self.category == 'funeral':
            return {
                'age': 'age',
                'location': 'location',
                'family_members_to_cover': 'family_size',
                'coverage_amount_needed': 'coverage_amount',
                'service_preference': 'service_level',
                'monthly_budget': 'base_premium',
                'waiting_period_tolerance': 'waiting_period_days',
                # Funeral policy fields
                'preferred_cover_amount': 'cover_amount',
                'marital_status': 'marital_status_requirement',
                'gender': 'gender_requirement'
            }
        else:
            return {}
    
    def _convert_response_value(self, survey_field: str, response_value: Any) -> Any:
        """
        Convert survey response value to format expected by comparison engine.
        
        Args:
            survey_field: Original survey field name
            response_value: Raw response value from survey
            
        Returns:
            Converted value for comparison engine
        """
        # Handle numeric conversions
        if survey_field in ['age', 'family_size', 'family_members_to_cover', 'monthly_budget', 'household_income']:
            try:
                return int(response_value) if response_value else 0
            except (ValueError, TypeError):
                return 0
        
        # Handle decimal conversions for monetary amounts
        if survey_field in ['preferred_annual_limit_per_family', 'preferred_cover_amount']:
            try:
                return float(response_value) if response_value else 0.0
            except (ValueError, TypeError):
                return 0.0
        
        # Handle boolean conversions (for remaining boolean fields)
        if survey_field in ['wants_ambulance_coverage', 'needs_chronic_medication']:
            if isinstance(response_value, bool):
                return response_value
            elif isinstance(response_value, str):
                return response_value.lower() in ['true', 'yes', '1', 'on']
            return bool(response_value)
        
        # Handle benefit level conversions (new choice fields)
        if survey_field in ['in_hospital_benefit_level', 'out_hospital_benefit_level']:
            # Convert benefit level to comparison criteria
            return self._convert_benefit_level_to_criteria(survey_field, response_value)
        
        # Handle range conversions (new range fields)
        if survey_field in ['annual_limit_family_range', 'annual_limit_member_range']:
            # Convert range selection to min/max values for matching
            return self._convert_range_to_criteria(survey_field, response_value)
        
        # Handle coverage amount conversions (remove 'R' and 'k' suffixes)
        if survey_field == 'coverage_amount_needed':
            if isinstance(response_value, str):
                # Convert "R25k" to 25000, "R100k" to 100000, etc.
                value = response_value.replace('R', '').replace('k', '').replace('+', '')
                try:
                    return int(value) * 1000
                except ValueError:
                    return 50000  # Default fallback
            return response_value
        
        # Handle waiting period tolerance
        if survey_field == 'waiting_period_tolerance':
            if response_value == 'None':
                return 0
            elif isinstance(response_value, str) and 'months' in response_value:
                months = int(response_value.split()[0])
                return months * 30  # Convert months to days
            return response_value
        
        # Handle list values (like chronic conditions)
        if isinstance(response_value, list):
            return response_value
        
        # Default: return as-is
        return response_value
    
    def _convert_benefit_level_to_criteria(self, survey_field: str, benefit_level: str) -> Dict[str, Any]:
        """
        Convert benefit level selection to comparison criteria.
        
        Args:
            survey_field: The benefit level field name
            benefit_level: Selected benefit level (e.g., 'basic', 'comprehensive')
            
        Returns:
            Dictionary with criteria for policy matching
        """
        if not benefit_level:
            return {'level': 'no_cover', 'weight': 0}
        
        # Define benefit level weights for comparison scoring
        level_weights = {
            'no_cover': 0,
            'basic': 25,
            'basic_visits': 25,  # For out-of-hospital
            'moderate': 50,
            'routine_care': 50,  # For out-of-hospital
            'extensive': 75,
            'extended_care': 75,  # For out-of-hospital
            'comprehensive': 100,
            'comprehensive_care': 100  # For out-of-hospital
        }
        
        return {
            'level': benefit_level,
            'weight': level_weights.get(benefit_level, 50),
            'requires_coverage': benefit_level != 'no_cover'
        }
    
    def _convert_range_to_criteria(self, survey_field: str, range_selection: str) -> Dict[str, Any]:
        """
        Convert range selection to min/max values for policy matching.
        
        Args:
            survey_field: The range field name
            range_selection: Selected range (e.g., '100k-250k')
            
        Returns:
            Dictionary with min/max values and matching criteria
        """
        if not range_selection or range_selection == 'not_sure':
            return {'min_value': 0, 'max_value': float('inf'), 'guidance_needed': True}
        
        # Define range mappings
        range_mappings = {
            # Family ranges
            '10k-50k': {'min': 10000, 'max': 50000},
            '50k-100k': {'min': 50001, 'max': 100000},
            '100k-250k': {'min': 100001, 'max': 250000},
            '250k-500k': {'min': 250001, 'max': 500000},
            '500k-1m': {'min': 500001, 'max': 1000000},
            '1m-2m': {'min': 1000001, 'max': 2000000},
            '2m-5m': {'min': 2000001, 'max': 5000000},
            '5m-plus': {'min': 5000001, 'max': float('inf')},
            
            # Member ranges
            '10k-25k': {'min': 10000, 'max': 25000},
            '25k-50k': {'min': 25001, 'max': 50000},
            '50k-100k': {'min': 50001, 'max': 100000},
            '100k-200k': {'min': 100001, 'max': 200000},
            '200k-500k': {'min': 200001, 'max': 500000},
            '500k-1m': {'min': 500001, 'max': 1000000},
            '1m-2m': {'min': 1000001, 'max': 2000000},
            '2m-plus': {'min': 2000001, 'max': float('inf')},
        }
        
        range_data = range_mappings.get(range_selection, {'min': 0, 'max': float('inf')})
        
        return {
            'min_value': range_data['min'],
            'max_value': range_data['max'],
            'range_selection': range_selection,
            'guidance_needed': False
        }
    
    def _get_default_weights(self, criteria: Dict[str, Any]) -> Dict[str, int]:
        """
        Get default weights for comparison criteria.
        
        Args:
            criteria: Current criteria dictionary
            
        Returns:
            Dictionary with default weights for each criterion
        """
        default_weights = {}
        
        if self.category == 'health':
            default_weights = {
                'base_premium': 25,  # Budget is important
                'annual_limit_per_family': 30,  # Primary coverage field - very important
                'monthly_household_income': 20,  # Income eligibility is important
                'ambulance_coverage': 12,  # Important safety feature
                'coverage_priority': 20,  # Coverage type matters
                'health_status': 15,  # Health status affects eligibility
                'chronic_medication_availability': 15,  # Important for chronic conditions
                'in_hospital_benefit_level': 25,  # New benefit level field - important
                'out_hospital_benefit_level': 20,  # New benefit level field - important
                'annual_limit_family_range': 30,  # New range field - very important
                'annual_limit_member_range': 25,  # New range field - important
                'deductible_amount': 8   # Deductible preference
                # Removed: currently_on_medical_aid (no longer used)
            }
        elif self.category == 'funeral':
            default_weights = {
                'base_premium': 35,  # Budget is very important for funeral
                'cover_amount': 30,  # Coverage amount is key
                'service_level': 20,  # Service preference matters
                'waiting_period_days': 15,  # Waiting period tolerance
                'marital_status_requirement': 10,  # Eligibility criteria
                'gender_requirement': 10  # Eligibility criteria
            }
        
        # Only include weights for criteria that exist
        return {k: v for k, v in default_weights.items() if k in criteria}
    
    def _apply_category_specific_processing(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply category-specific processing to criteria.
        
        Args:
            criteria: Base criteria dictionary
            
        Returns:
            Enhanced criteria with category-specific adjustments
        """
        if self.category == 'health':
            # Adjust premium range based on family size
            if 'family_size' in criteria and 'base_premium' in criteria:
                family_size = criteria['family_size']
                base_budget = criteria['base_premium']
                
                # Increase budget tolerance for larger families
                if family_size > 4:
                    criteria['base_premium'] = int(base_budget * 1.2)
                elif family_size > 2:
                    criteria['base_premium'] = int(base_budget * 1.1)
            
            # Handle chronic conditions impact
            if 'chronic_conditions' in criteria:
                conditions = criteria['chronic_conditions']
                if isinstance(conditions, list) and len(conditions) > 0 and 'None' not in conditions:
                    # Increase weight for coverage if chronic conditions exist
                    if 'weights' in criteria:
                        criteria['weights']['coverage_priority'] = criteria['weights'].get('coverage_priority', 25) + 10
        
        elif self.category == 'funeral':
            # Adjust coverage based on family size
            if 'family_size' in criteria and 'coverage_amount' in criteria:
                family_size = criteria['family_size']
                base_coverage = criteria['coverage_amount']
                
                # Suggest higher coverage for larger families
                if family_size > 10:
                    criteria['coverage_amount'] = max(base_coverage, 100000)
                elif family_size > 5:
                    criteria['coverage_amount'] = max(base_coverage, 50000)
        
        return criteria
    
    def _get_eligible_policy_ids(self, criteria: Dict[str, Any]) -> List[int]:
        """
        Get list of policy IDs that are eligible based on basic criteria.
        
        Args:
            criteria: Comparison criteria
            
        Returns:
            List of eligible policy IDs
        """
        try:
            # Get category object
            category = PolicyCategory.objects.get(slug=self.category)
            
            # Base query for active, approved policies
            queryset = BasePolicy.objects.filter(
                category=category,
                is_active=True,
                approval_status='APPROVED'
            )
            
            # Apply basic filtering based on criteria
            if 'base_premium' in criteria:
                max_premium = criteria['base_premium'] * 1.2  # Allow 20% over budget
                queryset = queryset.filter(base_premium__lte=max_premium)
            
            if 'age' in criteria:
                age = criteria['age']
                queryset = queryset.filter(
                    minimum_age__lte=age,
                    maximum_age__gte=age
                )
            
            if 'coverage_amount' in criteria:
                min_coverage = criteria['coverage_amount'] * 0.8  # Allow 20% under desired
                queryset = queryset.filter(coverage_amount__gte=min_coverage)
            
            # Order by premium for consistent results
            policy_ids = list(queryset.order_by('base_premium').values_list('id', flat=True))
            
            logger.info(f"Found {len(policy_ids)} eligible policies for {self.category} category")
            return policy_ids
            
        except Exception as e:
            logger.error(f"Error getting eligible policies: {e}")
            return []
    
    def _simplify_comparison_results(
        self, 
        comparison_result: Dict[str, Any], 
        max_results: int
    ) -> Dict[str, Any]:
        """
        Simplify comparison results by removing complex features and limiting results.
        
        Args:
            comparison_result: Full comparison result from engine
            max_results: Maximum number of results to return
            
        Returns:
            Simplified results dictionary
        """
        results = comparison_result.get('results', [])
        
        # Limit to max_results
        top_results = results[:max_results]
        
        simplified_policies = []
        for result in top_results:
            policy = result['policy']
            score_data = result['score_data']
            
            # Create simplified policy result
            simplified_policy = {
                'id': policy.id,
                'name': policy.name,
                'organization': policy.organization.name,
                'monthly_premium': float(policy.base_premium),
                'coverage_amount': float(policy.coverage_amount),
                'waiting_period_days': policy.waiting_period_days,
                'match_score': round(score_data['overall_score'], 1),
                'rank': result.get('rank', 0),
                'key_features': self._extract_key_features(policy),
                'pros': result.get('pros', [])[:3],  # Limit to top 3 pros
                'cons': result.get('cons', [])[:3],  # Limit to top 3 cons
                'value_rating': self._get_value_rating(score_data.get('value_score', 50)),
                'get_quote_url': f'/policies/{policy.id}/quote/',
                'policy_features': self._get_policy_features(policy)  # Add policy features
            }
            
            simplified_policies.append(simplified_policy)
        
        # Create summary
        summary = {
            'best_match_score': simplified_policies[0]['match_score'] if simplified_policies else 0,
            'average_premium': sum(p['monthly_premium'] for p in simplified_policies) / len(simplified_policies) if simplified_policies else 0,
            'premium_range': {
                'min': min(p['monthly_premium'] for p in simplified_policies) if simplified_policies else 0,
                'max': max(p['monthly_premium'] for p in simplified_policies) if simplified_policies else 0
            },
            'coverage_range': {
                'min': min(p['coverage_amount'] for p in simplified_policies) if simplified_policies else 0,
                'max': max(p['coverage_amount'] for p in simplified_policies) if simplified_policies else 0
            }
        }
        
        return {
            'best_match': simplified_policies[0] if simplified_policies else None,
            'policies': simplified_policies,
            'summary': summary
        }
    
    def _extract_key_features(self, policy: BasePolicy) -> List[str]:
        """
        Extract key features from a policy for display.
        
        Args:
            policy: Policy instance
            
        Returns:
            List of key feature strings
        """
        features = []
        
        # Add PolicyFeatures-based features
        try:
            policy_features = policy.policy_features
            
            if self.category == 'health':
                # Add health policy features based on new structure
                if policy_features.annual_limit_per_family:
                    features.append(f'Annual Family Limit: R{policy_features.annual_limit_per_family:,.0f}')
                if policy_features.annual_limit_per_member:
                    features.append(f'Annual Member Limit: R{policy_features.annual_limit_per_member:,.0f}')
                if policy_features.ambulance_coverage:
                    features.append('Ambulance Coverage')
                
                # Handle benefit levels (these are now stored as levels, not boolean)
                if hasattr(policy_features, 'in_hospital_benefit_level'):
                    level = policy_features.in_hospital_benefit_level
                    if level and level != 'no_cover':
                        level_display = {
                            'basic': 'Basic Hospital Care',
                            'moderate': 'Moderate Hospital Care', 
                            'extensive': 'Extensive Hospital Care',
                            'comprehensive': 'Comprehensive Hospital Care'
                        }.get(level, 'Hospital Benefits')
                        features.append(level_display)
                elif policy_features.in_hospital_benefit:  # Fallback to boolean field
                    features.append('In-Hospital Benefits')
                
                if hasattr(policy_features, 'out_hospital_benefit_level'):
                    level = policy_features.out_hospital_benefit_level
                    if level and level != 'no_cover':
                        level_display = {
                            'basic_visits': 'Basic Clinic Visits',
                            'routine_care': 'Routine Medical Care',
                            'extended_care': 'Extended Medical Care',
                            'comprehensive_care': 'Comprehensive Day-to-Day Care'
                        }.get(level, 'Out-of-Hospital Benefits')
                        features.append(level_display)
                elif policy_features.out_hospital_benefit:  # Fallback to boolean field
                    features.append('Out-of-Hospital Benefits')
                
                if policy_features.chronic_medication_availability:
                    features.append('Chronic Medication')
            
            elif self.category == 'funeral':
                if policy_features.cover_amount:
                    features.append(f'Cover Amount: R{policy_features.cover_amount:,.0f}')
                
        except AttributeError:
            # Policy has no policy_features, fall back to legacy attributes
            pass
        
        # Add category-specific features (legacy support)
        if self.category == 'health':
            if hasattr(policy, 'includes_dental_cover') and policy.includes_dental_cover:
                features.append('Dental Cover')
            if hasattr(policy, 'includes_optical_cover') and policy.includes_optical_cover:
                features.append('Optical Cover')
            if hasattr(policy, 'chronic_medication_covered') and policy.chronic_medication_covered:
                features.append('Chronic Medication')
            if hasattr(policy, 'includes_maternity_cover') and policy.includes_maternity_cover:
                features.append('Maternity Cover')
        
        elif self.category == 'funeral':
            if hasattr(policy, 'repatriation_covered') and policy.repatriation_covered:
                features.append('Repatriation')
            if hasattr(policy, 'grocery_benefit') and policy.grocery_benefit:
                features.append('Grocery Benefit')
            if hasattr(policy, 'tombstone_benefit') and policy.tombstone_benefit:
                features.append('Tombstone Benefit')
        
        # Add general features
        if policy.waiting_period_days == 0:
            features.append('No Waiting Period')
        elif policy.waiting_period_days <= 30:
            features.append('Short Waiting Period')
        
        if policy.organization.is_verified:
            features.append('Verified Provider')
        
        return features[:4]  # Limit to 4 key features
    
    def _get_value_rating(self, value_score: float) -> str:
        """
        Convert value score to simple rating.
        
        Args:
            value_score: Numeric value score (0-100)
            
        Returns:
            String rating (Excellent, Good, Fair, Poor)
        """
        if value_score >= 80:
            return 'Excellent'
        elif value_score >= 65:
            return 'Good'
        elif value_score >= 50:
            return 'Fair'
        else:
            return 'Poor'
    
    def _get_policy_features(self, policy: BasePolicy) -> dict:
        """
        Extract PolicyFeatures data for template display.
        
        Args:
            policy: Policy instance
            
        Returns:
            Dictionary with policy features or None if no features exist
        """
        try:
            policy_features = policy.policy_features
            return {
                'annual_limit_per_family': policy_features.annual_limit_per_family,
                'annual_limit_per_member': policy_features.annual_limit_per_member,
                'monthly_household_income': policy_features.monthly_household_income,
                'ambulance_coverage': policy_features.ambulance_coverage,
                'in_hospital_benefit': policy_features.in_hospital_benefit,
                'out_hospital_benefit': policy_features.out_hospital_benefit,
                'chronic_medication_availability': policy_features.chronic_medication_availability,
                'cover_amount': policy_features.cover_amount,
                'marital_status_requirement': policy_features.marital_status_requirement,
                'gender_requirement': policy_features.gender_requirement,
                'insurance_type': policy_features.insurance_type,
                # Removed: currently_on_medical_aid (no longer used)
            }
        except AttributeError:
            # Policy has no policy_features
            return None
    
    def _update_quotation_session(
        self, 
        session_key: str, 
        criteria: Dict[str, Any], 
        results: Dict[str, Any]
    ):
        """
        Update or create quotation session with results.
        
        Args:
            session_key: Session identifier
            criteria: Processed criteria
            results: Quotation results
        """
        try:
            session, created = QuotationSession.objects.update_or_create(
                session_key=session_key,
                defaults={
                    'category': self.category,
                    'user_criteria': criteria,
                    'is_completed': True,
                    'expires_at': timezone.now() + timezone.timedelta(hours=24)
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} quotation session for {session_key[:8]}")
            
        except Exception as e:
            logger.error(f"Error updating quotation session: {e}")


class SimplifiedPolicyComparisonEngine(PolicyComparisonEngine):
    """
    Simplified version of PolicyComparisonEngine that removes complex survey context features.
    
    This class extends the existing PolicyComparisonEngine but overrides methods to:
    - Remove complex survey context processing
    - Simplify scoring algorithms
    - Focus on essential comparison features only
    - Use streamlined weights and criteria
    """
    
    # Simplified scoring weights for essential factors only
    CRITERIA_WEIGHT = Decimal('0.70')  # 70% - Increased focus on criteria match
    VALUE_WEIGHT = Decimal('0.20')     # 20% - Value for money
    REVIEW_WEIGHT = Decimal('0.05')    # 5% - Reduced review weight
    ORGANIZATION_WEIGHT = Decimal('0.05')  # 5% - Reduced organization weight
    
    def compare_policies(
        self,
        policy_ids: List[int],
        user_criteria: Dict[str, Any],
        user=None,
        session_key: str = None,
        survey_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Simplified policy comparison that ignores survey context and uses streamlined processing.
        
        Args:
            policy_ids: List of policy IDs to compare
            user_criteria: Dictionary of user preferences and criteria
            user: User object (optional for anonymous)
            session_key: Session key for anonymous users
            survey_context: Ignored in simplified version
            
        Returns:
            Dictionary with comparison results
        """
        try:
            # Validate inputs with simplified requirements
            if not policy_ids or len(policy_ids) < 1:
                return {'error': 'At least 1 policy required for comparison'}
            
            if len(policy_ids) > 20:  # Allow more policies for better selection
                policy_ids = policy_ids[:20]
            
            # Get policies using simplified query
            policies = self._get_policies_simplified(policy_ids)
            
            if not policies:
                return {'error': 'No valid policies found for comparison'}
            
            # Store user criteria (no survey context)
            self.user_criteria = user_criteria
            
            # Create simplified comparison session
            session = self._create_simplified_session(policies, user_criteria, user, session_key)
            
            # Load simplified criteria
            self._load_simplified_criteria(user_criteria)
            
            # Score each policy with simplified algorithm
            logger.info(f"Scoring {len(policies)} policies with simplified algorithm")
            results = []
            for policy in policies:
                try:
                    score_data = self._score_policy_simplified(policy, user_criteria)
                    results.append({
                        'policy': policy,
                        'score_data': score_data
                    })
                except Exception as e:
                    logger.error(f"Error scoring policy {policy.id}: {str(e)}")
                    continue
            
            if not results:
                return {'error': 'Failed to score policies'}
            
            # Rank policies by simplified score
            ranked_results = self._rank_policies_simplified(results)
            
            # Generate simplified analysis
            analysis = self._generate_simplified_analysis(ranked_results, user_criteria)
            
            # Save results to session
            self._save_simplified_results(session, ranked_results)
            
            return {
                'success': True,
                'session_id': session.id,
                'session_key': session.session_key,
                'category': session.category.name,
                'total_policies': len(policies),
                'best_match': ranked_results[0]['policy'] if ranked_results else None,
                'results': ranked_results,
                'analysis': analysis,
                'created_at': session.created_at,
                'simplified_engine': True  # Flag to indicate simplified processing
            }
            
        except Exception as e:
            logger.error(f"Simplified comparison engine error: {str(e)}")
            return {'error': f'Comparison failed: {str(e)}'}
    
    def _get_policies_simplified(self, policy_ids: List[int]) -> List[BasePolicy]:
        """
        Get policies with minimal prefetching for performance.
        
        Args:
            policy_ids: List of policy IDs
            
        Returns:
            List of BasePolicy instances with essential relations loaded
        """
        base_query = {
            'id__in': policy_ids,
            'is_active': True,
            'approval_status': 'APPROVED'
        }
        
        # Use base policy model with minimal prefetching
        policies = BasePolicy.objects.filter(**base_query).select_related(
            'organization', 'category', 'policy_type'
        ).prefetch_related('policy_features')
        
        return list(policies)
    
    def _create_simplified_session(
        self,
        policies: List[BasePolicy],
        criteria: Dict,
        user,
        session_key
    ) -> 'ComparisonSession':
        """Create a simplified comparison session."""
        from datetime import timedelta
        from django.utils import timezone
        import uuid
        
        if not session_key:
            session_key = str(uuid.uuid4())
        
        # Import here to avoid circular imports
        from comparison.models import ComparisonSession
        
        session = ComparisonSession.objects.create(
            user=user,
            session_key=session_key,
            category=policies[0].category,
            criteria=criteria,
            expires_at=timezone.now() + timedelta(hours=24),  # Shorter expiry
            fallback_mode=True,  # Mark as simplified mode
            fallback_type='simplified_survey',
            fallback_reason='Using simplified survey comparison engine'
        )
        
        session.policies.set(policies)
        return session
    
    def _load_simplified_criteria(self, user_criteria: Dict[str, Any]):
        """
        Load simplified criteria with essential weights only.
        
        Args:
            user_criteria: User criteria from survey responses
        """
        # Use simplified default weights
        default_weights = {
            'base_premium': 40,  # Budget is most important
            'coverage_amount': 30,  # Coverage level
            'waiting_period_days': 20,  # Waiting period
            'organization_reputation': 10  # Provider reputation
        }
        
        # Override with user-specified weights if provided
        user_weights = user_criteria.get('weights', {})
        self.weights = {}
        
        for field_name, default_weight in default_weights.items():
            weight = user_weights.get(field_name, default_weight)
            self.weights[field_name] = Decimal(str(weight))
        
        # Store criteria for evaluation
        self.criteria = {field_name: None for field_name in self.weights.keys()}
    
    def _score_policy_simplified(
        self,
        policy: BasePolicy,
        user_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simplified scoring algorithm focusing on essential factors.
        
        Args:
            policy: Policy to score
            user_criteria: User criteria from survey
            
        Returns:
            Dictionary with simplified score data
        """
        criteria_scores = {}
        total_weighted_score = Decimal('0')
        total_weight = Decimal('0')
        
        # Score essential criteria only
        for field_name, weight in self.weights.items():
            if weight == 0:
                continue
            
            try:
                score = self._evaluate_simplified_criterion(
                    policy, field_name, user_criteria.get(field_name)
                )
                
                criteria_scores[field_name] = {
                    'score': float(score),
                    'weight': float(weight),
                    'weighted_score': float(score * weight / 100)
                }
                
                total_weighted_score += score * weight / 100
                total_weight += weight
                
            except Exception as e:
                logger.warning(f"Error evaluating {field_name} for policy {policy.id}: {str(e)}")
                continue
        
        # Calculate overall criteria score
        if total_weight > 0:
            criteria_score = (total_weighted_score / total_weight) * 100
        else:
            criteria_score = Decimal('50')
        
        # Calculate simplified component scores
        value_score = self._calculate_simplified_value_score(policy, user_criteria)
        review_score = self._calculate_simplified_review_score(policy)
        org_score = self._calculate_simplified_organization_score(policy)
        
        # Combine with simplified weights
        final_score = (
            criteria_score * self.CRITERIA_WEIGHT +
            value_score * self.VALUE_WEIGHT +
            review_score * self.REVIEW_WEIGHT +
            org_score * self.ORGANIZATION_WEIGHT
        )
        
        final_score = final_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'overall_score': float(final_score),
            'criteria_score': float(criteria_score),
            'value_score': float(value_score),
            'review_score': float(review_score),
            'organization_score': float(org_score),
            'criteria_scores': criteria_scores,
            'simplified_scoring': True
        }
    
    def _evaluate_simplified_criterion(
        self,
        policy: BasePolicy,
        field_name: str,
        user_value: Any
    ) -> Decimal:
        """
        Simplified criterion evaluation focusing on essential comparisons.
        
        Args:
            policy: Policy to evaluate
            field_name: Criterion field name
            user_value: User's preference value
            
        Returns:
            Score from 0 to 100
        """
        if field_name == 'base_premium':
            return self._score_premium_match(policy, user_value)
        elif field_name == 'coverage_amount':
            return self._score_coverage_match(policy, user_value)
        elif field_name == 'waiting_period_days':
            return self._score_waiting_period_match(policy, user_value)
        elif field_name == 'organization_reputation':
            return self._score_organization_reputation(policy)
        else:
            # Default neutral score for unknown criteria
            return Decimal('50')
    
    def _score_premium_match(self, policy: BasePolicy, user_budget: Any) -> Decimal:
        """Score how well policy premium matches user budget."""
        if not user_budget:
            return Decimal('50')
        
        try:
            budget = float(user_budget)
            premium = float(policy.base_premium)
            
            if premium <= budget:
                # Premium within budget - score based on how much under
                ratio = premium / budget
                return Decimal(str(100 - (ratio * 20)))  # Higher score for lower premium
            else:
                # Premium over budget - penalize based on how much over
                ratio = budget / premium
                return Decimal(str(max(0, ratio * 80)))  # Penalty for going over budget
                
        except (ValueError, TypeError, ZeroDivisionError):
            return Decimal('50')
    
    def _score_coverage_match(self, policy: BasePolicy, user_coverage: Any) -> Decimal:
        """Score how well policy coverage matches user needs."""
        if not user_coverage:
            return Decimal('50')
        
        try:
            desired_coverage = float(user_coverage)
            policy_coverage = float(policy.coverage_amount)
            
            if policy_coverage >= desired_coverage:
                # Coverage meets or exceeds needs
                if policy_coverage <= desired_coverage * 1.5:
                    return Decimal('100')  # Perfect match
                else:
                    # Too much coverage might mean higher premium
                    ratio = desired_coverage / policy_coverage
                    return Decimal(str(80 + (ratio * 20)))
            else:
                # Coverage below needs - score based on how close
                ratio = policy_coverage / desired_coverage
                return Decimal(str(max(0, ratio * 70)))
                
        except (ValueError, TypeError, ZeroDivisionError):
            return Decimal('50')
    
    def _score_waiting_period_match(self, policy: BasePolicy, user_tolerance: Any) -> Decimal:
        """Score waiting period against user tolerance."""
        if user_tolerance is None:
            return Decimal('50')
        
        try:
            tolerance_days = int(user_tolerance) if user_tolerance else 0
            policy_waiting = policy.waiting_period_days
            
            if policy_waiting <= tolerance_days:
                # Within tolerance - shorter is better
                if tolerance_days == 0:
                    return Decimal('100') if policy_waiting == 0 else Decimal('80')
                else:
                    ratio = 1 - (policy_waiting / tolerance_days)
                    return Decimal(str(80 + (ratio * 20)))
            else:
                # Exceeds tolerance - penalty
                if tolerance_days == 0:
                    return Decimal('20')  # User wants no waiting period
                else:
                    ratio = tolerance_days / policy_waiting
                    return Decimal(str(max(10, ratio * 60)))
                    
        except (ValueError, TypeError, ZeroDivisionError):
            return Decimal('50')
    
    def _score_organization_reputation(self, policy: BasePolicy) -> Decimal:
        """Simple organization reputation scoring."""
        score = Decimal('50')  # Base score
        
        if hasattr(policy.organization, 'is_verified') and policy.organization.is_verified:
            score += Decimal('30')
        
        if hasattr(policy.organization, 'rating') and policy.organization.rating:
            # Assume rating is 1-5 scale
            rating_score = (float(policy.organization.rating) - 1) * 12.5
            score += Decimal(str(rating_score))
        
        return min(Decimal('100'), max(Decimal('0'), score))
    
    def _calculate_simplified_value_score(self, policy: BasePolicy, user_criteria: Dict) -> Decimal:
        """Simplified value calculation - coverage per rand spent."""
        try:
            coverage_per_rand = policy.coverage_amount / policy.base_premium
            
            # Normalize to 0-100 scale (this is category-dependent)
            if self.category_slug == 'health':
                # Health insurance: good value is 1000+ coverage per rand
                normalized_score = min(100, (coverage_per_rand / 1000) * 100)
            elif self.category_slug == 'funeral':
                # Funeral insurance: good value is 200+ coverage per rand
                normalized_score = min(100, (coverage_per_rand / 200) * 100)
            else:
                # Generic calculation
                normalized_score = min(100, (coverage_per_rand / 500) * 100)
            
            return Decimal(str(max(0, normalized_score)))
            
        except (ValueError, TypeError, ZeroDivisionError):
            return Decimal('50')
    
    def _calculate_simplified_review_score(self, policy: BasePolicy) -> Decimal:
        """Simplified review scoring - basic average if available."""
        try:
            if hasattr(policy, 'reviews') and policy.reviews.exists():
                avg_rating = policy.reviews.aggregate(
                    avg_rating=models.Avg('rating')
                )['avg_rating']
                
                if avg_rating:
                    # Convert 1-5 rating to 0-100 score
                    return Decimal(str((avg_rating - 1) * 25))
            
            # Default score if no reviews
            return Decimal('60')
            
        except Exception:
            return Decimal('60')
    
    def _calculate_simplified_organization_score(self, policy: BasePolicy) -> Decimal:
        """Simplified organization scoring."""
        return self._score_organization_reputation(policy)
    
    def _rank_policies_simplified(self, results: List[Dict]) -> List[Dict]:
        """Rank policies by simplified score with essential information."""
        # Sort by overall score
        sorted_results = sorted(
            results, 
            key=lambda x: x['score_data']['overall_score'], 
            reverse=True
        )
        
        # Add rank and simplified pros/cons
        for i, result in enumerate(sorted_results):
            result['rank'] = i + 1
            result['pros'] = self._generate_simplified_pros(result['policy'], result['score_data'])
            result['cons'] = self._generate_simplified_cons(result['policy'], result['score_data'])
        
        return sorted_results
    
    def _generate_simplified_pros(self, policy: BasePolicy, score_data: Dict) -> List[str]:
        """Generate simplified pros list."""
        pros = []
        
        if score_data['value_score'] >= 70:
            pros.append("Good value for money")
        
        if policy.waiting_period_days == 0:
            pros.append("No waiting period")
        elif policy.waiting_period_days <= 30:
            pros.append("Short waiting period")
        
        if hasattr(policy.organization, 'is_verified') and policy.organization.is_verified:
            pros.append("Verified provider")
        
        if score_data['overall_score'] >= 80:
            pros.append("Excellent match for your needs")
        
        return pros[:3]  # Limit to 3 pros
    
    def _generate_simplified_cons(self, policy: BasePolicy, score_data: Dict) -> List[str]:
        """Generate simplified cons list."""
        cons = []
        
        if score_data['value_score'] < 40:
            cons.append("Higher cost relative to coverage")
        
        if policy.waiting_period_days > 180:
            cons.append("Long waiting period")
        
        if score_data['overall_score'] < 60:
            cons.append("Limited match for your preferences")
        
        return cons[:3]  # Limit to 3 cons
    
    def _generate_simplified_analysis(self, ranked_results: List[Dict], user_criteria: Dict) -> Dict:
        """Generate simplified analysis of comparison results."""
        if not ranked_results:
            return {'summary': 'No policies found matching your criteria'}
        
        best_policy = ranked_results[0]['policy']
        best_score = ranked_results[0]['score_data']['overall_score']
        
        analysis = {
            'summary': f"Found {len(ranked_results)} matching policies. "
                      f"Best match: {best_policy.name} with {best_score:.1f}% compatibility.",
            'best_match_reason': self._get_best_match_reason(best_policy, ranked_results[0]['score_data']),
            'average_score': sum(r['score_data']['overall_score'] for r in ranked_results) / len(ranked_results),
            'score_range': {
                'highest': ranked_results[0]['score_data']['overall_score'],
                'lowest': ranked_results[-1]['score_data']['overall_score']
            }
        }
        
        return analysis
    
    def _get_best_match_reason(self, policy: BasePolicy, score_data: Dict) -> str:
        """Get reason why this policy is the best match."""
        reasons = []
        
        if score_data['criteria_score'] >= 80:
            reasons.append("excellent criteria match")
        
        if score_data['value_score'] >= 70:
            reasons.append("good value for money")
        
        if policy.waiting_period_days == 0:
            reasons.append("no waiting period")
        
        if reasons:
            return f"Best match due to {', '.join(reasons)}"
        else:
            return "Best available option for your requirements"
    
    def _save_simplified_results(self, session: 'ComparisonSession', ranked_results: List[Dict]):
        """Save simplified results to session."""
        try:
            # Import here to avoid circular imports
            from comparison.models import ComparisonResult
            
            # Clear existing results
            session.results.all().delete()
            
            # Save new results
            for result in ranked_results:
                ComparisonResult.objects.create(
                    session=session,
                    policy=result['policy'],
                    overall_score=result['score_data']['overall_score'],
                    criteria_scores=result['score_data']['criteria_scores'],
                    rank=result['rank'],
                    pros=result.get('pros', []),
                    cons=result.get('cons', []),
                    recommendation_reason=f"Simplified scoring: {result['score_data']['overall_score']:.1f}% match"
                )
            
            # Update session
            if ranked_results:
                session.best_match_policy = ranked_results[0]['policy']
                session.match_scores = {
                    str(r['policy'].id): r['score_data']['overall_score'] 
                    for r in ranked_results
                }
                session.status = 'COMPLETED'
                session.save()
            
        except Exception as e:
            logger.error(f"Error saving simplified results: {e}")
    
    def _score_policy_with_survey_context(
        self,
        policy: BasePolicy,
        user_criteria: Dict[str, Any],
        survey_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Override to use simplified scoring instead of survey-enhanced scoring.
        
        Args:
            policy: Policy to score
            user_criteria: User criteria
            survey_context: Ignored in simplified version
            
        Returns:
            Simplified score data without survey enhancements
        """
        # Use simplified scoring method instead of survey-enhanced version
        return self._score_policy_simplified(policy, user_criteria)