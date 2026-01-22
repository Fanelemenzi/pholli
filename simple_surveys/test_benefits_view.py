"""
Test for the benefits viewing functionality.
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from policies.models import (
    BasePolicy, PolicyCategory, PolicyType, PolicyFeatures, 
    AdditionalFeatures, Rewards
)
from organizations.models import Organization


class BenefitsViewTestCase(TestCase):
    """Test case for the policy benefits AJAX view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            email="test@insurance.com",
            phone="123-456-7890",
            is_verified=True
        )
        
        # Create test category and type
        self.category = PolicyCategory.objects.create(
            name="Health",
            slug="health",
            description="Health insurance policies"
        )
        
        self.policy_type = PolicyType.objects.create(
            category=self.category,
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health coverage"
        )
        
        # Create test policy
        self.policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Test Health Policy",
            policy_number="TEST001",
            description="Test policy description",
            short_description="Test policy",
            base_premium=500.00,
            coverage_amount=100000.00,
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms",
            is_active=True,
            approval_status=BasePolicy.ApprovalStatus.APPROVED
        )
        
        # Create policy features
        self.policy_features = PolicyFeatures.objects.create(
            policy=self.policy,
            insurance_type='HEALTH',
            annual_limit_per_family=50000.00,
            monthly_household_income=10000.00,
            currently_on_medical_aid=False,
            ambulance_coverage=True,
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        # Create additional features
        self.additional_feature = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Emergency Services",
            description="24/7 emergency medical services",
            coverage_details="Covers emergency room visits, ambulance services, and urgent care",
            icon="bi-hospital",
            is_highlighted=True
        )
        
        # Create rewards
        self.reward = Rewards.objects.create(
            policy=self.policy,
            title="Wellness Cashback",
            description="Get cashback for maintaining healthy lifestyle",
            reward_type='CASHBACK',
            percentage=5.00,
            eligibility_criteria="Complete annual health check-up",
            is_active=True
        )
    
    def test_policy_benefits_ajax_success(self):
        """Test successful benefits data retrieval."""
        url = reverse('simple_surveys:policy_benefits', kwargs={'policy_id': self.policy.id})
        
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check policy data
        policy_data = data['policy']
        self.assertEqual(policy_data['name'], 'Test Health Policy')
        self.assertEqual(policy_data['organization'], 'Test Insurance Co')
        self.assertEqual(policy_data['base_premium'], 500.0)
        
        # Check features data
        features = data['features']
        self.assertIn('Annual Limit per Family', features)
        self.assertEqual(features['Annual Limit per Family'], 'R50,000.00')
        self.assertIn('Ambulance Coverage', features)
        self.assertEqual(features['Ambulance Coverage'], 'Included')
        
        # Check additional features
        additional_features = data['additional_features']
        self.assertEqual(len(additional_features), 1)
        self.assertEqual(additional_features[0]['title'], 'Emergency Services')
        self.assertEqual(additional_features[0]['coverage_details'], 
                        'Covers emergency room visits, ambulance services, and urgent care')
        
        # Check rewards
        rewards = data['rewards']
        self.assertEqual(len(rewards), 1)
        self.assertEqual(rewards[0]['title'], 'Wellness Cashback')
        self.assertEqual(rewards[0]['display_value'], '5.0%')
    
    def test_policy_benefits_ajax_not_found(self):
        """Test benefits retrieval for non-existent policy."""
        url = reverse('simple_surveys:policy_benefits', kwargs={'policy_id': 99999})
        
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 404)
    
    def test_policy_benefits_ajax_inactive_policy(self):
        """Test benefits retrieval for inactive policy."""
        # Make policy inactive
        self.policy.is_active = False
        self.policy.save()
        
        url = reverse('simple_surveys:policy_benefits', kwargs={'policy_id': self.policy.id})
        
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 404)
    
    def test_policy_benefits_without_features(self):
        """Test benefits retrieval for policy without features."""
        # Delete policy features
        self.policy_features.delete()
        
        url = reverse('simple_surveys:policy_benefits', kwargs={'policy_id': self.policy.id})
        
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Should have empty features
        self.assertEqual(len(data['features']), 0)
        
        # Should still have additional features and rewards
        self.assertEqual(len(data['additional_features']), 1)
        self.assertEqual(len(data['rewards']), 1)
    
    def test_funeral_policy_features(self):
        """Test benefits retrieval for funeral policy."""
        # Create funeral policy
        funeral_category = PolicyCategory.objects.create(
            name="Funeral",
            slug="funeral",
            description="Funeral insurance policies"
        )
        
        funeral_type = PolicyType.objects.create(
            category=funeral_category,
            name="Basic",
            slug="basic",
            description="Basic funeral coverage"
        )
        
        funeral_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=funeral_category,
            policy_type=funeral_type,
            name="Test Funeral Policy",
            policy_number="FUNERAL001",
            description="Test funeral policy",
            short_description="Test funeral policy",
            base_premium=150.00,
            coverage_amount=25000.00,
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Test terms",
            is_active=True,
            approval_status=BasePolicy.ApprovalStatus.APPROVED
        )
        
        # Create funeral policy features
        funeral_features = PolicyFeatures.objects.create(
            policy=funeral_policy,
            insurance_type='FUNERAL',
            cover_amount=25000.00,
            marital_status_requirement='Any',
            gender_requirement='Any'
        )
        
        url = reverse('simple_surveys:policy_benefits', kwargs={'policy_id': funeral_policy.id})
        
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check funeral-specific features
        features = data['features']
        self.assertIn('Cover Amount', features)
        self.assertEqual(features['Cover Amount'], 'R25,000.00')
        self.assertIn('Marital Status Requirement', features)
        self.assertEqual(features['Marital Status Requirement'], 'Any')


if __name__ == '__main__':
    import django
    import os
    import sys
    
    # Add the project root to the Python path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Configure Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
    django.setup()
    
    # Run the tests
    import unittest
    unittest.main()