"""
Unit tests for Feature Matching Engine.
Tests the core functionality of feature-based policy comparison.
"""

import unittest
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from .feature_matching_engine import FeatureMatchingEngine, FeatureComparisonResult
from .feature_comparison_manager import FeatureComparisonManager
from .match_explanations import MatchExplanationGenerator
from policies.models import BasePolicy, PolicyFeatures

User = get_user_model()


class FeatureMatchingEngineTest(TestCase):
    """Test cases for FeatureMatchingEngine."""
    
    def setUp(self):
        """Set up test data."""
        self.health_engine = FeatureMatchingEngine('HEALTH')
        self.funeral_engine = FeatureMatchingEngine('FUNERAL')
        
        # Create mock policy with features
        self.mock_policy = Mock(spec=BasePolicy)
        self.mock_policy.id = 1
        self.mock_policy.name = "Test Health Policy"
        
        # Create mock policy features
        self.mock_health_features = Mock(spec=PolicyFeatures)
        self.mock_health_features.insurance_type = 'HEALTH'
        self.mock_health_features.annual_limit_per_member = Decimal('100000.00')
        self.mock_health_features.monthly_household_income = Decimal('5000.00')
        self.mock_health_features.in_hospital_benefit = True
        self.mock_health_features.out_hospital_benefit = True
        self.mock_health_features.chronic_medication_availability = False
        
        self.mock_policy.get_policy_features.return_value = self.mock_health_features
    
    def test_engine_initialization(self):
        """Test engine initialization with different insurance types."""
        # Valid types
        health_engine = FeatureMatchingEngine('health')
        self.assertEqual(health_engine.insurance_type, 'HEALTH')
        
        funeral_engine = FeatureMatchingEngine('FUNERAL')
        self.assertEqual(funeral_engine.insurance_type, 'FUNERAL')
        
        # Invalid type should raise error
        with self.assertRaises(ValueError):
            FeatureMatchingEngine('INVALID')
    
    def test_health_policy_compatibility_calculation(self):
        """Test compatibility calculation for health policies."""
        user_preferences = {
            'annual_limit_per_member': Decimal('80000.00'),  # Policy exceeds this
            'monthly_household_income': Decimal('6000.00'),  # User exceeds requirement
            'in_hospital_benefit': True,  # Matches
            'out_hospital_benefit': True,  # Matches
            'chronic_medication_availability': False   # Matches
        }
        
        result = self.health_engine.calculate_policy_compatibility(
            self.mock_policy, user_preferences
        )
        
        # Check result structure
        self.assertIn('overall_score', result)
        self.assertIn('feature_scores', result)
        self.assertIn('matches', result)
        self.assertIn('mismatches', result)
        self.assertIn('explanation', result)
        
        # Should have high score due to good matches
        self.assertGreater(result['overall_score'], 0.7)
        
        # Should have matches for boolean features
        self.assertGreater(len(result['matches']), 0)
    
    def test_funeral_policy_compatibility_calculation(self):
        """Test compatibility calculation for funeral policies."""
        # Create mock funeral policy
        mock_funeral_policy = Mock(spec=BasePolicy)
        mock_funeral_policy.id = 2
        mock_funeral_policy.name = "Test Funeral Policy"
        
        mock_funeral_features = Mock(spec=PolicyFeatures)
        mock_funeral_features.insurance_type = 'FUNERAL'
        mock_funeral_features.cover_amount = Decimal('50000.00')
        mock_funeral_features.monthly_net_income = Decimal('3000.00')
        mock_funeral_features.marital_status_requirement = 'any'
        mock_funeral_features.gender_requirement = 'any'
        
        mock_funeral_policy.get_policy_features.return_value = mock_funeral_features
        
        user_preferences = {
            'cover_amount': Decimal('45000.00'),  # Policy exceeds
            'monthly_net_income': Decimal('4000.00'),  # User exceeds requirement
            'marital_status_requirement': 'single',  # Policy accepts any
            'gender_requirement': 'male'  # Policy accepts any
        }
        
        result = self.funeral_engine.calculate_policy_compatibility(
            mock_funeral_policy, user_preferences
        )
        
        # Should have good score
        self.assertGreater(result['overall_score'], 0.6)
        self.assertEqual(result['insurance_type'], 'FUNERAL')
    
    def test_boolean_feature_scoring(self):
        """Test scoring of boolean features."""
        # Test exact matches
        score = self.health_engine._calculate_feature_score(
            'in_hospital_benefit', True, True
        )
        self.assertEqual(score, 1.0)
        
        score = self.health_engine._calculate_feature_score(
            'in_hospital_benefit', False, False
        )
        self.assertEqual(score, 1.0)
        
        # Test mismatches
        score = self.health_engine._calculate_feature_score(
            'in_hospital_benefit', True, False
        )
        self.assertEqual(score, 0.0)
    
    def test_numeric_feature_scoring(self):
        """Test scoring of numeric features."""
        # Test coverage amount (higher is better)
        score = self.health_engine._score_numeric_feature(
            'annual_limit_per_member', 100000, 80000
        )
        self.assertEqual(score, 1.0)  # Policy exceeds preference
        
        score = self.health_engine._score_numeric_feature(
            'annual_limit_per_member', 60000, 80000
        )
        self.assertEqual(score, 0.75)  # Policy is 75% of preference
        
        # Test income requirement (lower is better for policy)
        score = self.health_engine._score_numeric_feature(
            'monthly_household_income', 4000, 5000
        )
        self.assertEqual(score, 1.0)  # User exceeds requirement
        
        score = self.health_engine._score_numeric_feature(
            'monthly_household_income', 6000, 5000
        )
        self.assertLess(score, 1.0)  # User doesn't meet requirement
    
    def test_string_feature_scoring(self):
        """Test scoring of string features."""
        # Test exact match
        score = self.health_engine._score_string_feature(
            'marital_status_requirement', 'single', 'single'
        )
        self.assertEqual(score, 1.0)
        
        # Test case insensitive
        score = self.health_engine._score_string_feature(
            'marital_status_requirement', 'Single', 'SINGLE'
        )
        self.assertEqual(score, 1.0)
        
        # Test no match
        score = self.health_engine._score_string_feature(
            'marital_status_requirement', 'married', 'single'
        )
        self.assertEqual(score, 0.0)
    
    def test_overall_score_calculation(self):
        """Test overall score calculation with weights."""
        feature_scores = {
            'annual_limit_per_member': 1.0,
            'monthly_household_income': 0.8,
            'in_hospital_benefit': 1.0,
            'out_hospital_benefit': 0.6,
            'chronic_medication_availability': 0.0
        }
        
        overall_score = self.health_engine._calculate_overall_score(feature_scores)
        
        # Should be weighted average
        self.assertGreater(overall_score, 0.0)
        self.assertLessEqual(overall_score, 1.0)
        
        # More important features should have higher impact
        weights = self.health_engine._get_feature_weights()
        self.assertGreater(weights['annual_limit_per_member'], weights['chronic_medication_availability'])
    
    def test_incompatible_policy_type(self):
        """Test handling of incompatible policy types."""
        # Try to use funeral engine with health policy
        result = self.funeral_engine.calculate_policy_compatibility(
            self.mock_policy, {}
        )
        
        self.assertEqual(result['overall_score'], 0.0)
        self.assertIn('Policy type does not match', result['explanation'])
    
    def test_missing_policy_features(self):
        """Test handling of policies without features."""
        mock_policy_no_features = Mock(spec=BasePolicy)
        mock_policy_no_features.get_policy_features.return_value = None
        
        result = self.health_engine.calculate_policy_compatibility(
            mock_policy_no_features, {}
        )
        
        self.assertEqual(result['overall_score'], 0.0)
    
    def test_empty_user_preferences(self):
        """Test handling of empty user preferences."""
        result = self.health_engine.calculate_policy_compatibility(
            self.mock_policy, {}
        )
        
        # Should return valid result even with no preferences
        self.assertIn('overall_score', result)
        self.assertEqual(result['overall_score'], 0.0)  # No features to compare


class FeatureComparisonResultTest(TestCase):
    """Test cases for FeatureComparisonResult."""
    
    def setUp(self):
        """Set up test data."""
        self.mock_policy = Mock(spec=BasePolicy)
        self.mock_policy.id = 1
        self.mock_policy.name = "Test Policy"
        
        self.compatibility_data = {
            'overall_score': 0.85,
            'feature_scores': {'feature1': 0.9, 'feature2': 0.8},
            'matches': [
                {'feature': 'Feature 1', 'score': 0.9, 'match_type': 'excellent'},
                {'feature': 'Feature 2', 'score': 0.8, 'match_type': 'good'}
            ],
            'mismatches': [
                {'feature': 'Feature 3', 'score': 0.3, 'mismatch_severity': 'moderate'}
            ],
            'explanation': 'Very good match',
            'insurance_type': 'HEALTH',
            'total_features_compared': 3
        }
        
        self.result = FeatureComparisonResult(self.mock_policy, self.compatibility_data)
    
    def test_compatibility_category(self):
        """Test compatibility category assignment."""
        self.assertEqual(self.result.get_compatibility_category(), 'EXCELLENT_MATCH')
        
        # Test other categories
        low_score_data = self.compatibility_data.copy()
        low_score_data['overall_score'] = 0.3
        low_result = FeatureComparisonResult(self.mock_policy, low_score_data)
        self.assertEqual(low_result.get_compatibility_category(), 'POOR_MATCH')
    
    def test_recommendation_strength(self):
        """Test recommendation strength calculation."""
        self.assertEqual(self.result.get_recommendation_strength(), 'Strongly Recommended')
    
    def test_top_matches(self):
        """Test getting top matches."""
        top_matches = self.result.get_top_matches(2)
        self.assertEqual(len(top_matches), 2)
        self.assertEqual(top_matches[0]['feature'], 'Feature 1')  # Highest score first
    
    def test_major_concerns(self):
        """Test getting major concerns."""
        concerns = self.result.get_major_concerns()
        self.assertEqual(len(concerns), 1)
        self.assertEqual(concerns[0]['feature'], 'Feature 3')
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        result_dict = self.result.to_dict()
        
        self.assertIn('policy_id', result_dict)
        self.assertIn('overall_score', result_dict)
        self.assertIn('compatibility_category', result_dict)
        self.assertEqual(result_dict['policy_id'], 1)
        self.assertEqual(result_dict['overall_score'], 0.85)


class FeatureComparisonManagerTest(TestCase):
    """Test cases for FeatureComparisonManager."""
    
    def setUp(self):
        """Set up test data."""
        self.manager = FeatureComparisonManager('HEALTH')
        
        # Create mock policies
        self.mock_policies = []
        for i in range(3):
            policy = Mock(spec=BasePolicy)
            policy.id = i + 1
            policy.name = f"Test Policy {i + 1}"
            
            features = Mock(spec=PolicyFeatures)
            features.insurance_type = 'HEALTH'
            features.annual_limit_per_member = Decimal(str(50000 + i * 25000))
            features.monthly_household_income = Decimal('5000.00')
            features.in_hospital_benefit = True
            features.out_hospital_benefit = i % 2 == 0  # Alternate
            features.chronic_medication_availability = i == 0  # Only first policy
            
            # Add base_premium attribute for ranking
            policy.base_premium = 1000 + i * 200
            
            policy.get_policy_features.return_value = features
            self.mock_policies.append(policy)
    
    def test_policy_filtering(self):
        """Test filtering of compatible policies."""
        # Add incompatible policy
        incompatible_policy = Mock(spec=BasePolicy)
        incompatible_features = Mock(spec=PolicyFeatures)
        incompatible_features.insurance_type = 'FUNERAL'
        incompatible_policy.get_policy_features.return_value = incompatible_features
        
        all_policies = self.mock_policies + [incompatible_policy]
        compatible = self.manager._filter_compatible_policies(all_policies)
        
        self.assertEqual(len(compatible), 3)  # Only health policies
    
    def test_policy_comparison(self):
        """Test complete policy comparison workflow."""
        user_preferences = {
            'annual_limit_per_member': Decimal('75000.00'),
            'monthly_household_income': Decimal('6000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': True,
            'chronic_medication_availability': True
        }
        
        result = self.manager.compare_policies_by_features(
            self.mock_policies, user_preferences
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_policies_compared'], 3)
        self.assertIn('results', result)
        self.assertIn('insights', result)
        self.assertIn('recommendations', result)
        
        # Results should be ranked
        results = result['results']
        self.assertGreaterEqual(len(results), 2)
        
        # First result should have highest score
        if len(results) > 1:
            self.assertGreaterEqual(results[0].overall_score, results[1].overall_score)
    
    def test_insufficient_policies(self):
        """Test handling of insufficient policies."""
        result = self.manager.compare_policies_by_features([], {})
        self.assertIn('error', result)
        
        result = self.manager.compare_policies_by_features([self.mock_policies[0]], {})
        self.assertIn('error', result)
    
    def test_insights_generation(self):
        """Test generation of comparison insights."""
        # Create mock results
        mock_results = []
        for i, policy in enumerate(self.mock_policies):
            compatibility_data = {
                'overall_score': 0.8 - i * 0.1,
                'feature_scores': {'feature1': 0.9 - i * 0.1},
                'matches': [{'feature': f'Feature {i}', 'score': 0.9 - i * 0.1}],
                'mismatches': [],
                'explanation': 'Good match',
                'insurance_type': 'HEALTH',
                'total_features_compared': 1
            }
            result = FeatureComparisonResult(policy, compatibility_data)
            mock_results.append(result)
        
        insights = self.manager._generate_comparison_insights(mock_results, {})
        
        self.assertIn('total_policies', insights)
        self.assertIn('score_distribution', insights)
        self.assertIn('feature_analysis', insights)
        self.assertEqual(insights['total_policies'], 3)


class MatchExplanationGeneratorTest(TestCase):
    """Test cases for MatchExplanationGenerator."""
    
    def setUp(self):
        """Set up test data."""
        self.generator = MatchExplanationGenerator('HEALTH')
        
        self.mock_policy = Mock(spec=BasePolicy)
        self.mock_policy.name = "Test Policy"
        
        self.compatibility_data = {
            'overall_score': 0.85,
            'feature_scores': {'feature1': 0.9},
            'matches': [
                {
                    'feature': 'Annual Limit per Member', 
                    'score': 0.9, 
                    'match_type': 'excellent',
                    'user_preference': 'R80,000',
                    'policy_value': 'R100,000'
                }
            ],
            'mismatches': [
                {
                    'feature': 'Chronic Medication Coverage', 
                    'score': 0.2, 
                    'mismatch_severity': 'major',
                    'user_preference': 'Yes',
                    'policy_value': 'No'
                }
            ],
            'explanation': 'Very good match',
            'insurance_type': 'HEALTH',
            'total_features_compared': 2
        }
    
    def test_overall_assessment_generation(self):
        """Test overall assessment generation."""
        assessment = self.generator._generate_overall_assessment(0.85)
        
        self.assertIn('category', assessment)
        self.assertIn('description', assessment)
        self.assertIn('confidence_level', assessment)
        self.assertEqual(assessment['category'], 'Very Good Match')
    
    def test_recommendation_reasons_generation(self):
        """Test recommendation reasons generation."""
        matches = [
            {'feature': 'Annual Limit per Member', 'match_type': 'excellent'},
            {'feature': 'In-Hospital Benefits', 'match_type': 'good'}
        ]
        
        reasons = self.generator._generate_recommendation_reasons(matches, 0.85)
        
        self.assertGreater(len(reasons), 0)
        self.assertIsInstance(reasons[0], str)
    
    def test_concern_explanations_generation(self):
        """Test concern explanations generation."""
        mismatches = [
            {
                'feature': 'Chronic Medication Coverage',
                'user_preference': 'Yes',
                'policy_value': 'No',
                'mismatch_severity': 'major'
            }
        ]
        
        concerns = self.generator._generate_concern_explanations(mismatches)
        
        self.assertEqual(len(concerns), 1)
        self.assertIn('feature', concerns[0])
        self.assertIn('severity', concerns[0])
        self.assertIn('explanation', concerns[0])
    
    def test_detailed_explanation_generation(self):
        """Test complete detailed explanation generation."""
        explanation = self.generator.generate_detailed_explanation(
            self.mock_policy, self.compatibility_data, {}
        )
        
        self.assertIn('overall_assessment', explanation)
        self.assertIn('why_recommended', explanation)
        self.assertIn('potential_concerns', explanation)
        self.assertIn('feature_breakdown', explanation)
        self.assertIn('next_steps', explanation)


if __name__ == '__main__':
    unittest.main()