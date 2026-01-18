"""
Unit tests for policy models.
Tests all new models including PolicyFeatures, AdditionalFeatures, and BasePolicy enhancements.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

from organizations.models import Organization
from .models import (
    PolicyCategory, PolicyType, BasePolicy, PolicyFeatures, 
    AdditionalFeatures, PolicyEligibility, PolicyExclusion,
    PolicyDocument, PolicyPremiumCalculation, PolicyReview
)

User = get_user_model()


class PolicyCategoryModelTest(TestCase):
    """Test PolicyCategory model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies",
            icon="fa-heart",
            display_order=1
        )
    
    def test_category_creation(self):
        """Test category creation and string representation."""
        self.assertEqual(self.category.name, "Health Insurance")
        self.assertEqual(self.category.slug, "health")
        self.assertTrue(self.category.is_active)
        self.assertEqual(str(self.category), "Health Insurance")
    
    def test_category_ordering(self):
        """Test category ordering by display_order and name."""
        category2 = PolicyCategory.objects.create(
            name="Funeral Insurance",
            slug="funeral",
            description="Funeral insurance policies",
            display_order=2
        )
        
        categories = list(PolicyCategory.objects.all())
        self.assertEqual(categories[0], self.category)
        self.assertEqual(categories[1], category2)
    
    def test_category_unique_constraints(self):
        """Test unique constraints on name and slug."""
        with self.assertRaises(Exception):
            PolicyCategory.objects.create(
                name="Health Insurance",  # Duplicate name
                slug="health-duplicate",
                description="Duplicate health category"
            )
        
        with self.assertRaises(Exception):
            PolicyCategory.objects.create(
                name="Health Insurance Duplicate",
                slug="health",  # Duplicate slug
                description="Duplicate health category"
            )


class PolicyTypeModelTest(TestCase):
    """Test PolicyType model functionality."""
    
    def setUp(self):
        """Set up test data."""
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
    
    def test_policy_type_creation(self):
        """Test policy type creation and string representation."""
        self.assertEqual(self.policy_type.name, "Comprehensive")
        self.assertEqual(self.policy_type.category, self.category)
        self.assertTrue(self.policy_type.is_active)
        self.assertEqual(str(self.policy_type), "Health Insurance - Comprehensive")
    
    def test_policy_type_unique_together(self):
        """Test unique_together constraint on category and slug."""
        with self.assertRaises(Exception):
            PolicyType.objects.create(
                category=self.category,
                name="Comprehensive Duplicate",
                slug="comprehensive",  # Duplicate slug within same category
                description="Duplicate comprehensive type"
            )
    
    def test_policy_type_ordering(self):
        """Test policy type ordering."""
        type2 = PolicyType.objects.create(
            category=self.category,
            name="Basic",
            slug="basic",
            description="Basic health coverage",
            display_order=1
        )
        
        types = list(PolicyType.objects.all())
        self.assertEqual(types[0], type2)  # Lower display_order comes first
        self.assertEqual(types[1], self.policy_type)


class BasePolicyModelTest(TestCase):
    """Test BasePolicy model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
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
            description="Test health policy description",
            short_description="Test health policy",
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            minimum_age=18,
            maximum_age=65,
            waiting_period_days=30,
            terms_and_conditions="Test terms and conditions"
        )
    
    def test_policy_creation(self):
        """Test policy creation and string representation."""
        self.assertEqual(self.policy.name, "Test Health Policy")
        self.assertEqual(self.policy.organization, self.organization)
        self.assertEqual(self.policy.category, self.category)
        self.assertEqual(self.policy.base_premium, Decimal('500.00'))
        self.assertEqual(str(self.policy), "Test Health Policy - Test Insurance Co")
    
    def test_policy_approval_status(self):
        """Test policy approval status functionality."""
        self.assertEqual(self.policy.approval_status, BasePolicy.ApprovalStatus.DRAFT)
        self.assertFalse(self.policy.is_approved())
        
        # Approve policy
        self.policy.approval_status = BasePolicy.ApprovalStatus.APPROVED
        self.policy.approved_by = self.user
        self.policy.save()
        
        self.assertTrue(self.policy.is_approved())
    
    def test_policy_activation_requirements(self):
        """Test policy activation requirements."""
        # Initially cannot be activated (not approved)
        self.assertFalse(self.policy.can_be_activated())
        
        # Approve policy
        self.policy.approval_status = BasePolicy.ApprovalStatus.APPROVED
        self.policy.save()
        
        # Should be able to activate now
        self.assertTrue(self.policy.can_be_activated())
    
    def test_policy_view_increment(self):
        """Test view count increment."""
        initial_views = self.policy.views_count
        self.policy.increment_views()
        self.assertEqual(self.policy.views_count, initial_views + 1)
    
    def test_policy_comparison_increment(self):
        """Test comparison count increment."""
        initial_comparisons = self.policy.comparison_count
        self.policy.increment_comparisons()
        self.assertEqual(self.policy.comparison_count, initial_comparisons + 1)
    
    def test_policy_feature_methods_without_features(self):
        """Test policy feature methods when no features exist."""
        self.assertIsNone(self.policy.get_policy_features())
        self.assertIsNone(self.policy.get_feature_value('annual_limit_per_member'))
        self.assertEqual(self.policy.get_all_features_dict(), {})
    
    def test_policy_unique_policy_number(self):
        """Test unique constraint on policy_number."""
        with self.assertRaises(Exception):
            BasePolicy.objects.create(
                organization=self.organization,
                category=self.category,
                policy_type=self.policy_type,
                name="Duplicate Policy",
                policy_number="TEST-001",  # Duplicate policy number
                description="Duplicate policy",
                short_description="Duplicate",
                base_premium=Decimal('400.00'),
                coverage_amount=Decimal('80000.00'),
                minimum_age=18,
                maximum_age=65,
                terms_and_conditions="Test terms"
            )


class PolicyFeaturesModelTest(TestCase):
    """Test PolicyFeatures model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            slug="test-insurance",
            email="test@insurance.com",
            phone="+268123456789",
            is_verified=True
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
    
    def test_health_policy_features_creation(self):
        """Test creating health policy features."""
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00'),
            monthly_household_income=Decimal('10000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        self.assertEqual(features.policy, self.health_policy)
        self.assertEqual(features.insurance_type, PolicyFeatures.InsuranceType.HEALTH)
        self.assertEqual(features.annual_limit_per_member, Decimal('50000.00'))
        self.assertTrue(features.in_hospital_benefit)
        self.assertEqual(str(features), "Test Health Policy - Health Policies Features")
    
    def test_funeral_policy_features_creation(self):
        """Test creating funeral policy features."""
        features = PolicyFeatures.objects.create(
            policy=self.funeral_policy,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('25000.00'),
            marital_status_requirement='Any',
            gender_requirement='Any',
            monthly_net_income=Decimal('5000.00')
        )
        
        self.assertEqual(features.policy, self.funeral_policy)
        self.assertEqual(features.insurance_type, PolicyFeatures.InsuranceType.FUNERAL)
        self.assertEqual(features.cover_amount, Decimal('25000.00'))
        self.assertEqual(features.marital_status_requirement, 'Any')
        self.assertEqual(str(features), "Test Funeral Policy - Funeral Policies Features")
    
    def test_policy_features_one_to_one_relationship(self):
        """Test one-to-one relationship between policy and features."""
        # Create first features
        features1 = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00')
        )
        
        # Try to create second features for same policy
        with self.assertRaises(Exception):
            PolicyFeatures.objects.create(
                policy=self.health_policy,
                insurance_type=PolicyFeatures.InsuranceType.HEALTH,
                annual_limit_per_member=Decimal('60000.00')
            )
    
    def test_policy_get_policy_features_method(self):
        """Test BasePolicy.get_policy_features() method."""
        # Initially no features
        self.assertIsNone(self.health_policy.get_policy_features())
        
        # Create features
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00'),
            in_hospital_benefit=True
        )
        
        # Should return features now
        retrieved_features = self.health_policy.get_policy_features()
        self.assertEqual(retrieved_features, features)
    
    def test_policy_get_feature_value_method(self):
        """Test BasePolicy.get_feature_value() method."""
        # Create features
        PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00'),
            in_hospital_benefit=True
        )
        
        # Test getting feature values
        self.assertEqual(
            self.health_policy.get_feature_value('annual_limit_per_member'),
            Decimal('50000.00')
        )
        self.assertTrue(self.health_policy.get_feature_value('in_hospital_benefit'))
        self.assertIsNone(self.health_policy.get_feature_value('nonexistent_feature'))
    
    def test_policy_get_all_features_dict_health(self):
        """Test BasePolicy.get_all_features_dict() for health policies."""
        # Create health features
        PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00'),
            monthly_household_income=Decimal('10000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=False,
            chronic_medication_availability=True
        )
        
        features_dict = self.health_policy.get_all_features_dict()
        
        expected_features = {
            'annual_limit_per_member': Decimal('50000.00'),
            'monthly_household_income': Decimal('10000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': False,
            'chronic_medication_availability': True
        }
        
        self.assertEqual(features_dict, expected_features)
    
    def test_policy_get_all_features_dict_funeral(self):
        """Test BasePolicy.get_all_features_dict() for funeral policies."""
        # Create funeral features
        PolicyFeatures.objects.create(
            policy=self.funeral_policy,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('25000.00'),
            marital_status_requirement='Married',
            gender_requirement='Any',
            monthly_net_income=Decimal('5000.00')
        )
        
        features_dict = self.funeral_policy.get_all_features_dict()
        
        expected_features = {
            'cover_amount': Decimal('25000.00'),
            'marital_status_requirement': 'Married',
            'gender_requirement': 'Any',
            'monthly_net_income': Decimal('5000.00')
        }
        
        self.assertEqual(features_dict, expected_features)
    
    def test_policy_features_null_values_excluded(self):
        """Test that null feature values are excluded from features dict."""
        # Create features with some null values
        PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('50000.00'),
            # Other fields left as null
        )
        
        features_dict = self.health_policy.get_all_features_dict()
        
        # Only non-null values should be included
        self.assertEqual(features_dict, {
            'annual_limit_per_member': Decimal('50000.00')
        })


class AdditionalFeaturesModelTest(TestCase):
    """Test AdditionalFeatures model functionality."""
    
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
    
    def test_additional_features_creation(self):
        """Test creating additional features."""
        feature = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="24/7 Customer Support",
            description="Round-the-clock customer support available",
            icon="fa-phone",
            is_highlighted=True,
            display_order=1
        )
        
        self.assertEqual(feature.policy, self.policy)
        self.assertEqual(feature.title, "24/7 Customer Support")
        self.assertTrue(feature.is_highlighted)
        self.assertEqual(str(feature), "24/7 Customer Support - Test Health Policy")
    
    def test_additional_features_ordering(self):
        """Test additional features ordering."""
        feature1 = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Feature 1",
            description="First feature",
            display_order=2
        )
        
        feature2 = AdditionalFeatures.objects.create(
            policy=self.policy,
            title="Feature 2",
            description="Second feature",
            display_order=1
        )
        
        features = list(AdditionalFeatures.objects.all())
        self.assertEqual(features[0], feature2)  # Lower display_order first
        self.assertEqual(features[1], feature1)
    
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


class PolicyEligibilityModelTest(TestCase):
    """Test PolicyEligibility model functionality."""
    
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
    
    def test_policy_eligibility_creation(self):
        """Test creating policy eligibility criteria."""
        eligibility = PolicyEligibility.objects.create(
            policy=self.policy,
            criterion="Must be a resident of Eswatini",
            description="Applicant must be a legal resident of Eswatini",
            is_mandatory=True,
            display_order=1
        )
        
        self.assertEqual(eligibility.policy, self.policy)
        self.assertEqual(eligibility.criterion, "Must be a resident of Eswatini")
        self.assertTrue(eligibility.is_mandatory)
        self.assertEqual(str(eligibility), "Must be a resident of Eswatini - Test Health Policy")


class PolicyExclusionModelTest(TestCase):
    """Test PolicyExclusion model functionality."""
    
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
    
    def test_policy_exclusion_creation(self):
        """Test creating policy exclusions."""
        exclusion = PolicyExclusion.objects.create(
            policy=self.policy,
            title="Pre-existing Conditions",
            description="Pre-existing medical conditions are not covered",
            display_order=1
        )
        
        self.assertEqual(exclusion.policy, self.policy)
        self.assertEqual(exclusion.title, "Pre-existing Conditions")
        self.assertEqual(str(exclusion), "Pre-existing Conditions - Test Health Policy")


class PolicyDocumentModelTest(TestCase):
    """Test PolicyDocument model functionality."""
    
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
    
    def test_policy_document_creation(self):
        """Test creating policy documents."""
        # Note: We're not actually uploading files in tests
        document = PolicyDocument.objects.create(
            policy=self.policy,
            document_type=PolicyDocument.DocumentType.BROCHURE,
            title="Policy Brochure",
            description="Detailed policy brochure",
            is_public=True
        )
        
        self.assertEqual(document.policy, self.policy)
        self.assertEqual(document.document_type, PolicyDocument.DocumentType.BROCHURE)
        self.assertTrue(document.is_public)
        self.assertEqual(str(document), "Policy Brochure - Test Health Policy")


class PolicyPremiumCalculationModelTest(TestCase):
    """Test PolicyPremiumCalculation model functionality."""
    
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
    
    def test_premium_calculation_creation(self):
        """Test creating premium calculation rules."""
        calculation = PolicyPremiumCalculation.objects.create(
            policy=self.policy,
            factor_name="age",
            factor_value="18-25",
            multiplier=Decimal('0.8'),
            additional_amount=Decimal('0.00'),
            description="Discount for young adults"
        )
        
        self.assertEqual(calculation.policy, self.policy)
        self.assertEqual(calculation.factor_name, "age")
        self.assertEqual(calculation.multiplier, Decimal('0.8'))
        self.assertEqual(str(calculation), "age=18-25 - Test Health Policy")
    
    def test_premium_calculation_method(self):
        """Test premium calculation method."""
        calculation = PolicyPremiumCalculation.objects.create(
            policy=self.policy,
            factor_name="age",
            factor_value="18-25",
            multiplier=Decimal('0.8'),
            additional_amount=Decimal('50.00')
        )
        
        base_premium = Decimal('500.00')
        calculated_premium = calculation.calculate_premium(base_premium)
        expected_premium = (base_premium * Decimal('0.8')) + Decimal('50.00')
        
        self.assertEqual(calculated_premium, expected_premium)
    
    def test_premium_calculation_unique_together(self):
        """Test unique_together constraint."""
        PolicyPremiumCalculation.objects.create(
            policy=self.policy,
            factor_name="age",
            factor_value="18-25",
            multiplier=Decimal('0.8')
        )
        
        # Try to create duplicate
        with self.assertRaises(Exception):
            PolicyPremiumCalculation.objects.create(
                policy=self.policy,
                factor_name="age",
                factor_value="18-25",  # Same combination
                multiplier=Decimal('0.9')
            )


class PolicyReviewModelTest(TestCase):
    """Test PolicyReview model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
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
    
    def test_policy_review_creation(self):
        """Test creating policy reviews."""
        review = PolicyReview.objects.create(
            policy=self.policy,
            user=self.user,
            rating=5,
            title="Excellent Policy",
            comment="This policy provided excellent coverage and service.",
            is_verified_purchase=True
        )
        
        self.assertEqual(review.policy, self.policy)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.rating, 5)
        self.assertEqual(str(review), "Excellent Policy - Test Health Policy (5★)")
    
    def test_policy_review_unique_together(self):
        """Test unique_together constraint on policy and user."""
        PolicyReview.objects.create(
            policy=self.policy,
            user=self.user,
            rating=5,
            title="First Review",
            comment="First review comment"
        )
        
        # Try to create second review by same user for same policy
        with self.assertRaises(Exception):
            PolicyReview.objects.create(
                policy=self.policy,
                user=self.user,
                rating=4,
                title="Second Review",
                comment="Second review comment"
            )
    
    def test_policy_review_rating_validation(self):
        """Test rating validation (1-5 stars)."""
        # Valid rating
        review = PolicyReview(
            policy=self.policy,
            user=self.user,
            rating=3,
            title="Average Policy",
            comment="Average policy experience"
        )
        review.full_clean()  # Should not raise ValidationError
        
        # Invalid rating (too low)
        review.rating = 0
        with self.assertRaises(ValidationError):
            review.full_clean()
        
        # Invalid rating (too high)
        review.rating = 6
        with self.assertRaises(ValidationError):
            review.full_clean()