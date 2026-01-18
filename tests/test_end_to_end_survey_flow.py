"""
End-to-end tests for the complete survey-to-results flow.
Tests the entire user journey from survey creation to policy recommendations.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from decimal import Decimal
from datetime import date
import json

from organizations.models import Organization
from policies.models import (
    PolicyCategory, PolicyType, BasePolicy, PolicyFeatures, AdditionalFeatures
)
from simple_surveys.models import SimpleSurvey
from comparison.models import FeatureComparisonResult
from comparison.feature_comparison_manager import FeatureComparisonManager

User = get_user_model()


class EndToEndSurveyFlowTest(TestCase):
    """End-to-end tests for complete survey workflow."""
    
    def setUp(self):
        """Set up comprehensive test environment."""
        self.client = Client()
        
        # Create organization
        self.organization = Organization.objects.create(
            name="Eswatini Life Insurance",
            slug="eswatini-life",
            email="info@eswatinilife.co.sz",
            phone="+268123456789",
            is_verified=True
        )
        
        # Create categories
        self.health_category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health and medical insurance policies"
        )
        
        self.funeral_category = PolicyCategory.objects.create(
            name="Funeral Insurance",
            slug="funeral",
            description="Funeral and burial insurance policies"
        )
        
        # Create policy types
        self.health_comprehensive = PolicyType.objects.create(
            category=self.health_category,
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health coverage"
        )
        
        self.funeral_family = PolicyType.objects.create(
            category=self.funeral_category,
            name="Family",
            slug="family",
            description="Family funeral coverage"
        )
        
        # Create realistic health policies
        self.health_policy_premium = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_comprehensive,
            name="LifeCare Premium",
            policy_number="LC-PREM-001",
            description="Premium health insurance with comprehensive medical coverage including chronic conditions",
            short_description="Premium health coverage with chronic care",
            base_premium=Decimal('950.00'),
            coverage_amount=Decimal('250000.00'),
            minimum_age=18,
            maximum_age=65,
            waiting_period_days=30,
            terms_and_conditions="Premium health insurance terms and conditions",
            is_active=True
        )
        
        self.health_policy_standard = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_comprehensive,
            name="LifeCare Standard",
            policy_number="LC-STD-001",
            description="Standard health insurance with good medical coverage for families",
            short_description="Standard family health coverage",
            base_premium=Decimal('650.00'),
            coverage_amount=Decimal('150000.00'),
            minimum_age=18,
            maximum_age=65,
            waiting_period_days=60,
            terms_and_conditions="Standard health insurance terms and conditions",
            is_active=True
        )
        
        self.health_policy_basic = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_comprehensive,
            name="LifeCare Essential",
            policy_number="LC-ESS-001",
            description="Essential health insurance with basic medical coverage for individuals",
            short_description="Essential individual health coverage",
            base_premium=Decimal('350.00'),
            coverage_amount=Decimal('75000.00'),
            minimum_age=18,
            maximum_age=65,
            waiting_period_days=90,
            terms_and_conditions="Essential health insurance terms and conditions",
            is_active=True
        )
        
        # Create realistic funeral policies
        self.funeral_policy_comprehensive = BasePolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_family,
            name="FuneralCare Complete",
            policy_number="FC-COMP-001",
            description="Complete funeral insurance with repatriation and additional benefits",
            short_description="Complete funeral coverage with extras",
            base_premium=Decimal('280.00'),
            coverage_amount=Decimal('85000.00'),
            minimum_age=18,
            maximum_age=75,
            waiting_period_days=180,
            terms_and_conditions="Complete funeral insurance terms and conditions",
            is_active=True
        )
        
        self.funeral_policy_standard = BasePolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_family,
            name="FuneralCare Family",
            policy_number="FC-FAM-001",
            description="Family funeral insurance with standard coverage and benefits",
            short_description="Standard family funeral coverage",
            base_premium=Decimal('180.00'),
            coverage_amount=Decimal('45000.00'),
            minimum_age=18,
            maximum_age=75,
            waiting_period_days=365,
            terms_and_conditions="Family funeral insurance terms and conditions",
            is_active=True
        )
        
        # Create policy features
        self.create_policy_features()
        
        # Create additional features
        self.create_additional_features()
    
    def create_policy_features(self):
        """Create realistic policy features."""
        # Health policy features
        PolicyFeatures.objects.create(
            policy=self.health_policy_premium,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('200000.00'),
            monthly_household_income=Decimal('25000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        PolicyFeatures.objects.create(
            policy=self.health_policy_standard,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('120000.00'),
            monthly_household_income=Decimal('15000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=False
        )
        
        PolicyFeatures.objects.create(
            policy=self.health_policy_basic,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('60000.00'),
            monthly_household_income=Decimal('10000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=False,
            chronic_medication_availability=False
        )
        
        # Funeral policy features
        PolicyFeatures.objects.create(
            policy=self.funeral_policy_comprehensive,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('75000.00'),
            marital_status_requirement='Any',
            gender_requirement='Any',
            monthly_net_income=Decimal('20000.00')
        )
        
        PolicyFeatures.objects.create(
            policy=self.funeral_policy_standard,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('40000.00'),
            marital_status_requirement='Any',
            gender_requirement='Any',
            monthly_net_income=Decimal('12000.00')
        )
    
    def create_additional_features(self):
        """Create additional features for policies."""
        # Premium health policy features
        AdditionalFeatures.objects.create(
            policy=self.health_policy_premium,
            title="24/7 Medical Helpline",
            description="Round-the-clock access to qualified medical professionals",
            icon="fa-phone-medical",
            is_highlighted=True,
            display_order=1
        )
        
        AdditionalFeatures.objects.create(
            policy=self.health_policy_premium,
            title="Chronic Disease Management",
            description="Specialized support for diabetes, hypertension, and other chronic conditions",
            icon="fa-heartbeat",
            is_highlighted=True,
            display_order=2
        )
        
        AdditionalFeatures.objects.create(
            policy=self.health_policy_premium,
            title="International Emergency Coverage",
            description="Medical emergency coverage while traveling abroad",
            icon="fa-globe",
            is_highlighted=False,
            display_order=3
        )
        
        # Standard health policy features
        AdditionalFeatures.objects.create(
            policy=self.health_policy_standard,
            title="Family Doctor Network",
            description="Access to network of family doctors and specialists",
            icon="fa-user-md",
            is_highlighted=True,
            display_order=1
        )
        
        AdditionalFeatures.objects.create(
            policy=self.health_policy_standard,
            title="Preventive Care Benefits",
            description="Annual health screenings and preventive care coverage",
            icon="fa-shield-alt",
            is_highlighted=False,
            display_order=2
        )
        
        # Comprehensive funeral policy features
        AdditionalFeatures.objects.create(
            policy=self.funeral_policy_comprehensive,
            title="Repatriation Services",
            description="Transportation of deceased to home country or region",
            icon="fa-plane",
            is_highlighted=True,
            display_order=1
        )
        
        AdditionalFeatures.objects.create(
            policy=self.funeral_policy_comprehensive,
            title="Tombstone Benefit",
            description="Contribution towards tombstone and memorial expenses",
            icon="fa-monument",
            is_highlighted=True,
            display_order=2
        )
        
        AdditionalFeatures.objects.create(
            policy=self.funeral_policy_comprehensive,
            title="Grief Counseling",
            description="Professional grief counseling services for family members",
            icon="fa-hands-helping",
            is_highlighted=False,
            display_order=3
        )
    
    def test_complete_health_survey_flow_high_income_user(self):
        """Test complete flow for high-income user seeking comprehensive health coverage."""
        # Step 1: Create survey (simulating form submission)
        survey_data = {
            'first_name': 'Sipho',
            'last_name': 'Dlamini',
            'date_of_birth': '1985-03-15',
            'email': 'sipho.dlamini@example.com',
            'phone': '+268123456789',
            'insurance_type': 'HEALTH',
            'preferred_annual_limit': '180000.00',
            'household_income': '28000.00',
            'wants_in_hospital_benefit': True,
            'wants_out_hospital_benefit': True,
            'needs_chronic_medication': True
        }
        
        survey = SimpleSurvey.objects.create(**survey_data)
        
        # Step 2: Generate policy comparisons
        health_policies = [
            self.health_policy_premium,
            self.health_policy_standard,
            self.health_policy_basic
        ]
        
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            survey,
            health_policies,
            force_regenerate=True
        )
        
        # Step 3: Verify results match user profile
        self.assertEqual(len(results), 3)
        
        # Premium policy should rank highest (has chronic medication coverage)
        top_result = results[0]
        self.assertEqual(top_result.policy, self.health_policy_premium)
        self.assertEqual(top_result.compatibility_rank, 1)
        self.assertGreater(top_result.overall_compatibility_score, Decimal('85.0'))
        
        # Verify feature matches
        self.assertGreater(top_result.feature_match_count, 3)
        self.assertIn('chronic_medication_availability', 
                     [match.get('feature', '').lower().replace(' ', '_') 
                      for match in top_result.feature_matches])
        
        # Step 4: Verify recommendation category
        self.assertIn(top_result.recommendation_category, [
            FeatureComparisonResult.RecommendationCategory.PERFECT_MATCH,
            FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH
        ])
        
        # Step 5: Verify explanation quality
        self.assertIsNotNone(top_result.match_explanation)
        self.assertGreater(len(top_result.match_explanation), 20)
        
        # Step 6: Test that standard policy ranks second
        second_result = results[1]
        self.assertEqual(second_result.policy, self.health_policy_standard)
        self.assertEqual(second_result.compatibility_rank, 2)
        
        # Should have chronic medication as a mismatch
        chronic_mismatch = any(
            'chronic' in mismatch.get('feature', '').lower()
            for mismatch in second_result.feature_mismatches
        )
        self.assertTrue(chronic_mismatch)
    
    def test_complete_health_survey_flow_budget_conscious_user(self):
        """Test complete flow for budget-conscious user seeking basic coverage."""
        # Step 1: Create survey for budget-conscious user
        survey_data = {
            'first_name': 'Nomsa',
            'last_name': 'Mthembu',
            'date_of_birth': '1992-07-22',
            'email': 'nomsa.mthembu@example.com',
            'phone': '+268987654321',
            'insurance_type': 'HEALTH',
            'preferred_annual_limit': '50000.00',
            'household_income': '8500.00',
            'wants_in_hospital_benefit': True,
            'wants_out_hospital_benefit': False,
            'needs_chronic_medication': False
        }
        
        survey = SimpleSurvey.objects.create(**survey_data)
        
        # Step 2: Generate comparisons
        health_policies = [
            self.health_policy_premium,
            self.health_policy_standard,
            self.health_policy_basic
        ]
        
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            survey,
            health_policies,
            force_regenerate=True
        )
        
        # Step 3: Verify basic policy performs well
        # Find basic policy result
        basic_result = next(r for r in results if r.policy == self.health_policy_basic)
        
        # Basic policy should have good compatibility (meets income requirement, no out-hospital needed)
        self.assertGreater(basic_result.overall_compatibility_score, Decimal('70.0'))
        
        # Should have income requirement match
        income_match = any(
            'income' in match.get('feature', '').lower()
            for match in basic_result.feature_matches
        )
        self.assertTrue(income_match)
        
        # Premium policy should have income mismatch (user doesn't meet requirement)
        premium_result = next(r for r in results if r.policy == self.health_policy_premium)
        income_mismatch = any(
            'income' in mismatch.get('feature', '').lower()
            for mismatch in premium_result.feature_mismatches
        )
        self.assertTrue(income_mismatch)
    
    def test_complete_funeral_survey_flow_family_coverage(self):
        """Test complete flow for user seeking family funeral coverage."""
        # Step 1: Create funeral survey
        survey_data = {
            'first_name': 'Thabo',
            'last_name': 'Nkomo',
            'date_of_birth': '1978-11-08',
            'email': 'thabo.nkomo@example.com',
            'phone': '+268555123456',
            'insurance_type': 'FUNERAL',
            'preferred_cover_amount': '60000.00',
            'marital_status': 'Married',
            'gender': 'Male',
            'net_income': '18000.00'
        }
        
        survey = SimpleSurvey.objects.create(**survey_data)
        
        # Step 2: Generate comparisons
        funeral_policies = [
            self.funeral_policy_comprehensive,
            self.funeral_policy_standard
        ]
        
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            survey,
            funeral_policies,
            force_regenerate=True
        )
        
        # Step 3: Verify results
        self.assertEqual(len(results), 2)
        
        # Comprehensive policy should rank higher (better coverage, meets income)
        top_result = results[0]
        self.assertEqual(top_result.policy, self.funeral_policy_comprehensive)
        self.assertGreater(top_result.overall_compatibility_score, Decimal('80.0'))
        
        # Should have coverage amount match (policy exceeds preference)
        coverage_match = any(
            'cover' in match.get('feature', '').lower()
            for match in top_result.feature_matches
        )
        self.assertTrue(coverage_match)
        
        # Step 4: Verify additional features are considered
        comprehensive_additional_features = self.funeral_policy_comprehensive.additional_features.all()
        self.assertGreater(comprehensive_additional_features.count(), 0)
        
        # Highlighted features should include repatriation
        highlighted_features = comprehensive_additional_features.filter(is_highlighted=True)
        repatriation_feature = highlighted_features.filter(title__icontains='repatriation').first()
        self.assertIsNotNone(repatriation_feature)
    
    def test_survey_validation_and_error_handling(self):
        """Test survey validation and error handling in the flow."""
        # Test incomplete health survey
        incomplete_health_data = {
            'first_name': 'Incomplete',
            'last_name': 'User',
            'date_of_birth': '1990-01-01',
            'insurance_type': 'HEALTH',
            # Missing required health fields
        }
        
        survey = SimpleSurvey.objects.create(**incomplete_health_data)
        
        # Should handle gracefully with empty preferences
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            survey,
            [self.health_policy_standard],
            force_regenerate=True
        )
        
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.overall_compatibility_score, Decimal('0.0'))
        self.assertEqual(result.feature_match_count, 0)
        self.assertEqual(result.feature_mismatch_count, 0)
    
    def test_cross_insurance_type_prevention(self):
        """Test that health surveys don't match funeral policies."""
        # Create health survey
        health_survey = SimpleSurvey.objects.create(
            first_name='Health',
            last_name='User',
            date_of_birth='1985-01-01',
            insurance_type='HEALTH',
            preferred_annual_limit='100000.00',
            household_income='15000.00',
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=True,
            needs_chronic_medication=False
        )
        
        # Try to match against funeral policies
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            health_survey,
            [self.funeral_policy_comprehensive],
            force_regenerate=True
        )
        
        # Should create result but with zero score
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.overall_compatibility_score, Decimal('0.0'))
        self.assertIn('Policy type does not match', result.match_explanation)
    
    def test_policy_ranking_consistency(self):
        """Test that policy ranking is consistent and logical."""
        # Create survey that should clearly prefer premium policy
        survey = SimpleSurvey.objects.create(
            first_name='Premium',
            last_name='Seeker',
            date_of_birth='1980-05-10',
            insurance_type='HEALTH',
            preferred_annual_limit='250000.00',
            household_income='35000.00',
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=True,
            needs_chronic_medication=True
        )
        
        # Generate results multiple times to test consistency
        manager = FeatureComparisonManager()
        
        for _ in range(3):
            results = manager.generate_comparison_results(
                survey,
                [self.health_policy_premium, self.health_policy_standard, self.health_policy_basic],
                force_regenerate=True
            )
            
            # Premium should always rank first
            self.assertEqual(results[0].policy, self.health_policy_premium)
            self.assertEqual(results[0].compatibility_rank, 1)
            
            # Scores should be in descending order
            scores = [result.overall_compatibility_score for result in results]
            self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_feature_explanation_quality(self):
        """Test quality and completeness of feature explanations."""
        # Create survey with mixed preferences
        survey = SimpleSurvey.objects.create(
            first_name='Mixed',
            last_name='Preferences',
            date_of_birth='1987-09-14',
            insurance_type='HEALTH',
            preferred_annual_limit='90000.00',
            household_income='13000.00',
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=False,
            needs_chronic_medication=True
        )
        
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            survey,
            [self.health_policy_standard],
            force_regenerate=True
        )
        
        result = results[0]
        
        # Should have detailed feature analysis
        self.assertIsNotNone(result.feature_scores)
        self.assertIsInstance(result.feature_scores, dict)
        self.assertGreater(len(result.feature_scores), 0)
        
        # Should have matches and mismatches
        self.assertIsNotNone(result.feature_matches)
        self.assertIsNotNone(result.feature_mismatches)
        
        # Should have meaningful explanation
        self.assertIsNotNone(result.match_explanation)
        self.assertGreater(len(result.match_explanation), 10)
        
        # Chronic medication should be a mismatch for standard policy
        chronic_mismatch = any(
            'chronic' in str(mismatch).lower()
            for mismatch in result.feature_mismatches
        )
        self.assertTrue(chronic_mismatch)
    
    def test_database_integrity_after_multiple_operations(self):
        """Test database integrity after multiple survey operations."""
        # Create multiple surveys and process them
        surveys_data = [
            {
                'first_name': 'User1', 'last_name': 'Test', 'date_of_birth': '1985-01-01',
                'insurance_type': 'HEALTH', 'preferred_annual_limit': '80000.00',
                'household_income': '12000.00', 'wants_in_hospital_benefit': True,
                'wants_out_hospital_benefit': True, 'needs_chronic_medication': False
            },
            {
                'first_name': 'User2', 'last_name': 'Test', 'date_of_birth': '1990-06-15',
                'insurance_type': 'HEALTH', 'preferred_annual_limit': '150000.00',
                'household_income': '22000.00', 'wants_in_hospital_benefit': True,
                'wants_out_hospital_benefit': True, 'needs_chronic_medication': True
            },
            {
                'first_name': 'User3', 'last_name': 'Test', 'date_of_birth': '1982-11-30',
                'insurance_type': 'FUNERAL', 'preferred_cover_amount': '50000.00',
                'marital_status': 'Single', 'gender': 'Female', 'net_income': '14000.00'
            }
        ]
        
        manager = FeatureComparisonManager()
        all_results = []
        
        for survey_data in surveys_data:
            survey = SimpleSurvey.objects.create(**survey_data)
            
            if survey.insurance_type == 'HEALTH':
                policies = [self.health_policy_premium, self.health_policy_standard, self.health_policy_basic]
            else:
                policies = [self.funeral_policy_comprehensive, self.funeral_policy_standard]
            
            results = manager.generate_comparison_results(
                survey,
                policies,
                force_regenerate=True
            )
            all_results.extend(results)
        
        # Verify database integrity
        total_surveys = SimpleSurvey.objects.count()
        total_results = FeatureComparisonResult.objects.count()
        
        self.assertEqual(total_surveys, 3)
        self.assertEqual(total_results, 8)  # 2 health surveys × 3 policies + 1 funeral survey × 2 policies
        
        # Verify unique constraints
        for survey in SimpleSurvey.objects.all():
            survey_results = FeatureComparisonResult.objects.filter(survey=survey)
            policy_ids = [result.policy.id for result in survey_results]
            self.assertEqual(len(policy_ids), len(set(policy_ids)))  # No duplicate policy results per survey
        
        # Verify ranking consistency
        for survey in SimpleSurvey.objects.all():
            survey_results = FeatureComparisonResult.objects.filter(survey=survey).order_by('compatibility_rank')
            ranks = [result.compatibility_rank for result in survey_results]
            expected_ranks = list(range(1, len(ranks) + 1))
            self.assertEqual(ranks, expected_ranks)
    
    def test_performance_with_realistic_data_volume(self):
        """Test performance with realistic data volumes."""
        import time
        
        # Create 20 surveys with different profiles
        surveys = []
        for i in range(20):
            if i % 3 == 0:  # Funeral surveys
                survey = SimpleSurvey.objects.create(
                    first_name=f'Funeral{i}',
                    last_name='User',
                    date_of_birth=date(1980 + i % 20, 1, 1),
                    insurance_type='FUNERAL',
                    preferred_cover_amount=Decimal(str(30000 + i * 2000)),
                    marital_status='Married' if i % 2 == 0 else 'Single',
                    gender='Male' if i % 2 == 0 else 'Female',
                    net_income=Decimal(str(8000 + i * 500))
                )
            else:  # Health surveys
                survey = SimpleSurvey.objects.create(
                    first_name=f'Health{i}',
                    last_name='User',
                    date_of_birth=date(1980 + i % 20, 1, 1),
                    insurance_type='HEALTH',
                    preferred_annual_limit=Decimal(str(50000 + i * 5000)),
                    household_income=Decimal(str(8000 + i * 1000)),
                    wants_in_hospital_benefit=True,
                    wants_out_hospital_benefit=i % 2 == 0,
                    needs_chronic_medication=i % 3 == 0
                )
            surveys.append(survey)
        
        # Process all surveys and measure time
        start_time = time.time()
        
        manager = FeatureComparisonManager()
        total_results = 0
        
        for survey in surveys:
            if survey.insurance_type == 'HEALTH':
                policies = [self.health_policy_premium, self.health_policy_standard, self.health_policy_basic]
            else:
                policies = [self.funeral_policy_comprehensive, self.funeral_policy_standard]
            
            results = manager.generate_comparison_results(
                survey,
                policies,
                force_regenerate=True
            )
            total_results += len(results)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify results
        expected_results = (14 * 3) + (6 * 2)  # 14 health surveys × 3 policies + 6 funeral surveys × 2 policies
        self.assertEqual(total_results, expected_results)
        
        # Performance should be reasonable (less than 10 seconds for 20 surveys)
        self.assertLess(execution_time, 10.0, f"Processing took {execution_time:.2f} seconds, which is too slow")
        
        # Verify database state
        db_results = FeatureComparisonResult.objects.count()
        self.assertEqual(db_results, expected_results)