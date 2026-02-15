"""
Simple integration test to verify survey to policy matching works.
"""

import os
import sys
import django
from decimal import Decimal

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from django.test import TestCase
from organizations.models import Organization
from policies.models import BasePolicy, PolicyCategory, PolicyType, PolicyFeatures
from health_policies.models import HealthPolicy
from simple_surveys.models import SimpleSurveyQuestion, SimpleSurveyResponse
from comparison.feature_matching_engine import FeatureMatchingEngine


class SimpleIntegrationTest(TestCase):
    """Simple test to verify the integration works."""
    
    def setUp(self):
        """Set up minimal test data."""
        # Create organization
        self.org = Organization.objects.create(
            name="Test Org",
            email="test@test.com",
            phone="123456789",
            address_line1="Test Address",
            city="Test City",
            state_province="Test Province",
            postal_code="12345",
            registration_number="REG123",
            license_number="LIC123",
            verification_status=Organization.VerificationStatus.VERIFIED
        )
        
        # Create category
        self.category = PolicyCategory.objects.create(
            name="Health",
            slug="health",
            description="Health insurance"
        )
        
        # Create policy type
        self.policy_type = PolicyType.objects.create(
            category=self.category,
            name="Test Type",
            slug="test",
            description="Test policy type"
        )
        
        # Create health policy
        self.policy = HealthPolicy.objects.create(
            organization=self.org,
            category=self.category,
            policy_type=self.policy_type,
            name="Test Health Policy",
            policy_number="TEST001",
            description="Test policy",
            short_description="Test",
            base_premium=Decimal('1000.00'),
            coverage_amount=Decimal('200000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            coverage_level=HealthPolicy.CoverageLevel.STANDARD,
            hospital_network_type="Test Network",
            includes_hospital_cover=True,
            ambulance_cover=True
        )
        
        # Create policy features
        self.features = PolicyFeatures.objects.create(
            policy=self.policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_family=Decimal('200000.00'),
            ambulance_coverage=True,
            in_hospital_benefit=True,
            chronic_medication_availability=True
        )
    
    def test_basic_integration(self):
        """Test basic integration between survey and policy matching."""
        print("\n=== TESTING BASIC INTEGRATION ===")
        
        # Test user preferences
        user_preferences = {
            'annual_limit_per_family': Decimal('200000.00'),
            'ambulance_coverage': True,
            'chronic_medication_availability': True
        }
        
        print(f"User preferences: {user_preferences}")
        
        # Test feature matching engine
        engine = FeatureMatchingEngine('HEALTH')
        result = engine.calculate_policy_compatibility(self.policy, user_preferences)
        
        print(f"Policy: {self.policy.name}")
        print(f"Compatibility score: {result['overall_score']:.3f}")
        print(f"Matches: {len(result['matches'])}")
        print(f"Explanation: {result['explanation']}")
        
        # Verify results
        self.assertIsInstance(result, dict)
        self.assertIn('overall_score', result)
        self.assertGreater(result['overall_score'], 0.5)
        
        print("✅ Basic integration test PASSED")
    
    def test_survey_response_conversion(self):
        """Test converting survey responses to preferences."""
        print("\n=== TESTING SURVEY RESPONSE CONVERSION ===")
        
        # Create survey question
        question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Do you want ambulance coverage?',
            field_name='wants_ambulance_coverage',
            input_type='radio',
            is_required=True,
            choices=[('true', 'Yes'), ('false', 'No')]
        )
        
        # Create survey response
        response = SimpleSurveyResponse.objects.create(
            session_key='test_session',
            question=question,
            category='health',
            response_value='true'
        )
        
        print(f"Survey response: {response.question.field_name} = {response.response_value}")
        
        # Convert to preferences (simplified)
        preferences = {}
        if response.question.field_name == 'wants_ambulance_coverage':
            preferences['ambulance_coverage'] = response.response_value.lower() == 'true'
        
        print(f"Converted preferences: {preferences}")
        
        # Test with engine
        engine = FeatureMatchingEngine('HEALTH')
        result = engine.calculate_policy_compatibility(self.policy, preferences)
        
        print(f"Compatibility score: {result['overall_score']:.3f}")
        
        # Should be a good match since policy has ambulance coverage
        self.assertGreater(result['overall_score'], 0.8)
        
        print("✅ Survey response conversion test PASSED")
    
    def test_policy_features_access(self):
        """Test accessing policy features."""
        print("\n=== TESTING POLICY FEATURES ACCESS ===")
        
        # Test get_policy_features method
        features = self.policy.get_policy_features()
        
        print(f"Policy features found: {features is not None}")
        if features:
            print(f"Insurance type: {features.insurance_type}")
            print(f"Annual limit: {features.annual_limit_per_family}")
            print(f"Ambulance coverage: {features.ambulance_coverage}")
        
        self.assertIsNotNone(features)
        self.assertEqual(features.insurance_type, 'HEALTH')
        
        print("✅ Policy features access test PASSED")


def run_tests():
    """Run the integration tests."""
    print("Starting Simple Integration Tests...")
    
    import unittest
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(SimpleIntegrationTest)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False


if __name__ == '__main__':
    run_tests()