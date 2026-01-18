"""
Ranking and categorization utilities for feature-based policy comparison.
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from .models import FeatureComparisonResult
from simple_surveys.models import SimpleSurvey
import logging

logger = logging.getLogger(__name__)


class PolicyRankingEngine:
    """
    Handles ranking and categorization of policy comparison results.
    """
    
    # Scoring thresholds for recommendation categories
    PERFECT_MATCH_THRESHOLD = 95.0
    EXCELLENT_MATCH_THRESHOLD = 80.0
    GOOD_MATCH_THRESHOLD = 60.0
    PARTIAL_MATCH_THRESHOLD = 40.0
    
    def __init__(self):
        self.ranking_factors = {
            'compatibility_score': 0.7,  # Primary factor
            'feature_match_count': 0.15,
            'policy_popularity': 0.1,
            'premium_value': 0.05
        }
    
    def rank_comparison_results(
        self, 
        results: List[FeatureComparisonResult],
        ranking_criteria: Optional[Dict] = None
    ) -> List[FeatureComparisonResult]:
        """
        Rank comparison results using multiple criteria.
        
        Args:
            results: List of FeatureComparisonResult instances
            ranking_criteria: Optional custom ranking criteria weights
            
        Returns:
            List of results sorted by rank
        """
        if not results:
            return []
        
        # Use custom criteria if provided
        criteria = ranking_criteria or self.ranking_factors
        
        # Calculate composite scores for ranking
        scored_results = []
        for result in results:
            composite_score = self._calculate_composite_score(result, criteria)
            scored_results.append((result, composite_score))
        
        # Sort by composite score (descending)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Update ranks
        ranked_results = []
        for rank, (result, score) in enumerate(scored_results, 1):
            result.compatibility_rank = rank
            result.recommendation_category = self._categorize_result(
                float(result.overall_compatibility_score)
            )
            ranked_results.append(result)
        
        return ranked_results
    
    def _calculate_composite_score(
        self, 
        result: FeatureComparisonResult, 
        criteria: Dict[str, float]
    ) -> float:
        """
        Calculate composite score for ranking based on multiple factors.
        
        Args:
            result: FeatureComparisonResult instance
            criteria: Dictionary of ranking criteria and their weights
            
        Returns:
            Composite score for ranking
        """
        score = 0.0
        
        # Compatibility score (primary factor)
        compatibility_weight = criteria.get('compatibility_score', 0.7)
        score += float(result.overall_compatibility_score) * compatibility_weight
        
        # Feature match count
        match_weight = criteria.get('feature_match_count', 0.15)
        max_possible_matches = result.feature_match_count + result.feature_mismatch_count
        if max_possible_matches > 0:
            match_ratio = result.feature_match_count / max_possible_matches
            score += (match_ratio * 100) * match_weight
        
        # Policy popularity (based on organization or policy attributes)
        popularity_weight = criteria.get('policy_popularity', 0.1)
        popularity_score = self._get_policy_popularity_score(result.policy)
        score += popularity_score * popularity_weight
        
        # Premium value (lower premium is better, but consider coverage)
        value_weight = criteria.get('premium_value', 0.05)
        value_score = self._get_premium_value_score(result.policy)
        score += value_score * value_weight
        
        return score
    
    def _get_policy_popularity_score(self, policy) -> float:
        """
        Calculate popularity score for a policy.
        
        Args:
            policy: BasePolicy instance
            
        Returns:
            Popularity score (0-100)
        """
        # This is a simplified implementation
        # In a real system, this could be based on:
        # - Number of active policies
        # - Customer reviews/ratings
        # - Organization reputation
        # - Market share
        
        score = 50.0  # Base score
        
        # Boost score for established organizations
        if hasattr(policy, 'organization') and policy.organization:
            # This could be enhanced with actual organization metrics
            score += 10.0
        
        # Consider policy age (newer policies might be less proven)
        if hasattr(policy, 'created_at'):
            # Policies older than 1 year get a small boost
            from django.utils import timezone
            from datetime import timedelta
            
            if timezone.now() - policy.created_at > timedelta(days=365):
                score += 5.0
        
        return min(100.0, score)
    
    def _get_premium_value_score(self, policy) -> float:
        """
        Calculate premium value score for a policy.
        
        Args:
            policy: BasePolicy instance
            
        Returns:
            Value score (0-100)
        """
        # This is a simplified implementation
        # In a real system, this would consider:
        # - Premium vs coverage ratio
        # - Premium vs market average
        # - Additional benefits included
        
        base_score = 50.0
        
        if hasattr(policy, 'base_premium') and hasattr(policy, 'coverage_amount'):
            if policy.base_premium > 0 and policy.coverage_amount > 0:
                # Calculate coverage per rand of premium
                coverage_ratio = float(policy.coverage_amount) / float(policy.base_premium)
                
                # Normalize to 0-50 range (higher coverage per rand is better)
                # This is a simplified calculation
                if coverage_ratio > 100:  # Good value
                    base_score += min(25.0, (coverage_ratio - 100) / 10)
                elif coverage_ratio < 50:  # Poor value
                    base_score -= min(25.0, (50 - coverage_ratio) / 2)
        
        return max(0.0, min(100.0, base_score))
    
    def _categorize_result(self, compatibility_score: float) -> str:
        """
        Categorize a comparison result based on compatibility score.
        
        Args:
            compatibility_score: Compatibility score (0-100)
            
        Returns:
            Recommendation category
        """
        if compatibility_score >= self.PERFECT_MATCH_THRESHOLD:
            return FeatureComparisonResult.RecommendationCategory.PERFECT_MATCH
        elif compatibility_score >= self.EXCELLENT_MATCH_THRESHOLD:
            return FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH
        elif compatibility_score >= self.GOOD_MATCH_THRESHOLD:
            return FeatureComparisonResult.RecommendationCategory.GOOD_MATCH
        elif compatibility_score >= self.PARTIAL_MATCH_THRESHOLD:
            return FeatureComparisonResult.RecommendationCategory.PARTIAL_MATCH
        else:
            return FeatureComparisonResult.RecommendationCategory.POOR_MATCH
    
    def get_category_distribution(
        self, 
        results: List[FeatureComparisonResult]
    ) -> Dict[str, int]:
        """
        Get distribution of results across recommendation categories.
        
        Args:
            results: List of FeatureComparisonResult instances
            
        Returns:
            Dictionary with category counts
        """
        distribution = {}
        
        for category in FeatureComparisonResult.RecommendationCategory:
            count = sum(1 for r in results if r.recommendation_category == category)
            distribution[category.label] = count
        
        return distribution
    
    def get_ranking_insights(
        self, 
        results: List[FeatureComparisonResult]
    ) -> Dict[str, any]:
        """
        Generate insights about the ranking results.
        
        Args:
            results: List of FeatureComparisonResult instances
            
        Returns:
            Dictionary with ranking insights
        """
        if not results:
            return {'message': 'No results to analyze'}
        
        scores = [float(r.overall_compatibility_score) for r in results]
        
        insights = {
            'total_policies': len(results),
            'best_score': max(scores),
            'worst_score': min(scores),
            'average_score': sum(scores) / len(scores),
            'score_range': max(scores) - min(scores),
            'category_distribution': self.get_category_distribution(results)
        }
        
        # Add qualitative insights
        insights['insights'] = []
        
        if insights['score_range'] < 10:
            insights['insights'].append({
                'type': 'info',
                'message': 'All policies have similar compatibility scores, indicating consistent quality options.'
            })
        elif insights['score_range'] > 40:
            insights['insights'].append({
                'type': 'warning',
                'message': 'Wide variation in compatibility scores. Focus on top-ranked options.'
            })
        
        excellent_count = insights['category_distribution'].get('Excellent Match', 0)
        if excellent_count == 0:
            insights['insights'].append({
                'type': 'tip',
                'message': 'No excellent matches found. Consider adjusting your preferences or exploring more policies.'
            })
        elif excellent_count > 3:
            insights['insights'].append({
                'type': 'success',
                'message': f'Found {excellent_count} excellent matches. You have great options to choose from.'
            })
        
        return insights


class ComparisonResultAnalyzer:
    """
    Analyzes comparison results to provide insights and recommendations.
    """
    
    def __init__(self):
        self.ranking_engine = PolicyRankingEngine()
    
    def analyze_survey_results(
        self, 
        survey: SimpleSurvey,
        results: List[FeatureComparisonResult]
    ) -> Dict[str, any]:
        """
        Comprehensive analysis of comparison results for a survey.
        
        Args:
            survey: SimpleSurvey instance
            results: List of FeatureComparisonResult instances
            
        Returns:
            Dictionary with comprehensive analysis
        """
        analysis = {
            'survey_info': {
                'insurance_type': survey.get_insurance_type_display(),
                'preferences_count': len([v for v in survey.get_preferences_dict().values() if v is not None])
            },
            'ranking_analysis': self.ranking_engine.get_ranking_insights(results),
            'feature_analysis': self._analyze_feature_patterns(results),
            'recommendations': self._generate_recommendations(survey, results)
        }
        
        return analysis
    
    def _analyze_feature_patterns(
        self, 
        results: List[FeatureComparisonResult]
    ) -> Dict[str, any]:
        """
        Analyze patterns in feature matching across results.
        
        Args:
            results: List of FeatureComparisonResult instances
            
        Returns:
            Dictionary with feature analysis
        """
        if not results:
            return {}
        
        # Collect all feature scores
        all_feature_scores = {}
        for result in results:
            for feature_name, score_data in result.feature_scores.items():
                if feature_name not in all_feature_scores:
                    all_feature_scores[feature_name] = []
                
                if isinstance(score_data, dict) and 'score' in score_data:
                    all_feature_scores[feature_name].append(score_data['score'])
        
        # Calculate feature statistics
        feature_stats = {}
        for feature_name, scores in all_feature_scores.items():
            if scores:
                feature_stats[feature_name] = {
                    'average_score': sum(scores) / len(scores),
                    'best_score': max(scores),
                    'worst_score': min(scores),
                    'policies_with_feature': len(scores)
                }
        
        # Identify challenging features (low average scores)
        challenging_features = [
            name for name, stats in feature_stats.items()
            if stats['average_score'] < 0.5
        ]
        
        # Identify well-covered features (high average scores)
        well_covered_features = [
            name for name, stats in feature_stats.items()
            if stats['average_score'] > 0.8
        ]
        
        return {
            'feature_statistics': feature_stats,
            'challenging_features': challenging_features,
            'well_covered_features': well_covered_features,
            'total_features_analyzed': len(feature_stats)
        }
    
    def _generate_recommendations(
        self, 
        survey: SimpleSurvey,
        results: List[FeatureComparisonResult]
    ) -> Dict[str, any]:
        """
        Generate personalized recommendations based on analysis.
        
        Args:
            survey: SimpleSurvey instance
            results: List of FeatureComparisonResult instances
            
        Returns:
            Dictionary with recommendations
        """
        if not results:
            return {'message': 'No policies to recommend'}
        
        recommendations = {
            'primary_recommendation': None,
            'alternative_options': [],
            'considerations': []
        }
        
        # Primary recommendation (best match)
        best_result = min(results, key=lambda r: r.compatibility_rank)
        recommendations['primary_recommendation'] = {
            'policy': best_result.policy,
            'score': float(best_result.overall_compatibility_score),
            'reason': best_result.match_explanation,
            'key_matches': best_result.get_top_matching_features()
        }
        
        # Alternative options (next 2-3 best)
        alternatives = sorted(results, key=lambda r: r.compatibility_rank)[1:4]
        for alt_result in alternatives:
            recommendations['alternative_options'].append({
                'policy': alt_result.policy,
                'score': float(alt_result.overall_compatibility_score),
                'reason': f"Rank #{alt_result.compatibility_rank} option",
                'key_differentiator': self._identify_key_differentiator(best_result, alt_result)
            })
        
        # Generate considerations based on survey type and results
        if survey.insurance_type == SimpleSurvey.InsuranceType.HEALTH:
            recommendations['considerations'].extend(
                self._get_health_considerations(survey, results)
            )
        elif survey.insurance_type == SimpleSurvey.InsuranceType.FUNERAL:
            recommendations['considerations'].extend(
                self._get_funeral_considerations(survey, results)
            )
        
        return recommendations
    
    def _identify_key_differentiator(
        self, 
        primary_result: FeatureComparisonResult,
        alternative_result: FeatureComparisonResult
    ) -> str:
        """
        Identify the key differentiator between two results.
        
        Args:
            primary_result: Best match result
            alternative_result: Alternative result
            
        Returns:
            String describing key differentiator
        """
        # Compare feature scores to find biggest difference
        primary_scores = primary_result.feature_scores
        alt_scores = alternative_result.feature_scores
        
        biggest_diff = 0
        diff_feature = None
        
        for feature_name in primary_scores.keys():
            if feature_name in alt_scores:
                primary_score = primary_scores[feature_name].get('score', 0)
                alt_score = alt_scores[feature_name].get('score', 0)
                diff = abs(primary_score - alt_score)
                
                if diff > biggest_diff:
                    biggest_diff = diff
                    diff_feature = feature_name
        
        if diff_feature:
            feature_display = diff_feature.replace('_', ' ').title()
            return f"Different {feature_display} coverage"
        
        return "Alternative pricing or coverage structure"
    
    def _get_health_considerations(
        self, 
        survey: SimpleSurvey,
        results: List[FeatureComparisonResult]
    ) -> List[str]:
        """Get health insurance specific considerations."""
        considerations = []
        
        # Check chronic medication needs
        if survey.needs_chronic_medication:
            chronic_covered = sum(
                1 for r in results 
                if any('chronic' in match.get('feature', '').lower() 
                      for match in r.feature_matches)
            )
            if chronic_covered < len(results) / 2:
                considerations.append(
                    "Limited chronic medication coverage available. Verify coverage details before deciding."
                )
        
        # Check hospital benefit preferences
        if survey.wants_in_hospital_benefit and survey.wants_out_hospital_benefit:
            considerations.append(
                "You want both in-hospital and out-of-hospital benefits. Ensure your chosen policy covers both."
            )
        
        return considerations
    
    def _get_funeral_considerations(
        self, 
        survey: SimpleSurvey,
        results: List[FeatureComparisonResult]
    ) -> List[str]:
        """Get funeral insurance specific considerations."""
        considerations = []
        
        # Check cover amount adequacy
        if survey.preferred_cover_amount:
            avg_coverage = sum(
                float(r.policy.coverage_amount) for r in results 
                if hasattr(r.policy, 'coverage_amount')
            ) / len(results)
            
            if float(survey.preferred_cover_amount) > avg_coverage * 1.2:
                considerations.append(
                    "Your preferred coverage amount is higher than average. Consider if the additional cost is justified."
                )
        
        return considerations