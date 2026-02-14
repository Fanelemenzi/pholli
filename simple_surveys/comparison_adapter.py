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
        max_results: int = 5,
        include_shortcomings: bool = False
    ) -> Dict[str, Any]:
        """
        Generate policy quotations from simple survey responses.
        
        Args:
            session_key: Session identifier containing survey responses
            max_results: Maximum number of policy results to return
            include_shortcomings: Whether to include detailed shortcomings analysis
            
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
            fallback_used = False
            
            # Console logging for policy matching
            print(f"\n{'='*60}")
            print(f"POLICY MATCHING ANALYSIS - Session: {session_key[:8]}")
            print(f"{'='*60}")
            print(f"Category: {self.category}")
            print(f"Initial strict matching found: {len(policy_ids)} policies")
            
            if not policy_ids:
                # Fallback: Get best available policies with relaxed criteria
                print(f"⚠️  No policies found with strict criteria, applying fallback...")
                logger.info(f"No policies found with strict criteria, applying fallback for session {session_key}")
                policy_ids = self._get_fallback_policy_ids(criteria)
                fallback_used = True
                print(f"Fallback matching found: {len(policy_ids)} policies")
                
                if not policy_ids:
                    print(f"❌ No policies available even with fallback criteria")
                    print(f"{'='*60}\n")
                    return {
                        'success': False,
                        'error': 'No policies available in this category',
                        'session_key': session_key,
                        'criteria': criteria
                    }
                else:
                    print(f"✅ Fallback successful - showing best available policies")
            else:
                print(f"✅ Strict matching successful - showing exact matches")
            
            # Limit to max_results for performance
            if len(policy_ids) > max_results * 2:
                # Get more than needed for better selection
                original_count = len(policy_ids)
                policy_ids = policy_ids[:max_results * 2]
                print(f"📊 Limited policies for performance: {original_count} → {len(policy_ids)}")
            
            print(f"🔍 Analyzing {len(policy_ids)} policies for comparison...")
            
            # Use comparison engine with simplified criteria
            comparison_result = self.comparison_engine.compare_policies(
                policy_ids=policy_ids,
                user_criteria=criteria,
                session_key=session_key
            )
            
            if not comparison_result.get('success'):
                print(f"❌ Comparison engine failed: {comparison_result.get('error', 'Unknown error')}")
                print(f"{'='*60}\n")
                return {
                    'success': False,
                    'error': comparison_result.get('error', 'Comparison failed'),
                    'session_key': session_key
                }
            
            # Simplify and limit results
            simplified_results = self._simplify_comparison_results(
                comparison_result, max_results
            )
            
            # Console logging for final results
            final_count = len(simplified_results['policies'])
            print(f"📋 Final results prepared: {final_count} policies")
            
            if simplified_results['policies']:
                best_score = simplified_results['policies'][0].get('match_score', 0)
                avg_premium = sum(p['monthly_premium'] for p in simplified_results['policies']) / final_count
                print(f"🏆 Best match score: {best_score}%")
                print(f"💰 Average premium: R{avg_premium:.0f}")
                
                # Show top 3 policy names
                print(f"📝 Top policies:")
                for i, policy in enumerate(simplified_results['policies'][:3], 1):
                    print(f"   {i}. {policy['name']} - R{policy['monthly_premium']:.0f} ({policy['match_score']}% match)")
            
            print(f"{'='*60}\n")
            
            # Add shortcomings analysis if requested
            if include_shortcomings:
                simplified_results = self._add_shortcomings_to_results(
                    simplified_results, session_key
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
                'generated_at': timezone.now().isoformat(),
                'has_shortcomings_analysis': include_shortcomings,
                'fallback_used': fallback_used
            }
            
        except Exception as e:
            logger.error(f"Error generating quotations for session {session_key}: {e}")
            return {
                'success': False,
                'error': f'Failed to generate quotations: {str(e)}',
                'session_key': session_key
            }
    
    def generate_quotations_with_shortcomings(
        self, 
        session_key: str, 
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Generate quotations with detailed shortcomings analysis.
        
        This is a convenience method that calls generate_quotations with 
        include_shortcomings=True and adds additional analysis.
        
        Args:
            session_key: Session identifier containing survey responses
            max_results: Maximum number of policy results to return
            
        Returns:
            Dictionary with enhanced quotation results and shortcomings analysis
        """
        # Get base quotations with shortcomings
        result = self.generate_quotations(
            session_key=session_key, 
            max_results=max_results, 
            include_shortcomings=True
        )
        
        if not result.get('success'):
            return result
        
        # Add enhanced analysis
        user_criteria = self._get_user_criteria_for_analysis(session_key)
        enhanced_policies = result.get('policies', [])
        
        # Add overall shortcomings analysis
        overall_analysis = self._generate_overall_shortcomings_analysis(
            enhanced_policies, user_criteria
        )
        
        result.update({
            'shortcomings_analysis': overall_analysis,
            'has_perfect_match': any(p.get('shortcomings_severity') == 'none' for p in enhanced_policies),
            'common_gaps': self._identify_common_gaps(enhanced_policies),
            'recommendations': self._generate_recommendations(enhanced_policies, user_criteria)
        })
        
        return result
    
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
        if survey_field in ['age', 'family_size', 'family_members_to_cover', 'household_income']:
            try:
                return int(response_value) if response_value else 0
            except (ValueError, TypeError):
                return 0
        
        # Handle monthly budget range conversions
        if survey_field == 'monthly_budget':
            return self._convert_budget_range_to_value(response_value)
        
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
        # Use a large number instead of infinity for JSON compatibility
        MAX_VALUE = 999999999  # 999 million
        
        if not range_selection or range_selection == 'not_sure':
            return {'min_value': 0, 'max_value': MAX_VALUE, 'guidance_needed': True}
        
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
            '5m-plus': {'min': 5000001, 'max': MAX_VALUE},
            
            # Member ranges
            '10k-25k': {'min': 10000, 'max': 25000},
            '25k-50k': {'min': 25001, 'max': 50000},
            '50k-100k': {'min': 50001, 'max': 100000},
            '100k-200k': {'min': 100001, 'max': 200000},
            '200k-500k': {'min': 200001, 'max': 500000},
            '500k-1m': {'min': 500001, 'max': 1000000},
            '1m-2m': {'min': 1000001, 'max': 2000000},
            '2m-plus': {'min': 2000001, 'max': MAX_VALUE},
        }
        
        range_data = range_mappings.get(range_selection, {'min': 0, 'max': MAX_VALUE})
        
        return {
            'min_value': range_data['min'],
            'max_value': range_data['max'],
            'range_selection': range_selection,
            'guidance_needed': False
        }
    
    def _convert_budget_range_to_value(self, range_selection: str) -> int:
        """
        Convert budget range selection to a single value for comparison.
        
        Args:
            range_selection: Selected budget range (e.g., '101-200')
            
        Returns:
            Integer value representing the budget for comparison (uses range midpoint)
        """
        if not range_selection:
            return 200  # Default fallback
        
        # Define budget range mappings
        budget_mappings = {
            '50-100': 75,      # Midpoint of range
            '101-200': 150,    # Midpoint of range
            '201-350': 275,    # Midpoint of range
            '351-500': 425,    # Midpoint of range
            '500+': 600,       # Reasonable value for unlimited budget
            '500-750': 625,    # Handle legacy range format
            '750+': 800        # Handle higher budget ranges
        }
        
        return budget_mappings.get(range_selection, 200)  # Default to R200 if unknown range
    
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
            
            # Console logging for policy filtering
            print(f"🔍 Policy Filtering Details:")
            print(f"   Category: {self.category}")
            print(f"   Base query (active, approved): Found policies")
            
            if 'base_premium' in criteria:
                max_premium = criteria['base_premium'] * 1.2
                print(f"   Budget filter: ≤ R{max_premium:.0f} (user budget: R{criteria['base_premium']:.0f})")
            
            if 'age' in criteria:
                age = criteria['age']
                print(f"   Age filter: {age} years old")
            
            if 'coverage_amount' in criteria:
                min_coverage = criteria['coverage_amount'] * 0.8
                print(f"   Coverage filter: ≥ R{min_coverage:.0f} (user needs: R{criteria['coverage_amount']:.0f})")
            
            print(f"   ✅ Final eligible policies: {len(policy_ids)}")
            
            return policy_ids
            
        except Exception as e:
            logger.error(f"Error getting eligible policies: {e}")
            return []
    
    def _get_fallback_policy_ids(self, criteria: Dict[str, Any]) -> List[int]:
        """
        Get fallback policy IDs when no policies match strict criteria.
        Uses relaxed filtering to find the best available policies.
        
        Args:
            criteria: Comparison criteria
            
        Returns:
            List of fallback policy IDs
        """
        try:
            # Get category object
            category = PolicyCategory.objects.get(slug=self.category)
            
            # Base query for active, approved policies (no strict filtering)
            queryset = BasePolicy.objects.filter(
                category=category,
                is_active=True,
                approval_status='APPROVED'
            )
            
            # Apply very relaxed filtering - only age if specified
            if 'age' in criteria:
                age = criteria['age']
                # Allow wider age range for fallback
                queryset = queryset.filter(
                    minimum_age__lte=age + 5,  # Allow 5 years over
                    maximum_age__gte=age - 5   # Allow 5 years under
                )
            
            # Order by premium to get most affordable options first
            policy_ids = list(queryset.order_by('base_premium').values_list('id', flat=True)[:10])
            
            logger.info(f"Found {len(policy_ids)} fallback policies for {self.category} category")
            
            # Console logging for fallback filtering
            print(f"🔄 Fallback Policy Filtering:")
            print(f"   Relaxed criteria applied (wider age range, no budget/coverage limits)")
            
            if 'age' in criteria:
                age = criteria['age']
                print(f"   Age range: {age-5} to {age+5} years (original: {age})")
            
            print(f"   ✅ Fallback policies found: {len(policy_ids)}")
            
            return policy_ids
            
        except Exception as e:
            logger.error(f"Error getting fallback policies: {e}")
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
    
    def _add_shortcomings_to_results(
        self, 
        simplified_results: Dict[str, Any], 
        session_key: str
    ) -> Dict[str, Any]:
        """
        Add shortcomings analysis to simplified results.
        
        Args:
            simplified_results: Base simplified results
            session_key: Session identifier for getting user criteria
            
        Returns:
            Enhanced results with shortcomings analysis
        """
        try:
            user_criteria = self._get_user_criteria_for_analysis(session_key)
            enhanced_policies = []
            
            for policy_data in simplified_results.get('policies', []):
                enhanced_policy = self._add_shortcomings_analysis_to_policy(
                    policy_data, user_criteria
                )
                enhanced_policies.append(enhanced_policy)
            
            simplified_results['policies'] = enhanced_policies
            return simplified_results
            
        except Exception as e:
            logger.error(f"Error adding shortcomings analysis: {e}")
            return simplified_results
    
    def _get_user_criteria_for_analysis(self, session_key: str) -> Dict[str, Any]:
        """Get user criteria from survey responses for shortcomings analysis."""
        try:
            responses = SimpleSurveyResponse.objects.filter(
                session_key=session_key,
                category=self.category
            )
            
            criteria = {}
            for response in responses:
                criteria[response.question.field_name] = {
                    'value': response.response_value,
                    'display_value': response.get_display_value()
                }
            
            return criteria
            
        except Exception as e:
            logger.error(f"Error getting user criteria for analysis: {e}")
            return {}
    
    def _add_shortcomings_analysis_to_policy(
        self, 
        policy_data: Dict[str, Any], 
        user_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add shortcomings analysis to a single policy.
        
        Args:
            policy_data: Base policy data
            user_criteria: User's survey responses
            
        Returns:
            Enhanced policy data with shortcomings analysis
        """
        try:
            # Get the actual policy object
            policy = BasePolicy.objects.get(id=policy_data['id'])
            
            # Analyze shortcomings
            shortcomings = self._analyze_policy_shortcomings(policy, user_criteria)
            
            # Categorize shortcomings by severity
            critical_gaps = [s for s in shortcomings if s['severity'] == 'critical']
            moderate_gaps = [s for s in shortcomings if s['severity'] == 'moderate']
            minor_gaps = [s for s in shortcomings if s['severity'] == 'minor']
            
            # Determine overall shortcomings severity
            if critical_gaps:
                severity = 'critical'
                severity_description = "Has critical gaps that may make this policy unsuitable"
            elif moderate_gaps:
                severity = 'moderate'
                severity_description = "Has some important limitations to consider"
            elif minor_gaps:
                severity = 'minor'
                severity_description = "Minor limitations that may not be significant"
            else:
                severity = 'none'
                severity_description = "Excellent match with no significant gaps"
            
            # Add shortcomings data to policy
            policy_data.update({
                'shortcomings': shortcomings,
                'critical_gaps': critical_gaps,
                'moderate_gaps': moderate_gaps,
                'minor_gaps': minor_gaps,
                'shortcomings_severity': severity,
                'shortcomings_description': severity_description,
                'gap_count': len(shortcomings),
                'suitability_score': self._calculate_suitability_score(shortcomings),
                'improvement_suggestions': self._generate_improvement_suggestions(shortcomings, policy)
            })
            
            return policy_data
            
        except Exception as e:
            logger.error(f"Error analyzing shortcomings for policy {policy_data.get('id')}: {e}")
            # Return original data if analysis fails
            policy_data.update({
                'shortcomings': [],
                'shortcomings_severity': 'unknown',
                'shortcomings_description': 'Unable to analyze gaps',
                'gap_count': 0,
                'suitability_score': policy_data.get('match_score', 50)
            })
            return policy_data
    
    def _analyze_policy_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze specific shortcomings between policy and user needs.
        
        Args:
            policy: Policy object to analyze
            user_criteria: User's preferences and requirements
            
        Returns:
            List of shortcoming dictionaries with details
        """
        shortcomings = []
        
        if self.category == 'health':
            shortcomings.extend(self._analyze_health_shortcomings(policy, user_criteria))
        elif self.category == 'funeral':
            shortcomings.extend(self._analyze_funeral_shortcomings(policy, user_criteria))
        
        return shortcomings
    
    def _analyze_health_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze health policy shortcomings."""
        shortcomings = []
        
        try:
            policy_features = policy.policy_features
        except AttributeError:
            shortcomings.append({
                'type': 'missing_features',
                'severity': 'critical',
                'title': 'No Policy Features Available',
                'description': 'This policy lacks detailed feature information',
                'impact': 'Cannot verify coverage details',
                'suggestion': 'Contact provider for detailed policy information'
            })
            return shortcomings
        
        # Budget analysis
        user_budget = user_criteria.get('monthly_budget', {}).get('value')
        if user_budget:
            budget_value = self._convert_budget_range_to_value(user_budget)
            if float(policy.base_premium) > budget_value * 1.1:  # 10% tolerance
                excess = float(policy.base_premium) - budget_value
                shortcomings.append({
                    'type': 'budget_exceeded',
                    'severity': 'moderate' if excess <= 100 else 'critical',
                    'title': 'Over Budget',
                    'description': f'Premium is R{excess:.0f} above your stated budget',
                    'impact': 'May strain your monthly finances',
                    'suggestion': f'Consider policies under R{budget_value} or increase your budget'
                })
        
        # Chronic medication
        needs_chronic = user_criteria.get('needs_chronic_medication', {}).get('value')
        if needs_chronic == 'yes' and not policy_features.chronic_medication_availability:
            shortcomings.append({
                'type': 'missing_feature',
                'severity': 'critical',
                'title': 'No Chronic Medication Coverage',
                'description': 'You need chronic medication coverage but this policy does not provide it',
                'impact': 'Will need to pay full cost of chronic medications',
                'suggestion': 'This is a critical gap - look for policies that include chronic medication benefits'
            })
        
        return shortcomings
    
    def _analyze_funeral_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze funeral policy shortcomings."""
        shortcomings = []
        # Add funeral-specific analysis here
        return shortcomings
    
    def _calculate_suitability_score(self, shortcomings: List[Dict[str, Any]]) -> int:
        """Calculate overall suitability score based on shortcomings."""
        if not shortcomings:
            return 100
        
        penalty = 0
        for shortcoming in shortcomings:
            if shortcoming['severity'] == 'critical':
                penalty += 25
            elif shortcoming['severity'] == 'moderate':
                penalty += 15
            elif shortcoming['severity'] == 'minor':
                penalty += 5
        
        return max(0, 100 - penalty)
    
    def _generate_improvement_suggestions(
        self, 
        shortcomings: List[Dict[str, Any]], 
        policy: BasePolicy
    ) -> List[str]:
        """Generate suggestions for addressing shortcomings."""
        suggestions = []
        
        critical_gaps = [s for s in shortcomings if s['severity'] == 'critical']
        moderate_gaps = [s for s in shortcomings if s['severity'] == 'moderate']
        
        if critical_gaps:
            suggestions.append("This policy has critical gaps - consider other options first")
            for gap in critical_gaps:
                suggestions.append(gap['suggestion'])
        
        if moderate_gaps:
            suggestions.append("Consider if you can accept these limitations:")
            for gap in moderate_gaps[:2]:  # Limit to top 2
                suggestions.append(f"• {gap['title']}: {gap['suggestion']}")
        
        if not critical_gaps and not moderate_gaps:
            suggestions.append("This policy is a good match for your needs")
        
        return suggestions[:4]  # Limit to 4 suggestions
    
    def _identify_common_gaps(self, enhanced_policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify gaps that are common across multiple policies."""
        gap_counts = {}
        
        for policy in enhanced_policies:
            for shortcoming in policy.get('shortcomings', []):
                gap_type = shortcoming['type']
                if gap_type not in gap_counts:
                    gap_counts[gap_type] = {
                        'count': 0,
                        'title': shortcoming['title'],
                        'description': shortcoming['description']
                    }
                gap_counts[gap_type]['count'] += 1
        
        # Return gaps that affect more than half the policies
        threshold = len(enhanced_policies) / 2
        common_gaps = [
            {
                'type': gap_type,
                'title': data['title'],
                'description': data['description'],
                'affected_policies': data['count'],
                'percentage': (data['count'] / len(enhanced_policies)) * 100
            }
            for gap_type, data in gap_counts.items()
            if data['count'] > threshold
        ]
        
        return sorted(common_gaps, key=lambda x: x['affected_policies'], reverse=True)
    
    def _generate_recommendations(
        self, 
        enhanced_policies: List[Dict[str, Any]], 
        user_criteria: Dict[str, Any]
    ) -> List[str]:
        """Generate overall recommendations based on the analysis."""
        recommendations = []
        
        if not enhanced_policies:
            return ["No policies match your criteria. Consider broadening your requirements."]
        
        best_policy = enhanced_policies[0]
        
        if best_policy.get('shortcomings_severity') == 'none':
            recommendations.append(f"Excellent match found: {best_policy['name']} meets all your requirements")
        elif best_policy.get('shortcomings_severity') == 'critical':
            recommendations.append("No ideal matches found. Consider:")
            recommendations.append("• Adjusting your budget or coverage requirements")
            recommendations.append("• Looking into supplementary insurance for gaps")
            recommendations.append("• Consulting with an insurance advisor")
        else:
            recommendations.append(f"Best available option: {best_policy['name']}")
            recommendations.append("Consider if you can accept the identified limitations")
        
        return recommendations[:5]  # Limit to 5 recommendations


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
            from surveys.session_key_manager import session_key_manager
            session_key = session_key_manager.generate_new_session_key(
                self.category,
                None,  # No user context in adapter
                "comparison_adapter"
            )
        
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
    
    def _add_shortcomings_to_results(
        self, 
        simplified_results: Dict[str, Any], 
        session_key: str
    ) -> Dict[str, Any]:
        """
        Add shortcomings analysis to simplified results.
        
        Args:
            simplified_results: Base simplified results
            session_key: Session identifier for getting user criteria
            
        Returns:
            Enhanced results with shortcomings analysis
        """
        try:
            user_criteria = self._get_user_criteria_for_analysis(session_key)
            enhanced_policies = []
            
            for policy_data in simplified_results.get('policies', []):
                enhanced_policy = self._add_shortcomings_analysis_to_policy(
                    policy_data, user_criteria
                )
                enhanced_policies.append(enhanced_policy)
            
            simplified_results['policies'] = enhanced_policies
            return simplified_results
            
        except Exception as e:
            logger.error(f"Error adding shortcomings analysis: {e}")
            return simplified_results
    
    def _get_user_criteria_for_analysis(self, session_key: str) -> Dict[str, Any]:
        """Get user criteria from survey responses for shortcomings analysis."""
        try:
            responses = SimpleSurveyResponse.objects.filter(
                session_key=session_key,
                category=self.category
            )
            
            criteria = {}
            for response in responses:
                criteria[response.question.field_name] = {
                    'value': response.response_value,
                    'display_value': response.get_display_value()
                }
            
            return criteria
            
        except Exception as e:
            logger.error(f"Error getting user criteria for analysis: {e}")
            return {}
    
    def _add_shortcomings_analysis_to_policy(
        self, 
        policy_data: Dict[str, Any], 
        user_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add shortcomings analysis to a single policy.
        
        Args:
            policy_data: Base policy data
            user_criteria: User's survey responses
            
        Returns:
            Enhanced policy data with shortcomings analysis
        """
        try:
            # Get the actual policy object
            policy = BasePolicy.objects.get(id=policy_data['id'])
            
            # Analyze shortcomings
            shortcomings = self._analyze_policy_shortcomings(policy, user_criteria)
            
            # Categorize shortcomings by severity
            critical_gaps = [s for s in shortcomings if s['severity'] == 'critical']
            moderate_gaps = [s for s in shortcomings if s['severity'] == 'moderate']
            minor_gaps = [s for s in shortcomings if s['severity'] == 'minor']
            
            # Determine overall shortcomings severity
            if critical_gaps:
                severity = 'critical'
                severity_description = "Has critical gaps that may make this policy unsuitable"
            elif moderate_gaps:
                severity = 'moderate'
                severity_description = "Has some important limitations to consider"
            elif minor_gaps:
                severity = 'minor'
                severity_description = "Minor limitations that may not be significant"
            else:
                severity = 'none'
                severity_description = "Excellent match with no significant gaps"
            
            # Add shortcomings data to policy
            policy_data.update({
                'shortcomings': shortcomings,
                'critical_gaps': critical_gaps,
                'moderate_gaps': moderate_gaps,
                'minor_gaps': minor_gaps,
                'shortcomings_severity': severity,
                'shortcomings_description': severity_description,
                'gap_count': len(shortcomings),
                'suitability_score': self._calculate_suitability_score(shortcomings),
                'improvement_suggestions': self._generate_improvement_suggestions(shortcomings, policy)
            })
            
            return policy_data
            
        except Exception as e:
            logger.error(f"Error analyzing shortcomings for policy {policy_data.get('id')}: {e}")
            # Return original data if analysis fails
            policy_data.update({
                'shortcomings': [],
                'shortcomings_severity': 'unknown',
                'shortcomings_description': 'Unable to analyze gaps',
                'gap_count': 0,
                'suitability_score': policy_data.get('match_score', 50)
            })
            return policy_data
    
    def _analyze_policy_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze specific shortcomings between policy and user needs.
        
        Args:
            policy: Policy object to analyze
            user_criteria: User's preferences and requirements
            
        Returns:
            List of shortcoming dictionaries with details
        """
        shortcomings = []
        
        if self.category == 'health':
            shortcomings.extend(self._analyze_health_shortcomings(policy, user_criteria))
        elif self.category == 'funeral':
            shortcomings.extend(self._analyze_funeral_shortcomings(policy, user_criteria))
        
        return shortcomings
    
    def _analyze_health_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze health policy shortcomings."""
        shortcomings = []
        
        try:
            policy_features = policy.policy_features
        except AttributeError:
            shortcomings.append({
                'type': 'missing_features',
                'severity': 'critical',
                'title': 'No Policy Features Available',
                'description': 'This policy lacks detailed feature information',
                'impact': 'Cannot verify coverage details',
                'suggestion': 'Contact provider for detailed policy information'
            })
            return shortcomings
        
        # Budget analysis
        user_budget = user_criteria.get('monthly_budget', {}).get('value')
        if user_budget:
            budget_value = self._convert_budget_range_to_value(user_budget)
            if float(policy.base_premium) > budget_value * 1.1:  # 10% tolerance
                excess = float(policy.base_premium) - budget_value
                shortcomings.append({
                    'type': 'budget_exceeded',
                    'severity': 'moderate' if excess <= 100 else 'critical',
                    'title': 'Over Budget',
                    'description': f'Premium is R{excess:.0f} above your stated budget',
                    'impact': 'May strain your monthly finances',
                    'suggestion': f'Consider policies under R{budget_value} or increase your budget'
                })
        
        # Annual limit analysis
        family_limit_pref = user_criteria.get('annual_limit_family_range', {}).get('value')
        if family_limit_pref and hasattr(policy_features, 'annual_limit_per_family'):
            if policy_features.annual_limit_per_family:
                user_range = self._convert_range_to_criteria('annual_limit_family_range', family_limit_pref)
                policy_limit = float(policy_features.annual_limit_per_family)
                
                if policy_limit < user_range['min_value']:
                    shortfall = user_range['min_value'] - policy_limit
                    shortcomings.append({
                        'type': 'coverage_shortfall',
                        'severity': 'critical' if shortfall > 100000 else 'moderate',
                        'title': 'Annual Family Limit Too Low',
                        'description': f'Policy limit (R{policy_limit:,.0f}) is R{shortfall:,.0f} below your minimum preference',
                        'impact': 'May not cover major medical expenses',
                        'suggestion': 'Look for policies with higher annual limits or consider gap insurance'
                    })
        
        # Benefit level analysis
        hospital_pref = user_criteria.get('in_hospital_benefit_level', {}).get('value')
        if hospital_pref and hasattr(policy_features, 'in_hospital_benefit_level'):
            policy_level = policy_features.in_hospital_benefit_level
            if self._is_benefit_level_insufficient(hospital_pref, policy_level):
                shortcomings.append({
                    'type': 'benefit_level_gap',
                    'severity': 'moderate',
                    'title': 'In-Hospital Coverage Below Preference',
                    'description': f'Policy offers {policy_level or "no"} coverage, you wanted {hospital_pref}',
                    'impact': 'May have higher out-of-pocket costs for hospital stays',
                    'suggestion': 'Consider upgrading to a plan with higher hospital coverage'
                })
        
        # Ambulance coverage
        wants_ambulance = user_criteria.get('wants_ambulance_coverage', {}).get('value')
        if wants_ambulance == 'yes' and not policy_features.ambulance_coverage:
            shortcomings.append({
                'type': 'missing_feature',
                'severity': 'moderate',
                'title': 'No Ambulance Coverage',
                'description': 'You requested ambulance coverage but this policy does not include it',
                'impact': 'Will need to pay ambulance costs out-of-pocket',
                'suggestion': 'Look for policies with ambulance coverage or consider separate ambulance insurance'
            })
        
        # Chronic medication
        needs_chronic = user_criteria.get('needs_chronic_medication', {}).get('value')
        if needs_chronic == 'yes' and not policy_features.chronic_medication_availability:
            shortcomings.append({
                'type': 'missing_feature',
                'severity': 'critical',
                'title': 'No Chronic Medication Coverage',
                'description': 'You need chronic medication coverage but this policy does not provide it',
                'impact': 'Will need to pay full cost of chronic medications',
                'suggestion': 'This is a critical gap - look for policies that include chronic medication benefits'
            })
        
        return shortcomings
    
    def _analyze_funeral_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze funeral policy shortcomings."""
        shortcomings = []
        
        # Add funeral-specific shortcoming analysis here
        # This would follow similar patterns to health analysis
        
        return shortcomings
    
    def _is_benefit_level_insufficient(self, user_preference: str, policy_level: str) -> bool:
        """Check if policy benefit level is insufficient for user preference."""
        level_hierarchy = {
            'no_cover': 0,
            'basic': 1,
            'basic_visits': 1,
            'moderate': 2,
            'routine_care': 2,
            'extensive': 3,
            'extended_care': 3,
            'comprehensive': 4,
            'comprehensive_care': 4
        }
        
        user_level = level_hierarchy.get(user_preference, 2)
        policy_level_num = level_hierarchy.get(policy_level, 2)
        
        return policy_level_num < user_level
    
    def _calculate_suitability_score(self, shortcomings: List[Dict[str, Any]]) -> int:
        """Calculate overall suitability score based on shortcomings."""
        if not shortcomings:
            return 100
        
        penalty = 0
        for shortcoming in shortcomings:
            if shortcoming['severity'] == 'critical':
                penalty += 25
            elif shortcoming['severity'] == 'moderate':
                penalty += 15
            elif shortcoming['severity'] == 'minor':
                penalty += 5
        
        return max(0, 100 - penalty)
    
    def _generate_improvement_suggestions(
        self, 
        shortcomings: List[Dict[str, Any]], 
        policy: BasePolicy
    ) -> List[str]:
        """Generate suggestions for addressing shortcomings."""
        suggestions = []
        
        critical_gaps = [s for s in shortcomings if s['severity'] == 'critical']
        moderate_gaps = [s for s in shortcomings if s['severity'] == 'moderate']
        
        if critical_gaps:
            suggestions.append("This policy has critical gaps - consider other options first")
            for gap in critical_gaps:
                suggestions.append(gap['suggestion'])
        
        if moderate_gaps:
            suggestions.append("Consider if you can accept these limitations:")
            for gap in moderate_gaps[:2]:  # Limit to top 2
                suggestions.append(f"• {gap['title']}: {gap['suggestion']}")
        
        if not critical_gaps and not moderate_gaps:
            suggestions.append("This policy is a good match for your needs")
        
        return suggestions[:4]  # Limit to 4 suggestions
    
    def _generate_overall_shortcomings_analysis(
        self, 
        enhanced_policies: List[Dict[str, Any]], 
        user_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate overall analysis of shortcomings across all policies."""
        if not enhanced_policies:
            return {'summary': 'No policies to analyze'}
        
        total_policies = len(enhanced_policies)
        perfect_matches = len([p for p in enhanced_policies if p.get('shortcomings_severity') == 'none'])
        critical_issues = len([p for p in enhanced_policies if p.get('shortcomings_severity') == 'critical'])
        
        analysis = {
            'total_policies': total_policies,
            'perfect_matches': perfect_matches,
            'policies_with_critical_issues': critical_issues,
            'best_available_score': enhanced_policies[0].get('suitability_score', 0) if enhanced_policies else 0,
            'summary': self._generate_analysis_summary(enhanced_policies),
            'market_gaps': self._identify_market_gaps(enhanced_policies, user_criteria)
        }
        
        return analysis
    
    def _generate_analysis_summary(self, enhanced_policies: List[Dict[str, Any]]) -> str:
        """Generate a summary of the overall analysis."""
        if not enhanced_policies:
            return "No policies found matching your criteria."
        
        perfect_matches = len([p for p in enhanced_policies if p.get('shortcomings_severity') == 'none'])
        critical_issues = len([p for p in enhanced_policies if p.get('shortcomings_severity') == 'critical'])
        
        if perfect_matches > 0:
            return f"Great news! Found {perfect_matches} policies that fully match your needs with no significant gaps."
        elif critical_issues == len(enhanced_policies):
            return "All available policies have critical gaps. You may need to adjust your requirements or consider additional coverage."
        else:
            good_options = len(enhanced_policies) - critical_issues
            return f"Found {good_options} policies with minor to moderate limitations that may still meet your needs."
    
    def _identify_common_gaps(self, enhanced_policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify gaps that are common across multiple policies."""
        gap_counts = {}
        
        for policy in enhanced_policies:
            for shortcoming in policy.get('shortcomings', []):
                gap_type = shortcoming['type']
                if gap_type not in gap_counts:
                    gap_counts[gap_type] = {
                        'count': 0,
                        'title': shortcoming['title'],
                        'description': shortcoming['description']
                    }
                gap_counts[gap_type]['count'] += 1
        
        # Return gaps that affect more than half the policies
        threshold = len(enhanced_policies) / 2
        common_gaps = [
            {
                'type': gap_type,
                'title': data['title'],
                'description': data['description'],
                'affected_policies': data['count'],
                'percentage': (data['count'] / len(enhanced_policies)) * 100
            }
            for gap_type, data in gap_counts.items()
            if data['count'] > threshold
        ]
        
        return sorted(common_gaps, key=lambda x: x['affected_policies'], reverse=True)
    
    def _identify_market_gaps(
        self, 
        enhanced_policies: List[Dict[str, Any]], 
        user_criteria: Dict[str, Any]
    ) -> List[str]:
        """Identify gaps in the market based on user needs vs available policies."""
        market_gaps = []
        
        # Check if all policies exceed budget
        user_budget = user_criteria.get('monthly_budget', {}).get('value')
        if user_budget:
            budget_value = self._convert_budget_range_to_value(user_budget)
            over_budget = all(p['monthly_premium'] > budget_value for p in enhanced_policies)
            if over_budget:
                market_gaps.append(f"No policies available within your R{budget_value} budget")
        
        # Check for common missing features
        common_gaps = self._identify_common_gaps(enhanced_policies)
        for gap in common_gaps:
            if gap['percentage'] > 80:  # If 80%+ of policies lack this feature
                market_gaps.append(f"Limited availability: {gap['title']}")
        
        return market_gaps
    
    def _generate_recommendations(
        self, 
        enhanced_policies: List[Dict[str, Any]], 
        user_criteria: Dict[str, Any]
    ) -> List[str]:
        """Generate overall recommendations based on the analysis."""
        recommendations = []
        
        if not enhanced_policies:
            return ["No policies match your criteria. Consider broadening your requirements."]
        
        best_policy = enhanced_policies[0]
        
        if best_policy.get('shortcomings_severity') == 'none':
            recommendations.append(f"Excellent match found: {best_policy['name']} meets all your requirements")
        elif best_policy.get('shortcomings_severity') == 'critical':
            recommendations.append("No ideal matches found. Consider:")
            recommendations.append("• Adjusting your budget or coverage requirements")
            recommendations.append("• Looking into supplementary insurance for gaps")
            recommendations.append("• Consulting with an insurance advisor")
        else:
            recommendations.append(f"Best available option: {best_policy['name']}")
            recommendations.append("Consider if you can accept the identified limitations")
        
        # Add market-specific recommendations
        market_gaps = self._identify_market_gaps(enhanced_policies, user_criteria)
        if market_gaps:
            recommendations.append("Market limitations identified:")
            recommendations.extend([f"• {gap}" for gap in market_gaps[:2]])
        
        return recommendations[:5]  # Limit to 5 recommendations
    
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
        return self._calculate_simplified_scores(policy, user_criteria)
    
    def _add_shortcomings_to_results(
        self, 
        simplified_results: Dict[str, Any], 
        session_key: str
    ) -> Dict[str, Any]:
        """
        Add shortcomings analysis to simplified results.
        
        Args:
            simplified_results: Base simplified results
            session_key: Session identifier for getting user criteria
            
        Returns:
            Enhanced results with shortcomings analysis
        """
        try:
            user_criteria = self._get_user_criteria_for_analysis(session_key)
            enhanced_policies = []
            
            for policy_data in simplified_results.get('policies', []):
                enhanced_policy = self._add_shortcomings_analysis_to_policy(
                    policy_data, user_criteria
                )
                enhanced_policies.append(enhanced_policy)
            
            simplified_results['policies'] = enhanced_policies
            return simplified_results
            
        except Exception as e:
            logger.error(f"Error adding shortcomings analysis: {e}")
            return simplified_results
    
    def _get_user_criteria_for_analysis(self, session_key: str) -> Dict[str, Any]:
        """Get user criteria from survey responses for shortcomings analysis."""
        try:
            responses = SimpleSurveyResponse.objects.filter(
                session_key=session_key,
                category=self.category
            )
            
            criteria = {}
            for response in responses:
                criteria[response.question.field_name] = {
                    'value': response.response_value,
                    'display_value': response.get_display_value()
                }
            
            return criteria
            
        except Exception as e:
            logger.error(f"Error getting user criteria for analysis: {e}")
            return {}
    
    def _add_shortcomings_analysis_to_policy(
        self, 
        policy_data: Dict[str, Any], 
        user_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add shortcomings analysis to a single policy.
        
        Args:
            policy_data: Base policy data
            user_criteria: User's survey responses
            
        Returns:
            Enhanced policy data with shortcomings analysis
        """
        try:
            # Get the actual policy object
            policy = BasePolicy.objects.get(id=policy_data['id'])
            
            # Analyze shortcomings
            shortcomings = self._analyze_policy_shortcomings(policy, user_criteria)
            
            # Categorize shortcomings by severity
            critical_gaps = [s for s in shortcomings if s['severity'] == 'critical']
            moderate_gaps = [s for s in shortcomings if s['severity'] == 'moderate']
            minor_gaps = [s for s in shortcomings if s['severity'] == 'minor']
            
            # Determine overall shortcomings severity
            if critical_gaps:
                severity = 'critical'
                severity_description = "Has critical gaps that may make this policy unsuitable"
            elif moderate_gaps:
                severity = 'moderate'
                severity_description = "Has some important limitations to consider"
            elif minor_gaps:
                severity = 'minor'
                severity_description = "Minor limitations that may not be significant"
            else:
                severity = 'none'
                severity_description = "Excellent match with no significant gaps"
            
            # Add shortcomings data to policy
            policy_data.update({
                'shortcomings': shortcomings,
                'critical_gaps': critical_gaps,
                'moderate_gaps': moderate_gaps,
                'minor_gaps': minor_gaps,
                'shortcomings_severity': severity,
                'shortcomings_description': severity_description,
                'gap_count': len(shortcomings),
                'suitability_score': self._calculate_suitability_score(shortcomings),
                'improvement_suggestions': self._generate_improvement_suggestions(shortcomings, policy)
            })
            
            return policy_data
            
        except Exception as e:
            logger.error(f"Error analyzing shortcomings for policy {policy_data.get('id')}: {e}")
            # Return original data if analysis fails
            policy_data.update({
                'shortcomings': [],
                'shortcomings_severity': 'unknown',
                'shortcomings_description': 'Unable to analyze gaps',
                'gap_count': 0,
                'suitability_score': policy_data.get('match_score', 50)
            })
            return policy_data
    
    def _analyze_policy_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze specific shortcomings between policy and user needs.
        
        Args:
            policy: Policy object to analyze
            user_criteria: User's preferences and requirements
            
        Returns:
            List of shortcoming dictionaries with details
        """
        shortcomings = []
        
        if self.category == 'health':
            shortcomings.extend(self._analyze_health_shortcomings(policy, user_criteria))
        elif self.category == 'funeral':
            shortcomings.extend(self._analyze_funeral_shortcomings(policy, user_criteria))
        
        return shortcomings
    
    def _analyze_health_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze health policy shortcomings."""
        shortcomings = []
        
        try:
            policy_features = policy.policy_features
        except AttributeError:
            shortcomings.append({
                'type': 'missing_features',
                'severity': 'critical',
                'title': 'No Policy Features Available',
                'description': 'This policy lacks detailed feature information',
                'impact': 'Cannot verify coverage details',
                'suggestion': 'Contact provider for detailed policy information'
            })
            return shortcomings
        
        # Budget analysis
        user_budget = user_criteria.get('monthly_budget', {}).get('value')
        if user_budget:
            budget_value = self._convert_budget_range_to_value(user_budget)
            if float(policy.base_premium) > budget_value * 1.1:  # 10% tolerance
                excess = float(policy.base_premium) - budget_value
                shortcomings.append({
                    'type': 'budget_exceeded',
                    'severity': 'moderate' if excess <= 100 else 'critical',
                    'title': 'Over Budget',
                    'description': f'Premium is R{excess:.0f} above your stated budget',
                    'impact': 'May strain your monthly finances',
                    'suggestion': f'Consider policies under R{budget_value} or increase your budget'
                })
        
        # Chronic medication
        needs_chronic = user_criteria.get('needs_chronic_medication', {}).get('value')
        if needs_chronic == 'yes' and not policy_features.chronic_medication_availability:
            shortcomings.append({
                'type': 'missing_feature',
                'severity': 'critical',
                'title': 'No Chronic Medication Coverage',
                'description': 'You need chronic medication coverage but this policy does not provide it',
                'impact': 'Will need to pay full cost of chronic medications',
                'suggestion': 'This is a critical gap - look for policies that include chronic medication benefits'
            })
        
        return shortcomings
    
    def _analyze_funeral_shortcomings(
        self, 
        policy: BasePolicy, 
        user_criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze funeral policy shortcomings."""
        shortcomings = []
        # Add funeral-specific analysis here
        return shortcomings
    
    def _calculate_suitability_score(self, shortcomings: List[Dict[str, Any]]) -> int:
        """Calculate overall suitability score based on shortcomings."""
        if not shortcomings:
            return 100
        
        penalty = 0
        for shortcoming in shortcomings:
            if shortcoming['severity'] == 'critical':
                penalty += 25
            elif shortcoming['severity'] == 'moderate':
                penalty += 15
            elif shortcoming['severity'] == 'minor':
                penalty += 5
        
        return max(0, 100 - penalty)
    
    def _generate_improvement_suggestions(
        self, 
        shortcomings: List[Dict[str, Any]], 
        policy: BasePolicy
    ) -> List[str]:
        """Generate suggestions for addressing shortcomings."""
        suggestions = []
        
        critical_gaps = [s for s in shortcomings if s['severity'] == 'critical']
        moderate_gaps = [s for s in shortcomings if s['severity'] == 'moderate']
        
        if critical_gaps:
            suggestions.append("This policy has critical gaps - consider other options first")
            for gap in critical_gaps:
                suggestions.append(gap['suggestion'])
        
        if moderate_gaps:
            suggestions.append("Consider if you can accept these limitations:")
            for gap in moderate_gaps[:2]:  # Limit to top 2
                suggestions.append(f"• {gap['title']}: {gap['suggestion']}")
        
        if not critical_gaps and not moderate_gaps:
            suggestions.append("This policy is a good match for your needs")
        
        return suggestions[:4]  # Limit to 4 suggestions
    
    def _identify_common_gaps(self, enhanced_policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify gaps that are common across multiple policies."""
        gap_counts = {}
        
        for policy in enhanced_policies:
            for shortcoming in policy.get('shortcomings', []):
                gap_type = shortcoming['type']
                if gap_type not in gap_counts:
                    gap_counts[gap_type] = {
                        'count': 0,
                        'title': shortcoming['title'],
                        'description': shortcoming['description']
                    }
                gap_counts[gap_type]['count'] += 1
        
        # Return gaps that affect more than half the policies
        threshold = len(enhanced_policies) / 2
        common_gaps = [
            {
                'type': gap_type,
                'title': data['title'],
                'description': data['description'],
                'affected_policies': data['count'],
                'percentage': (data['count'] / len(enhanced_policies)) * 100
            }
            for gap_type, data in gap_counts.items()
            if data['count'] > threshold
        ]
        
        return sorted(common_gaps, key=lambda x: x['affected_policies'], reverse=True)
    
    def _generate_recommendations(
        self, 
        enhanced_policies: List[Dict[str, Any]], 
        user_criteria: Dict[str, Any]
    ) -> List[str]:
        """Generate overall recommendations based on the analysis."""
        recommendations = []
        
        if not enhanced_policies:
            return ["No policies match your criteria. Consider broadening your requirements."]
        
        best_policy = enhanced_policies[0]
        
        if best_policy.get('shortcomings_severity') == 'none':
            recommendations.append(f"Excellent match found: {best_policy['name']} meets all your requirements")
        elif best_policy.get('shortcomings_severity') == 'critical':
            recommendations.append("No ideal matches found. Consider:")
            recommendations.append("• Adjusting your budget or coverage requirements")
            recommendations.append("• Looking into supplementary insurance for gaps")
            recommendations.append("• Consulting with an insurance advisor")
        else:
            recommendations.append(f"Best available option: {best_policy['name']}")
            recommendations.append("Consider if you can accept the identified limitations")
        
        return recommendations[:5]  # Limit to 5 recommendations

