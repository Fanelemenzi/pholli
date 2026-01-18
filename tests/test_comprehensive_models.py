"""
Comprehensive unit tests for all new models in the Eswatini policy system.
Tests PolicyFeatures, AdditionalFeatures, SimpleSurvey, and FeatureComparisonResult models.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

from organizations.models import Organization
from policies.models import (
    PolicyCategory, PolicyType, BasePolicy, PolicyFeatures, AdditionalFeatures
)
from simple_surveys.models import SimpleSurvey
from comparison.models import FeatureComparisonResult

User = get_user_model()


class PolicyFeaturesModelTest(TestCase):
    """Comprehensive tests for PolicyFeatures model."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            description="Test insurance company",
            email="test@insurance.com",
            phone="+268123456789",
            address_line1="123 Test Street",
            city="Mbabane",
            state_province="Hhohho",
            postal_code="H100",
            registration_number="REG123456",
            license_number="LIC123456",
            verification_status=Organization.VerificationStatus.VERIFIED
        )
        
        self.health_category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.funeral_category = PolicyCategory.objects.create(
            name="Funeral Insurance",
            slug="funeral",
            description="Funeral insurance policies"
        )
        
        self.health_type = PolicyType.objects.create(
            category=self.health_category,
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health coverage"
        )
        
        self.funeral_type = PolicyType.objects.create(
            category=self.funeral_category,
            name="Family",
            slug="family",
            description="Family funeral coverage"
        )
        
        self.health_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Test Health Policy",
            policy_number="HEALTH-001",
            description="Test health policy",
            short_description="Test health",
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms"
        )
        
        self.funeral_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_type,
            name="Test Funeral Policy",
            policy_number="FUNERAL-001",
            description="Test funeral policy",
            short_description="Test funeral",
            base_premium=Decimal('200.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Test terms"
        )
    
    def test_health_policy_features_creation_complete(self):
        """Test creating complete health policy features."""
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('100000.00'),
            monthly_household_income=Decimal('15000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        self.assertEqual(features.policy, self.health_policy)
        self.assertEqual(features.insurance_type, PolicyFeatures.InsuranceType.HEALTH)
        self.assertEqual(features.annual_limit_per_member, Decimal('100000.00'))
        self.assertEqual(features.monthly_household_income, Decimal('15000.00'))
        self.assertTrue(features.in_hospital_benefit)
        self.assertTrue(features.out_hospital_benefit)
        self.assertTrue(features.chronic_medication_availability)
        self.assertEqual(str(features), "Test Health Policy - Health Policies Features")
    
    def test_health_policy_features_creation_minimal(self):
        """Test creating minimal health policy features."""
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00'),
            monthly_household_income=Decimal('8000.00'),
            in_hospital_benefit=False,
            out_hospital_benefit=False,
            chronic_medication_availability=False
        )
        
        self.assertEqual(features.annual_limit_per_member, Decimal('50000.00'))
        self.assertFalse(features.in_hospital_benefit)
        self.assertFalse(features.out_hospital_benefit)
        self.assertFalse(features.chronic_medication_availability)
    
    def test_funeral_policy_features_creation_complete(self):
        """Test creating complete funeral policy features."""
        features = PolicyFeatures.objects.create(
            policy=self.funeral_policy,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('75000.00'),
            marital_status_requirement='Any',
            gender_requirement='Any',
            monthly_net_income=Decimal('12000.00')
        )
        
        self.assertEqual(features.policy, self.funeral_policy)
        self.assertEqual(features.insurance_type, PolicyFeatures.InsuranceType.FUNERAL)
        self.assertEqual(features.cover_amount, Decimal('75000.00'))
        self.assertEqual(features.marital_status_requirement, 'Any')
        self.assertEqual(features.gender_requirement, 'Any')
        self.assertEqual(features.monthly_net_income, Decimal('12000.00'))
        self.assertEqual(str(features), "Test Funeral Policy - Funeral Policies Features")
    
    def test_funeral_policy_features_creation_specific_requirements(self):
        """Test creating funeral policy features with specific requirements."""
        features = PolicyFeatures.objects.create(
            policy=self.funeral_policy,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('25000.00'),
            marital_status_requirement='Married',
            gender_requirement='Female',
            monthly_net_income=Decimal('5000.00')
        )
        
        self.assertEqual(features.marital_status_requirement, 'Married')
        self.assertEqual(features.gender_requirement, 'Female')
        self.assertEqual(features.monthly_net_income, Decimal('5000.00'))
    
    def test_policy_features_one_to_one_constraint(self):
        """Test one-to-one relationship constraint."""
        # Create first features
        PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00')
        )
        
        # Attempt to create second features for same policy should fail
        with self.assertRaises(Exception):
            PolicyFeatures.objects.create(
                policy=self.health_policy,
                insurance_type=PolicyFeatures.InsuranceType.HEALTH,
                annual_limit_per_member=Decimal('60000.00')
            )
    
    def test_policy_features_decimal_precision(self):
        """Test decimal field precision and scale."""
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('9999999999.99'),  # Max for 12,2
            monthly_household_income=Decimal('99999999.99')    # Max for 10,2
        )
        
        self.assertEqual(features.annual_limit_per_member, Decimal('9999999999.99'))
        self.assertEqual(features.monthly_household_income, Decimal('99999999.99'))
    
    def test_policy_features_null_values(self):
        """Test handling of null values in features."""
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            # All other fields left as null
        )
        
        self.assertIsNone(features.annual_limit_per_member)
        self.assertIsNone(features.monthly_household_income)
        self.assertIsNone(features.in_hospital_benefit)
        self.assertIsNone(features.out_hospital_benefit)
        self.assertIsNone(features.chronic_medication_availability)
    
    def test_policy_features_timestamps(self):
        """Test automatic timestamp creation and updates."""
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00')
        )
        
        self.assertIsNotNone(features.created_at)
        self.assertIsNotNone(features.updated_at)
        
        # Update and check timestamp changes
        original_updated_at = features.updated_at
        features.annual_limit_per_member = Decimal('60000.00')
        features.save()
        
        self.assertGreater(features.updated_at, original_updated_at)
    
    def test_policy_features_meta_configuration(self):
        """Test model meta configuration."""
        self.assertEqual(PolicyFeatures._meta.verbose_name, "Policy Features")
        self.assertEqual(PolicyFeatures._meta.verbose_name_plural, "Policy Features")


class AdditionalFeaturesModelTest(TestCase):
    """Comprehensive tests for AdditionalFeatures model."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            slug="test-insurance",
            email="test@insurance.com",
            phone="+268123456789",
            is_verified=True
        )
        
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.policy_type = PolicyType.objects.create(
            category=self.category,
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health coverage"
        )
        
        self.policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Test Health Policy",
            policy_number="TEST-001",
            description="Test health policy",
            short_description="Test health",
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms"
        )
    
    def test_additional_features_creation_complete(self):
        """Test creating complete additional features."""
        feature = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="24/7 Customer Support",
            description="Round-the-clock customer support available via phone, email, and chat",
            icon="fa-phone",
            is_highlighted=True,
            display_order=1
        )
        
        self.assertEqual(feature.policy, self.policy)
        self.assertEqual(feature.title, "24/7 Customer Support")
        self.assertEqual(feature.description, "Round-the-clock customer support available via phone, email, and chat")
        self.assertEqual(feature.icon, "fa-phone")
        self.assertTrue(feature.is_highlighted)
        self.assertEqual(feature.display_order, 1)
        self.assertEqual(str(feature), "24/7 Customer Support - Test Health Policy")
    
    def test_additional_features_creation_minimal(self):
        """Test creating minimal additional features."""
        feature = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Basic Support",
            description="Standard customer support during business hours"
        )
        
        self.assertEqual(feature.title, "Basic Support")
        self.assertEqual(feature.icon, "")  # Default empty
        self.assertFalse(feature.is_highlighted)  # Default False
        self.assertEqual(feature.display_order, 0)  # Default 0
    
    def test_additional_features_ordering(self):
        """Test additional features ordering."""
        feature1 = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Feature 1",
            description="First feature",
            display_order=3
        )
        
        feature2 = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Feature 2",
            description="Second feature",
            display_order=1
        )
        
        feature3 = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Feature 3",
            description="Third feature",
            display_order=2
        )
        
        features = list(AdditionalFeatures.objects.all())
        self.assertEqual(features[0], feature2)  # display_order=1
        self.assertEqual(features[1], feature3)  # display_order=2
        self.assertEqual(features[2], feature1)  # display_order=3
    
    def test_additional_features_relationship(self):
        """Test relationship with policy."""
        feature1 = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Feature 1",
            description="First feature"
        )
        
        feature2 = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Feature 2",
            description="Second feature"
        )
        
        # Test reverse relationship
        policy_features = self.policy.additional_features.all()
        self.assertIn(feature1, policy_features)
        self.assertIn(feature2, policy_features)
        self.assertEqual(policy_features.count(), 2)
    
    def test_additional_features_highlighting(self):
        """Test highlighting functionality."""
        highlighted_feature = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Premium Feature",
            description="This is a premium feature",
            is_highlighted=True
        )
        
        regular_feature = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Regular Feature",
            description="This is a regular feature",
            is_highlighted=False
        )
        
        highlighted_features = AdditionalFeatures.objects.filter(is_highlighted=True)
        self.assertIn(highlighted_feature, highlighted_features)
        self.assertNotIn(regular_feature, highlighted_features)
    
    def test_additional_features_timestamps(self):
        """Test automatic timestamp creation."""
        feature = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Test Feature",
            description="Test feature description"
        )
        
        self.assertIsNotNone(feature.created_at)
    
    def test_additional_features_meta_configuration(self):
        """Test model meta configuration."""
        self.assertEqual(AdditionalFeatures._meta.verbose_name, "Additional Features")
        self.assertEqual(AdditionalFeatures._meta.verbose_name_plural, "Additional Features")
        
        # Test ordering
        expected_ordering = ['policy', 'display_order', 'title']
        self.assertEqual(AdditionalFeatures._meta.ordering, expected_ordering)
        
        # Test indexes
        index_fields = [index.fields for index in AdditionalFeatures._meta.indexes]
        self.assertIn(['policy', 'is_highlighted'], index_fields)


class SimpleSurveyModelTest(TestCase):
    """Comprehensive tests for SimpleSurvey model."""
    
    def setUp(self):
        """Set up test data."""
        self.health_survey_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': date(1990, 1, 1),
            'email': 'john@example.com',
            'phone': '+268123456789',
            'insurance_type': SimpleSurvey.InsuranceType.HEALTH,
            'preferred_annual_limit': Decimal('75000.00'),
            'household_income': Decimal('12000.00'),
            'wants_in_hospital_benefit': True,
            'wants_out_hospital_benefit': True,
            'needs_chronic_medication': False
        }
        
        self.funeral_survey_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': date(1985, 5, 15),
            'email': 'jane@example.com',
            'phone': '+268987654321',
            'insurance_type': SimpleSurvey.InsuranceType.FUNERAL,
            'preferred_cover_amount': Decimal('50000.00'),
            'marital_status': 'Married',
            'gender': 'Female',
            'net_income': Decimal('10000.00')
        }
    
    def test_health_survey_creation_complete(self):
        """Test creating complete health survey."""
        survey = SimpleSurvey.objects.create(**self.health_survey_data)
        
        self.assertEqual(survey.first_name, 'John')
        self.assertEqual(survey.last_name, 'Doe')
        self.assertEqual(survey.date_of_birth, date(1990, 1, 1))
        self.assertEqual(survey.email, 'john@example.com')
        self.assertEqual(survey.phone, '+268123456789')
        self.assertEqual(survey.insurance_type, SimpleSurvey.InsuranceType.HEALTH)
        self.assertEqual(survey.preferred_annual_limit, Decimal('75000.00'))
        self.assertEqual(survey.household_income, Decimal('12000.00'))
        self.assertTrue(survey.wants_in_hospital_benefit)
        self.assertTrue(survey.wants_out_hospital_benefit)
        self.assertFalse(survey.needs_chronic_medication)
        self.assertEqual(str(survey), "John Doe - Health Policies")
    
    def test_funeral_survey_creation_complete(self):
        """Test creating complete funeral survey."""
        survey = SimpleSurvey.objects.create(**self.funeral_survey_data)
        
        self.assertEqual(survey.first_name, 'Jane')
        self.assertEqual(survey.last_name, 'Smith')
        self.assertEqual(survey.date_of_birth, date(1985, 5, 15))
        self.assertEqual(survey.email, 'jane@example.com')
        self.assertEqual(survey.phone, '+268987654321')
        self.assertEqual(survey.insurance_type, SimpleSurvey.InsuranceType.FUNERAL)
        self.assertEqual(survey.preferred_cover_amount, Decimal('50000.00'))
        self.assertEqual(survey.marital_status, 'Married')
        self.assertEqual(survey.gender, 'Female')
        self.assertEqual(survey.net_income, Decimal('10000.00'))
        self.assertEqual(str(survey), "Jane Smith - Funeral Policies")
    
    def test_survey_optional_fields(self):
        """Test that email and phone are optional."""
        data = self.health_survey_data.copy()
        data['email'] = ''
        data['phone'] = ''
        
        survey = SimpleSurvey.objects.create(**data)
        self.assertEqual(survey.email, '')
        self.assertEqual(survey.phone, '')
    
    def test_health_survey_get_preferences_dict(self):
        """Test get_preferences_dict for health survey."""
        survey = SimpleSurvey.objects.create(**self.health_survey_data)
        preferences = survey.get_preferences_dict()
        
        expected_preferences = {
            'annual_limit_per_member': Decimal('75000.00'),
            'monthly_household_income': Decimal('12000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': True,
            'chronic_medication_availability': False
        }
        
        self.assertEqual(preferences, expected_preferences)
    
    def test_funeral_survey_get_preferences_dict(self):
        """Test get_preferences_dict for funeral survey."""
        survey = SimpleSurvey.objects.create(**self.funeral_survey_data)
        preferences = survey.get_preferences_dict()
        
        expected_preferences = {
            'cover_amount': Decimal('50000.00'),
            'marital_status_requirement': 'Married',
            'gender_requirement': 'Female',
            'monthly_net_income': Decimal('10000.00')
        }
        
        self.assertEqual(preferences, expected_preferences)
    
    def test_survey_get_preferences_dict_unknown_type(self):
        """Test get_preferences_dict for unknown insurance type."""
        data = self.health_survey_data.copy()
        survey = SimpleSurvey(**data)
        survey.insurance_type = 'UNKNOWN'  # Invalid type
        
        preferences = survey.get_preferences_dict()
        self.assertEqual(preferences, {})
    
    def test_survey_decimal_precision(self):
        """Test decimal field precision and scale."""
        data = self.health_survey_data.copy()
        data['preferred_annual_limit'] = Decimal('9999999999.99')  # Max for 12,2
        data['household_income'] = Decimal('99999999.99')  # Max for 10,2
        
        survey = SimpleSurvey.objects.create(**data)
        self.assertEqual(survey.preferred_annual_limit, Decimal('9999999999.99'))
        self.assertEqual(survey.household_income, Decimal('99999999.99'))
    
    def test_survey_boolean_combinations(self):
        """Test all boolean field combinations for health surveys."""
        boolean_combinations = [
            (True, True, True),
            (True, True, False),
            (True, False, True),
            (True, False, False),
            (False, True, True),
            (False, True, False),
            (False, False, True),
            (False, False, False),
        ]
        
        for in_hospital, out_hospital, chronic_med in boolean_combinations:
            data = self.health_survey_data.copy()
            data['wants_in_hospital_benefit'] = in_hospital
            data['wants_out_hospital_benefit'] = out_hospital
            data['needs_chronic_medication'] = chronic_med
            
            survey = SimpleSurvey.objects.create(**data)
            preferences = survey.get_preferences_dict()
            
            self.assertEqual(preferences['in_hospital_benefit'], in_hospital)
            self.assertEqual(preferences['out_hospital_benefit'], out_hospital)
            self.assertEqual(preferences['chronic_medication_availability'], chronic_med)
            
            # Clean up for next iteration
            survey.delete()
    
    def test_survey_timestamps(self):
        """Test automatic timestamp creation and updates."""
        survey = SimpleSurvey.objects.create(**self.health_survey_data)
        
        self.assertIsNotNone(survey.created_at)
        self.assertIsNotNone(survey.updated_at)
        
        # Update survey and check timestamp changes
        original_updated_at = survey.updated_at
        survey.first_name = 'Updated'
        survey.save()
        
        self.assertGreater(survey.updated_at, original_updated_at)
    
    def test_survey_meta_configuration(self):
        """Test model meta configuration."""
        self.assertEqual(SimpleSurvey._meta.verbose_name, "Simple Survey")
        self.assertEqual(SimpleSurvey._meta.verbose_name_plural, "Simple Surveys")
        
        # Test indexes
        index_fields = [index.fields for index in SimpleSurvey._meta.indexes]
        self.assertIn(['insurance_type', 'created_at'], index_fields)
        self.assertIn(['created_at'], index_fields)


class FeatureComparisonResultModelTest(TestCase):
    """Comprehensive tests for FeatureComparisonResult model."""
    
    def setUp(self):
        """Set up test data."""
        # Create organization
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            slug="test-insurance",
            email="test@insurance.com",
            phone="+268123456789",
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
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health coverage"
        )
        
        # Create policy
        self.policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Test Health Policy",
            policy_number="TEST-001",
            description="Test health policy",
            short_description="Test health",
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms"
        )
        
        # Create survey
        self.survey = SimpleSurvey.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1990, 1, 1),
            email="john@example.com",
            insurance_type=SimpleSurvey.InsuranceType.HEALTH,
            preferred_annual_limit=Decimal('50000.00'),
            household_income=Decimal('10000.00'),
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=True,
            needs_chronic_medication=False
        )
    
    def test_feature_comparison_result_creation_complete(self):
        """Test creating complete FeatureComparisonResult."""
        result = FeatureComparisonResult.objects.create(
            survey=self.survey,
            policy=self.policy,
            overall_compatibility_score=Decimal('87.50'),
            feature_match_count=4,
            feature_mismatch_count=1,
            feature_scores={
                'annual_limit_per_member': 0.9,
                'monthly_household_income': 1.0,
                'in_hospital_benefit': 1.0,
                'out_hospital_benefit': 1.0,
                'chronic_medication_availability': 0.0
            },
            feature_matches=[
                {'feature': 'Annual Limit per Member', 'score': 0.9, 'match_type': 'excellent'},
                {'feature': 'Monthly Household Income', 'score': 1.0, 'match_type': 'perfect'},
                {'feature': 'In-Hospital Benefit', 'score': 1.0, 'match_type': 'perfect'},
                {'feature': 'Out-Hospital Benefit', 'score': 1.0, 'match_type': 'perfect'}
            ],
            feature_mismatches=[
                {'feature': 'Chronic Medication Availability', 'score': 0.0, 'mismatch_severity': 'major'}
            ],
            compatibility_rank=1,
            recommendation_category=FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH,
            match_explanation="Excellent match with strong coverage alignment and good value"
        )
        
        self.assertEqual(result.survey, self.survey)
        self.assertEqual(result.policy, self.policy)
        self.assertEqual(result.overall_compatibility_score, Decimal('87.50'))
        self.assertEqual(result.feature_match_count, 4)
        self.assertEqual(result.feature_mismatch_count, 1)
        self.assertEqual(result.compatibility_rank, 1)
        self.assertEqual(result.recommendation_category, FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH)
        self.assertEqual(result.match_explanation, "Excellent match with strong coverage alignment and good value")
    
    def test_feature_comparison_result_json_fields(self):
        """Test JSON field functionality."""
        feature_scores = {
            'annual_limit_per_member': 0.85,
            'in_hospital_benefit': 1.0,
            'out_hospital_benefit': 0.6
        }
        
        feature_matches = [
            {'feature': 'In-Hospital Benefit', 'score': 1.0, 'user_preference': True, 'policy_value': True},
            {'feature': 'Annual Limit', 'score': 0.85, 'user_preference': 50000, 'policy_value': 60000}
        ]
        
        feature_mismatches = [
            {'feature': 'Out-Hospital Benefit', 'score': 0.6, 'user_preference': True, 'policy_value': False}
        ]
        
        result = FeatureComparisonResult.objects.create(
            survey=self.survey,
            policy=self.policy,
            overall_compatibility_score=Decimal('75.00'),
            feature_match_count=2,
            feature_mismatch_count=1,
            feature_scores=feature_scores,
            feature_matches=feature_matches,
            feature_mismatches=feature_mismatches,
            compatibility_rank=2,
            recommendation_category=FeatureComparisonResult.RecommendationCategory.GOOD_MATCH,
            match_explanation="Good match with some considerations"
        )
        
        # Test JSON field retrieval
        self.assertEqual(result.feature_scores, feature_scores)
        self.assertEqual(result.feature_matches, feature_matches)
        self.assertEqual(result.feature_mismatches, feature_mismatches)
        
        # Test JSON field querying
        results_with_hospital_benefit = FeatureComparisonResult.objects.filter(
            feature_scores__has_key='in_hospital_benefit'
        )
        self.assertIn(result, results_with_hospital_benefit)
    
    def test_feature_comparison_result_recommendation_categories(self):
        """Test all recommendation categories."""
        categories = [
            (Decimal('98.0'), FeatureComparisonResult.RecommendationCategory.PERFECT_MATCH),
            (Decimal('88.0'), FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH),
            (Decimal('72.0'), FeatureComparisonResult.RecommendationCategory.GOOD_MATCH),
            (Decimal('55.0'), FeatureComparisonResult.RecommendationCategory.PARTIAL_MATCH),
            (Decimal('25.0'), FeatureComparisonResult.RecommendationCategory.POOR_MATCH),
        ]
        
        for score, expected_category in categories:
            result = FeatureComparisonResult.objects.create(
                survey=self.survey,
                policy=self.policy,
                overall_compatibility_score=score,
                feature_match_count=3,
                feature_mismatch_count=2,
                compatibility_rank=1,
                recommendation_category=expected_category,
                match_explanation=f"Test explanation for {expected_category}"
            )
            
            self.assertEqual(result.recommendation_category, expected_category)
            result.delete()  # Clean up for next iteration
    
    def test_feature_comparison_result_unique_constraint(self):
        """Test unique constraint on survey-policy pair."""
        # Create first result
        FeatureComparisonResult.objects.create(
            survey=self.survey,
            policy=self.policy,
            overall_compatibility_score=Decimal('80.0'),
            feature_match_count=3,
            feature_mismatch_count=1,
            compatibility_rank=1,
            recommendation_category=FeatureComparisonResult.RecommendationCategory.GOOD_MATCH,
            match_explanation="First result"
        )
        
        # Attempt to create duplicate should fail
        with self.assertRaises(Exception):
            FeatureComparisonResult.objects.create(
                survey=self.survey,
                policy=self.policy,
                overall_compatibility_score=Decimal('85.0'),
                feature_match_count=4,
                feature_mismatch_count=0,
                compatibility_rank=1,
                recommendation_category=FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH,
                match_explanation="Duplicate result"
            )
    
    def test_feature_comparison_result_ordering(self):
        """Test default ordering by compatibility score."""
        # Create second policy for comparison
        policy2 = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Test Health Policy 2",
            policy_number="TEST-002",
            description="Second test health policy",
            short_description="Test health 2",
            base_premium=Decimal('600.00'),
            coverage_amount=Decimal('120000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms"
        )
        
        # Create results with different scores
        result1 = FeatureComparisonResult.objects.create(
            survey=self.survey,
            policy=self.policy,
            overall_compatibility_score=Decimal('75.0'),
            feature_match_count=3,
            feature_mismatch_count=2,
            compatibility_rank=2,
            recommendation_category=FeatureComparisonResult.RecommendationCategory.GOOD_MATCH,
            match_explanation="Lower score result"
        )
        
        result2 = FeatureComparisonResult.objects.create(
            survey=self.survey,
            policy=policy2,
            overall_compatibility_score=Decimal('90.0'),
            feature_match_count=4,
            feature_mismatch_count=1,
            compatibility_rank=1,
            recommendation_category=FeatureComparisonResult.RecommendationCategory.EXCELLENT_MATCH,
            match_explanation="Higher score result"
        )
        
        # Test ordering (highest score first)
        results = list(FeatureComparisonResult.objects.all())
        self.assertEqual(results[0], result2)  # Higher score first
        self.assertEqual(results[1], result1)  # Lower score second
    
    def test_feature_comparison_result_timestamps(self):
        """Test automatic timestamp creation."""
        result = FeatureComparisonResult.objects.create(
            survey=self.survey,
            policy=self.policy,
            overall_compatibility_score=Decimal('80.0'),
            feature_match_count=3,
            feature_mismatch_count=1,
            compatibility_rank=1,
            recommendation_category=FeatureComparisonResult.RecommendationCategory.GOOD_MATCH,
            match_explanation="Test result"
        )
        
        self.assertIsNotNone(result.created_at)
    
    def test_feature_comparison_result_meta_configuration(self):
        """Test model meta configuration."""
        # Test ordering
        expected_ordering = ['-overall_compatibility_score']
        self.assertEqual(FeatureComparisonResult._meta.ordering, expected_ordering)
        
        # Test unique_together constraint
        unique_together = FeatureComparisonResult._meta.unique_together
        self.assertIn(('survey', 'policy'), unique_together)


class BasePolicyEnhancementsTest(TestCase):
    """Test enhancements to BasePolicy model for feature access."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            slug="test-insurance",
            email="test@insurance.com",
            phone="+268123456789",
            is_verified=True
        )
        
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.policy_type = PolicyType.objects.create(
            category=self.category,
            name="Comprehensive",
            slug="comprehensive",
            description="Comprehensive health coverage"
        )
        
        self.policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.category,
            policy_type=self.policy_type,
            name="Test Health Policy",
            policy_number="TEST-001",
            description="Test health policy",
            short_description="Test health",
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms"
        )
    
    def test_get_policy_features_with_features(self):
        """Test get_policy_features when features exist."""
        features = PolicyFeatures.objects.create(
            policy=self.policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00'),
            in_hospital_benefit=True
        )
        
        retrieved_features = self.policy.get_policy_features()
        self.assertEqual(retrieved_features, features)
    
    def test_get_policy_features_without_features(self):
        """Test get_policy_features when no features exist."""
        retrieved_features = self.policy.get_policy_features()
        self.assertIsNone(retrieved_features)
    
    def test_get_feature_value_existing_feature(self):
        """Test get_feature_value for existing feature."""
        PolicyFeatures.objects.create(
            policy=self.policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('75000.00'),
            in_hospital_benefit=True
        )
        
        annual_limit = self.policy.get_feature_value('annual_limit_per_member')
        self.assertEqual(annual_limit, Decimal('75000.00'))
        
        hospital_benefit = self.policy.get_feature_value('in_hospital_benefit')
        self.assertTrue(hospital_benefit)
    
    def test_get_feature_value_nonexistent_feature(self):
        """Test get_feature_value for nonexistent feature."""
        PolicyFeatures.objects.create(
            policy=self.policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00')
        )
        
        nonexistent_value = self.policy.get_feature_value('nonexistent_feature')
        self.assertIsNone(nonexistent_value)
    
    def test_get_feature_value_no_features(self):
        """Test get_feature_value when no features exist."""
        feature_value = self.policy.get_feature_value('annual_limit_per_member')
        self.assertIsNone(feature_value)
    
    def test_get_all_features_dict_health_policy(self):
        """Test get_all_features_dict for health policy."""
        PolicyFeatures.objects.create(
            policy=self.policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('100000.00'),
            monthly_household_income=Decimal('15000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=False,
            chronic_medication_availability=True
        )
        
        features_dict = self.policy.get_all_features_dict()
        
        expected_features = {
            'annual_limit_per_member': Decimal('100000.00'),
            'monthly_household_income': Decimal('15000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': False,
            'chronic_medication_availability': True
        }
        
        self.assertEqual(features_dict, expected_features)
    
    def test_get_all_features_dict_funeral_policy(self):
        """Test get_all_features_dict for funeral policy."""
        # Create funeral policy
        funeral_category = PolicyCategory.objects.create(
            name="Funeral Insurance",
            slug="funeral",
            description="Funeral insurance policies"
        )
        
        funeral_type = PolicyType.objects.create(
            category=funeral_category,
            name="Family",
            slug="family",
            description="Family funeral coverage"
        )
        
        funeral_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=funeral_category,
            policy_type=funeral_type,
            name="Test Funeral Policy",
            policy_number="FUNERAL-001",
            description="Test funeral policy",
            short_description="Test funeral",
            base_premium=Decimal('200.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Test terms"
        )
        
        PolicyFeatures.objects.create(
            policy=funeral_policy,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('60000.00'),
            marital_status_requirement='Any',
            gender_requirement='Any',
            monthly_net_income=Decimal('8000.00')
        )
        
        features_dict = funeral_policy.get_all_features_dict()
        
        expected_features = {
            'cover_amount': Decimal('60000.00'),
            'marital_status_requirement': 'Any',
            'gender_requirement': 'Any',
            'monthly_net_income': Decimal('8000.00')
        }
        
        self.assertEqual(features_dict, expected_features)
    
    def test_get_all_features_dict_excludes_null_values(self):
        """Test that null values are excluded from features dict."""
        PolicyFeatures.objects.create(
            policy=self.policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00'),
            # Other fields left as null
        )
        
        features_dict = self.policy.get_all_features_dict()
        
        # Only non-null values should be included
        self.assertEqual(features_dict, {
            'annual_limit_per_member': Decimal('50000.00')
        })
    
    def test_get_all_features_dict_no_features(self):
        """Test get_all_features_dict when no features exist."""
        features_dict = self.policy.get_all_features_dict()
        self.assertEqual(features_dict, {})