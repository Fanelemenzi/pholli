"""
Integration tests for feature matching system.
Tests the complete flow from survey creation to policy matching and results generation.
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date
from unittest.mock import patch, Mock

from organizations.models import Organization
from policies.models import (
    PolicyCategory, PolicyType, BasePolicy, PolicyFeatures, AdditionalFeatures
)
from simple_surveys.models import SimpleSurvey
from comparison.models import FeatureComparisonResult
from comparison.feature_matching_engine import FeatureMatchingEngine
from comparison.feature_comparison_manager import FeatureComparisonManager

User = get_user_model()


class FeatureMatchingIntegrationTest(TestCase):
    """Integration tests for feature matching functionality."""
    
    def setUp(self):
        """Set up comprehensive test data."""
        # Create organization
        self.organization = Organization.objects.create(
            name="Eswatini Insurance Co",
            slug="eswatini-insurance",
            email="info@eswatini-insurance.co.sz",
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
        
        self.health_basic = PolicyType.objects.create(
            category=self.health_category,
            name="Basic",
            slug="basic",
            description="Basic health coverage"
        )
        
        self.funeral_family = PolicyType.objects.create(
            category=self.funeral_category,
            name="Family",
            slug="family",
            description="Family funeral coverage"
        )
        
        # Create health policies with different feature sets
        self.health_policy_premium = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_comprehensive,
            name="Premium Health Plan",
            policy_number="HEALTH-PREMIUM-001",
            description="Premium health insurance with comprehensive coverage",
            short_description="Premium health plan",
            base_premium=Decimal('800.00'),
            coverage_amount=Decimal('200000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Premium health plan terms"
        )
        
        self.health_policy_standard = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_comprehensive,
            name="Standard Health Plan",
            policy_number="HEALTH-STANDARD-001",
            description="Standard health insurance with good coverage",
            short_description="Standard health plan",
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Standard health plan terms"
        )
        
        self.health_policy_basic = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_basic,
            name="Basic Health Plan",
            policy_number="HEALTH-BASIC-001",
            description="Basic health insurance with essential coverage",
            short_description="Basic health plan",
            base_premium=Decimal('300.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Basic health plan terms"
        )
        
        # Create funeral policies
        self.funeral_policy_comprehensive = BasePolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_family,
            name="Comprehensive Funeral Plan",
            policy_number="FUNERAL-COMP-001",
            description="Comprehensive funeral insurance for families",
            short_description="Comprehensive funeral plan",
            base_premium=Decimal('250.00'),
            coverage_amount=Decimal('75000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Comprehensive funeral plan terms"
        )
        
        self.funeral_policy_basic = BasePolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_family,
            name="Basic Funeral Plan",
            policy_number="FUNERAL-BASIC-001",
            description="Basic funeral insurance coverage",
            short_description="Basic funeral plan",
            base_premium=Decimal('150.00'),
            coverage_amount=Decimal('35000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Basic funeral plan terms"
        )
        
        # Create policy features for health policies
        self.health_premium_features = PolicyFeatures.objects.create(
            policy=self.health_policy_premium,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('150000.00'),
            monthly_household_income=Decimal('20000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        self.health_standard_features = PolicyFeatures.objects.create(
            policy=self.health_policy_standard,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('80000.00'),
            monthly_household_income=Decimal('12000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=False
        )
        
        self.health_basic_features = PolicyFeatures.objects.create(
            policy=self.health_policy_basic,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('40000.00'),
            monthly_household_income=Decimal('8000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=False,
            chronic_medication_availability=False
        )
        
        # Create policy features for funeral policies
        self.funeral_comprehensive_features = PolicyFeatures.objects.create(
            policy=self.funeral_policy_comprehensive,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('60000.00'),
            marital_status_requirement='Any',
            gender_requirement='Any',
            monthly_net_income=Decimal('15000.00')
        )
        
        self.funeral_basic_features = PolicyFeatures.objects.create(
            policy=self.funeral_policy_basic,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('30000.00'),
            marital_status_requirement='Married',
            gender_requirement='Any',
            monthly_net_income=Decimal('8000.00')
        )
        
        # Create additional features
        AdditionalFeatures.objects.create(
            policy=self.health_policy_premium,
            title="24/7 Emergency Hotline",
            description="Round-the-clock emergency medical assistance",
            is_highlighted=True,
            display_order=1
        )
        
        AdditionalFeatures.objects.create(
            policy=self.health_policy_premium,
            title="International Coverage",
            description="Coverage for medical emergencies while traveling",
            is_highlighted=True,
            display_order=2
        )
        
        AdditionalFeatures.objects.create(
            policy=self.funeral_policy_comprehensive,
            title="Repatriation Services",
            description="Transportation of deceased to home country",
            is_highlighted=True,
            display_order=1
        )
    
    def test_health_survey_to_policy_matching_perfect_match(self):
        """Test complete flow from health survey to policy matching with perfect match."""
        # Create health survey that perfectly matches premium policy
        survey = SimpleSurvey.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 3, 15),
            email="john.doe@example.com",
            phone="+268123456789",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            preferred_annual_limit=Decimal('120000.00'),  # Premium policy exceeds this
            household_income=Decimal('25000.00'),  # User exceeds premium policy requirement
            wants_in_hospital_benefit=True,  # Premium policy has this
            wants_out_hospital_benefit=True,  # Premium policy has this
            needs_chronic_medication=True  # Premium policy has this
        )
        
        # Test feature matching engine
        engine = FeatureMatchingEngine('HEALTH')
        
        # Test matching against premium policy
        premium_result = engine.calculate_policy_compatibility(
            self.health_policy_premium, 
            survey.get_preferences_dict()
        )
        
        self.assertGreater(premium_result['overall_score'], 0.9)  # Should be very high
        self.assertEqual(len(premium_result['matches']), 5)  # All features match
        self.assertEqual(len(premium_result['mismatches']), 0)  # No mismatches
        
        # Test matching against standard policy
        standard_result = engine.calculate_policy_compatibility(
            self.health_policy_standard,
            survey.get_preferences_dict()
        )
        
        self.assertLess(standard_result['overall_score'], premium_result['overall_score'])
        self.assertGreater(len(standard_result['mismatches']), 0)  # Should have chronic medication mismatch
        
        # Test matching against basic policy
        basic_result = engine.calculate_policy_compatibility(
            self.health_policy_basic,
            survey.get_preferences_dict()
        )
        
        self.assertLess(basic_result['overall_score'], standard_result['overall_score'])
        self.assertGreater(len(basic_result['mismatches']), len(standard_result['mismatches']))
    
    def test_health_survey_to_policy_matching_partial_match(self):
        """Test health survey matching with partial matches."""
        # Create health survey with mixed requirements
        survey = SimpleSurvey.objects.create(
            first_name="Jane",
            last_name="Smith",
            date_of_birth=date(1990, 7, 22),
            email="jane.smith@example.com",
            phone="+268987654321",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            preferred_annual_limit=Decimal('60000.00'),  # Between standard and basic
            household_income=Decimal('10000.00'),  # Meets standard but not premium
            wants_in_hospital_benefit=True,  # All policies have this
            wants_out_hospital_benefit=False,  # Basic policy matches this
            needs_chronic_medication=False  # Standard and basic match this
        )
        
        engine = FeatureMatchingEngine('HEALTH')
        
        # Test all policies
        policies = [self.health_policy_premium, self.health_policy_standard, self.health_policy_basic]
        results = []
        
        for policy in policies:
            result = engine.calculate_policy_compatibility(
                policy, 
                survey.get_preferences_dict()
            )
            results.append((policy, result))
        
        # Sort by score
        results.sort(key=lambda x: x[1]['overall_score'], reverse=True)
        
        # Standard policy should score highest (meets income, has good coverage, no chronic meds)
        self.assertEqual(results[0][0], self.health_policy_standard)
        
        # All should have reasonable scores
        for policy, result in results:
            self.assertGreater(result['overall_score'], 0.5)
    
    def test_funeral_survey_to_policy_matching(self):
        """Test complete flow from funeral survey to policy matching."""
        # Create funeral survey
        survey = SimpleSurvey.objects.create(
            first_name="Robert",
            last_name="Johnson",
            date_of_birth=date(1975, 11, 8),
            email="robert.johnson@example.com",
            phone="+268555123456",
            insurance_type=SimpleSurvey.InsuranceType.FUNERAL,
            preferred_cover_amount=Decimal('50000.00'),
            marital_status='Married',
            gender='Male',
            net_income=Decimal('12000.00')
        )
        
        engine = FeatureMatchingEngine('FUNERAL')
        
        # Test comprehensive funeral policy
        comprehensive_result = engine.calculate_policy_compatibility(
            self.funeral_policy_comprehensive,
            survey.get_preferences_dict()
        )
        
        # Test basic funeral policy
        basic_result = engine.calculate_policy_compatibility(
            self.funeral_policy_basic,
            survey.get_preferences_dict()
        )
        
        # Comprehensive should score higher (better coverage, accepts any marital status)
        self.assertGreater(comprehensive_result['overall_score'], basic_result['overall_score'])
        
        # Basic policy should have marital status match but lower coverage
        self.assertIn('marital_status_requirement', 
                     [match['feature'].lower().replace(' ', '_') for match in basic_result['matches']])
    
    def test_cross_insurance_type_matching_prevention(self):
        """Test that health surveys don't match funeral policies and vice versa."""
        # Create health survey
        health_survey = SimpleSurvey.objects.create(
            first_name="Alice",
            last_name="Brown",
            date_of_birth=date(1988, 4, 12),
            email="alice.brown@example.com",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            preferred_annual_limit=Decimal('70000.00'),
            household_income=Decimal('15000.00'),
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=True,
            needs_chronic_medication=False
        )
        
        # Create funeral survey
        funeral_survey = SimpleSurvey.objects.create(
            first_name="Bob",
            last_name="Wilson",
            date_of_birth=date(1980, 9, 3),
            email="bob.wilson@example.com",
            insurance_type=SimpleSurvey.InsuranceType.FUNERAL,
            preferred_cover_amount=Decimal('40000.00'),
            marital_status='Single',
            gender='Male',
            net_income=Decimal('9000.00')
        )
        
        health_engine = FeatureMatchingEngine('HEALTH')
        funeral_engine = FeatureMatchingEngine('FUNERAL')
        
        # Test health survey against funeral policy (should fail)
        health_vs_funeral = health_engine.calculate_policy_compatibility(
            self.funeral_policy_comprehensive,
            health_survey.get_preferences_dict()
        )
        
        self.assertEqual(health_vs_funeral['overall_score'], 0.0)
        self.assertIn('Policy type does not match', health_vs_funeral['explanation'])
        
        # Test funeral survey against health policy (should fail)
        funeral_vs_health = funeral_engine.calculate_policy_compatibility(
            self.health_policy_standard,
            funeral_survey.get_preferences_dict()
        )
        
        self.assertEqual(funeral_vs_health['overall_score'], 0.0)
        self.assertIn('Policy type does not match', funeral_vs_health['explanation'])
    
    def test_feature_comparison_manager_integration(self):
        """Test FeatureComparisonManager integration with full workflow."""
        # Create health survey
        survey = SimpleSurvey.objects.create(
            first_name="Carol",
            last_name="Davis",
            date_of_birth=date(1992, 1, 28),
            email="carol.davis@example.com",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            preferred_annual_limit=Decimal('90000.00'),
            household_income=Decimal('18000.00'),
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=True,
            needs_chronic_medication=True
        )
        
        # Get all health policies
        health_policies = [
            self.health_policy_premium,
            self.health_policy_standard,
            self.health_policy_basic
        ]
        
        # Use FeatureComparisonManager to generate results
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            survey,
            health_policies,
            force_regenerate=True
        )
        
        # Should have results for all policies
        self.assertEqual(len(results), 3)
        
        # Results should be ordered by compatibility score
        scores = [result.overall_compatibility_score for result in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
        # Premium policy should rank highest (has chronic medication coverage)
        self.assertEqual(results[0].policy, self.health_policy_premium)
        self.assertEqual(results[0].compatibility_rank, 1)
        
        # Check that results are saved to database
        db_results = FeatureComparisonResult.objects.filter(survey=survey)
        self.assertEqual(db_results.count(), 3)
        
        # Test recommendation categories
        excellent_matches = db_results.filter(
            recommendation_category=FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH
        )
        self.assertGreater(excellent_matches.count(), 0)
    
    def test_feature_comparison_result_persistence(self):
        """Test that comparison results are properly persisted and retrievable."""
        # Create survey
        survey = SimpleSurvey.objects.create(
            first_name="David",
            last_name="Miller",
            date_of_birth=date(1987, 6, 14),
            email="david.miller@example.com",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            preferred_annual_limit=Decimal('100000.00'),
            household_income=Decimal('16000.00'),
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=False,
            needs_chronic_medication=False
        )
        
        # Generate comparison results
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            survey,
            [self.health_policy_standard],
            force_regenerate=True
        )
        
        # Verify result was saved
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Check all fields are properly saved
        self.assertIsNotNone(result.id)
        self.assertEqual(result.survey, survey)
        self.assertEqual(result.policy, self.health_policy_standard)
        self.assertGreater(result.overall_compatibility_score, 0)
        self.assertGreater(result.feature_match_count, 0)
        self.assertIsNotNone(result.feature_scores)
        self.assertIsNotNone(result.feature_matches)
        self.assertIsNotNone(result.match_explanation)
        self.assertIsNotNone(result.created_at)
        
        # Test retrieval from database
        db_result = FeatureComparisonResult.objects.get(
            survey=survey,
            policy=self.health_policy_standard
        )
        
        self.assertEqual(db_result.overall_compatibility_score, result.overall_compatibility_score)
        self.assertEqual(db_result.feature_scores, result.feature_scores)
        self.assertEqual(db_result.feature_matches, result.feature_matches)
    
    def test_empty_preferences_handling(self):
        """Test handling of surveys with empty or minimal preferences."""
        # Create survey with minimal data
        survey = SimpleSurvey.objects.create(
            first_name="Emma",
            last_name="Taylor",
            date_of_birth=date(1995, 12, 5),
            email="emma.taylor@example.com",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            # Only required fields, no preferences
        )
        
        engine = FeatureMatchingEngine('HEALTH')
        
        # Test matching with empty preferences
        result = engine.calculate_policy_compatibility(
            self.health_policy_standard,
            survey.get_preferences_dict()
        )
        
        # Should handle gracefully
        self.assertIsNotNone(result)
        self.assertIn('overall_score', result)
        self.assertEqual(result['overall_score'], 0.0)  # No preferences to match
        self.assertEqual(len(result['matches']), 0)
        self.assertEqual(len(result['mismatches']), 0)
    
    def test_policy_without_features_handling(self):
        """Test handling of policies without PolicyFeatures."""
        # Create policy without features
        policy_no_features = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_basic,
            name="Policy Without Features",
            policy_number="NO-FEATURES-001",
            description="Policy without features for testing",
            short_description="No features policy",
            base_premium=Decimal('400.00'),
            coverage_amount=Decimal('60000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="No features policy terms"
        )
        
        # Create survey
        survey = SimpleSurvey.objects.create(
            first_name="Frank",
            last_name="Anderson",
            date_of_birth=date(1983, 8, 19),
            email="frank.anderson@example.com",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            preferred_annual_limit=Decimal('50000.00'),
            household_income=Decimal('12000.00'),
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=True,
            needs_chronic_medication=False
        )
        
        engine = FeatureMatchingEngine('HEALTH')
        
        # Test matching against policy without features
        result = engine.calculate_policy_compatibility(
            policy_no_features,
            survey.get_preferences_dict()
        )
        
        # Should handle gracefully
        self.assertEqual(result['overall_score'], 0.0)
        self.assertEqual(len(result['matches']), 0)
        self.assertEqual(len(result['mismatches']), 0)
    
    def test_comprehensive_workflow_with_multiple_surveys(self):
        """Test comprehensive workflow with multiple surveys and policies."""
        # Create multiple surveys with different profiles
        surveys = [
            SimpleSurvey.objects.create(
                first_name="High",
                last_name="Earner",
                date_of_birth=date(1978, 2, 10),
                email="high.earner@example.com",
                insurance_type=SimpleSurvey.InsuranceType.HEALTH,
                preferred_annual_limit=Decimal('200000.00'),
                household_income=Decimal('30000.00'),
                wants_in_hospital_benefit=True,
                wants_out_hospital_benefit=True,
                needs_chronic_medication=True
            ),
            SimpleSurvey.objects.create(
                first_name="Budget",
                last_name="Conscious",
                date_of_birth=date(1993, 5, 25),
                email="budget.conscious@example.com",
                insurance_type=SimpleSurvey.InsuranceType.HEALTH,
                preferred_annual_limit=Decimal('30000.00'),
                household_income=Decimal('6000.00'),
                wants_in_hospital_benefit=True,
                wants_out_hospital_benefit=False,
                needs_chronic_medication=False
            ),
            SimpleSurvey.objects.create(
                first_name="Family",
                last_name="Person",
                date_of_birth=date(1982, 10, 3),
                email="family.person@example.com",
                insurance_type=SimpleSurvey.InsuranceType.FUNERAL,
                preferred_cover_amount=Decimal('45000.00'),
                marital_status='Married',
                gender='Female',
                net_income=Decimal('11000.00')
            )
        ]
        
        manager = FeatureComparisonManager()
        
        # Process each survey
        for survey in surveys:
            if survey.insurance_type == SimpleSurvey.InsuranceType.HEALTH:
                policies = [self.health_policy_premium, self.health_policy_standard, self.health_policy_basic]
            else:
                policies = [self.funeral_policy_comprehensive, self.funeral_policy_basic]
            
            results = manager.generate_comparison_results(
                survey,
                policies,
                force_regenerate=True
            )
            
            # Verify results
            self.assertEqual(len(results), len(policies))
            self.assertTrue(all(result.survey == survey for result in results))
            
            # Check ranking
            for i, result in enumerate(results):
                self.assertEqual(result.compatibility_rank, i + 1)
        
        # Verify all results are in database
        total_expected_results = 3 + 3 + 2  # 3 health policies for 2 health surveys + 2 funeral policies for 1 funeral survey
        total_db_results = FeatureComparisonResult.objects.count()
        self.assertEqual(total_db_results, total_expected_results)
        
        # Test querying by survey type
        health_results = FeatureComparisonResult.objects.filter(
            survey__insurance_type=SimpleSurvey.InsuranceType.HEALTH
        )
        funeral_results = FeatureComparisonResult.objects.filter(
            survey__insurance_type=SimpleSurvey.InsuranceType.FUNERAL
        )
        
        self.assertEqual(health_results.count(), 6)  # 2 surveys × 3 policies
        self.assertEqual(funeral_results.count(), 2)  # 1 survey × 2 policies


class FeatureMatchingPerformanceTest(TransactionTestCase):
    """Performance tests for feature matching system."""
    
    def setUp(self):
        """Set up performance test data."""
        # Create organization
        self.organization = Organization.objects.create(
            name="Performance Test Insurance",
            slug="performance-test",
            email="test@performance.com",
            phone="+268999999999",
            is_verified=True
        )
        
        # Create category
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.policy_type = PolicyType.objects.create(
            category=self.category,
            name="Standard",
            slug="standard",
            description="Standard coverage"
        )
    
    def test_large_scale_policy_matching(self):
        """Test performance with large number of policies."""
        # Create 50 policies with features
        policies = []
        for i in range(50):
            policy = BasePolicy.objects.create(
                organization=self.organization,
                category=self.category,
                policy_type=self.policy_type,
                name=f"Test Policy {i+1}",
                policy_number=f"PERF-{i+1:03d}",
                description=f"Performance test policy {i+1}",
                short_description=f"Test policy {i+1}",
                base_premium=Decimal(str(300 + i * 10)),
                coverage_amount=Decimal(str(50000 + i * 1000)),
                minimum_age=18,
                maximum_age=65,
                terms_and_conditions="Performance test terms"
            )
            
            PolicyFeatures.objects.create(
                policy=policy,
                insurance_type=PolicyFeatures.InsuranceType.HEALTH,
                annual_limit_per_member=Decimal(str(40000 + i * 2000)),
                monthly_household_income=Decimal(str(8000 + i * 200)),
                in_hospital_benefit=i % 2 == 0,
                out_hospital_benefit=i % 3 == 0,
                chronic_medication_availability=i % 4 == 0
            )
            
            policies.append(policy)
        
        # Create survey
        survey = SimpleSurvey.objects.create(
            first_name="Performance",
            last_name="Test",
            date_of_birth=date(1990, 1, 1),
            email="performance@test.com",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            preferred_annual_limit=Decimal('80000.00'),
            household_income=Decimal('15000.00'),
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=True,
            needs_chronic_medication=False
        )
        
        # Test performance of matching
        import time
        start_time = time.time()
        
        manager = FeatureComparisonManager()
        results = manager.generate_comparison_results(
            survey,
            policies,
            force_regenerate=True
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify results
        self.assertEqual(len(results), 50)
        self.assertTrue(all(isinstance(result, FeatureComparisonResult) for result in results))
        
        # Performance should be reasonable (less than 5 seconds for 50 policies)
        self.assertLess(execution_time, 5.0, f"Matching took {execution_time:.2f} seconds, which is too slow")
        
        # Verify database operations
        db_results = FeatureComparisonResult.objects.filter(survey=survey)
        self.assertEqual(db_results.count(), 50)
    
    def test_concurrent_survey_processing(self):
        """Test handling of concurrent survey processing."""
        # Create policies
        policies = []
        for i in range(10):
            policy = BasePolicy.objects.create(
                organization=self.organization,
                category=self.category,
                policy_type=self.policy_type,
                name=f"Concurrent Test Policy {i+1}",
                policy_number=f"CONC-{i+1:03d}",
                description=f"Concurrent test policy {i+1}",
                short_description=f"Concurrent policy {i+1}",
                base_premium=Decimal(str(400 + i * 50)),
                coverage_amount=Decimal(str(60000 + i * 5000)),
                minimum_age=18,
                maximum_age=65,
                terms_and_conditions="Concurrent test terms"
            )
            
            PolicyFeatures.objects.create(
                policy=policy,
                insurance_type=PolicyFeatures.InsuranceType.HEALTH,
                annual_limit_per_member=Decimal(str(50000 + i * 10000)),
                monthly_household_income=Decimal(str(10000 + i * 1000)),
                in_hospital_benefit=True,
                out_hospital_benefit=i % 2 == 0,
                chronic_medication_availability=i % 3 == 0
            )
            
            policies.append(policy)
        
        # Create multiple surveys
        surveys = []
        for i in range(5):
            survey = SimpleSurvey.objects.create(
                first_name=f"Concurrent{i+1}",
                last_name="Test",
                date_of_birth=date(1985 + i, 1, 1),
                email=f"concurrent{i+1}@test.com",
                insurance_type=SimpleSurvey.InsuranceType.HEALTH,
                preferred_annual_limit=Decimal(str(60000 + i * 20000)),
                household_income=Decimal(str(12000 + i * 2000)),
                wants_in_hospital_benefit=True,
                wants_out_hospital_benefit=i % 2 == 0,
                needs_chronic_medication=i % 3 == 0
            )
            surveys.append(survey)
        
        # Process all surveys
        manager = FeatureComparisonManager()
        all_results = []
        
        for survey in surveys:
            results = manager.generate_comparison_results(
                survey,
                policies,
                force_regenerate=True
            )
            all_results.extend(results)
        
        # Verify all results
        self.assertEqual(len(all_results), 50)  # 5 surveys × 10 policies
        
        # Verify database consistency
        total_db_results = FeatureComparisonResult.objects.count()
        self.assertEqual(total_db_results, 50)
        
        # Verify each survey has correct number of results
        for survey in surveys:
            survey_results = FeatureComparisonResult.objects.filter(survey=survey)
            self.assertEqual(survey_results.count(), 10)