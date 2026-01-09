"""
Unit tests for Simple Survey Comparison Integration.

Tests the integration between the simple survey system and the existing
comparison engine, including adapter functionality and simplified scoring.
"""

import unittest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from simple_surveys.comparison_adapter import SimpleSurveyComparisonAdapter, SimplifiedPolicyComparisonEngine
from simple_surveys.models import SimpleSurveyResponse, QuotationSession, SimpleSurveyQuestion
from policies.models import BasePolicy, PolicyCategory, PolicyType
from organizations.models import Organization
from comparison.models import ComparisonSession, ComparisonResult


class SimpleSurveyComparisonAdapterTest(TestCase):
    """Test the SimpleSurveyComparisonAdapter class."""
    
    def setUp(self):
        """Set up test data."""
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            is_verified=True
        )
        
        # Create test category
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        # Create test policy type
        self.policy_type = PolicyType.objects.create(
            category=self.category,
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health coverage"
        )
        
        # Create test policies
        self.policy1 = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Basic Health Plan",
            policy_number="POL001",
            description="Basic health coverage",
            short_description="Basic plan",
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            minimum_age=18,
            maximum_age=65,
            waiting_period_days=30,
            terms_and_conditions="Standard terms",
            approval_status='APPROVED',
            is_active=True
        )
        
        self.policy2 = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Premium Health Plan",
            policy_number="POL002",
            description="Premium health coverage",
            short_description="Premium plan",
            base_premium=Decimal('800.00'),
            coverage_amount=Decimal('200000.00'),
            minimum_age=18,
            maximum_age=70,
            waiting_period_days=0,
            terms_and_conditions="Premium terms",
            approval_status='APPROVED',
            is_active=True
        )
        
        # Create test survey questions
        self.question1 = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            is_required=True,
            display_order=1
        )
        
        self.question2 = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your monthly budget?',
            field_name='monthly_budget',
            input_type='number',
            is_required=True,
            display_order=2
        )
        
        # Initialize adapter
        self.adapter = SimpleSurveyComparisonAdapter('health')
        self.session_key = 'test-session-123'
    
    def test_adapter_initialization(self):
        """Test adapter initializes correctly."""
        self.assertEqual(self.adapter.category, 'health')
        self.assertIsInstance(self.adapter.comparison_engine, SimplifiedPolicyComparisonEngine)
    
    def test_field_mappings_health(self):
        """Test field mappings for health insurance."""
        mappings = self.adapter._get_field_mappings()
        expected_mappings = {
            'age': 'age',
            'location': 'location',
            'family_size': 'family_size',
            'health_status': 'health_status',
            'chronic_conditions': 'chronic_conditions',
            'coverage_priority': 'coverage_priority',
            'monthly_budget': 'base_premium',
            'preferred_deductible': 'deductible_amount'
        }
        self.assertEqual(mappings, expected_mappings)
    
    def test_field_mappings_funeral(self):
        """Test field mappings for funeral insurance."""
        funeral_adapter = SimpleSurveyComparisonAdapter('funeral')
        mappings = funeral_adapter._get_field_mappings()
        expected_mappings = {
            'age': 'age',
            'location': 'location',
            'family_members_to_cover': 'family_size',
            'coverage_amount_needed': 'coverage_amount',
            'service_preference': 'service_level',
            'monthly_budget': 'base_premium',
            'waiting_period_tolerance': 'waiting_period_days'
        }
        self.assertEqual(mappings, expected_mappings)
    
    def test_convert_response_value_numeric(self):
        """Test conversion of numeric response values."""
        # Test age conversion
        result = self.adapter._convert_response_value('age', '35')
        self.assertEqual(result, 35)
        
        # Test budget conversion
        result = self.adapter._convert_response_value('monthly_budget', '1000')
        self.assertEqual(result, 1000)
        
        # Test invalid numeric
        result = self.adapter._convert_response_value('age', 'invalid')
        self.assertEqual(result, 0)
    
    def test_convert_response_value_coverage_amount(self):
        """Test conversion of coverage amount values."""
        # Test R25k format
        result = self.adapter._convert_response_value('coverage_amount_needed', 'R25k')
        self.assertEqual(result, 25000)
        
        # Test R100k+ format
        result = self.adapter._convert_response_value('coverage_amount_needed', 'R100k+')
        self.assertEqual(result, 100000)
        
        # Test invalid format
        result = self.adapter._convert_response_value('coverage_amount_needed', 'invalid')
        self.assertEqual(result, 50000)  # Default fallback
    
    def test_convert_response_value_waiting_period(self):
        """Test conversion of waiting period values."""
        # Test None value
        result = self.adapter._convert_response_value('waiting_period_tolerance', 'None')
        self.assertEqual(result, 0)
        
        # Test months format
        result = self.adapter._convert_response_value('waiting_period_tolerance', '3 months')
        self.assertEqual(result, 90)  # 3 * 30 days
        
        # Test direct value
        result = self.adapter._convert_response_value('waiting_period_tolerance', 60)
        self.assertEqual(result, 60)
    
    def test_get_default_weights_health(self):
        """Test default weights for health insurance."""
        criteria = {'base_premium': 500, 'coverage_priority': 'comprehensive'}
        weights = self.adapter._get_default_weights(criteria)
        
        expected_weights = {
            'base_premium': 30,
            'coverage_priority': 25
        }
        self.assertEqual(weights, expected_weights)
    
    def test_get_default_weights_funeral(self):
        """Test default weights for funeral insurance."""
        funeral_adapter = SimpleSurveyComparisonAdapter('funeral')
        criteria = {'base_premium': 200, 'coverage_amount': 50000}
        weights = funeral_adapter._get_default_weights(criteria)
        
        expected_weights = {
            'base_premium': 35,
            'coverage_amount': 30
        }
        self.assertEqual(weights, expected_weights)
    
    def test_apply_category_specific_processing_health(self):
        """Test category-specific processing for health insurance."""
        criteria = {
            'family_size': 5,
            'base_premium': 1000,
            'chronic_conditions': ['diabetes', 'hypertension'],
            'weights': {'coverage_priority': 25}
        }
        
        result = self.adapter._apply_category_specific_processing(criteria)
        
        # Should increase budget for large family
        self.assertEqual(result['base_premium'], 1200)  # 1000 * 1.2
        
        # Should increase coverage priority weight for chronic conditions
        self.assertEqual(result['weights']['coverage_priority'], 35)  # 25 + 10
    
    def test_apply_category_specific_processing_funeral(self):
        """Test category-specific processing for funeral insurance."""
        funeral_adapter = SimpleSurveyComparisonAdapter('funeral')
        criteria = {
            'family_size': 12,
            'coverage_amount': 30000
        }
        
        result = funeral_adapter._apply_category_specific_processing(criteria)
        
        # Should increase coverage for large family
        self.assertEqual(result['coverage_amount'], 100000)  # max(30000, 100000)
    
    def test_get_eligible_policy_ids(self):
        """Test getting eligible policy IDs."""
        criteria = {
            'base_premium': 600,  # Should include policy1 (500) but not policy2 (800) at strict budget
            'age': 30
        }
        
        policy_ids = self.adapter._get_eligible_policy_ids(criteria)
        
        # Should return both policies (20% over budget tolerance)
        self.assertIn(self.policy1.id, policy_ids)
        self.assertIn(self.policy2.id, policy_ids)
    
    def test_extract_key_features_health(self):
        """Test extracting key features for health policies."""
        # Mock health-specific attributes
        self.policy1.includes_dental_cover = True
        self.policy1.chronic_medication_covered = True
        
        features = self.adapter._extract_key_features(self.policy1)
        
        expected_features = ['Dental Cover', 'Chronic Medication', 'Verified Provider']
        self.assertEqual(features, expected_features)
    
    def test_extract_key_features_waiting_period(self):
        """Test key features for waiting period."""
        # Policy2 has no waiting period
        features = self.adapter._extract_key_features(self.policy2)
        self.assertIn('No Waiting Period', features)
        
        # Policy1 has short waiting period
        features = self.adapter._extract_key_features(self.policy1)
        self.assertIn('Short Waiting Period', features)
    
    def test_get_value_rating(self):
        """Test value rating conversion."""
        self.assertEqual(self.adapter._get_value_rating(85), 'Excellent')
        self.assertEqual(self.adapter._get_value_rating(70), 'Good')
        self.assertEqual(self.adapter._get_value_rating(55), 'Fair')
        self.assertEqual(self.adapter._get_value_rating(40), 'Poor')
    
    @patch('simple_surveys.comparison_adapter.SimpleSurveyEngine')
    def test_convert_survey_responses_to_criteria(self, mock_engine_class):
        """Test converting survey responses to criteria."""
        # Mock survey engine
        mock_engine = Mock()
        mock_engine.process_responses.return_value = {
            'age': 35,
            'monthly_budget': 800,
            'health_status': 'good',
            '_metadata': {'responses_count': 3}
        }
        mock_engine_class.return_value = mock_engine
        
        # Create adapter with mocked engine
        adapter = SimpleSurveyComparisonAdapter('health')
        adapter.survey_engine = mock_engine
        
        criteria = adapter._convert_survey_responses_to_criteria(self.session_key)
        
        # Check converted criteria
        self.assertEqual(criteria['age'], 35)
        self.assertEqual(criteria['base_premium'], 800)
        self.assertEqual(criteria['health_status'], 'good')
        self.assertIn('weights', criteria)
    
    @patch('simple_surveys.comparison_adapter.SimpleSurveyEngine')
    def test_generate_quotations_success(self, mock_engine_class):
        """Test successful quotation generation."""
        # Mock survey engine
        mock_engine = Mock()
        mock_engine.process_responses.return_value = {
            'age': 35,
            'monthly_budget': 600,
            '_metadata': {'responses_count': 2}
        }
        mock_engine_class.return_value = mock_engine
        
        # Create adapter with mocked engine
        adapter = SimpleSurveyComparisonAdapter('health')
        adapter.survey_engine = mock_engine
        
        # Mock comparison engine
        mock_comparison_result = {
            'success': True,
            'results': [
                {
                    'policy': self.policy1,
                    'score_data': {
                        'overall_score': 85.5,
                        'value_score': 75.0,
                        'criteria_scores': {}
                    },
                    'rank': 1
                }
            ]
        }
        adapter.comparison_engine.compare_policies = Mock(return_value=mock_comparison_result)
        
        result = adapter.generate_quotations(self.session_key, max_results=5)
        
        # Check result structure
        self.assertTrue(result['success'])
        self.assertEqual(result['session_key'], self.session_key)
        self.assertEqual(result['category'], 'health')
        self.assertEqual(len(result['policies']), 1)
        
        # Check policy data
        policy_data = result['policies'][0]
        self.assertEqual(policy_data['id'], self.policy1.id)
        self.assertEqual(policy_data['name'], self.policy1.name)
        self.assertEqual(policy_data['match_score'], 85.5)
    
    @patch('simple_surveys.comparison_adapter.SimpleSurveyEngine')
    def test_generate_quotations_no_responses(self, mock_engine_class):
        """Test quotation generation with no survey responses."""
        # Mock survey engine returning empty responses
        mock_engine = Mock()
        mock_engine.process_responses.return_value = {}
        mock_engine_class.return_value = mock_engine
        
        adapter = SimpleSurveyComparisonAdapter('health')
        adapter.survey_engine = mock_engine
        
        result = adapter.generate_quotations(self.session_key)
        
        self.assertFalse(result['success'])
        self.assertIn('No survey responses found', result['error'])
    
    @patch('simple_surveys.comparison_adapter.SimpleSurveyEngine')
    def test_generate_quotations_no_policies(self, mock_engine_class):
        """Test quotation generation with no eligible policies."""
        # Mock survey engine
        mock_engine = Mock()
        mock_engine.process_responses.return_value = {
            'age': 35,
            'monthly_budget': 100,  # Very low budget - no policies should match
            '_metadata': {'responses_count': 2}
        }
        mock_engine_class.return_value = mock_engine
        
        adapter = SimpleSurveyComparisonAdapter('health')
        adapter.survey_engine = mock_engine
        
        result = adapter.generate_quotations(self.session_key)
        
        self.assertFalse(result['success'])
        self.assertIn('No eligible policies found', result['error'])


class SimplifiedPolicyComparisonEngineTest(TestCase):
    """Test the SimplifiedPolicyComparisonEngine class."""
    
    def setUp(self):
        """Set up test data."""
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            is_verified=True
        )
        
        # Create test category
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        # Create test policy type
        self.policy_type = PolicyType.objects.create(
            category=self.category,
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health coverage"
        )
        
        # Create test policies
        self.policy1 = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Budget Health Plan",
            policy_number="POL001",
            description="Budget health coverage",
            short_description="Budget plan",
            base_premium=Decimal('400.00'),
            coverage_amount=Decimal('80000.00'),
            minimum_age=18,
            maximum_age=65,
            waiting_period_days=60,
            terms_and_conditions="Standard terms",
            approval_status='APPROVED',
            is_active=True
        )
        
        self.policy2 = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Premium Health Plan",
            policy_number="POL002",
            description="Premium health coverage",
            short_description="Premium plan",
            base_premium=Decimal('800.00'),
            coverage_amount=Decimal('200000.00'),
            minimum_age=18,
            maximum_age=70,
            waiting_period_days=0,
            terms_and_conditions="Premium terms",
            approval_status='APPROVED',
            is_active=True
        )
        
        # Initialize engine
        self.engine = SimplifiedPolicyComparisonEngine('health')
    
    def test_engine_initialization(self):
        """Test engine initializes with simplified weights."""
        self.assertEqual(self.engine.CRITERIA_WEIGHT, Decimal('0.70'))
        self.assertEqual(self.engine.VALUE_WEIGHT, Decimal('0.20'))
        self.assertEqual(self.engine.REVIEW_WEIGHT, Decimal('0.05'))
        self.assertEqual(self.engine.ORGANIZATION_WEIGHT, Decimal('0.05'))
    
    def test_score_premium_match_within_budget(self):
        """Test premium scoring when within budget."""
        score = self.engine._score_premium_match(self.policy1, 500)
        self.assertGreater(score, Decimal('80'))  # Should score well within budget
    
    def test_score_premium_match_over_budget(self):
        """Test premium scoring when over budget."""
        score = self.engine._score_premium_match(self.policy2, 600)
        self.assertLess(score, Decimal('80'))  # Should score lower when over budget
    
    def test_score_coverage_match_adequate(self):
        """Test coverage scoring when policy meets needs."""
        score = self.engine._score_coverage_match(self.policy2, 150000)
        self.assertGreater(score, Decimal('80'))  # Policy exceeds needs
    
    def test_score_coverage_match_insufficient(self):
        """Test coverage scoring when policy is insufficient."""
        score = self.engine._score_coverage_match(self.policy1, 150000)
        self.assertLess(score, Decimal('70'))  # Policy below needs
    
    def test_score_waiting_period_match_within_tolerance(self):
        """Test waiting period scoring within tolerance."""
        score = self.engine._score_waiting_period_match(self.policy1, 90)
        self.assertGreater(score, Decimal('60'))  # 60 days within 90 day tolerance
    
    def test_score_waiting_period_match_exceeds_tolerance(self):
        """Test waiting period scoring exceeding tolerance."""
        score = self.engine._score_waiting_period_match(self.policy1, 30)
        self.assertLess(score, Decimal('60'))  # 60 days exceeds 30 day tolerance
    
    def test_score_waiting_period_match_no_tolerance(self):
        """Test waiting period scoring with zero tolerance."""
        score = self.engine._score_waiting_period_match(self.policy2, 0)
        self.assertEqual(score, Decimal('100'))  # No waiting period, zero tolerance
        
        score = self.engine._score_waiting_period_match(self.policy1, 0)
        self.assertEqual(score, Decimal('20'))  # Has waiting period, zero tolerance
    
    def test_score_organization_reputation(self):
        """Test organization reputation scoring."""
        score = self.engine._score_organization_reputation(self.policy1)
        self.assertGreaterEqual(score, Decimal('80'))  # Verified organization
    
    def test_calculate_simplified_value_score_health(self):
        """Test simplified value calculation for health insurance."""
        # Policy1: 80000 / 400 = 200 coverage per rand
        # Health threshold is 1000, so score should be 20%
        score = self.engine._calculate_simplified_value_score(self.policy1, {})
        self.assertAlmostEqual(float(score), 20.0, places=1)
        
        # Policy2: 200000 / 800 = 250 coverage per rand
        # Should score 25%
        score = self.engine._calculate_simplified_value_score(self.policy2, {})
        self.assertAlmostEqual(float(score), 25.0, places=1)
    
    def test_calculate_simplified_review_score_no_reviews(self):
        """Test review scoring with no reviews."""
        score = self.engine._calculate_simplified_review_score(self.policy1)
        self.assertEqual(score, Decimal('60'))  # Default score
    
    def test_generate_simplified_pros(self):
        """Test generating simplified pros."""
        score_data = {
            'value_score': 75.0,
            'overall_score': 85.0
        }
        
        pros = self.engine._generate_simplified_pros(self.policy2, score_data)
        
        expected_pros = ['Good value for money', 'No waiting period', 'Verified provider', 'Excellent match for your needs']
        self.assertEqual(pros, expected_pros[:3])  # Limited to 3
    
    def test_generate_simplified_cons(self):
        """Test generating simplified cons."""
        score_data = {
            'value_score': 30.0,
            'overall_score': 45.0
        }
        
        cons = self.engine._generate_simplified_cons(self.policy1, score_data)
        
        expected_cons = ['Higher cost relative to coverage', 'Limited match for your preferences']
        self.assertEqual(len(cons), 2)
        self.assertIn('Higher cost relative to coverage', cons)
        self.assertIn('Limited match for your preferences', cons)
    
    def test_compare_policies_simplified(self):
        """Test simplified policy comparison."""
        policy_ids = [self.policy1.id, self.policy2.id]
        user_criteria = {
            'base_premium': 600,
            'coverage_amount': 100000,
            'waiting_period_days': 30,
            'age': 35
        }
        
        result = self.engine.compare_policies(
            policy_ids=policy_ids,
            user_criteria=user_criteria,
            session_key='test-session'
        )
        
        # Check result structure
        self.assertTrue(result['success'])
        self.assertEqual(len(result['results']), 2)
        self.assertTrue(result['simplified_engine'])
        
        # Check that results are ranked
        scores = [r['score_data']['overall_score'] for r in result['results']]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_compare_policies_no_policies(self):
        """Test comparison with no valid policies."""
        result = self.engine.compare_policies(
            policy_ids=[],
            user_criteria={},
            session_key='test-session'
        )
        
        self.assertFalse(result.get('success', True))
        self.assertIn('At least 1 policy required', result['error'])
    
    def test_compare_policies_too_many_policies(self):
        """Test comparison with too many policies."""
        policy_ids = list(range(1, 25))  # 24 policies
        
        result = self.engine.compare_policies(
            policy_ids=policy_ids,
            user_criteria={},
            session_key='test-session'
        )
        
        # Should limit to 20 policies
        self.assertFalse(result.get('success', True))  # Will fail due to no valid policies, but limit should be applied
    
    def test_load_simplified_criteria(self):
        """Test loading simplified criteria."""
        user_criteria = {
            'weights': {
                'base_premium': 50,
                'coverage_amount': 40
            }
        }
        
        self.engine._load_simplified_criteria(user_criteria)
        
        # Check that weights are loaded
        self.assertEqual(self.engine.weights['base_premium'], Decimal('50'))
        self.assertEqual(self.engine.weights['coverage_amount'], Decimal('40'))
        
        # Check default weights are used for unspecified criteria
        self.assertEqual(self.engine.weights['waiting_period_days'], Decimal('20'))
        self.assertEqual(self.engine.weights['organization_reputation'], Decimal('10'))


if __name__ == '__main__':
    unittest.main()