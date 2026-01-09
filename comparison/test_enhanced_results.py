"""
Test script for enhanced results display functionality.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from comparison.models import ComparisonSession, ComparisonResult
from policies.models import PolicyCategory, BasePolicy
from organizations.models import Organization
from surveys.models import SurveyResponse, SurveyQuestion
import json

User = get_user_model()


class EnhancedResultsTestCase(TestCase):
    """Test cases for enhanced results display."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test organization
        from datetime import date, timedelta
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            slug="test-insurance-co",
            description="Test insurance company",
            email="test@insurance.co",
            phone="0123456789",
            address_line1="123 Test Street",
            city="Cape Town",
            state_province="Western Cape",
            postal_code="8000",
            verification_status='VERIFIED',
            is_active=True,
            registration_number="REG123456",
            license_number="LIC123456",
            license_expiry_date=date.today() + timedelta(days=365)
        )
        
        # Create test category
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        # Create test policy type
        from policies.models import PolicyType
        self.policy_type = PolicyType.objects.create(
            category=self.category,
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health insurance"
        )
        
        # Create test policies
        self.policy1 = BasePolicy.objects.create(
            name="Premium Health Plan",
            policy_number="POL001",
            description="Premium health insurance plan",
            short_description="Premium coverage with comprehensive benefits",
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            base_premium=1200.00,
            coverage_amount=500000.00,
            waiting_period_days=30,
            minimum_age=18,
            maximum_age=65,
            is_active=True,
            approval_status='APPROVED'
        )
        
        self.policy2 = BasePolicy.objects.create(
            name="Basic Health Plan",
            policy_number="POL002",
            description="Basic health insurance plan",
            short_description="Affordable basic coverage",
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            base_premium=800.00,
            coverage_amount=200000.00,
            waiting_period_days=90,
            minimum_age=18,
            maximum_age=70,
            is_active=True,
            approval_status='APPROVED'
        )
        
        # Create test session
        self.session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category,
            survey_completed=True,
            survey_completion_percentage=100.00,
            survey_responses_count=10,
            user_profile={
                'priorities': {
                    'monthly_budget': 4,
                    'coverage_amount_preference': 5,
                    'waiting_period_tolerance': 3
                },
                'user_values': {
                    'monthly_budget': 1000,
                    'coverage_amount_preference': 300000,
                    'waiting_period_tolerance': 60
                },
                'confidence_levels': {
                    'monthly_budget': 5,
                    'coverage_amount_preference': 4,
                    'waiting_period_tolerance': 3
                }
            },
            criteria={
                'weights': {
                    'base_premium': 80,
                    'coverage_amount': 90,
                    'waiting_period_days': 60
                }
            }
        )
        
        self.session.policies.set([self.policy1, self.policy2])
        
        # Create test results
        self.result1 = ComparisonResult.objects.create(
            session=self.session,
            policy=self.policy1,
            overall_score=85.5,
            rank=1,
            criteria_scores={
                'criteria_score': 88.0,
                'value_score': 75.0,
                'review_score': 80.0,
                'organization_score': 90.0,
                'criteria_scores': {
                    'base_premium': {'score': 70, 'weight': 80},
                    'coverage_amount': {'score': 95, 'weight': 90},
                    'waiting_period_days': {'score': 85, 'weight': 60}
                },
                'survey_enhancements': {
                    'confidence_weighted': True,
                    'priority_boost': 2.5,
                    'personalization_factors': [
                        'Provides coverage close to your preferred R300,000',
                        'Fits within your budget of R1000/month',
                        'Short waiting period meets your tolerance'
                    ]
                }
            },
            pros=[
                'Excellent coverage amount',
                'Fits within your budget',
                'Short waiting period',
                'Reputable provider'
            ],
            cons=[
                'Higher premium than basic options',
                'Age restrictions apply'
            ],
            recommendation_reason='This policy provides excellent coverage that matches your preferences while staying within your budget constraints.'
        )
        
        self.result2 = ComparisonResult.objects.create(
            session=self.session,
            policy=self.policy2,
            overall_score=72.3,
            rank=2,
            criteria_scores={
                'criteria_score': 70.0,
                'value_score': 85.0,
                'review_score': 75.0,
                'organization_score': 90.0,
                'criteria_scores': {
                    'base_premium': {'score': 90, 'weight': 80},
                    'coverage_amount': {'score': 60, 'weight': 90},
                    'waiting_period_days': {'score': 55, 'weight': 60}
                }
            },
            pros=[
                'Very affordable premium',
                'Good value for money',
                'Reputable provider'
            ],
            cons=[
                'Lower coverage amount',
                'Longer waiting period',
                'Limited benefits'
            ],
            recommendation_reason='A budget-friendly option that provides basic coverage at an affordable price.'
        )
    
    def test_enhanced_results_view(self):
        """Test the enhanced results view loads correctly."""
        url = reverse('comparison:enhanced_results', kwargs={'session_key': 'test-session-123'})
        response = self.client.get(url)
        
        # Print debug info if test fails
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            if hasattr(response, 'url'):
                print(f"Redirect URL: {response.url}")
            print(f"Response content: {response.content.decode()}")
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your Health Insurance Results')
        self.assertContains(response, 'Premium Health Plan')
        self.assertContains(response, 'Basic Health Plan')
        self.assertContains(response, '85.5% Match')
        self.assertContains(response, 'Personalized based on your survey responses')
    
    def test_policy_detail_modal(self):
        """Test the policy detail modal AJAX endpoint."""
        url = reverse('comparison:policy_detail', kwargs={
            'session_key': 'test-session-123',
            'policy_id': self.policy1.id
        })
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['policy']['name'], 'Premium Health Plan')
        self.assertEqual(data['policy']['rank'], 1)
        self.assertIn('personalization_factors', data['policy']['survey_context'])
    
    def test_comparison_matrix_view(self):
        """Test the comparison matrix view."""
        url = reverse('comparison:comparison_matrix', kwargs={'session_key': 'test-session-123'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Side-by-Side Comparison')
        self.assertContains(response, 'Premium Health Plan')
        self.assertContains(response, 'Basic Health Plan')
        self.assertContains(response, 'R1,200')  # Premium
        self.assertContains(response, 'R500,000')  # Coverage
    
    def test_recommendation_categories(self):
        """Test that recommendation categories are generated correctly."""
        from comparison.views import _generate_recommendation_categories
        
        results = [self.result1, self.result2]
        survey_context = {
            'user_profile': self.session.user_profile
        }
        
        recommendations = _generate_recommendation_categories(results, survey_context)
        
        self.assertIn('best_match', recommendations)
        self.assertIn('best_value', recommendations)
        self.assertIn('most_popular', recommendations)
        
        # Best match should be the highest scoring policy
        self.assertEqual(recommendations['best_match']['policy'], self.result1)
        
        # Best value should be the policy with highest value score
        self.assertEqual(recommendations['best_value']['policy'], self.result2)
    
    def test_comparison_insights(self):
        """Test that comparison insights are generated correctly."""
        from comparison.views import _generate_comparison_insights
        
        results = [self.result1, self.result2]
        survey_context = {
            'user_profile': self.session.user_profile
        }
        
        insights = _generate_comparison_insights(results, self.session, survey_context)
        
        self.assertIsInstance(insights, list)
        # Should have at least one insight
        self.assertGreater(len(insights), 0)
    
    def test_survey_based_comparison_detection(self):
        """Test that survey-based comparisons are detected correctly."""
        self.assertTrue(self.session.is_survey_based_comparison())
        
        # Create a non-survey session
        non_survey_session = ComparisonSession.objects.create(
            session_key="non-survey-session",
            category=self.category,
            survey_completed=False
        )
        
        self.assertFalse(non_survey_session.is_survey_based_comparison())
    
    def test_invalid_session_key(self):
        """Test handling of invalid session keys."""
        url = reverse('comparison:enhanced_results', kwargs={'session_key': 'invalid-session'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_session_without_results(self):
        """Test handling of sessions without comparison results."""
        # Create session without results
        empty_session = ComparisonSession.objects.create(
            session_key="empty-session",
            category=self.category
        )
        
        url = reverse('comparison:enhanced_results', kwargs={'session_key': 'empty-session'})
        response = self.client.get(url)
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)


if __name__ == '__main__':
    import django
    import os
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
    django.setup()
    
    # Run tests
    import unittest
    unittest.main()