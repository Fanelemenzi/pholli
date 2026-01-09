"""
Test file for survey-driven comparison engine enhancements.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from policies.models import PolicyCategory, BasePolicy
from organizations.models import Organization
from comparison.models import ComparisonSession
from comparison.engine import PolicyComparisonEngine
from surveys.models import SurveyQuestion, SurveyResponse


class SurveyDrivenComparisonTest(TestCase):
    """Test survey-driven comparison engine functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            is_verified=True,
            is_active=True,
            license_is_expired=False
        )
        
        # Create test category
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health"
        )
        
        # Create test policies
        self.policy1 = BasePolicy.objects.create(
            name="Basic Health Plan",
            organization=self.organization,
            category=self.category,
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            waiting_period_days=30,
            minimum_age=18,
            maximum_age=65,
            is_active=True,
            approval_status='APPROVED'
        )
        
        self.policy2 = BasePolicy.objects.create(
            name="Premium Health Plan",
            organization=self.organization,
            category=self.category,
            base_premium=Decimal('800.00'),
            coverage_amount=Decimal('500000.00'),
            waiting_period_days=60,
            minimum_age=18,
            maximum_age=70,
            is_active=True,
            approval_status='APPROVED'
        )
        
        # Create test user and session
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        
        self.session = ComparisonSession.objects.create(
            user=self.user,
            session_key='test-session-123',
            category=self.category,
            criteria={}
        )
        
        # Create test survey questions
        self.budget_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Budget",
            question_text="What is your monthly budget?",
            question_type="NUMBER",
            field_name="monthly_budget",
            weight_impact=Decimal('80.0'),
            is_required=True,
            display_order=1
        )
        
        self.coverage_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Coverage",
            question_text="How much coverage do you need?",
            question_type="NUMBER",
            field_name="coverage_amount_preference",
            weight_impact=Decimal('70.0'),
            is_required=True,
            display_order=2
        )
    
    def test_basic_survey_scoring(self):
        """Test basic survey-driven scoring functionality."""
        # Create survey responses
        SurveyResponse.objects.create(
            session=self.session,
            question=self.budget_question,
            response_value=600,  # Budget of R600
            confidence_level=5
        )
        
        SurveyResponse.objects.create(
            session=self.session,
            question=self.coverage_question,
            response_value=200000,  # Want R200k coverage
            confidence_level=4
        )
        
        # Create survey context
        survey_context = {
            'user_profile': {
                'confidence_levels': {
                    'monthly_budget': 5,
                    'coverage_amount_preference': 4
                },
                'user_values': {
                    'monthly_budget': 600,
                    'coverage_amount_preference': 200000
                },
                'priorities': {},
                'profile_strength': 0.8
            },
            'criteria': {
                'base_premium': 600,
                'coverage_amount': 200000
            },
            'filters': {
                'base_premium__lte': 660  # 10% over budget
            }
        }
        
        # Test comparison engine
        engine = PolicyComparisonEngine('health')
        
        # Test with survey context
        results = engine.compare_policies(
            policy_ids=[self.policy1.id, self.policy2.id],
            user_criteria={'base_premium': 600, 'coverage_amount': 200000},
            user=self.user,
            session_key='test-session-123',
            survey_context=survey_context
        )
        
        # Verify results
        self.assertTrue(results['success'])
        self.assertEqual(len(results['results']), 2)
        
        # Policy 1 should score better (fits budget, though less coverage)
        policy1_result = next(r for r in results['results'] if r['policy'].id == self.policy1.id)
        policy2_result = next(r for r in results['results'] if r['policy'].id == self.policy2.id)
        
        # Check that survey enhancements were applied
        self.assertIn('survey_enhancements', policy1_result['score_data'])
        self.assertTrue(policy1_result['score_data']['survey_enhancements']['confidence_weighted'])
        
        print(f"Policy 1 score: {policy1_result['score_data']['overall_score']}")
        print(f"Policy 2 score: {policy2_result['score_data']['overall_score']}")
        print(f"Policy 1 pros: {policy1_result['pros']}")
        print(f"Policy 2 cons: {policy2_result['cons']}")
    
    def test_confidence_weighting(self):
        """Test that confidence levels affect scoring."""
        # Test high confidence response
        high_confidence_context = {
            'user_profile': {
                'confidence_levels': {'monthly_budget': 5},
                'user_values': {'monthly_budget': 500},
                'profile_strength': 0.9
            }
        }
        
        # Test low confidence response
        low_confidence_context = {
            'user_profile': {
                'confidence_levels': {'monthly_budget': 2},
                'user_values': {'monthly_budget': 500},
                'profile_strength': 0.4
            }
        }
        
        engine = PolicyComparisonEngine('health')
        
        # Compare with high confidence
        high_conf_results = engine.compare_policies(
            policy_ids=[self.policy1.id],
            user_criteria={'base_premium': 500},
            survey_context=high_confidence_context
        )
        
        # Compare with low confidence
        low_conf_results = engine.compare_policies(
            policy_ids=[self.policy1.id],
            user_criteria={'base_premium': 500},
            survey_context=low_confidence_context
        )
        
        # High confidence should have different scoring than low confidence
        high_score = high_conf_results['results'][0]['score_data']['overall_score']
        low_score = low_conf_results['results'][0]['score_data']['overall_score']
        
        print(f"High confidence score: {high_score}")
        print(f"Low confidence score: {low_score}")
        
        # The scores should be different due to confidence weighting
        self.assertNotEqual(high_score, low_score)
    
    def test_personalized_explanations(self):
        """Test that personalized explanations are generated."""
        survey_context = {
            'user_profile': {
                'confidence_levels': {'monthly_budget': 5},
                'user_values': {'monthly_budget': 600},
                'priorities': {'monthly_budget': 'high'},
                'profile_strength': 0.8
            }
        }
        
        engine = PolicyComparisonEngine('health')
        results = engine.compare_policies(
            policy_ids=[self.policy1.id],
            user_criteria={'base_premium': 600},
            survey_context=survey_context
        )
        
        result = results['results'][0]
        
        # Check for personalization factors
        survey_enhancements = result['score_data'].get('survey_enhancements', {})
        self.assertIn('personalization_factors', survey_enhancements)
        
        # Check that recommendation reason includes personalization
        recommendation_reason = result.get('recommendation_reason', '')
        self.assertIn('personalized', recommendation_reason.lower())
        
        print(f"Personalization factors: {survey_enhancements.get('personalization_factors', [])}")
        print(f"Recommendation reason: {recommendation_reason}")


if __name__ == '__main__':
    # Simple test runner for development
    import django
    import os
    import sys
    
    # Add the project root to Python path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
    django.setup()
    
    # Run a simple test
    test = SurveyDrivenComparisonTest()
    test.setUp()
    
    try:
        test.test_basic_survey_scoring()
        print("✅ Basic survey scoring test passed")
    except Exception as e:
        print(f"❌ Basic survey scoring test failed: {e}")
    
    try:
        test.test_confidence_weighting()
        print("✅ Confidence weighting test passed")
    except Exception as e:
        print(f"❌ Confidence weighting test failed: {e}")
    
    try:
        test.test_personalized_explanations()
        print("✅ Personalized explanations test passed")
    except Exception as e:
        print(f"❌ Personalized explanations test failed: {e}")