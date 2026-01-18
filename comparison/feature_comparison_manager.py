"""
Feature-based comparison manager for health and funeral policies.
Handles comparison result generation, ranking, and categorization.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from .models import FeatureComparisonResult
from .feature_matching_engine import FeatureMatchingEngine
from simple_surveys.models import SimpleSurvey
from policies.models import BasePolicy
import logging

logger = logging.getLogger(__name__)


class FeatureComparisonManager:
    """
    Manages the generation and ranking of feature-based comparison results.
    """
    
    def __init__(self):
        self.matching_engines = {}
    
    def get_matching_engine(self, insurance_type: str) -> FeatureMatchingEngine:
        """Get or create a matching engine for the specified insurance type."""
        if insurance_type not in self.matching_engines:
            self.matching_engines[insurance_type] = FeatureMatchingEngine(insurance_type)
        return self.matching_engines[insurance_type]
    
    def generate_comparison_results(
        self, 
        survey: SimpleSurvey, 
        policies: List[BasePolicy],
        force_regenerate: bool = False
    ) -> List[FeatureComparisonResult]:
        """
        Generate feature-based comparison results for a survey against a list of policies.
        
        Args:
            survey: SimpleSurvey instance with user preferences
            policies: List of BasePolicy instances to compare
            force_regenerate: Whether to regenerate existing results
            
        Returns:
            List of FeatureComparisonResult instances, ordered by compatibility rank
        """
        try:
            # Check if results already exist and don't need regeneration
            if not force_regenerate:
                existing_results = FeatureComparisonResult.objects.filter(
                    survey=survey,
                    policy__in=policies
                ).order_by('compatibility_rank')
                
                if existing_results.count() == len(policies):
                    logger.info(f"Using existing comparison results for survey {survey.id}")
                    return list(existing_results)
            
            # Get user preferences from survey
            user_preferences = survey.get_preferences_dict()
            if not user_preferences:
                logger.warning(f"No preferences found for survey {survey.id}")
                return []
            
            # Get matching engine for the insurance type
            matching_engine = self.get_matching_engine(survey.insurance_type)
            
            # Calculate compatibility for each policy
            policy_scores = []
            for policy in policies:
                try:
                    compatibility_result = matching_engine.calculate_policy_compatibility(
                        policy, user_preferences
                    )
                    policy_scores.append((policy, compatibility_result))
                except Exception as e:
                    logger.error(f"Error calculating compatibility for policy {policy.id}: {str(e)}")
                    # Add empty result for failed calculations
                    policy_scores.append((policy, matching_engine._empty_result()))
            
            # Sort by overall score (descending)
            policy_scores.sort(key=lambda x: x[1]['overall_score'], reverse=True)
            
            # Generate comparison results with transaction
            with transaction.atomic():
                # Delete existing results if regenerating
                if force_regenerate:
                    FeatureComparisonResult.objects.filter(
                        survey=survey,
                        policy__in=policies
                    ).delete()
                
                results = []
                for rank, (policy, compatibility_result) in enumerate(policy_scores, 1):
                    result = self._create_comparison_result(
                        survey=survey,
                        policy=policy,
                        compatibility_result=compatibility_result,
                        rank=rank
                    )
                    results.append(result)
                
                logger.info(f"Generated {len(results)} comparison results for survey {survey.id}")
                return results
                
        except Exception as e:
            logger.error(f"Error generating comparison results for survey {survey.id}: {str(e)}")
            raise
    
    def _create_comparison_result(
        self,
        survey: SimpleSurvey,
        policy: BasePolicy,
        compatibility_result: Dict,
        rank: int
    ) -> FeatureComparisonResult:
        """Create a FeatureComparisonResult instance from compatibility calculation."""
        
        # Calculate match and mismatch counts
        matches = compatibility_result.get('matches', [])
        mismatches = compatibility_result.get('mismatches', [])
        
        # Create the result instance
        result = FeatureComparisonResult.objects.create(
            survey=survey,
            policy=policy,
            overall_compatibility_score=Decimal(str(compatibility_result['overall_score'] * 100)),
            feature_match_count=len(matches),
            feature_mismatch_count=len(mismatches),
            feature_scores=compatibility_result.get('feature_scores', {}),
            feature_matches=matches,
            feature_mismatches=mismatches,
            compatibility_rank=rank,
            recommendation_category=self._determine_recommendation_category(
                compatibility_result['overall_score']
            ),
            match_explanation=compatibility_result.get('explanation', '')
        )
        
        return result
    
    def _determine_recommendation_category(self, overall_score: float) -> str:
        """Determine recommendation category based on overall compatibility score."""
        score_percentage = overall_score * 100
        
        if score_percentage >= 95:
            return FeatureComparisonResult.RecommendationCategory.PERFECT_MATCH
        elif score_percentage >= 80:
            return FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH
        elif score_percentage >= 60:
            return FeatureComparisonResult.RecommendationCategory.GOOD_MATCH
        elif score_percentage >= 40:
            return FeatureComparisonResult.RecommendationCategory.PARTIAL_MATCH
        else:
            return FeatureComparisonResult.RecommendationCategory.POOR_MATCH
    
    def get_comparison_results(
        self, 
        survey: SimpleSurvey, 
        limit: Optional[int] = None
    ) -> List[FeatureComparisonResult]:
        """
        Get existing comparison results for a survey.
        
        Args:
            survey: SimpleSurvey instance
            limit: Optional limit on number of results to return
            
        Returns:
            List of FeatureComparisonResult instances, ordered by rank
        """
        queryset = FeatureComparisonResult.objects.filter(
            survey=survey
        ).select_related('policy', 'policy__organization').order_by('compatibility_rank')
        
        if limit:
            queryset = queryset[:limit]
        
        return list(queryset)
    
    def get_best_matches(
        self, 
        survey: SimpleSurvey, 
        min_score: float = 60.0,
        limit: int = 5
    ) -> List[FeatureComparisonResult]:
        """
        Get the best matching policies for a survey.
        
        Args:
            survey: SimpleSurvey instance
            min_score: Minimum compatibility score to include
            limit: Maximum number of results to return
            
        Returns:
            List of top FeatureComparisonResult instances
        """
        return FeatureComparisonResult.objects.filter(
            survey=survey,
            overall_compatibility_score__gte=min_score
        ).select_related(
            'policy', 'policy__organization'
        ).order_by('compatibility_rank')[:limit]
    
    def get_recommendation_summary(self, survey: SimpleSurvey) -> Dict:
        """
        Get a summary of recommendations for a survey.
        
        Args:
            survey: SimpleSurvey instance
            
        Returns:
            Dictionary with recommendation summary statistics
        """
        results = FeatureComparisonResult.objects.filter(survey=survey)
        
        if not results.exists():
            return {
                'total_policies': 0,
                'best_match_score': 0,
                'average_score': 0,
                'excellent_matches': 0,
                'good_matches': 0,
                'recommendations': {}
            }
        
        # Calculate statistics
        scores = [float(r.overall_compatibility_score) for r in results]
        best_result = results.order_by('compatibility_rank').first()
        
        # Count by recommendation category
        category_counts = {}
        for category in FeatureComparisonResult.RecommendationCategory:
            count = results.filter(recommendation_category=category).count()
            category_counts[category.label] = count
        
        return {
            'total_policies': results.count(),
            'best_match_score': float(best_result.overall_compatibility_score) if best_result else 0,
            'average_score': sum(scores) / len(scores) if scores else 0,
            'excellent_matches': results.filter(
                overall_compatibility_score__gte=80
            ).count(),
            'good_matches': results.filter(
                overall_compatibility_score__gte=60,
                overall_compatibility_score__lt=80
            ).count(),
            'category_breakdown': category_counts,
            'best_match_policy': best_result.policy if best_result else None
        }
    
    def update_rankings(self, survey: SimpleSurvey) -> None:
        """
        Recalculate and update rankings for all results of a survey.
        
        Args:
            survey: SimpleSurvey instance
        """
        results = FeatureComparisonResult.objects.filter(
            survey=survey
        ).order_by('-overall_compatibility_score', 'policy__name')
        
        with transaction.atomic():
            for rank, result in enumerate(results, 1):
                if result.compatibility_rank != rank:
                    result.update_ranking(rank)
        
        logger.info(f"Updated rankings for {results.count()} results for survey {survey.id}")
    
    def compare_policies_for_survey(
        self,
        survey: SimpleSurvey,
        policy_ids: Optional[List[int]] = None,
        category_slug: Optional[str] = None
    ) -> List[FeatureComparisonResult]:
        """
        High-level method to compare policies for a survey.
        
        Args:
            survey: SimpleSurvey instance
            policy_ids: Optional list of specific policy IDs to compare
            category_slug: Optional category slug to filter policies
            
        Returns:
            List of FeatureComparisonResult instances
        """
        # Determine policies to compare
        if policy_ids:
            policies = BasePolicy.objects.filter(id__in=policy_ids)
        elif category_slug:
            policies = BasePolicy.objects.filter(category__slug=category_slug)
        else:
            # Default to policies matching the survey's insurance type
            insurance_type_mapping = {
                SimpleSurvey.InsuranceType.HEALTH: 'health',
                SimpleSurvey.InsuranceType.FUNERAL: 'funeral'
            }
            category_slug = insurance_type_mapping.get(survey.insurance_type)
            if category_slug:
                policies = BasePolicy.objects.filter(category__slug=category_slug)
            else:
                policies = BasePolicy.objects.none()
        
        # Filter out policies without required features
        policies = self._filter_policies_with_features(policies, survey.insurance_type)
        
        if not policies.exists():
            logger.warning(f"No suitable policies found for survey {survey.id}")
            return []
        
        return self.generate_comparison_results(survey, list(policies))
    
    def _filter_policies_with_features(
        self, 
        policies, 
        insurance_type: str
    ) -> 'QuerySet[BasePolicy]':
        """
        Filter policies that have the required feature definitions.
        
        Args:
            policies: QuerySet of BasePolicy instances
            insurance_type: Insurance type to check features for
            
        Returns:
            Filtered QuerySet of policies with required features
        """
        # For now, return all policies - in a real implementation,
        # this would check for PolicyFeatures relationship
        return policies.filter(is_active=True)