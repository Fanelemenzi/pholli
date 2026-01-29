"""
Comparison Engine for Insurance Policies.
Intelligent policy comparison and recommendation system with advanced scoring algorithms.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Q, Avg, Count
from django.core.cache import cache
from policies.models import BasePolicy
from health_policies.models import HealthPolicy
# from life_policies.models import LifePolicy  # Module doesn't exist yet
from funeral_policies.models import FuneralPolicy
from .models import ComparisonSession, ComparisonResult, ComparisonCriteria
import logging

logger = logging.getLogger(__name__)


class PolicyComparisonEngine:
    """
    Main comparison engine for evaluating and ranking insurance policies.
    Uses weighted scoring based on user-defined criteria with intelligent algorithms.
    """
    
    # Scoring weights for final calculation
    CRITERIA_WEIGHT = Decimal('0.60')  # 60% - How well policy matches criteria
    VALUE_WEIGHT = Decimal('0.25')     # 25% - Value for money
    REVIEW_WEIGHT = Decimal('0.10')    # 10% - User reviews
    ORGANIZATION_WEIGHT = Decimal('0.05')  # 5% - Organization reputation
    
    def __init__(self, category_slug: str):
        """
        Initialize the comparison engine for a specific category.
        
        Args:
            category_slug: Slug of the policy category (health, life, funeral)
        """
        self.category_slug = category_slug
        self.weights = {}
        self.criteria = {}
        self.user_criteria = {}
        
    def compare_policies(
        self,
        policy_ids: List[int],
        user_criteria: Dict[str, Any],
        user=None,
        session_key: str = None,
        survey_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple policies and return ranked results with detailed analysis.
        
        Args:
            policy_ids: List of policy IDs to compare
            user_criteria: Dictionary of user preferences and criteria
            user: User object (optional for anonymous)
            session_key: Session key for anonymous users
            
        Returns:
            Dictionary with comparison results, rankings, and recommendations
        """
        try:
            # Validate inputs
            if not policy_ids or len(policy_ids) < 2:
                return {'error': 'At least 2 policies required for comparison'}
            
            if len(policy_ids) > 10:
                return {'error': 'Maximum 10 policies can be compared at once'}
            
            # Get policies
            policies = self._get_policies(policy_ids)
            
            # Apply survey-based filtering if available
            if self.survey_context and 'filters' in self.survey_context:
                policies = self._apply_survey_filters(policies, self.survey_context['filters'])
            
            if not policies:
                return {'error': 'No valid policies found for comparison'}
            
            if len(policies) < 2:
                return {'error': 'At least 2 valid policies required for comparison'}
            
            # Store user criteria and survey context
            self.user_criteria = user_criteria
            self.survey_context = survey_context or {}
            
            # Create comparison session
            session = self._create_session(policies, user_criteria, user, session_key)
            
            # Load comparison criteria (enhanced with survey data if available)
            self._load_criteria(user_criteria)
            
            # Score each policy (with survey context if available)
            logger.info(f"Scoring {len(policies)} policies for comparison")
            results = []
            for policy in policies:
                try:
                    if self.survey_context:
                        score_data = self._score_policy_with_survey_context(policy, user_criteria, self.survey_context)
                    else:
                        score_data = self._score_policy(policy, user_criteria)
                    results.append({
                        'policy': policy,
                        'score_data': score_data
                    })
                except Exception as e:
                    logger.error(f"Error scoring policy {policy.id}: {str(e)}")
                    continue
            
            if not results:
                return {'error': 'Failed to score policies'}
            
            # Rank policies
            ranked_results = self._rank_policies(results)
            
            # Generate detailed analysis
            analysis = self._generate_detailed_analysis(ranked_results, user_criteria)
            
            # Save results to session
            self._save_results(session, ranked_results)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(ranked_results, user_criteria)
            
            # Calculate comparison insights
            insights = self._generate_insights(ranked_results, user_criteria)
            
            return {
                'success': True,
                'session_id': session.id,
                'session_key': session.session_key,
                'category': session.category.name,
                'total_policies': len(policies),
                'best_match': ranked_results[0]['policy'],
                'results': ranked_results,
                'recommendations': recommendations,
                'analysis': analysis,
                'insights': insights,
                'created_at': session.created_at
            }
            
        except Exception as e:
            logger.error(f"Comparison engine error: {str(e)}")
            return {'error': f'Comparison failed: {str(e)}'}
    
    def _get_policies(self, policy_ids: List[int]) -> List[BasePolicy]:
        """
        Get active and approved policies by IDs with category-specific models.
        """
        base_query = {
            'id__in': policy_ids,
            'is_active': True,
            'approval_status': 'APPROVED'
        }
        
        # Get category-specific instances with prefetching
        if self.category_slug == 'health':
            policies = HealthPolicy.objects.filter(**base_query).select_related(
                'organization', 'category', 'policy_type'
            ).prefetch_related(
                'health_benefits',
                'hospital_networks',
                'chronic_conditions',
                'reviews'
            )
        # elif self.category_slug == 'life':
        #     policies = LifePolicy.objects.filter(**base_query).select_related(
        #         'organization', 'category', 'policy_type'
        #     ).prefetch_related(
        #         'coverage_tiers',
        #         'critical_illnesses',
        #         'riders',
        #         'reviews'
        #     )
        elif self.category_slug == 'funeral':
            policies = FuneralPolicy.objects.filter(**base_query).select_related(
                'organization', 'category', 'policy_type'
            ).prefetch_related(
                'family_tiers',
                'service_providers',
                'additional_benefits',
                'reviews'
            )
        else:
            # Fallback to base policies
            policies = BasePolicy.objects.filter(**base_query).select_related(
                'organization', 'category', 'policy_type', 'policy_features'
            ).prefetch_related('additional_features', 'reviews')
        
        return list(policies)
    
    def _create_session(
        self,
        policies: List[BasePolicy],
        criteria: Dict,
        user,
        session_key
    ) -> ComparisonSession:
        """Create a new comparison session with expiration."""
        from datetime import timedelta
        from django.utils import timezone
        import uuid
        
        if not session_key:
            session_key = str(uuid.uuid4())
        
        session = ComparisonSession.objects.create(
            user=user,
            session_key=session_key,
            category=policies[0].category,
            criteria=criteria,
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        session.policies.set(policies)
        
        return session
    
    def _load_criteria(self, user_criteria: Dict[str, Any]):
        """
        Load comparison criteria and weights from database and user input.
        Merges default criteria with user-specified weights.
        """
        # Get default criteria for category from database
        default_criteria = ComparisonCriteria.objects.filter(
            category__slug=self.category_slug,
            is_active=True
        )
        
        # Apply user-specified weights or use defaults
        for criteria in default_criteria:
            weight = user_criteria.get('weights', {}).get(
                criteria.field_name,
                criteria.weight
            )
            self.weights[criteria.field_name] = Decimal(str(weight))
            self.criteria[criteria.field_name] = criteria
        
        # Add any custom criteria from user that aren't in database
        custom_weights = user_criteria.get('weights', {})
        for field_name, weight in custom_weights.items():
            if field_name not in self.weights:
                self.weights[field_name] = Decimal(str(weight))
    
    def _score_policy(
        self,
        policy: BasePolicy,
        user_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive score for a policy across multiple dimensions.
        
        Returns:
            Dictionary with overall score and detailed breakdowns
        """
        criteria_scores = {}
        total_weighted_score = Decimal('0')
        total_weight = Decimal('0')
        
        # Score based on user criteria
        for field_name, weight in self.weights.items():
            if weight == 0:
                continue
            
            try:
                score = self._evaluate_criterion(
                    policy,
                    field_name,
                    user_criteria.get(field_name)
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
        
        # Calculate overall criteria score (0-100)
        if total_weight > 0:
            criteria_score = (total_weighted_score / total_weight) * 100
        else:
            criteria_score = Decimal('50')  # Neutral if no criteria
        
        # Calculate value score (coverage vs premium)
        value_score = self._calculate_value_score(policy)
        
        # Calculate review score
        review_score = self._calculate_review_score(policy)
        
        # Calculate organization reputation score
        org_score = self._calculate_organization_score(policy)
        
        # Combine scores with defined weights
        final_score = (
            criteria_score * self.CRITERIA_WEIGHT +
            value_score * self.VALUE_WEIGHT +
            review_score * self.REVIEW_WEIGHT +
            org_score * self.ORGANIZATION_WEIGHT
        )
        
        # Round to 2 decimal places
        final_score = final_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            'overall_score': float(final_score),
            'criteria_score': float(criteria_score),
            'value_score': float(value_score),
            'review_score': float(review_score),
            'organization_score': float(org_score),
            'criteria_scores': criteria_scores,
            'score_breakdown': {
                'criteria_contribution': float(criteria_score * self.CRITERIA_WEIGHT),
                'value_contribution': float(value_score * self.VALUE_WEIGHT),
                'review_contribution': float(review_score * self.REVIEW_WEIGHT),
                'organization_contribution': float(org_score * self.ORGANIZATION_WEIGHT)
            }
        }
    
    def _score_policy_with_survey_context(
        self,
        policy: BasePolicy,
        user_criteria: Dict[str, Any],
        survey_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced scoring that considers survey context with confidence weighting.
        
        Args:
            policy: Policy to score
            user_criteria: User criteria from survey responses
            survey_context: Survey context including user profile and confidence levels
            
        Returns:
            Dictionary with enhanced score data including survey-specific adjustments
        """
        # Get base score using standard method
        base_score_data = self._score_policy(policy, user_criteria)
        
        # Apply survey-specific enhancements
        user_profile = survey_context.get('user_profile', {})
        confidence_levels = user_profile.get('confidence_levels', {})
        
        # Apply confidence weighting to criteria scores
        enhanced_criteria_scores = {}
        total_weighted_score = Decimal('0')
        total_weight = Decimal('0')
        
        for field_name, score_info in base_score_data['criteria_scores'].items():
            # Get confidence level for this field (default to 3 if not found)
            confidence = confidence_levels.get(field_name, 3)
            confidence_multiplier = self._get_confidence_multiplier(confidence)
            
            # Apply confidence weighting
            adjusted_score = score_info['score'] * confidence_multiplier
            adjusted_weight = score_info['weight'] * confidence_multiplier
            
            enhanced_criteria_scores[field_name] = {
                'score': float(adjusted_score),
                'weight': float(adjusted_weight),
                'weighted_score': float(adjusted_score * adjusted_weight / 100),
                'confidence_level': confidence,
                'confidence_multiplier': float(confidence_multiplier),
                'original_score': score_info['score']
            }
            
            total_weighted_score += adjusted_score * adjusted_weight / 100
            total_weight += adjusted_weight
        
        # Recalculate criteria score with confidence weighting
        if total_weight > 0:
            enhanced_criteria_score = (total_weighted_score / total_weight) * 100
        else:
            enhanced_criteria_score = Decimal(str(base_score_data['criteria_score']))
        
        # Apply priority boosting based on user profile
        priority_boost = self._calculate_priority_boost(policy, user_profile)
        enhanced_criteria_score += priority_boost
        
        # Ensure score stays within bounds
        enhanced_criteria_score = min(max(enhanced_criteria_score, Decimal('0')), Decimal('100'))
        
        # Recalculate final score with enhanced criteria score
        final_score = (
            enhanced_criteria_score * self.CRITERIA_WEIGHT +
            Decimal(str(base_score_data['value_score'])) * self.VALUE_WEIGHT +
            Decimal(str(base_score_data['review_score'])) * self.REVIEW_WEIGHT +
            Decimal(str(base_score_data['organization_score'])) * self.ORGANIZATION_WEIGHT
        )
        
        final_score = final_score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Generate personalized explanations
        personalization_factors = self._get_personalization_factors(policy, user_profile)
        
        return {
            'overall_score': float(final_score),
            'criteria_score': float(enhanced_criteria_score),
            'value_score': base_score_data['value_score'],
            'review_score': base_score_data['review_score'],
            'organization_score': base_score_data['organization_score'],
            'criteria_scores': enhanced_criteria_scores,
            'score_breakdown': {
                'criteria_contribution': float(enhanced_criteria_score * self.CRITERIA_WEIGHT),
                'value_contribution': float(Decimal(str(base_score_data['value_score'])) * self.VALUE_WEIGHT),
                'review_contribution': float(Decimal(str(base_score_data['review_score'])) * self.REVIEW_WEIGHT),
                'organization_contribution': float(Decimal(str(base_score_data['organization_score'])) * self.ORGANIZATION_WEIGHT)
            },
            'survey_enhancements': {
                'confidence_weighted': True,
                'priority_boost': float(priority_boost),
                'personalization_factors': personalization_factors,
                'profile_strength': user_profile.get('profile_strength', 0.0)
            }
        }
    
    def _get_confidence_multiplier(self, confidence_level: int) -> Decimal:
        """
        Get confidence multiplier based on user's confidence level.
        
        Args:
            confidence_level: User confidence level (1-5)
            
        Returns:
            Multiplier to apply to scores
        """
        confidence_multipliers = {
            5: Decimal('1.0'),    # Very confident - no adjustment
            4: Decimal('0.95'),   # Confident - slight reduction
            3: Decimal('0.85'),   # Neutral - moderate reduction
            2: Decimal('0.75'),   # Not confident - significant reduction
            1: Decimal('0.60')    # Very unsure - major reduction
        }
        
        return confidence_multipliers.get(confidence_level, Decimal('0.85'))
    
    def _calculate_priority_boost(self, policy: BasePolicy, user_profile: Dict[str, Any]) -> Decimal:
        """
        Calculate priority boost based on how well policy matches user's stated priorities.
        
        Args:
            policy: Policy to evaluate
            user_profile: User profile from survey responses
            
        Returns:
            Priority boost score (can be positive or negative)
        """
        priorities = user_profile.get('priorities', {})
        if not priorities:
            return Decimal('0')
        
        boost = Decimal('0')
        priority_count = 0
        
        for field_name, priority_value in priorities.items():
            # Convert priority to numeric score
            priority_score = self._convert_priority_to_score(priority_value)
            if priority_score is None:
                continue
            
            # Check how well policy performs in this priority area
            policy_performance = self._evaluate_policy_performance(policy, field_name)
            
            # Calculate boost based on alignment
            if policy_performance >= 80 and priority_score >= 80:
                # High priority, high performance - positive boost
                boost += Decimal('3')
            elif policy_performance >= 60 and priority_score >= 60:
                # Medium priority, good performance - small boost
                boost += Decimal('1')
            elif policy_performance <= 40 and priority_score >= 80:
                # High priority, poor performance - penalty
                boost -= Decimal('2')
            
            priority_count += 1
        
        # Average the boost and cap it
        if priority_count > 0:
            boost = boost / priority_count
        
        return min(max(boost, Decimal('-5')), Decimal('5'))
    
    def _convert_priority_to_score(self, priority_value: Any) -> Optional[Decimal]:
        """
        Convert priority value to numeric score.
        
        Args:
            priority_value: Priority value from survey
            
        Returns:
            Numeric score (0-100) or None if invalid
        """
        if isinstance(priority_value, str):
            priority_map = {
                'very_high': 100, 'essential': 100,
                'high': 85, 'very_important': 85,
                'important': 70,
                'medium': 60, 'somewhat_important': 50,
                'low': 40, 'nice_to_have': 30,
                'very_low': 20, 'not_important': 10,
                'not_needed': 0
            }
            return Decimal(str(priority_map.get(priority_value.lower(), 50)))
        
        elif isinstance(priority_value, (int, float)):
            if 1 <= priority_value <= 5:
                return Decimal(str(priority_value * 20))
            elif 1 <= priority_value <= 10:
                return Decimal(str(priority_value * 10))
        
        return None
    
    def _evaluate_policy_performance(self, policy: BasePolicy, field_name: str) -> Decimal:
        """
        Evaluate how well a policy performs in a specific area.
        
        Args:
            policy: Policy to evaluate
            field_name: Field to evaluate performance for
            
        Returns:
            Performance score (0-100)
        """
        # Map survey fields to policy evaluation methods
        field_evaluators = {
            'monthly_budget': lambda p: self._evaluate_budget_performance(p),
            'coverage_amount_preference': lambda p: self._evaluate_coverage_performance(p),
            'waiting_period_tolerance': lambda p: self._evaluate_waiting_period_performance(p),
            'chronic_medication_needed': lambda p: self._evaluate_chronic_medication_performance(p),
            'dental_cover_needed': lambda p: self._evaluate_dental_performance(p),
            'optical_cover_needed': lambda p: self._evaluate_optical_performance(p),
            'repatriation_needed': lambda p: self._evaluate_repatriation_performance(p),
            'claim_payout_speed_importance': lambda p: self._evaluate_claim_speed_performance(p)
        }
        
        evaluator = field_evaluators.get(field_name)
        if evaluator:
            return evaluator(policy)
        
        return Decimal('50')  # Default neutral score
    
    def _evaluate_budget_performance(self, policy: BasePolicy) -> Decimal:
        """Evaluate budget performance - lower premium is better."""
        # This is a simplified evaluation - in practice, you'd compare against user's budget
        if policy.base_premium <= 500:
            return Decimal('90')
        elif policy.base_premium <= 1000:
            return Decimal('70')
        elif policy.base_premium <= 2000:
            return Decimal('50')
        else:
            return Decimal('30')
    
    def _evaluate_coverage_performance(self, policy: BasePolicy) -> Decimal:
        """Evaluate coverage performance - higher coverage is better."""
        if policy.coverage_amount >= 1000000:
            return Decimal('90')
        elif policy.coverage_amount >= 500000:
            return Decimal('70')
        elif policy.coverage_amount >= 100000:
            return Decimal('50')
        else:
            return Decimal('30')
    
    def _evaluate_waiting_period_performance(self, policy: BasePolicy) -> Decimal:
        """Evaluate waiting period performance - shorter is better."""
        if policy.waiting_period_days <= 30:
            return Decimal('90')
        elif policy.waiting_period_days <= 90:
            return Decimal('70')
        elif policy.waiting_period_days <= 180:
            return Decimal('50')
        else:
            return Decimal('30')
    
    def _evaluate_chronic_medication_performance(self, policy: BasePolicy) -> Decimal:
        """Evaluate chronic medication coverage."""
        if hasattr(policy, 'chronic_medication_covered') and policy.chronic_medication_covered:
            return Decimal('90')
        return Decimal('20')
    
    def _evaluate_dental_performance(self, policy: BasePolicy) -> Decimal:
        """Evaluate dental coverage."""
        if hasattr(policy, 'includes_dental_cover') and policy.includes_dental_cover:
            return Decimal('90')
        return Decimal('20')
    
    def _evaluate_optical_performance(self, policy: BasePolicy) -> Decimal:
        """Evaluate optical coverage."""
        if hasattr(policy, 'includes_optical_cover') and policy.includes_optical_cover:
            return Decimal('90')
        return Decimal('20')
    
    def _evaluate_repatriation_performance(self, policy: BasePolicy) -> Decimal:
        """Evaluate repatriation coverage."""
        if hasattr(policy, 'repatriation_covered') and policy.repatriation_covered:
            return Decimal('90')
        return Decimal('20')
    
    def _evaluate_claim_speed_performance(self, policy: BasePolicy) -> Decimal:
        """Evaluate claim processing speed."""
        if hasattr(policy, 'claim_payout_days'):
            if policy.claim_payout_days <= 48:
                return Decimal('90')
            elif policy.claim_payout_days <= 120:
                return Decimal('70')
            elif policy.claim_payout_days <= 240:
                return Decimal('50')
            else:
                return Decimal('30')
        return Decimal('50')
    
    def _get_personalization_factors(self, policy: BasePolicy, user_profile: Dict[str, Any]) -> List[str]:
        """
        Generate personalization factors that explain why this policy matches the user.
        
        Args:
            policy: Policy to analyze
            user_profile: User profile from survey responses
            
        Returns:
            List of personalization factor strings
        """
        factors = []
        priorities = user_profile.get('priorities', {})
        user_values = user_profile.get('user_values', {})
        
        # Check budget alignment
        if 'monthly_budget' in user_values:
            budget = user_values['monthly_budget']
            if isinstance(budget, (int, float)) and policy.base_premium <= budget * 1.1:
                factors.append(f"Fits within your budget of R{budget:.0f}/month")
            elif isinstance(budget, str) and 'affordable' in budget.lower():
                factors.append("Matches your preference for affordable coverage")
        
        # Check coverage preferences
        if 'coverage_amount_preference' in user_values:
            coverage_pref = user_values['coverage_amount_preference']
            if isinstance(coverage_pref, (int, float)) and policy.coverage_amount >= coverage_pref * 0.9:
                factors.append(f"Provides coverage close to your preferred R{coverage_pref:,.0f}")
        
        # Check specific feature preferences
        feature_checks = [
            ('chronic_medication_needed', 'chronic_medication_covered', 'Covers chronic medication as you requested'),
            ('dental_cover_needed', 'includes_dental_cover', 'Includes dental coverage as preferred'),
            ('optical_cover_needed', 'includes_optical_cover', 'Includes optical coverage as needed'),
            ('repatriation_needed', 'repatriation_covered', 'Provides repatriation services as required'),
        ]
        
        for user_field, policy_field, message in feature_checks:
            if user_values.get(user_field) and hasattr(policy, policy_field) and getattr(policy, policy_field):
                factors.append(message)
        
        # Check waiting period tolerance
        if 'waiting_period_tolerance' in user_values:
            tolerance = user_values['waiting_period_tolerance']
            if isinstance(tolerance, (int, float)) and policy.waiting_period_days <= tolerance:
                factors.append(f"Waiting period of {policy.waiting_period_days} days meets your tolerance")
        
        # Add priority-based factors
        for priority_field, priority_value in priorities.items():
            if self._convert_priority_to_score(priority_value) and self._convert_priority_to_score(priority_value) >= 70:
                performance = self._evaluate_policy_performance(policy, priority_field)
                if performance >= 70:
                    factors.append(f"Strong performance in {priority_field.replace('_', ' ')} (high priority for you)")
        
        return factors[:5]  # Limit to top 5 factors
    
    def _evaluate_benefit_level_criterion(
        self,
        policy: BasePolicy,
        field_name: str,
        user_value: Any
    ) -> Decimal:
        """
        Evaluate benefit level fields with intelligent scoring based on coverage levels.
        
        Args:
            policy: Policy to evaluate
            field_name: Field name (in_hospital_benefit_level or out_hospital_benefit_level)
            user_value: User's preferred benefit level
            
        Returns:
            Score from 0 to 100
        """
        # Get policy features
        try:
            policy_features = policy.policy_features
            policy_value = getattr(policy_features, field_name, None)
        except:
            policy_value = None
        
        if policy_value is None or user_value is None:
            return Decimal('50')  # Neutral if no data
        
        # Define benefit level hierarchy (higher index = better coverage)
        benefit_levels = [
            'no_cover',
            'basic' if 'hospital' in field_name else 'basic_visits',
            'moderate' if 'hospital' in field_name else 'routine_care',
            'extensive' if 'hospital' in field_name else 'extended_care',
            'comprehensive' if 'hospital' in field_name else 'comprehensive_care'
        ]
        
        try:
            policy_level_index = benefit_levels.index(policy_value)
            user_level_index = benefit_levels.index(user_value)
        except ValueError:
            return Decimal('50')  # Unknown level
        
        # Exact match gets full score
        if policy_level_index == user_level_index:
            return Decimal('100')
        
        # Higher coverage than requested gets good score
        if policy_level_index > user_level_index:
            # Bonus for exceeding requirements, but diminishing returns
            excess = policy_level_index - user_level_index
            return min(Decimal('100'), Decimal('90') + (excess * Decimal('5')))
        
        # Lower coverage than requested gets penalty
        else:
            deficit = user_level_index - policy_level_index
            penalty = deficit * Decimal('25')  # 25 points per level below
            return max(Decimal('0'), Decimal('100') - penalty)
    
    def _evaluate_annual_limit_range_criterion(
        self,
        policy: BasePolicy,
        field_name: str,
        user_value: Any
    ) -> Decimal:
        """
        Evaluate annual limit range fields with intelligent range matching.
        
        Args:
            policy: Policy to evaluate
            field_name: Field name (annual_limit_family_range or annual_limit_member_range)
            user_value: User's preferred range
            
        Returns:
            Score from 0 to 100
        """
        # Get policy features
        try:
            policy_features = policy.policy_features
            policy_value = getattr(policy_features, field_name, None)
        except:
            policy_value = None
        
        if policy_value is None or user_value is None:
            return Decimal('50')  # Neutral if no data
        
        # Define range hierarchy with numeric values for comparison
        range_values = {
            '10k-25k': (10000, 25000),
            '10k-50k': (10000, 50000),
            '25k-50k': (25000, 50000),
            '50k-100k': (50000, 100000),
            '100k-200k': (100000, 200000),
            '100k-250k': (100000, 250000),
            '200k-500k': (200000, 500000),
            '250k-500k': (250000, 500000),
            '500k-1m': (500000, 1000000),
            '1m-2m': (1000000, 2000000),
            '2m-5m': (2000000, 5000000),
            '2m-plus': (2000000, float('inf')),
            '5m-plus': (5000000, float('inf')),
            'not_sure': None  # Special case
        }
        
        # Handle "not_sure" user preference
        if user_value == 'not_sure':
            return Decimal('75')  # Good score for any coverage when user is unsure
        
        policy_range = range_values.get(policy_value)
        user_range = range_values.get(user_value)
        
        if policy_range is None or user_range is None:
            return Decimal('50')  # Unknown range
        
        # Exact match gets full score
        if policy_value == user_value:
            return Decimal('100')
        
        # Calculate overlap between ranges
        policy_min, policy_max = policy_range
        user_min, user_max = user_range
        
        # Check for overlap
        overlap_min = max(policy_min, user_min)
        overlap_max = min(policy_max, user_max)
        
        if overlap_min <= overlap_max:
            # There's overlap - calculate percentage
            overlap_size = overlap_max - overlap_min
            user_range_size = user_max - user_min
            policy_range_size = policy_max - policy_min
            
            # Score based on how much of user's preferred range is covered
            if user_range_size > 0:
                coverage_percentage = overlap_size / user_range_size
                base_score = Decimal(str(coverage_percentage * 80))  # Up to 80 points for overlap
                
                # Bonus if policy range is higher than user range
                if policy_min >= user_min:
                    base_score += Decimal('20')  # 20 point bonus for meeting or exceeding
                
                return min(base_score, Decimal('100'))
        
        # No overlap - check if policy is higher or lower
        if policy_min > user_max:
            # Policy offers more than user wants - good but not perfect
            return Decimal('70')
        elif policy_max < user_min:
            # Policy offers less than user wants - penalty based on gap
            gap_ratio = (user_min - policy_max) / user_min if user_min > 0 else 1
            penalty = Decimal(str(gap_ratio * 60))  # Up to 60 point penalty
            return max(Decimal('10'), Decimal('50') - penalty)
        
        return Decimal('50')  # Default neutral score
    def _evaluate_criterion(
        self,
        policy: BasePolicy,
        field_name: str,
        user_value: Any
    ) -> Decimal:
        """
        Evaluate a single criterion for a policy with intelligent scoring.
        Handles new benefit level fields and range-based matching.
        
        Returns:
            Score from 0 to 100
        """
        criteria = self.criteria.get(field_name)
        
        # Handle benefit level fields (new implementation)
        if field_name in ['in_hospital_benefit_level', 'out_hospital_benefit_level']:
            return self._evaluate_benefit_level_criterion(policy, field_name, user_value)
        
        # Handle annual limit range fields (new implementation)
        if field_name in ['annual_limit_family_range', 'annual_limit_member_range']:
            return self._evaluate_annual_limit_range_criterion(policy, field_name, user_value)
        
        # Skip currently_on_medical_aid field (removed from comparison)
        if field_name == 'currently_on_medical_aid':
            return Decimal('50')  # Neutral score since this field is no longer used
        
        # Try to get value from policy
        policy_value = getattr(policy, field_name, None)
        
        # If not found, might be nested (e.g., organization.is_verified)
        if policy_value is None and '.' in field_name:
            parts = field_name.split('.')
            obj = policy
            for part in parts:
                obj = getattr(obj, part, None)
                if obj is None:
                    break
            policy_value = obj
        
        # Try to get from policy features if not found on policy directly
        if policy_value is None:
            try:
                policy_features = policy.policy_features
                policy_value = getattr(policy_features, field_name, None)
            except:
                pass
        
        if policy_value is None:
            return Decimal('0')  # No data = no score
        
        # If no criteria definition, try intelligent default
        if not criteria:
            return self._smart_evaluate(policy_value, user_value)
        
        # Evaluate based on comparison type
        comparison_type = criteria.comparison_type
        
        if comparison_type == 'LOWER_BETTER':
            return self._score_lower_better(policy_value, user_value)
        
        elif comparison_type == 'HIGHER_BETTER':
            return self._score_higher_better(policy_value, user_value)
        
        elif comparison_type == 'EXACT_MATCH':
            return Decimal('100') if policy_value == user_value else Decimal('0')
        
        elif comparison_type == 'RANGE':
            return self._score_range(policy_value, user_value)
        
        elif comparison_type == 'BOOLEAN':
            if user_value is None:
                return Decimal('50')  # Neutral if user doesn't care
            return Decimal('100') if bool(policy_value) == bool(user_value) else Decimal('0')
        
        return Decimal('50')  # Default neutral score
    
    def _smart_evaluate(self, policy_value: Any, user_value: Any) -> Decimal:
        """
        Intelligently evaluate when no criteria definition exists.
        Uses heuristics based on data types.
        """
        if user_value is None:
            return Decimal('50')
        
        # Boolean comparison
        if isinstance(policy_value, bool):
            return Decimal('100') if policy_value == user_value else Decimal('0')
        
        # Numeric comparison - assume lower is better for costs, higher for benefits
        if isinstance(policy_value, (int, float, Decimal)):
            policy_val = Decimal(str(policy_value))
            user_val = Decimal(str(user_value))
            
            # Simple proximity scoring
            if policy_val == user_val:
                return Decimal('100')
            
            diff_pct = abs((policy_val - user_val) / user_val * 100) if user_val != 0 else Decimal('100')
            return max(Decimal('100') - diff_pct, Decimal('0'))
        
        # String comparison - exact match
        if str(policy_value).lower() == str(user_value).lower():
            return Decimal('100')
        
        return Decimal('50')
    
    def _score_lower_better(
        self,
        policy_value: Any,
        user_target: Any
    ) -> Decimal:
        """
        Score where lower values are better (e.g., premium, waiting period).
        Uses graduated penalty system.
        """
        if user_target is None:
            return Decimal('50')
        
        try:
            policy_value = Decimal(str(policy_value))
            user_target = Decimal(str(user_target))
        except:
            return Decimal('0')
        
        if policy_value <= user_target:
            # Better than target - award bonus
            if policy_value == 0 and user_target > 0:
                return Decimal('100')  # Free is best!
            
            savings_pct = ((user_target - policy_value) / user_target * 100) if user_target != 0 else Decimal('0')
            # Cap bonus at 10 points
            bonus = min(savings_pct / 10, Decimal('10'))
            return min(Decimal('100') + bonus, Decimal('100'))
        
        # Worse than target - apply penalty
        excess_pct = ((policy_value - user_target) / user_target * 100)
        
        # Progressive penalty: first 20% over = -1 point per %, then steeper
        if excess_pct <= 20:
            penalty = excess_pct
        elif excess_pct <= 50:
            penalty = 20 + (excess_pct - 20) * Decimal('1.5')
        else:
            penalty = 65 + (excess_pct - 50) * Decimal('2')
        
        return max(Decimal('100') - penalty, Decimal('0'))
    
    def _score_higher_better(
        self,
        policy_value: Any,
        user_target: Any
    ) -> Decimal:
        """
        Score where higher values are better (e.g., coverage amount, benefits).
        """
        if user_target is None:
            return Decimal('50')
        
        try:
            policy_value = Decimal(str(policy_value))
            user_target = Decimal(str(user_target))
        except:
            return Decimal('0')
        
        if policy_value >= user_target:
            # Meets or exceeds target
            excess_pct = ((policy_value - user_target) / user_target * 100) if user_target != 0 else Decimal('0')
            # Award bonus for exceeding (capped at 10 points)
            bonus = min(excess_pct / 20, Decimal('10'))
            return min(Decimal('100') + bonus, Decimal('100'))
        
        # Below target - apply penalty
        shortfall_pct = ((user_target - policy_value) / user_target * 100)
        
        # Progressive penalty
        if shortfall_pct <= 20:
            penalty = shortfall_pct
        elif shortfall_pct <= 50:
            penalty = 20 + (shortfall_pct - 20) * Decimal('1.5')
        else:
            penalty = 65 + (shortfall_pct - 50) * Decimal('2')
        
        return max(Decimal('100') - penalty, Decimal('0'))
    
    def _score_range(
        self,
        policy_value: Any,
        user_range: Dict[str, Any]
    ) -> Decimal:
        """
        Score for range-based criteria (e.g., age eligibility).
        Full score if within range, graduated penalty if outside.
        """
        if not user_range or not isinstance(user_range, dict):
            return Decimal('50')
        
        min_val = user_range.get('min')
        max_val = user_range.get('max')
        
        if min_val is None and max_val is None:
            return Decimal('50')
        
        try:
            policy_value = Decimal(str(policy_value))
        except:
            return Decimal('0')
        
        # Check if within range
        within_min = min_val is None or policy_value >= Decimal(str(min_val))
        within_max = max_val is None or policy_value <= Decimal(str(max_val))
        
        if within_min and within_max:
            return Decimal('100')
        
        # Outside range - calculate how far out
        if not within_min:
            gap = Decimal(str(min_val)) - policy_value
            penalty = min(gap * 10, Decimal('100'))
        else:  # not within_max
            gap = policy_value - Decimal(str(max_val))
            penalty = min(gap * 10, Decimal('100'))
        
        return max(Decimal('100') - penalty, Decimal('0'))
    
    def _calculate_value_score(self, policy: BasePolicy) -> Decimal:
        """
        Calculate value-for-money score with intelligent analysis.
        Considers coverage amount, premium, and waiting period.
        """
        if policy.base_premium == 0:
            return Decimal('100')  # Free policy = perfect value
        
        # Basic value ratio
        basic_ratio = policy.coverage_amount / policy.base_premium
        
        # Normalize to 0-100 scale
        # Assuming 100:1 ratio is good, 200:1 is excellent
        base_score = min((basic_ratio / Decimal('150')) * 100, Decimal('100'))
        
        # Adjust for waiting period (penalty for long waiting periods)
        if policy.waiting_period_days > 0:
            waiting_penalty = min(policy.waiting_period_days / 10, Decimal('20'))
            base_score = base_score - waiting_penalty
        
        # Adjust for age restrictions (penalty for narrow age ranges)
        age_range = policy.maximum_age - policy.minimum_age
        if age_range < 30:  # Narrow age range
            age_penalty = (30 - age_range) / 3
            base_score = base_score - age_penalty
        
        return max(base_score, Decimal('0'))
    
    def _calculate_review_score(self, policy: BasePolicy) -> Decimal:
        """
        Calculate score based on user reviews with credibility weighting.
        More reviews = more credible score.
        """
        reviews = policy.reviews.filter(is_approved=True)
        review_count = reviews.count()
        
        if review_count == 0:
            return Decimal('50')  # Neutral score if no reviews
        
        # Get average rating
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        
        if avg_rating is None:
            return Decimal('50')
        
        # Convert 5-star rating to 0-100 scale
        base_score = Decimal(str(avg_rating)) * Decimal('20')
        
        # Apply credibility factor based on review count
        # More reviews = higher confidence in the score
        if review_count >= 50:
            credibility = Decimal('1.0')
        elif review_count >= 20:
            credibility = Decimal('0.95')
        elif review_count >= 10:
            credibility = Decimal('0.90')
        elif review_count >= 5:
            credibility = Decimal('0.85')
        else:
            credibility = Decimal('0.75')
        
        # Adjust base score toward neutral (50) based on credibility
        adjusted_score = base_score * credibility + Decimal('50') * (Decimal('1') - credibility)
        
        return adjusted_score
    
    def _calculate_organization_score(self, policy: BasePolicy) -> Decimal:
        """
        Calculate score based on organization reputation and status.
        """
        score = Decimal('50')  # Start neutral
        
        org = policy.organization
        
        # Verified organization
        if org.is_verified:
            score += Decimal('20')
        
        # Check if organization is active
        if org.is_active:
            score += Decimal('10')
        
        # Check license status
        if not org.license_is_expired:
            score += Decimal('15')
        else:
            score -= Decimal('30')  # Big penalty for expired license
        
        # Featured policy bonus
        if policy.is_featured:
            score += Decimal('5')
        
        return min(max(score, Decimal('0')), Decimal('100'))
    
    def _rank_policies(self, results: List[Dict]) -> List[Dict]:
        """
        Rank policies by overall score and generate pros/cons.
        Handles ties with secondary sorting criteria.
        """
        # Sort by score (descending), then by value score, then by review score
        sorted_results = sorted(
            results,
            key=lambda x: (
                -x['score_data']['overall_score'],
                -x['score_data']['value_score'],
                -x['score_data']['review_score']
            )
        )
        
        # Assign ranks (handle ties)
        current_rank = 1
        previous_score = None
        
        for i, result in enumerate(sorted_results):
            current_score = result['score_data']['overall_score']
            
            if previous_score is not None and abs(current_score - previous_score) < 0.01:
                # Tie - use same rank
                result['rank'] = current_rank
            else:
                result['rank'] = i + 1
                current_rank = i + 1
            
            previous_score = current_score
            
            # Generate pros and cons (enhanced with survey context if available)
            if self.survey_context:
                result['pros'] = self._generate_survey_aware_pros(result['policy'], result['score_data'], self.survey_context)
                result['cons'] = self._generate_survey_aware_cons(result['policy'], result['score_data'], self.survey_context)
            else:
                result['pros'] = self._generate_pros(result['policy'], result['score_data'])
                result['cons'] = self._generate_cons(result['policy'], result['score_data'])
            
            # Generate match percentage
            result['match_percentage'] = round(result['score_data']['overall_score'], 1)
        
        return sorted_results
    
    def _generate_pros(self, policy: BasePolicy, score_data: Dict) -> List[str]:
        """
        Generate list of advantages for a policy based on scoring.
        """
        pros = []
        
        # Check high-scoring criteria
        for field_name, scores in score_data['criteria_scores'].items():
            if scores['score'] >= 85:
                criteria = self.criteria.get(field_name)
                if criteria:
                    pros.append(f"Excellent {criteria.name.lower()}")
                else:
                    pros.append(f"Strong {field_name.replace('_', ' ')}")
        
        # Value for money
        if score_data['value_score'] >= 75:
            pros.append("Outstanding value for money")
        elif score_data['value_score'] >= 60:
            pros.append("Good value for money")
        
        # Reviews
        if score_data['review_score'] >= 85:
            pros.append("Highly rated by customers")
        elif score_data['review_score'] >= 70:
            pros.append("Well-reviewed by customers")
        
        # Organization
        if score_data['organization_score'] >= 80:
            pros.append("Reputable insurance provider")
        
        if policy.organization.is_verified:
            pros.append("Verified organization")
        
        # Featured status
        if policy.is_featured:
            pros.append("Featured policy")
        
        # Short waiting period
        if policy.waiting_period_days <= 30:
            pros.append("Short waiting period")
        
        # Category-specific pros
        pros.extend(self._get_category_specific_pros(policy))
        
        return pros[:8]  # Limit to top 8
    
    def _generate_cons(self, policy: BasePolicy, score_data: Dict) -> List[str]:
        """
        Generate list of disadvantages for a policy based on scoring.
        """
        cons = []
        
        # Check low-scoring criteria
        for field_name, scores in score_data['criteria_scores'].items():
            if scores['score'] <= 35:
                criteria = self.criteria.get(field_name)
                if criteria:
                    cons.append(f"Limited {criteria.name.lower()}")
                else:
                    cons.append(f"Weak {field_name.replace('_', ' ')}")
        
        # Value concerns
        if score_data['value_score'] <= 35:
            cons.append("Poor value for money")
        elif score_data['value_score'] <= 50:
            cons.append("Below average value")
        
        # Review concerns
        if score_data['review_score'] <= 40:
            cons.append("Lower customer satisfaction")
        
        # Organization concerns
        if score_data['organization_score'] <= 40:
            cons.append("Organization reputation concerns")
        
        # Long waiting period
        if policy.waiting_period_days > 180:
            cons.append(f"Very long waiting period ({policy.waiting_period_days} days)")
        elif policy.waiting_period_days > 90:
            cons.append(f"Long waiting period ({policy.waiting_period_days} days)")
        
        # High premium relative to user target
        if 'base_premium' in self.user_criteria:
            user_premium = self.user_criteria.get('base_premium')
            if user_premium and policy.base_premium > user_premium * Decimal('1.3'):
                cons.append("Higher premium than preferred")
        
        # Low coverage relative to user target
        if 'coverage_amount' in self.user_criteria:
            user_coverage = self.user_criteria.get('coverage_amount')
            if user_coverage and policy.coverage_amount < user_coverage * Decimal('0.7'):
                cons.append("Lower coverage than desired")
        
        # Category-specific cons
        cons.extend(self._get_category_specific_cons(policy))
        
        return cons[:8]  # Limit to top 8
    
    def _generate_survey_aware_pros(self, policy: BasePolicy, score_data: Dict, survey_context: Dict) -> List[str]:
        """
        Generate survey-aware pros that reference user's specific responses.
        
        Args:
            policy: Policy to analyze
            score_data: Policy scoring data
            survey_context: Survey context including user profile
            
        Returns:
            List of personalized pros
        """
        pros = []
        user_profile = survey_context.get('user_profile', {})
        user_values = user_profile.get('user_values', {})
        priorities = user_profile.get('priorities', {})
        
        # Start with standard pros
        standard_pros = self._generate_pros(policy, score_data)
        
        # Add survey-specific pros
        survey_pros = []
        
        # Budget alignment
        if 'monthly_budget' in user_values:
            budget = user_values['monthly_budget']
            if isinstance(budget, (int, float)) and policy.base_premium <= budget:
                savings = budget - policy.base_premium
                if savings > 0:
                    survey_pros.append(f"Saves you R{savings:.0f}/month from your budget")
                else:
                    survey_pros.append("Fits exactly within your stated budget")
        
        # Coverage preferences
        if 'coverage_amount_preference' in user_values:
            coverage_pref = user_values['coverage_amount_preference']
            if isinstance(coverage_pref, (int, float)) and policy.coverage_amount >= coverage_pref:
                excess = policy.coverage_amount - coverage_pref
                if excess > 0:
                    survey_pros.append(f"Provides R{excess:,.0f} more coverage than you requested")
                else:
                    survey_pros.append("Matches your exact coverage requirement")
        
        # Feature-specific pros based on survey responses
        feature_pros = [
            ('chronic_medication_needed', 'chronic_medication_covered', 'Covers chronic medication as you need'),
            ('dental_cover_needed', 'includes_dental_cover', 'Includes dental coverage you requested'),
            ('optical_cover_needed', 'includes_optical_cover', 'Provides optical coverage as preferred'),
            ('maternity_cover_needed', 'includes_maternity_cover', 'Includes maternity benefits you wanted'),
            ('repatriation_needed', 'repatriation_covered', 'Covers repatriation services as required'),
            ('inflation_protection_wanted', 'inflation_protection_included', 'Includes inflation protection you requested')
        ]
        
        for user_field, policy_field, message in feature_pros:
            if (user_values.get(user_field) and 
                hasattr(policy, policy_field) and 
                getattr(policy, policy_field)):
                survey_pros.append(message)
        
        # Priority-based pros
        for priority_field, priority_value in priorities.items():
            priority_score = self._convert_priority_to_score(priority_value)
            if priority_score and priority_score >= 70:
                performance = self._evaluate_policy_performance(policy, priority_field)
                if performance >= 80:
                    field_display = priority_field.replace('_', ' ').title()
                    survey_pros.append(f"Excels in {field_display} (your high priority)")
        
        # Waiting period pros
        if 'waiting_period_tolerance' in user_values:
            tolerance = user_values['waiting_period_tolerance']
            if isinstance(tolerance, (int, float)) and policy.waiting_period_days <= tolerance / 2:
                survey_pros.append(f"Much shorter waiting period than your {tolerance}-day tolerance")
        
        # Confidence-based pros (highlight areas where user was very confident)
        confidence_levels = user_profile.get('confidence_levels', {})
        for field_name, confidence in confidence_levels.items():
            if confidence >= 4 and field_name in score_data.get('criteria_scores', {}):
                criteria_score = score_data['criteria_scores'][field_name]['score']
                if criteria_score >= 80:
                    field_display = field_name.replace('_', ' ').title()
                    survey_pros.append(f"Strong match for {field_display} (high confidence area)")
        
        # Combine and prioritize
        all_pros = survey_pros + [pro for pro in standard_pros if pro not in survey_pros]
        
        return all_pros[:8]  # Limit to top 8
    
    def _generate_survey_aware_cons(self, policy: BasePolicy, score_data: Dict, survey_context: Dict) -> List[str]:
        """
        Generate survey-aware cons that reference user's specific responses.
        
        Args:
            policy: Policy to analyze
            score_data: Policy scoring data
            survey_context: Survey context including user profile
            
        Returns:
            List of personalized cons
        """
        cons = []
        user_profile = survey_context.get('user_profile', {})
        user_values = user_profile.get('user_values', {})
        priorities = user_profile.get('priorities', {})
        
        # Start with standard cons
        standard_cons = self._generate_cons(policy, score_data)
        
        # Add survey-specific cons
        survey_cons = []
        
        # Budget concerns
        if 'monthly_budget' in user_values:
            budget = user_values['monthly_budget']
            if isinstance(budget, (int, float)) and policy.base_premium > budget:
                excess = policy.base_premium - budget
                survey_cons.append(f"R{excess:.0f}/month over your stated budget")
        
        # Coverage gaps
        if 'coverage_amount_preference' in user_values:
            coverage_pref = user_values['coverage_amount_preference']
            if isinstance(coverage_pref, (int, float)) and policy.coverage_amount < coverage_pref:
                shortfall = coverage_pref - policy.coverage_amount
                survey_cons.append(f"R{shortfall:,.0f} less coverage than you wanted")
        
        # Missing features that user needs
        missing_features = [
            ('chronic_medication_needed', 'chronic_medication_covered', 'No chronic medication coverage (you need this)'),
            ('dental_cover_needed', 'includes_dental_cover', 'Missing dental coverage you requested'),
            ('optical_cover_needed', 'includes_optical_cover', 'No optical coverage (you wanted this)'),
            ('maternity_cover_needed', 'includes_maternity_cover', 'Missing maternity benefits you need'),
            ('repatriation_needed', 'repatriation_covered', 'No repatriation coverage (you require this)'),
            ('inflation_protection_wanted', 'inflation_protection_included', 'Missing inflation protection you wanted')
        ]
        
        for user_field, policy_field, message in missing_features:
            if (user_values.get(user_field) and 
                (not hasattr(policy, policy_field) or not getattr(policy, policy_field))):
                survey_cons.append(message)
        
        # Priority-based cons
        for priority_field, priority_value in priorities.items():
            priority_score = self._convert_priority_to_score(priority_value)
            if priority_score and priority_score >= 70:
                performance = self._evaluate_policy_performance(policy, priority_field)
                if performance <= 40:
                    field_display = priority_field.replace('_', ' ').title()
                    survey_cons.append(f"Weak performance in {field_display} (your high priority)")
        
        # Waiting period concerns
        if 'waiting_period_tolerance' in user_values:
            tolerance = user_values['waiting_period_tolerance']
            if isinstance(tolerance, (int, float)) and policy.waiting_period_days > tolerance:
                excess_days = policy.waiting_period_days - tolerance
                survey_cons.append(f"Waiting period {excess_days} days longer than your tolerance")
        
        # Age eligibility concerns
        if 'age' in user_values:
            age = user_values['age']
            if isinstance(age, (int, float)):
                if age < policy.minimum_age:
                    survey_cons.append(f"You're too young (minimum age: {policy.minimum_age})")
                elif age > policy.maximum_age:
                    survey_cons.append(f"You're over the maximum age ({policy.maximum_age})")
        
        # Family size mismatch
        if 'family_members_to_cover' in user_values:
            family_size = user_values['family_members_to_cover']
            if isinstance(family_size, (int, float)) and hasattr(policy, 'maximum_family_size'):
                if family_size > policy.maximum_family_size:
                    survey_cons.append(f"Cannot cover all {family_size} family members (max: {policy.maximum_family_size})")
        
        # Confidence-based cons (highlight areas where user was confident but policy scores poorly)
        confidence_levels = user_profile.get('confidence_levels', {})
        for field_name, confidence in confidence_levels.items():
            if confidence >= 4 and field_name in score_data.get('criteria_scores', {}):
                criteria_score = score_data['criteria_scores'][field_name]['score']
                if criteria_score <= 40:
                    field_display = field_name.replace('_', ' ').title()
                    survey_cons.append(f"Poor match for {field_display} (important to you)")
        
        # Combine and prioritize
        all_cons = survey_cons + [con for con in standard_cons if con not in survey_cons]
        
        return all_cons[:8]  # Limit to top 8
    
    def _get_category_specific_pros(self, policy: BasePolicy) -> List[str]:
        """Get category-specific advantages."""
        pros = []
        
        if isinstance(policy, HealthPolicy):
            if policy.includes_hospital_cover and policy.includes_outpatient_cover:
                pros.append("Comprehensive hospital and day-to-day cover")
            if policy.chronic_medication_covered:
                pros.append("Includes chronic medication")
            if policy.gp_visits_per_year and policy.gp_visits_per_year > 10:
                pros.append(f"Generous GP visits ({policy.gp_visits_per_year}/year)")
                
        # elif isinstance(policy, LifePolicy):
        #     if policy.has_cash_value:
        #         pros.append("Builds cash value over time")
        #     if policy.critical_illness_cover:
        #         pros.append("Includes critical illness cover")
        #     if policy.accidental_death_benefit:
        #         pros.append(f"Accidental death benefit ({policy.accidental_death_multiplier}x)")
                
        elif isinstance(policy, FuneralPolicy):
            if policy.includes_spouse_cover and policy.includes_children_cover:
                pros.append("Full family coverage included")
            if policy.repatriation_covered:
                pros.append("Repatriation services covered")
            if policy.claim_payout_days <= 48:
                pros.append(f"Fast claim payout ({policy.claim_payout_days} hours)")
        
        return pros
    
    def _get_category_specific_cons(self, policy: BasePolicy) -> List[str]:
        """Get category-specific disadvantages."""
        cons = []
        
        if isinstance(policy, HealthPolicy):
            if not policy.includes_dental_cover:
                cons.append("No dental coverage")
            if not policy.includes_optical_cover:
                cons.append("No optical/vision coverage")
            if not policy.chronic_medication_covered:
                cons.append("Chronic medication not covered")
                
        elif isinstance(policy, LifePolicy):
            if policy.medical_exam_required:
                cons.append("Medical examination required")
            if not policy.is_renewable:
                cons.append("Policy not renewable")
                
        elif isinstance(policy, FuneralPolicy):
            if policy.natural_death_waiting_period > 6:
                cons.append(f"Long natural death waiting period ({policy.natural_death_waiting_period} months)")
            if not policy.includes_children_cover:
                cons.append("Children not covered")
        
        return cons
    
    def _generate_detailed_analysis(
        self,
        ranked_results: List[Dict],
        user_criteria: Dict
    ) -> Dict[str, Any]:
        """
        Generate detailed comparison analysis.
        """
        if not ranked_results:
            return {}
        
        # Calculate statistics
        scores = [r['score_data']['overall_score'] for r in ranked_results]
        
        analysis = {
            'score_range': {
                'highest': max(scores),
                'lowest': min(scores),
                'average': sum(scores) / len(scores),
                'spread': max(scores) - min(scores)
            },
            'top_policy_advantages': ranked_results[0]['pros'],
            'common_strengths': self._find_common_strengths(ranked_results),
            'common_weaknesses': self._find_common_weaknesses(ranked_results),
            'value_leaders': self._find_value_leaders(ranked_results),
            'price_range': {
                'minimum': float(min([r['policy'].base_premium for r in ranked_results])),
                'maximum': float(max([r['policy'].base_premium for r in ranked_results])),
                'average': float(sum([r['policy'].base_premium for r in ranked_results]) / len(ranked_results))
            },
            'coverage_range': {
                'minimum': float(min([r['policy'].coverage_amount for r in ranked_results])),
                'maximum': float(max([r['policy'].coverage_amount for r in ranked_results])),
                'average': float(sum([r['policy'].coverage_amount for r in ranked_results]) / len(ranked_results))
            }
        }
        
        return analysis
    
    def _find_common_strengths(self, ranked_results: List[Dict]) -> List[str]:
        """Find strengths common across multiple policies."""
        all_pros = []
        for result in ranked_results:
            all_pros.extend(result['pros'])
        
        # Count frequency
        from collections import Counter
        pro_counts = Counter(all_pros)
        
        # Return pros that appear in at least 40% of policies
        threshold = len(ranked_results) * 0.4
        common = [pro for pro, count in pro_counts.items() if count >= threshold]
        
        return common[:5]
    
    def _find_common_weaknesses(self, ranked_results: List[Dict]) -> List[str]:
        """Find weaknesses common across multiple policies."""
        all_cons = []
        for result in ranked_results:
            all_cons.extend(result['cons'])
        
        from collections import Counter
        con_counts = Counter(all_cons)
        
        threshold = len(ranked_results) * 0.4
        common = [con for con, count in con_counts.items() if count >= threshold]
        
        return common[:5]
    
    def _find_value_leaders(self, ranked_results: List[Dict]) -> List[Dict]:
        """Find policies with best value scores."""
        value_sorted = sorted(
            ranked_results,
            key=lambda x: x['score_data']['value_score'],
            reverse=True
        )
        
        return [
            {
                'policy_id': r['policy'].id,
                'policy_name': r['policy'].name,
                'value_score': r['score_data']['value_score']
            }
            for r in value_sorted[:3]
        ]
    
    def _generate_insights(
        self,
        ranked_results: List[Dict],
        user_criteria: Dict
    ) -> Dict[str, Any]:
        """
        Generate actionable insights from the comparison.
        """
        insights = {
            'recommendations_summary': [],
            'trade_offs': [],
            'key_differences': []
        }
        
        if len(ranked_results) < 2:
            return insights
        
        best = ranked_results[0]
        second_best = ranked_results[1]
        
        # Price vs Coverage trade-off
        if best['policy'].base_premium > second_best['policy'].base_premium:
            if best['policy'].coverage_amount > second_best['policy'].coverage_amount:
                insights['trade_offs'].append(
                    f"Top match offers {float((best['policy'].coverage_amount - second_best['policy'].coverage_amount) / 1000):.1f}k more coverage "
                    f"for {float(best['policy'].base_premium - second_best['policy'].base_premium):.2f} extra per month"
                )
        
        # Score differences
        score_diff = best['score_data']['overall_score'] - second_best['score_data']['overall_score']
        if score_diff < 5:
            insights['recommendations_summary'].append(
                "Top two policies are very closely matched - consider other factors like provider preference"
            )
        elif score_diff > 20:
            insights['recommendations_summary'].append(
                "Clear best match identified with significantly better score"
            )
        
        # Identify key differentiators
        best_criteria = best['score_data']['criteria_scores']
        second_criteria = second_best['score_data']['criteria_scores']
        
        for field_name in best_criteria:
            if field_name in second_criteria:
                diff = abs(best_criteria[field_name]['score'] - second_criteria[field_name]['score'])
                if diff > 30:
                    insights['key_differences'].append(
                        f"{field_name.replace('_', ' ').title()}: Top policy scores {diff:.1f} points higher"
                    )
        
        return insights
    
    def _save_results(
        self,
        session: ComparisonSession,
        ranked_results: List[Dict]
    ):
        """Save comparison results to database."""
        if not ranked_results:
            return
        
        # Update session with best match
        session.best_match_policy = ranked_results[0]['policy']
        session.match_scores = {
            str(r['policy'].id): r['score_data']['overall_score']
            for r in ranked_results
        }
        session.save()
        
        # Create result objects
        ComparisonResult.objects.filter(session=session).delete()  # Clear old results
        
        for result in ranked_results:
            ComparisonResult.objects.create(
                session=session,
                policy=result['policy'],
                overall_score=Decimal(str(result['score_data']['overall_score'])),
                criteria_scores=result['score_data']['criteria_scores'],
                rank=result['rank'],
                pros=result['pros'],
                cons=result['cons'],
                recommendation_reason=self._generate_recommendation_reason(result)
            )
    
    def _generate_recommendation_reason(self, result: Dict) -> str:
        """Generate detailed explanation for policy ranking."""
        policy = result['policy']
        score = result['score_data']['overall_score']
        rank = result['rank']
        
        # Check if we have survey enhancements
        survey_enhancements = result['score_data'].get('survey_enhancements', {})
        personalization_factors = survey_enhancements.get('personalization_factors', [])
        
        base_reason = ""
        if rank == 1:
            base_reason = (
                f"🥇 {policy.name} is your best match with a score of {score:.1f}/100. "
                f"It excels in your priority areas and offers the best overall combination "
                f"of coverage, value, and quality for your specific needs."
            )
        elif rank == 2:
            base_reason = (
                f"🥈 {policy.name} is a strong alternative with a score of {score:.1f}/100. "
                f"While not the top match, it offers excellent value and may be worth "
                f"considering if certain factors are particularly important to you."
            )
        elif rank == 3:
            base_reason = (
                f"🥉 {policy.name} scored {score:.1f}/100 and ranks third. "
                f"It's a solid option that meets most of your requirements, though "
                f"other policies align better with your stated priorities."
            )
        elif score >= 70:
            base_reason = (
                f"{policy.name} scored {score:.1f}/100 (ranked #{rank}). "
                f"This is a good policy that meets many of your needs, though there "
                f"are better matches available based on your criteria."
            )
        elif score >= 50:
            base_reason = (
                f"{policy.name} scored {score:.1f}/100 (ranked #{rank}). "
                f"While this policy provides adequate coverage, it doesn't align as "
                f"closely with your priorities as other options. Review the trade-offs carefully."
            )
        else:
            base_reason = (
                f"{policy.name} scored {score:.1f}/100 (ranked #{rank}). "
                f"This policy has significant gaps compared to your requirements. "
                f"Consider whether the compromises are acceptable for your situation."
            )
        
        # Add personalization factors if available
        if personalization_factors:
            top_factors = personalization_factors[:2]  # Show top 2 factors
            factors_text = " Specifically: " + "; ".join(top_factors) + "."
            base_reason += factors_text
        
        # Add confidence note if survey data was used
        if survey_enhancements.get('confidence_weighted'):
            profile_strength = survey_enhancements.get('profile_strength', 0)
            if profile_strength >= 0.8:
                base_reason += " This recommendation is highly personalized based on your detailed survey responses."
            elif profile_strength >= 0.6:
                base_reason += " This recommendation is personalized based on your survey responses."
        
        return base_reason
    
    def _generate_recommendations(
        self,
        ranked_results: List[Dict],
        user_criteria: Dict
    ) -> Dict[str, Any]:
        """
        Generate personalized recommendations across different categories.
        """
        if not ranked_results:
            return {}
        
        best_policy = ranked_results[0]
        
        recommendations = {
            'best_overall': {
                'policy_id': best_policy['policy'].id,
                'policy_name': best_policy['policy'].name,
                'organization': best_policy['policy'].organization.name,
                'score': best_policy['score_data']['overall_score'],
                'premium': float(best_policy['policy'].base_premium),
                'coverage': float(best_policy['policy'].coverage_amount),
                'rank': best_policy['rank'],
                'reason': f"Best match based on your priorities with a score of {best_policy['score_data']['overall_score']:.1f}/100",
                'top_pros': best_policy['pros'][:3]
            }
        }
        
        # Best value
        value_sorted = sorted(
            ranked_results,
            key=lambda x: x['score_data']['value_score'],
            reverse=True
        )
        if value_sorted:
            best_value = value_sorted[0]
            recommendations['best_value'] = {
                'policy_id': best_value['policy'].id,
                'policy_name': best_value['policy'].name,
                'organization': best_value['policy'].organization.name,
                'value_score': best_value['score_data']['value_score'],
                'premium': float(best_value['policy'].base_premium),
                'coverage': float(best_value['policy'].coverage_amount),
                'value_ratio': float(best_value['policy'].coverage_amount / best_value['policy'].base_premium),
                'reason': "Offers the best coverage-to-premium ratio"
            }
        
        # Most reviewed/popular
        review_sorted = sorted(
            ranked_results,
            key=lambda x: x['score_data']['review_score'],
            reverse=True
        )
        if review_sorted and review_sorted[0]['score_data']['review_score'] > 50:
            most_reviewed = review_sorted[0]
            recommendations['most_popular'] = {
                'policy_id': most_reviewed['policy'].id,
                'policy_name': most_reviewed['policy'].name,
                'organization': most_reviewed['policy'].organization.name,
                'review_score': most_reviewed['score_data']['review_score'],
                'reason': "Highest rated by other customers"
            }
        
        # Budget option (lowest premium)
        budget_sorted = sorted(
            ranked_results,
            key=lambda x: x['policy'].base_premium
        )
        if budget_sorted:
            budget_policy = budget_sorted[0]
            recommendations['budget_friendly'] = {
                'policy_id': budget_policy['policy'].id,
                'policy_name': budget_policy['policy'].name,
                'organization': budget_policy['policy'].organization.name,
                'premium': float(budget_policy['policy'].base_premium),
                'coverage': float(budget_policy['policy'].coverage_amount),
                'overall_score': budget_policy['score_data']['overall_score'],
                'reason': "Most affordable option"
            }
        
        # Premium option (highest coverage)
        coverage_sorted = sorted(
            ranked_results,
            key=lambda x: x['policy'].coverage_amount,
            reverse=True
        )
        if coverage_sorted:
            premium_policy = coverage_sorted[0]
            recommendations['premium_coverage'] = {
                'policy_id': premium_policy['policy'].id,
                'policy_name': premium_policy['policy'].name,
                'organization': premium_policy['policy'].organization.name,
                'coverage': float(premium_policy['policy'].coverage_amount),
                'premium': float(premium_policy['policy'].base_premium),
                'overall_score': premium_policy['score_data']['overall_score'],
                'reason': "Highest coverage amount available"
            }
        
        return recommendations
    
    def _apply_survey_filters(self, policies: List[BasePolicy], filters: Dict[str, Any]) -> List[BasePolicy]:
        """
        Apply survey-generated filters to remove policies that don't meet hard requirements.
        
        Args:
            policies: List of policies to filter
            filters: Dictionary of filter criteria from survey responses
            
        Returns:
            Filtered list of policies
        """
        if not filters:
            return policies
        
        filtered_policies = []
        
        for policy in policies:
            meets_requirements = True
            
            # Check each filter criterion
            for filter_key, filter_value in filters.items():
                if not self._policy_meets_filter(policy, filter_key, filter_value):
                    meets_requirements = False
                    break
            
            if meets_requirements:
                filtered_policies.append(policy)
        
        logger.info(f"Survey filters reduced {len(policies)} policies to {len(filtered_policies)}")
        return filtered_policies
    
    def _policy_meets_filter(self, policy: BasePolicy, filter_key: str, filter_value: Any) -> bool:
        """
        Check if a policy meets a specific filter criterion.
        
        Args:
            policy: Policy to check
            filter_key: Filter criterion key
            filter_value: Required value
            
        Returns:
            True if policy meets the filter criterion
        """
        # Handle Django ORM-style filters
        if '__' in filter_key:
            field_name, operator = filter_key.split('__', 1)
            policy_value = getattr(policy, field_name, None)
            
            if policy_value is None:
                return False
            
            if operator == 'lte':
                return policy_value <= filter_value
            elif operator == 'gte':
                return policy_value >= filter_value
            elif operator == 'lt':
                return policy_value < filter_value
            elif operator == 'gt':
                return policy_value > filter_value
            elif operator == 'exact':
                return policy_value == filter_value
            elif operator == 'icontains':
                return str(filter_value).lower() in str(policy_value).lower()
        
        # Handle direct field comparisons
        else:
            policy_value = getattr(policy, filter_key, None)
            if policy_value is None:
                return False
            
            # Boolean filters
            if isinstance(filter_value, bool):
                return bool(policy_value) == filter_value
            
            # Exact match filters
            return policy_value == filter_value
        
        return True


def compare_policies_with_survey_data(
    category_slug: str,
    policy_ids: List[int],
    survey_session: 'ComparisonSession',
    user=None
) -> Dict[str, Any]:
    """
    Convenience function to compare policies using survey data from a session.
    
    Args:
        category_slug: Policy category slug
        policy_ids: List of policy IDs to compare
        survey_session: ComparisonSession with survey responses
        user: User object (optional)
        
    Returns:
        Comparison results with survey-driven scoring
    """
    from surveys.response_processor import ResponseProcessor
    
    # Process survey responses
    processor = ResponseProcessor(category_slug)
    survey_data = processor.process_responses(survey_session)
    
    # Create comparison engine
    engine = PolicyComparisonEngine(category_slug)
    
    # Run comparison with survey context
    return engine.compare_policies(
        policy_ids=policy_ids,
        user_criteria=survey_data.get('criteria', {}),
        user=user,
        session_key=survey_session.session_key,
        survey_context=survey_data
    )


class QuickComparisonEngine:
    """
    Simplified comparison engine for quick policy comparisons.
    Uses basic criteria without requiring detailed user input.
    """
    
    @staticmethod
    def compare_by_price(policy_ids: List[int]) -> List[BasePolicy]:
        """Compare policies by premium (lowest to highest)."""
        return list(
            BasePolicy.objects.filter(
                id__in=policy_ids,
                is_active=True,
                approval_status='APPROVED'
            ).order_by('base_premium').select_related(
                'organization', 'category', 'policy_type'
            )
        )
    
    @staticmethod
    def compare_by_coverage(policy_ids: List[int]) -> List[BasePolicy]:
        """Compare policies by coverage amount (highest to lowest)."""
        return list(
            BasePolicy.objects.filter(
                id__in=policy_ids,
                is_active=True,
                approval_status='APPROVED'
            ).order_by('-coverage_amount').select_related(
                'organization', 'category', 'policy_type'
            )
        )
    
    @staticmethod
    def compare_by_value(policy_ids: List[int]) -> List[Dict]:
        """Compare policies by value (coverage/premium ratio)."""
        policies = BasePolicy.objects.filter(
            id__in=policy_ids,
            is_active=True,
            approval_status='APPROVED'
        ).select_related('organization', 'category', 'policy_type')
        
        results = []
        for policy in policies:
            if policy.base_premium > 0:
                value_ratio = policy.coverage_amount / policy.base_premium
                results.append({
                    'policy': policy,
                    'policy_id': policy.id,
                    'policy_name': policy.name,
                    'organization': policy.organization.name,
                    'value_ratio': float(value_ratio),
                    'coverage': float(policy.coverage_amount),
                    'premium': float(policy.base_premium)
                })
        
        return sorted(results, key=lambda x: x['value_ratio'], reverse=True)
    
    @staticmethod
    def compare_by_rating(policy_ids: List[int]) -> List[Dict]:
        """Compare policies by user ratings."""
        from django.db.models import Avg, Count
        
        policies = BasePolicy.objects.filter(
            id__in=policy_ids,
            is_active=True,
            approval_status='APPROVED'
        ).annotate(
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            review_count=Count('reviews', filter=Q(reviews__is_approved=True))
        ).select_related('organization', 'category', 'policy_type')
        
        results = []
        for policy in policies:
            results.append({
                'policy': policy,
                'policy_id': policy.id,
                'policy_name': policy.name,
                'organization': policy.organization.name,
                'avg_rating': float(policy.avg_rating) if policy.avg_rating else 0,
                'review_count': policy.review_count,
                'premium': float(policy.base_premium),
                'coverage': float(policy.coverage_amount)
            })
        
        return sorted(
            results,
            key=lambda x: (x['avg_rating'], x['review_count']),
            reverse=True
        )