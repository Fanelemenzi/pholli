"""
A/B testing framework for survey optimization.
"""

import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from django.db import models, transaction
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging

from .models import SurveyQuestion, SurveyResponse, ComparisonSession

logger = logging.getLogger(__name__)


# A/B testing models are defined in models.py to avoid circular imports


class ABTestManager:
    """
    Manager for A/B testing functionality.
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
    
    def get_active_tests(self) -> List:
        """Get all currently active A/B tests."""
        cache_key = "active_ab_tests"
        tests = cache.get(cache_key)
        
        if tests is None:
            from .models import ABTestVariant
            tests = list(ABTestVariant.objects.filter(
                status=ABTestVariant.Status.ACTIVE,
                start_date__lte=timezone.now()
            ).exclude(
                end_date__lt=timezone.now()
            ))
            cache.set(cache_key, tests, self.cache_timeout)
        
        return tests
    
    def assign_user_to_tests(self, session: ComparisonSession) -> Dict[str, str]:
        """
        Assign a user session to appropriate A/B tests.
        Returns dict of test_id -> variant assignments.
        """
        active_tests = self.get_active_tests()
        assignments = {}
        
        # Use session ID as user identifier for consistency
        user_identifier = str(session.id)
        
        for test in active_tests:
            if test.should_include_user(user_identifier):
                variant = test.get_variant_for_user(user_identifier)
                assignments[str(test.id)] = variant
                
                # Create participant record
                participant, created = ABTestParticipant.objects.get_or_create(
                    test=test,
                    session=session,
                    defaults={'variant': variant}
                )
                
                if created:
                    # Update test participant count
                    test.participants_count += 1
                    test.save(update_fields=['participants_count'])
        
        return assignments
    
    def get_variant_config(self, test_id: int, variant: str) -> Dict[str, Any]:
        """
        Get configuration for a specific test variant.
        """
        try:
            test = ABTestVariant.objects.get(id=test_id)
            return test.variants_config.get(variant, {})
        except ABTestVariant.DoesNotExist:
            return {}
    
    def record_participant_action(
        self,
        session: ComparisonSession,
        action: str,
        data: Dict[str, Any] = None
    ) -> None:
        """
        Record an action for A/B test participants.
        """
        participants = ABTestParticipant.objects.filter(session=session)
        
        for participant in participants:
            if action == 'survey_completed':
                participant.completed_at = timezone.now()
                participant.completion_rate = data.get('completion_rate', 0)
                participant.responses_count = data.get('responses_count', 0)
                participant.conversion_achieved = True
                participant.save()
            
            elif action == 'question_answered':
                participant.responses_count += 1
                participant.save(update_fields=['responses_count'])
            
            elif action == 'survey_abandoned':
                participant.completion_rate = data.get('completion_rate', 0)
                participant.responses_count = data.get('responses_count', 0)
                participant.save()
    
    def calculate_test_results(self, test_id: int) -> Dict[str, Any]:
        """
        Calculate results for an A/B test.
        """
        try:
            test = ABTestVariant.objects.get(id=test_id)
            participants = ABTestParticipant.objects.filter(test=test)
            
            results = {
                'test_id': test_id,
                'test_name': test.name,
                'total_participants': participants.count(),
                'variants': {},
                'statistical_significance': None,
                'winning_variant': None
            }
            
            # Calculate metrics by variant
            variants = participants.values_list('variant', flat=True).distinct()
            
            for variant in variants:
                variant_participants = participants.filter(variant=variant)
                total_variant = variant_participants.count()
                
                if total_variant == 0:
                    continue
                
                completed = variant_participants.filter(conversion_achieved=True).count()
                avg_completion_rate = variant_participants.aggregate(
                    avg_rate=models.Avg('completion_rate')
                )['avg_rate'] or 0
                
                avg_response_time = variant_participants.aggregate(
                    avg_time=models.Avg('response_time_seconds')
                )['avg_time'] or 0
                
                results['variants'][variant] = {
                    'participants': total_variant,
                    'conversions': completed,
                    'conversion_rate': (completed / total_variant) * 100,
                    'avg_completion_rate': round(avg_completion_rate, 2),
                    'avg_response_time': round(avg_response_time, 2)
                }
            
            # Calculate statistical significance (simplified)
            if len(results['variants']) >= 2:
                results['statistical_significance'] = self._calculate_significance(
                    results['variants']
                )
                results['winning_variant'] = self._determine_winner(
                    results['variants'], test.primary_metric
                )
            
            # Update test results
            test.results_data = results
            test.statistical_significance = results['statistical_significance']
            test.winning_variant = results['winning_variant']
            test.save()
            
            return results
            
        except ABTestVariant.DoesNotExist:
            return {}
    
    def _calculate_significance(self, variants: Dict[str, Dict]) -> Optional[float]:
        """
        Calculate statistical significance between variants (simplified chi-square test).
        """
        try:
            # This is a simplified implementation
            # In production, you'd want to use proper statistical libraries
            variant_list = list(variants.values())
            
            if len(variant_list) < 2:
                return None
            
            # Compare first two variants for simplicity
            v1, v2 = variant_list[0], variant_list[1]
            
            # Chi-square test for conversion rates
            n1, n2 = v1['participants'], v2['participants']
            x1, x2 = v1['conversions'], v2['conversions']
            
            if n1 < 30 or n2 < 30:  # Minimum sample size
                return None
            
            # Simplified p-value calculation
            # In practice, use scipy.stats.chi2_contingency
            p_combined = (x1 + x2) / (n1 + n2)
            expected1 = n1 * p_combined
            expected2 = n2 * p_combined
            
            if expected1 < 5 or expected2 < 5:
                return None
            
            chi_square = (
                ((x1 - expected1) ** 2 / expected1) +
                ((x2 - expected2) ** 2 / expected2) +
                (((n1 - x1) - (n1 - expected1)) ** 2 / (n1 - expected1)) +
                (((n2 - x2) - (n2 - expected2)) ** 2 / (n2 - expected2))
            )
            
            # Simplified p-value (would need proper chi-square distribution)
            # This is just a placeholder
            if chi_square > 3.84:  # Critical value for p < 0.05
                return 0.05
            else:
                return 0.1
            
        except (ZeroDivisionError, KeyError):
            return None
    
    def _determine_winner(self, variants: Dict[str, Dict], metric: str) -> Optional[str]:
        """
        Determine the winning variant based on the primary metric.
        """
        if not variants:
            return None
        
        best_variant = None
        best_value = None
        
        for variant_name, data in variants.items():
            if metric == 'completion_rate':
                value = data.get('conversion_rate', 0)
            elif metric == 'response_time':
                value = -data.get('avg_response_time', float('inf'))  # Lower is better
            else:
                value = data.get('avg_completion_rate', 0)
            
            if best_value is None or value > best_value:
                best_value = value
                best_variant = variant_name
        
        return best_variant
    
    def create_question_variant_test(
        self,
        question_id: int,
        variants: Dict[str, Dict[str, Any]],
        test_name: str,
        description: str = "",
        traffic_percentage: float = 50.0
    ) -> ABTestVariant:
        """
        Create an A/B test for different question variants.
        
        Args:
            question_id: ID of the question to test
            variants: Dict of variant_name -> variant_config
            test_name: Name of the test
            description: Description of the test
            traffic_percentage: Percentage of traffic to include
        
        Returns:
            Created ABTestVariant instance
        """
        test = ABTestVariant.objects.create(
            name=test_name,
            description=description,
            traffic_percentage=traffic_percentage,
            primary_metric='completion_rate',
            variants_config=variants,
            status=ABTestVariant.Status.DRAFT
        )
        
        return test
    
    def start_test(self, test_id: int) -> bool:
        """
        Start an A/B test.
        """
        try:
            test = ABTestVariant.objects.get(id=test_id)
            test.status = ABTestVariant.Status.ACTIVE
            test.start_date = timezone.now()
            test.save()
            
            # Clear cache
            cache.delete("active_ab_tests")
            
            return True
        except ABTestVariant.DoesNotExist:
            return False
    
    def stop_test(self, test_id: int) -> bool:
        """
        Stop an A/B test and calculate final results.
        """
        try:
            test = ABTestVariant.objects.get(id=test_id)
            test.status = ABTestVariant.Status.COMPLETED
            test.end_date = timezone.now()
            test.save()
            
            # Calculate final results
            self.calculate_test_results(test_id)
            
            # Clear cache
            cache.delete("active_ab_tests")
            
            return True
        except ABTestVariant.DoesNotExist:
            return False


class SurveyOptimizer:
    """
    Uses A/B test results to optimize survey performance.
    """
    
    def __init__(self):
        self.ab_manager = ABTestManager()
    
    def suggest_optimizations(self, category_slug: str) -> List[Dict[str, Any]]:
        """
        Suggest optimizations based on A/B test results and analytics.
        """
        suggestions = []
        
        # Get completed tests for this category
        completed_tests = ABTestVariant.objects.filter(
            status=ABTestVariant.Status.COMPLETED,
            statistical_significance__lt=0.05  # Statistically significant
        )
        
        for test in completed_tests:
            if test.winning_variant and test.results_data:
                winning_data = test.results_data['variants'].get(test.winning_variant, {})
                
                suggestions.append({
                    'type': 'ab_test_winner',
                    'test_name': test.name,
                    'winning_variant': test.winning_variant,
                    'improvement': self._calculate_improvement(test.results_data),
                    'recommendation': f"Implement {test.winning_variant} variant from {test.name}",
                    'confidence': 'high' if test.statistical_significance < 0.01 else 'medium'
                })
        
        return suggestions
    
    def _calculate_improvement(self, results_data: Dict) -> Dict[str, float]:
        """
        Calculate improvement percentage from A/B test results.
        """
        variants = results_data.get('variants', {})
        if len(variants) < 2:
            return {}
        
        # Compare winning variant to control
        winning_variant = results_data.get('winning_variant')
        if not winning_variant or winning_variant not in variants:
            return {}
        
        control_variant = 'control' if 'control' in variants else list(variants.keys())[0]
        if control_variant == winning_variant:
            control_variant = [k for k in variants.keys() if k != winning_variant][0]
        
        winning_data = variants[winning_variant]
        control_data = variants[control_variant]
        
        improvements = {}
        
        for metric in ['conversion_rate', 'avg_completion_rate']:
            if metric in winning_data and metric in control_data:
                control_value = control_data[metric]
                winning_value = winning_data[metric]
                
                if control_value > 0:
                    improvement = ((winning_value - control_value) / control_value) * 100
                    improvements[metric] = round(improvement, 2)
        
        return improvements