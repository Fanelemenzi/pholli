"""
Test module for complete integration between surveys and policy comparison.
Tests the full user flow from survey completion to policy matching results.
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
from comparison.feature_comparison_manager import FeatureComparisonManager


class SurveyPolicyIntegrationTest(TestCase):
    """Test complete integration between survey responses and policy comparison."""
    
    def setUp(self):
        """Set up comprehensive test data."""
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
            description="Medical and health insurance policies",
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
            description="Full health coverage",
            is_active=True
        )
        
        self.funeral_type = PolicyType.objects.create(
            category=self.funeral_category,
            name="Family Funeral",
            slug="family",
            description="Family funeral coverage",
            is_active=True
        )
        
        # Create multiple test health policies
        self.create_health_policies()
        
        # Create multiple test funeral policies
        self.create_funeral_policies()
        
        # Create survey questions
        self.create_survey_questions()
        
        # Set up client
        self.client = Client()
    
    def create_health_policies(self):
        """Create multiple health policies for testing."""
        # Policy 1: High-end comprehensive
        self.health_policy_1 = HealthPolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Premium Health Plan",
            policy_number="HP001TEST",
            description="Premium health policy with comprehensive coverage",
            short_description="Premium health plan",
            base_premium=Decimal('2000.00'),
            coverage_amount=Decimal('500000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Premium terms",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            coverage_level=HealthPolicy.CoverageLevel.COMPREHENSIVE,
            hospital_network_type="Private and Public",
            includes_hospital_cover=True,
            includes_outpatient_cover=True,
            includes_dental_cover=True,
            includes_optical_cover=True,
            ambulance_cover=True,
            chronic_medication_covered=True
        )
        
        # Policy 2: Mid-range standard
        self.health_policy_2 = HealthPolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Standard Health Plan",
            policy_number="HP002TEST",
            description="Standard health policy with good coverage",
            short_description="Standard health plan",
            base_premium=Decimal('1200.00'),
            coverage_amount=Decimal('300000.00'),
            minimum_age=18,
            maximum_age=70,
            terms_and_conditions="Standard terms",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            coverage_level=HealthPolicy.CoverageLevel.STANDARD,
            hospital_network_type="Private and Public",
            includes_hospital_cover=True,
            includes_outpatient_cover=True,
            ambulance_cover=True,
            chronic_medication_covered=False
        )
        
        # Policy 3: Basic affordable
        self.health_policy_3 = HealthPolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Basic Health Plan",
            policy_number="HP003TEST",
            description="Basic health policy for essential coverage",
            short_description="Basic health plan",
            base_premium=Decimal('600.00'),
            coverage_amount=Decimal('150000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Basic terms",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            coverage_level=HealthPolicy.CoverageLevel.BASIC,
            hospital_network_type="Public",
            includes_hospital_cover=True,
            includes_outpatient_cover=False,
            ambulance_cover=False,
            chronic_medication_covered=False
        )
        
        # Create policy features for each
        PolicyFeatures.objects.create(
            policy=self.health_policy_1,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_family=Decimal('500000.00'),
            annual_limit_family_range='500k-1m',
            monthly_household_income=Decimal('15000.00'),
            currently_on_medical_aid=False,
            ambulance_coverage=True,
            in_hospital_benefit=True,
            in_hospital_benefit_level='comprehensive',
            out_hospital_benefit=True,
            out_hospital_benefit_level='comprehensive_care',
            chronic_medication_availability=True
        )
        
        PolicyFeatures.objects.create(
            policy=self.health_policy_2,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_family=Decimal('300000.00'),
            annual_limit_family_range='250k-500k',
            monthly_household_income=Decimal('8000.00'),
            currently_on_medical_aid=False,
            ambulance_coverage=True,
            in_hospital_benefit=True,
            in_hospital_benefit_level='extensive',
            out_hospital_benefit=True,
            out_hospital_benefit_level='routine_care',
            chronic_medication_availability=False
        )
        
        PolicyFeatures.objects.create(
            policy=self.health_policy_3,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_family=Decimal('150000.00'),
            annual_limit_family_range='100k-250k',
            monthly_household_income=Decimal('5000.00'),
            currently_on_medical_aid=False,
            ambulance_coverage=False,
            in_hospital_benefit=True,
            in_hospital_benefit_level='basic',
            out_hospital_benefit=False,
            out_hospital_benefit_level='no_cover',
            chronic_medication_availability=False
        )
    
    def create_funeral_policies(self):
        """Create multiple funeral policies for testing."""
        # Policy 1: Family funeral with comprehensive services
        self.funeral_policy_1 = FuneralPolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_type,
            name="Family Funeral Cover",
            policy_number="FP001TEST",
            description="Comprehensive family funeral coverage",
            short_description="Family funeral plan",
            base_premium=Decimal('300.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Family funeral terms",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            cover_type=FuneralPolicy.CoverType.FAMILY,
            service_type=FuneralPolicy.FuneralService.MANAGED_SERVICE,
            main_member_cover_amount=Decimal('50000.00'),
            includes_spouse_cover=True,
            spouse_cover_amount=Decimal('50000.00'),
            includes_children_cover=True,
            child_cover_amount=Decimal('25000.00'),
            includes_coffin=True,
            includes_transport=True,
            includes_venue=True,
            repatriation_covered=True
        )
        
        # Policy 2: Individual funeral with cash payout
        self.funeral_policy_2 = FuneralPolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_type,
            name="Individual Funeral Cover",
            policy_number="FP002TEST",
            description="Individual funeral coverage with cash payout",
            short_description="Individual funeral plan",
            base_premium=Decimal('150.00'),
            coverage_amount=Decimal('25000.00'),
            minimum_age=18,
            maximum_age=80,
            terms_and_conditions="Individual funeral terms",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            cover_type=FuneralPolicy.CoverType.INDIVIDUAL,
            service_type=FuneralPolicy.FuneralService.CASH_PAYOUT,
            main_member_cover_amount=Decimal('25000.00'),
            includes_spouse_cover=False,
            includes_children_cover=False,
            repatriation_covered=False
        )
        
        # Create policy features
        PolicyFeatures.objects.create(
            policy=self.funeral_policy_1,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('50000.00'),
            cover_amount_range='50k-75k',
            funeral_service_type='standard',
            family_coverage_type='extended_family',
            max_family_members=8,
            waiting_period_natural_death='6_months',
            waiting_period_accidental_death='none',
            includes_coffin=True,
            includes_transport=True,
            includes_venue=True,
            repatriation_covered=True,
            monthly_net_income=Decimal('4000.00')
        )
        
        PolicyFeatures.objects.create(
            policy=self.funeral_policy_2,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('25000.00'),
            cover_amount_range='25k-50k',
            funeral_service_type='cash_only',
            family_coverage_type='individual',
            max_family_members=1,
            waiting_period_natural_death='6_months',
            waiting_period_accidental_death='none',
            includes_coffin=False,
            includes_transport=False,
            includes_venue=False,
            repatriation_covered=False,
            monthly_net_income=Decimal('3000.00')
        )
    
    def create_survey_questions(self):
        """Create comprehensive survey questions for testing."""
        # Health survey questions
        SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your preferred annual family limit?',
            field_name='preferred_annual_limit_per_family',
            input_type='select',
            is_required=True,
            choices=[
                ('100000', 'R100,000'),
                ('200000', 'R200,000'),
                ('300000', 'R300,000'),
                ('500000', 'R500,000')
            ]
        )
        
        SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Do you want ambulance coverage?',
            field_name='wants_ambulance_coverage',
            input_type='radio',
            is_required=True,
            choices=[
                ('true', 'Yes'),
                ('false', 'No')
            ]
        )
        
        SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Do you need chronic medication coverage?',
            field_name='needs_chronic_medication',
            input_type='radio',
            is_required=True,
            choices=[
                ('true', 'Yes'),
                ('false', 'No')
            ]
        )
        
        SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your monthly household income?',
            field_name='monthly_household_income',
            input_type='select',
            is_required=True,
            choices=[
                ('5000', 'R5,000'),
                ('8000', 'R8,000'),
                ('12000', 'R12,000'),
                ('20000', 'R20,000+')
            ]
        )
        
        # Funeral survey questions
        SimpleSurveyQuestion.objects.create(
            category='funeral',
            question_text='What coverage amount do you prefer?',
            field_name='preferred_cover_amount',
            input_type='select',
            is_required=True,
            choices=[
                ('25000', 'R25,000'),
                ('50000', 'R50,000'),
                ('75000', 'R75,000'),
                ('100000', 'R100,000')
            ]
        )
        
        SimpleSurveyQuestion.objects.create(
            category='funeral',
            question_text='Do you need family coverage?',
            field_name='needs_family_coverage',
            input_type='radio',
            is_required=True,
            choices=[
                ('true', 'Yes'),
                ('false', 'No')
            ]
        )
        
        SimpleSurveyQuestion.objects.create(
            category='funeral',
            question_text='What is your monthly net income?',
            field_name='monthly_net_income',
            input_type='select',
            is_required=True,
            choices=[
                ('3000', 'R3,000'),
                ('4000', 'R4,000'),
                ('6000', 'R6,000'),
                ('8000', 'R8,000+')
            ]
        )
    
    def test_complete_health_survey_flow(self):
        """Test complete health survey to policy matching flow."""
        print("\n" + "="*60)
        print("TESTING COMPLETE HEALTH SURVEY FLOW")
        print("="*60)
        
        # 1. Simulate user session
        session = self.client.session
        session.create()
        session_key = session.session_key
        
        # 2. Create survey responses (user wants comprehensive coverage)
        health_responses = {
            'preferred_annual_limit_per_family': '500000',  # High limit
            'wants_ambulance_coverage': 'true',             # Yes to ambulance
            'needs_chronic_medication': 'true',             # Yes to chronic meds
            'monthly_household_income': '12000'             # Good income
        }
        
        print(f"\n1. Creating survey responses for session: {session_key}")
        for field_name, value in health_responses.items():
            question = SimpleSurveyQuestion.objects.get(
                category='health', 
                field_name=field_name
            )
            SimpleSurveyResponse.objects.create(
                session_key=session_key,
                question=question,
                category='health',
                response_value=value
            )
            print(f"   ✓ {field_name}: {value}")
        
        # 3. Convert responses to preferences
        user_preferences = self.convert_health_responses_to_preferences(session_key)
        print(f"\n2. Converted to preferences:")
        for key, value in user_preferences.items():
            print(f"   ✓ {key}: {value}")
        
        # 4. Test policy matching
        print(f"\n3. Testing policy matching against {HealthPolicy.objects.count()} health policies:")
        
        engine = FeatureMatchingEngine('HEALTH')
        policy_results = []
        
        for policy in HealthPolicy.objects.all():
            compatibility_result = engine.calculate_policy_compatibility(
                policy, user_preferences
            )
            policy_results.append({
                'policy': policy,
                'result': compatibility_result
            })
            
            print(f"   Policy: {policy.name}")
            print(f"   Score: {compatibility_result['overall_score']:.3f}")
            print(f"   Matches: {len(compatibility_result['matches'])}")
            print(f"   Explanation: {compatibility_result['explanation']}")
            print()
        
        # 5. Rank results
        policy_results.sort(key=lambda x: x['result']['overall_score'], reverse=True)
        
        print("4. FINAL RANKING:")
        for i, result in enumerate(policy_results, 1):
            policy = result['policy']
            score = result['result']['overall_score']
            print(f"   #{i}. {policy.name} - Score: {score:.3f} (R{policy.base_premium}/month)")
        
        # 6. Verify results make sense
        best_result = policy_results[0]
        self.assertGreater(best_result['result']['overall_score'], 0.7, 
                          "Best match should have high compatibility")
        
        # Premium policy should rank highest for comprehensive needs
        self.assertEqual(best_result['policy'].name, "Premium Health Plan",
                        "Premium policy should be best match for comprehensive needs")
        
        print(f"\n✅ HEALTH SURVEY FLOW TEST PASSED")
        print(f"   Best match: {best_result['policy'].name}")
        print(f"   Compatibility: {best_result['result']['overall_score']:.3f}")
    
    def test_complete_funeral_survey_flow(self):
        """Test complete funeral survey to policy matching flow."""
        print("\n" + "="*60)
        print("TESTING COMPLETE FUNERAL SURVEY FLOW")
        print("="*60)
        
        # 1. Simulate user session
        session = self.client.session
        session.create()
        session_key = session.session_key
        
        # 2. Create survey responses (user wants family coverage)
        funeral_responses = {
            'preferred_cover_amount': '50000',      # R50k coverage
            'needs_family_coverage': 'true',       # Yes to family
            'monthly_net_income': '4000'           # R4k income
        }
        
        print(f"\n1. Creating funeral survey responses for session: {session_key}")
        for field_name, value in funeral_responses.items():
            question = SimpleSurveyQuestion.objects.get(
                category='funeral', 
                field_name=field_name
            )
            SimpleSurveyResponse.objects.create(
                session_key=session_key,
                question=question,
                category='funeral',
                response_value=value
            )
            print(f"   ✓ {field_name}: {value}")
        
        # 3. Convert responses to preferences
        user_preferences = self.convert_funeral_responses_to_preferences(session_key)
        print(f"\n2. Converted to preferences:")
        for key, value in user_preferences.items():
            print(f"   ✓ {key}: {value}")
        
        # 4. Test policy matching
        print(f"\n3. Testing policy matching against {FuneralPolicy.objects.count()} funeral policies:")
        
        engine = FeatureMatchingEngine('FUNERAL')
        policy_results = []
        
        for policy in FuneralPolicy.objects.all():
            compatibility_result = engine.calculate_policy_compatibility(
                policy, user_preferences
            )
            policy_results.append({
                'policy': policy,
                'result': compatibility_result
            })
            
            print(f"   Policy: {policy.name}")
            print(f"   Score: {compatibility_result['overall_score']:.3f}")
            print(f"   Matches: {len(compatibility_result['matches'])}")
            print(f"   Explanation: {compatibility_result['explanation']}")
            print()
        
        # 5. Rank results
        policy_results.sort(key=lambda x: x['result']['overall_score'], reverse=True)
        
        print("4. FINAL RANKING:")
        for i, result in enumerate(policy_results, 1):
            policy = result['policy']
            score = result['result']['overall_score']
            print(f"   #{i}. {policy.name} - Score: {score:.3f} (R{policy.base_premium}/month)")
        
        # 6. Verify results
        best_result = policy_results[0]
        self.assertGreater(best_result['result']['overall_score'], 0.5, 
                          "Best match should have reasonable compatibility")
        
        # Family policy should rank highest for family coverage needs
        self.assertEqual(best_result['policy'].name, "Family Funeral Cover",
                        "Family policy should be best match for family coverage needs")
        
        print(f"\n✅ FUNERAL SURVEY FLOW TEST PASSED")
        print(f"   Best match: {best_result['policy'].name}")
        print(f"   Compatibility: {best_result['result']['overall_score']:.3f}")
    
    def test_policy_matching_logic_accuracy(self):
        """Test that policy matching logic produces accurate results."""
        print("\n" + "="*60)
        print("TESTING POLICY MATCHING LOGIC ACCURACY")
        print("="*60)
        
        # Test scenario 1: Budget-conscious user
        budget_preferences = {
            'annual_limit_per_family': Decimal('150000.00'),
            'ambulance_coverage': False,
            'chronic_medication_availability': False,
            'monthly_household_income': Decimal('5000.00')
        }
        
        print("\n1. Testing budget-conscious preferences:")
        for key, value in budget_preferences.items():
            print(f"   {key}: {value}")
        
        engine = FeatureMatchingEngine('HEALTH')
        results = []
        
        for policy in HealthPolicy.objects.all():
            result = engine.calculate_policy_compatibility(policy, budget_preferences)
            results.append((policy, result['overall_score']))
            print(f"   {policy.name}: {result['overall_score']:.3f}")
        
        # Basic policy should score highest for budget preferences
        results.sort(key=lambda x: x[1], reverse=True)
        best_policy = results[0][0]
        self.assertEqual(best_policy.name, "Basic Health Plan",
                        "Basic policy should be best for budget-conscious user")
        
        # Test scenario 2: Premium user
        premium_preferences = {
            'annual_limit_per_family': Decimal('500000.00'),
            'ambulance_coverage': True,
            'chronic_medication_availability': True,
            'monthly_household_income': Decimal('20000.00')
        }
        
        print("\n2. Testing premium preferences:")
        for key, value in premium_preferences.items():
            print(f"   {key}: {value}")
        
        results = []
        for policy in HealthPolicy.objects.all():
            result = engine.calculate_policy_compatibility(policy, premium_preferences)
            results.append((policy, result['overall_score']))
            print(f"   {policy.name}: {result['overall_score']:.3f}")
        
        # Premium policy should score highest
        results.sort(key=lambda x: x[1], reverse=True)
        best_policy = results[0][0]
        self.assertEqual(best_policy.name, "Premium Health Plan",
                        "Premium policy should be best for premium user")
        
        print("\n✅ POLICY MATCHING LOGIC ACCURACY TEST PASSED")
    
    def test_feature_comparison_manager_integration(self):
        """Test integration with FeatureComparisonManager."""
        print("\n" + "="*60)
        print("TESTING FEATURE COMPARISON MANAGER INTEGRATION")
        print("="*60)
        
        # Create manager
        manager = FeatureComparisonManager()
        
        # Test health engine
        health_engine = manager.get_matching_engine('HEALTH')
        self.assertIsInstance(health_engine, FeatureMatchingEngine)
        self.assertEqual(health_engine.insurance_type, 'HEALTH')
        
        # Test funeral engine
        funeral_engine = manager.get_matching_engine('FUNERAL')
        self.assertIsInstance(funeral_engine, FeatureMatchingEngine)
        self.assertEqual(funeral_engine.insurance_type, 'FUNERAL')
        
        # Test engine reuse
        health_engine_2 = manager.get_matching_engine('HEALTH')
        self.assertIs(health_engine, health_engine_2, "Engine should be reused")
        
        print("✅ FEATURE COMPARISON MANAGER INTEGRATION TEST PASSED")
    
    def convert_health_responses_to_preferences(self, session_key):
        """Convert health survey responses to user preferences format."""
        responses = SimpleSurveyResponse.objects.filter(
            session_key=session_key,
            category='health'
        )
        
        preferences = {}
        for response in responses:
            field_name = response.question.field_name
            value = response.response_value
            
            if field_name == 'preferred_annual_limit_per_family':
                preferences['annual_limit_per_family'] = Decimal(value)
            elif field_name == 'wants_ambulance_coverage':
                preferences['ambulance_coverage'] = value.lower() == 'true'
            elif field_name == 'needs_chronic_medication':
                preferences['chronic_medication_availability'] = value.lower() == 'true'
            elif field_name == 'monthly_household_income':
                preferences['monthly_household_income'] = Decimal(value)
        
        return preferences
    
    def convert_funeral_responses_to_preferences(self, session_key):
        """Convert funeral survey responses to user preferences format."""
        responses = SimpleSurveyResponse.objects.filter(
            session_key=session_key,
            category='funeral'
        )
        
        preferences = {}
        for response in responses:
            field_name = response.question.field_name
            value = response.response_value
            
            if field_name == 'preferred_cover_amount':
                preferences['cover_amount'] = Decimal(value)
            elif field_name == 'needs_family_coverage':
                # Map to family coverage type
                if value.lower() == 'true':
                    preferences['family_coverage_type'] = 'extended_family'
                else:
                    preferences['family_coverage_type'] = 'individual'
            elif field_name == 'monthly_net_income':
                preferences['monthly_net_income'] = Decimal(value)
        
        return preferences


if __name__ == '__main__':
    import unittest
    unittest.main(verbosity=2)