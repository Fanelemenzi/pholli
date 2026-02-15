"""
Test integration between simple surveys and policy comparison engines.
Tests the complete flow from survey completion to policy matching and results display.
"""

import os
import sys
import django
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.sessions.models import Session

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from organizations.models import Organization
from policies.models import BasePolicy, PolicyCategory, PolicyType, PolicyFeatures
from health_policies.models import HealthPolicy
from funeral_policies.models import FuneralPolicy
from simple_surveys.models import SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession
from comparison.feature_matching_engine import FeatureMatchingEngine


class SurveyPolicyIntegrationTest(TestCase):
    """Test integration between surveys and policy matching"""
    
    def setUp(self):
        """Set up test data"""
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            description="Test insurance company",
            email="test@insurance.com",
            phone="+27123456789",
            address_line1="123 Test Street",
            city="Cape Town",
            state_province="Western Cape",
            postal_code="8001",
            registration_number="REG123TEST",
            license_number="LIC789TEST",
            verification_status=Organization.VerificationStatus.VERIFIED,
            is_active=True
        )
        
        # Create policy categories
        self.health_category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies",
            is_active=True
        )
        
        self.funeral_category = PolicyCategory.objects.create(
            name="Funeral Insurance",
            slug="funeral",
            description="Funeral insurance policies",
            is_active=True
        )
        
        # Create policy types
        self.health_type = PolicyType.objects.create(
            category=self.health_category,
            name="Comprehensive Health",
            slug="comprehensive",
            description="Comprehensive health coverage",
            is_active=True
        )
        
        self.funeral_type = PolicyType.objects.create(
            category=self.funeral_category,
            name="Family Funeral",
            slug="family",
            description="Family funeral coverage",
            is_active=True
        )
        
        # Create test health policy
        self.health_policy = HealthPolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Premium Health Plan",
            policy_number="HP001TEST",
            description="Comprehensive health coverage",
            short_description="Premium health plan",
            base_premium=Decimal('1200.00'),
            coverage_amount=Decimal('500000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Standard terms apply",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            coverage_level=HealthPolicy.CoverageLevel.COMPREHENSIVE,
            hospital_network_type="Private and Public",
            includes_hospital_cover=True,
            includes_outpatient_cover=True,
            includes_dental_cover=True,
            ambulance_cover=True,
            chronic_medication_covered=True
        )
        
        # Create test funeral policy
        self.funeral_policy = FuneralPolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_type,
            name="Family Funeral Cover",
            policy_number="FP001TEST",
            description="Comprehensive funeral cover",
            short_description="Family funeral protection",
            base_premium=Decimal('250.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Standard funeral terms",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            cover_type=FuneralPolicy.CoverType.FAMILY,
            service_type=FuneralPolicy.FuneralService.MANAGED_SERVICE,
            main_member_cover_amount=Decimal('50000.00'),
            includes_spouse_cover=True,
            includes_children_cover=True,
            includes_coffin=True,
            includes_transport=True,
            repatriation_covered=True
        )
        
        # Create policy features for health policy
        self.health_features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_family=Decimal('500000.00'),
            annual_limit_family_range='500k-1m',
            monthly_household_income=Decimal('8000.00'),
            currently_on_medical_aid=False,
            ambulance_coverage=True,
            in_hospital_benefit=True,
            in_hospital_benefit_level='comprehensive',
            out_hospital_benefit=True,
            out_hospital_benefit_level='comprehensive_care',
            chronic_medication_availability=True
        )
        
        # Create policy features for funeral policy
        self.funeral_features = PolicyFeatures.objects.create(
            policy=self.funeral_policy,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('50000.00'),
            cover_amount_range='50k-75k',
            marital_status_requirement='any',
            gender_requirement='any',
            monthly_net_income=Decimal('3000.00')
        )
        
        # Create survey questions for health
        self.health_questions = [
            SimpleSurveyQuestion.objects.create(
                category='health',
                question_text='What is your monthly household income?',
                field_name='monthly_household_income',
                input_type='number',
                is_required=True,
                display_order=1
            ),
            SimpleSurveyQuestion.objects.create(
                category='health',
                question_text='Do you want in-hospital benefits?',
                field_name='in_hospital_benefit',
                input_type='radio',
                is_required=True,
                display_order=2,
                choices=[('true', 'Yes'), ('false', 'No')]
            ),
            SimpleSurveyQuestion.objects.create(
                category='health',
                question_text='Do you need chronic medication coverage?',
                field_name='chronic_medication_availability',
                input_type='radio',
                is_required=True,
                display_order=3,
                choices=[('true', 'Yes'), ('false', 'No')]
            )
        ]
        
        # Create survey questions for funeral
        self.funeral_questions = [
            SimpleSurveyQuestion.objects.create(
                category='funeral',
                question_text='What coverage amount do you prefer?',
                field_name='cover_amount',
                input_type='number',
                is_required=True,
                display_order=1
            ),
            SimpleSurveyQuestion.objects.create(
                category='funeral',
                question_text='What is your marital status?',
                field_name='marital_status_requirement',
                input_type='select',
                is_required=True,
                display_order=2,
                choices=[('single', 'Single'), ('married', 'Married'), ('any', 'Any')]
            )
        ]
        
        # Create test client
        self.client = Client()
    
    def test_health_survey_to_policy_matching_flow(self):
        """Test complete flow from health survey to policy matching"""
        print("\n=== Testing Health Survey to Policy Matching Flow ===")
        
        # Step 1: Access survey page
        response = self.client.get(reverse('survey', kwargs={'category': 'health'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Health Survey')
        print("✓ Survey page loads successfully")
        
        # Step 2: Submit survey responses
        session = self.client.session
        session_key = session.session_key or session.create()
        
        # Create survey responses
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[0],  # monthly_household_income
            category='health',
            response_value='10000'
        )
        
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[1],  # in_hospital_benefit
            category='health',
            response_value='true'
        )
        
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[2],  # chronic_medication_availability
            category='health',
            response_value='true'
        )
        
        print("✓ Survey responses created")
        
        # Step 3: Access results page
        response = self.client.get(reverse('results', kwargs={'category': 'health'}))
        self.assertEqual(response.status_code, 200)
        print("✓ Results page loads successfully")
        
        # Step 4: Verify policy matching occurred
        context = response.context
        self.assertIn('quotations', context)
        self.assertIn('total_quotations', context)
        
        quotations = context['quotations']
        self.assertGreater(len(quotations), 0, "Should have at least one quotation")
        print(f"✓ Found {len(quotations)} policy quotations")
        
        # Step 5: Verify quotation structure
        first_quotation = quotations[0]
        required_fields = [
            'id', 'name', 'provider_name', 'monthly_premium', 
            'coverage_amount', 'match_score', 'key_benefits'
        ]
        
        for field in required_fields:
            self.assertIn(field, first_quotation, f"Quotation missing field: {field}")
        
        print("✓ Quotation structure is correct")
        
        # Step 6: Verify match score is reasonable
        match_score = first_quotation['match_score']
        self.assertGreaterEqual(match_score, 0, "Match score should be >= 0")
        self.assertLessEqual(match_score, 100, "Match score should be <= 100")
        print(f"✓ Match score is reasonable: {match_score}%")
        
        # Step 7: Verify policy features are included
        if 'policy_features' in first_quotation and first_quotation['policy_features']:
            features = first_quotation['policy_features']
            self.assertIsInstance(features, dict, "Policy features should be a dictionary")
            print("✓ Policy features are included")
        
        print("✓ Health survey to policy matching flow completed successfully")
    
    def test_funeral_survey_to_policy_matching_flow(self):
        """Test complete flow from funeral survey to policy matching"""
        print("\n=== Testing Funeral Survey to Policy Matching Flow ===")
        
        # Step 1: Access survey page
        response = self.client.get(reverse('survey', kwargs={'category': 'funeral'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Funeral Survey')
        print("✓ Survey page loads successfully")
        
        # Step 2: Submit survey responses
        session = self.client.session
        session_key = session.session_key or session.create()
        
        # Create survey responses
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.funeral_questions[0],  # cover_amount
            category='funeral',
            response_value='45000'
        )
        
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.funeral_questions[1],  # marital_status_requirement
            category='funeral',
            response_value='married'
        )
        
        print("✓ Survey responses created")
        
        # Step 3: Access results page
        response = self.client.get(reverse('results', kwargs={'category': 'funeral'}))
        self.assertEqual(response.status_code, 200)
        print("✓ Results page loads successfully")
        
        # Step 4: Verify policy matching occurred
        context = response.context
        quotations = context['quotations']
        self.assertGreater(len(quotations), 0, "Should have at least one quotation")
        print(f"✓ Found {len(quotations)} policy quotations")
        
        # Step 5: Verify funeral-specific features
        first_quotation = quotations[0]
        self.assertEqual(first_quotation['id'], self.funeral_policy.id)
        self.assertGreater(first_quotation['match_score'], 0)
        print(f"✓ Funeral policy matched with score: {first_quotation['match_score']}%")
        
        print("✓ Funeral survey to policy matching flow completed successfully")
    
    def test_feature_matching_engine_directly(self):
        """Test the feature matching engine directly"""
        print("\n=== Testing Feature Matching Engine Directly ===")
        
        # Test health policy matching
        health_engine = FeatureMatchingEngine('HEALTH')
        health_preferences = {
            'monthly_household_income': Decimal('10000.00'),
            'in_hospital_benefit': True,
            'chronic_medication_availability': True,
            'ambulance_coverage': True
        }
        
        health_result = health_engine.calculate_policy_compatibility(
            self.health_policy, health_preferences
        )
        
        self.assertIn('overall_score', health_result)
        self.assertIn('matches', health_result)
        self.assertIn('explanation', health_result)
        self.assertGreater(health_result['overall_score'], 0)
        print(f"✓ Health policy compatibility: {health_result['overall_score']:.2f}")
        
        # Test funeral policy matching
        funeral_engine = FeatureMatchingEngine('FUNERAL')
        funeral_preferences = {
            'cover_amount': Decimal('45000.00'),
            'marital_status_requirement': 'married',
            'gender_requirement': 'any'
        }
        
        funeral_result = funeral_engine.calculate_policy_compatibility(
            self.funeral_policy, funeral_preferences
        )
        
        self.assertIn('overall_score', funeral_result)
        self.assertGreater(funeral_result['overall_score'], 0)
        print(f"✓ Funeral policy compatibility: {funeral_result['overall_score']:.2f}")
        
        print("✓ Feature matching engine works correctly")
    
    def test_no_survey_responses_handling(self):
        """Test handling when no survey responses exist"""
        print("\n=== Testing No Survey Responses Handling ===")
        
        # Access results page without completing survey
        response = self.client.get(reverse('results', kwargs={'category': 'health'}))
        self.assertEqual(response.status_code, 200)
        
        context = response.context
        self.assertEqual(len(context['quotations']), 0)
        self.assertIn('message', context)
        self.assertIn('complete the survey', context['message'])
        print("✓ Correctly handles missing survey responses")
    
    def test_no_policies_available_handling(self):
        """Test handling when no policies are available"""
        print("\n=== Testing No Policies Available Handling ===")
        
        # Deactivate all policies
        BasePolicy.objects.all().update(is_active=False)
        
        # Create survey responses
        session = self.client.session
        session_key = session.session_key or session.create()
        
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[0],
            category='health',
            response_value='10000'
        )
        
        # Access results page
        response = self.client.get(reverse('results', kwargs={'category': 'health'}))
        self.assertEqual(response.status_code, 200)
        
        context = response.context
        self.assertEqual(len(context['quotations']), 0)
        self.assertIn('message', context)
        self.assertIn('No health policies', context['message'])
        print("✓ Correctly handles no available policies")
        
        # Reactivate policies for other tests
        BasePolicy.objects.all().update(is_active=True)
    
    def test_policy_features_display(self):
        """Test that policy features are correctly displayed"""
        print("\n=== Testing Policy Features Display ===")
        
        # Create survey responses
        session = self.client.session
        session_key = session.session_key or session.create()
        
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[0],
            category='health',
            response_value='10000'
        )
        
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[1],
            category='health',
            response_value='true'
        )
        
        # Access results page
        response = self.client.get(reverse('results', kwargs={'category': 'health'}))
        self.assertEqual(response.status_code, 200)
        
        # Check that policy features are in the response
        self.assertContains(response, 'Coverage Details')
        self.assertContains(response, 'Annual Family Limit')
        print("✓ Policy features are displayed correctly")
    
    def test_match_score_calculation(self):
        """Test that match scores are calculated correctly"""
        print("\n=== Testing Match Score Calculation ===")
        
        # Test perfect match scenario
        session = self.client.session
        session_key = session.session_key or session.create()
        
        # Create responses that should match perfectly with our test policy
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[0],  # monthly_household_income
            category='health',
            response_value='8000'  # Matches policy requirement exactly
        )
        
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[1],  # in_hospital_benefit
            category='health',
            response_value='true'  # Matches policy feature
        )
        
        SimpleSurveyResponse.objects.create(
            session_key=session_key,
            question=self.health_questions[2],  # chronic_medication_availability
            category='health',
            response_value='true'  # Matches policy feature
        )
        
        # Access results page
        response = self.client.get(reverse('results', kwargs={'category': 'health'}))
        context = response.context
        
        quotations = context['quotations']
        self.assertGreater(len(quotations), 0)
        
        first_quotation = quotations[0]
        match_score = first_quotation['match_score']
        
        # Should have a high match score since responses align with policy features
        self.assertGreater(match_score, 50, "Match score should be > 50% for aligned responses")
        print(f"✓ Match score calculated correctly: {match_score}%")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("="*60)
        print("SURVEY-POLICY INTEGRATION TESTS")
        print("="*60)
        
        try:
            self.test_health_survey_to_policy_matching_flow()
            self.test_funeral_survey_to_policy_matching_flow()
            self.test_feature_matching_engine_directly()
            self.test_no_survey_responses_handling()
            self.test_no_policies_available_handling()
            self.test_policy_features_display()
            self.test_match_score_calculation()
            
            print("\n" + "="*60)
            print("✅ ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
            print("✅ Survey to policy matching integration is working correctly")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {str(e)}")
            raise


if __name__ == '__main__':
    # Run the integration tests
    import unittest
    
    # Create test suite
    suite = unittest.TestSuite()
    test_case = SurveyPolicyIntegrationTest()
    test_case.setUp()
    
    # Run all tests
    test_case.run_all_tests()