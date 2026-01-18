from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from decimal import Decimal

from organizations.models import Organization
from .models import PolicyCategory, PolicyType, BasePolicy, PolicyFeatures, AdditionalFeatures
from .forms import PolicyFeaturesAdminForm, AdditionalFeaturesAdminForm


class PolicyFeaturesAdminTest(TestCase):
    """Test cases for PolicyFeatures admin interface"""
    
    def setUp(self):
        # Create test user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        
        # Create test organization
        self.organization = Organization.objects.create(
            name='Test Insurance Co',
            email='test@insurance.com',
            phone='+268123456789',
            is_verified=True
        )
        
        # Create test category and type
        self.health_category = PolicyCategory.objects.create(
            name='Health',
            slug='health',
            description='Health insurance policies'
        )
        
        self.funeral_category = PolicyCategory.objects.create(
            name='Funeral',
            slug='funeral',
            description='Funeral insurance policies'
        )
        
        self.policy_type = PolicyType.objects.create(
            category=self.health_category,
            name='Comprehensive',
            slug='comprehensive',
            description='Comprehensive health coverage'
        )
        
        # Create test policy
        self.health_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.policy_type,
            name='Test Health Policy',
            policy_number='TEST-001',
            description='Test health policy description',
            short_description='Test health policy',
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions='Test terms'
        )
        
        self.client = Client()
        self.client.force_login(self.admin_user)
    
    def test_policy_features_admin_form_validation_health(self):
        """Test PolicyFeaturesAdminForm validation for health policies"""
        # Valid health policy data
        valid_data = {
            'policy': self.health_policy.id,
            'insurance_type': 'HEALTH',
            'annual_limit_per_member': Decimal('25000.00'),
            'monthly_household_income': Decimal('5000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': True,
            'chronic_medication_availability': True
        }
        
        form = PolicyFeaturesAdminForm(data=valid_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_policy_features_admin_form_validation_funeral(self):
        """Test PolicyFeaturesAdminForm validation for funeral policies"""
        # Create funeral policy
        funeral_policy_type = PolicyType.objects.create(
            category=self.funeral_category,
            name='Basic Funeral',
            slug='basic-funeral',
            description='Basic funeral coverage'
        )
        
        funeral_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=funeral_policy_type,
            name='Test Funeral Policy',
            policy_number='TEST-002',
            description='Test funeral policy description',
            short_description='Test funeral policy',
            base_premium=Decimal('200.00'),
            coverage_amount=Decimal('15000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions='Test terms'
        )
        
        # Valid funeral policy data
        valid_data = {
            'policy': funeral_policy.id,
            'insurance_type': 'FUNERAL',
            'cover_amount': Decimal('15000.00'),
            'marital_status_requirement': 'any',
            'gender_requirement': 'any',
            'monthly_net_income': Decimal('3000.00')
        }
        
        form = PolicyFeaturesAdminForm(data=valid_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_policy_features_admin_form_mixed_features_error(self):
        """Test that mixing health and funeral features raises validation error"""
        # Invalid data with mixed features
        invalid_data = {
            'policy': self.health_policy.id,
            'insurance_type': 'HEALTH',
            'annual_limit_per_member': Decimal('25000.00'),
            'monthly_household_income': Decimal('5000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': True,
            'chronic_medication_availability': True,
            # These should not be filled for health policies
            'cover_amount': Decimal('15000.00'),
            'marital_status_requirement': 'married'
        }
        
        form = PolicyFeaturesAdminForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
    
    def test_policy_features_admin_form_negative_values_error(self):
        """Test that negative numeric values raise validation error"""
        invalid_data = {
            'policy': self.health_policy.id,
            'insurance_type': 'HEALTH',
            'annual_limit_per_member': Decimal('-1000.00'),  # Negative value
            'monthly_household_income': Decimal('5000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': True,
            'chronic_medication_availability': True
        }
        
        form = PolicyFeaturesAdminForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('annual_limit_per_member', form.errors)
    
    def test_additional_features_admin_form_validation(self):
        """Test AdditionalFeaturesAdminForm validation"""
        valid_data = {
            'policy': self.health_policy.id,
            'title': 'Test Additional Feature',
            'description': 'This is a test additional feature description that is long enough.',
            'icon': 'fa-star',
            'is_highlighted': True,
            'display_order': 1
        }
        
        form = AdditionalFeaturesAdminForm(data=valid_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_additional_features_admin_form_short_title_error(self):
        """Test that short titles raise validation error"""
        invalid_data = {
            'policy': self.health_policy.id,
            'title': 'AB',  # Too short
            'description': 'This is a test additional feature description that is long enough.',
            'icon': 'fa-star',
            'is_highlighted': True,
            'display_order': 1
        }
        
        form = AdditionalFeaturesAdminForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
    
    def test_additional_features_admin_form_short_description_error(self):
        """Test that short descriptions raise validation error"""
        invalid_data = {
            'policy': self.health_policy.id,
            'title': 'Test Feature',
            'description': 'Too short',  # Too short
            'icon': 'fa-star',
            'is_highlighted': True,
            'display_order': 1
        }
        
        form = AdditionalFeaturesAdminForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)
    
    def test_additional_features_admin_form_duplicate_title_error(self):
        """Test that duplicate titles for same policy raise validation error"""
        # Create existing feature
        AdditionalFeatures.objects.create(
            policy=self.health_policy,
            title='Existing Feature',
            description='This is an existing feature description.'
        )
        
        # Try to create another with same title
        invalid_data = {
            'policy': self.health_policy.id,
            'title': 'Existing Feature',  # Duplicate title
            'description': 'This is another feature with the same title.',
            'icon': 'fa-star',
            'is_highlighted': False,
            'display_order': 2
        }
        
        form = AdditionalFeaturesAdminForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
    
    def test_policy_features_admin_access(self):
        """Test that admin interface is accessible"""
        url = reverse('admin:policies_policyfeatures_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_additional_features_admin_access(self):
        """Test that admin interface is accessible"""
        url = reverse('admin:policies_additionalfeatures_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class PolicyFeaturesValidationTest(TestCase):
    """Test cases for policy features validation logic"""
    
    def setUp(self):
        # Create test data
        self.organization = Organization.objects.create(
            name='Test Insurance Co',
            email='test@insurance.com',
            phone='+268123456789',
            is_verified=True
        )
        
        self.health_category = PolicyCategory.objects.create(
            name='Health',
            slug='health',
            description='Health insurance policies'
        )
        
        self.policy_type = PolicyType.objects.create(
            category=self.health_category,
            name='Comprehensive',
            slug='comprehensive',
            description='Comprehensive health coverage'
        )
        
        self.health_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.policy_type,
            name='Test Health Policy',
            policy_number='TEST-001',
            description='Test health policy description',
            short_description='Test health policy',
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions='Test terms'
        )
    
    def test_valid_health_policy_features(self):
        """Test creating valid health policy features"""
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type='HEALTH',
            annual_limit_per_member=Decimal('25000.00'),
            monthly_household_income=Decimal('5000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        self.assertEqual(features.insurance_type, 'HEALTH')
        self.assertEqual(features.annual_limit_per_member, Decimal('25000.00'))
        self.assertTrue(features.in_hospital_benefit)
    
    def test_policy_features_string_representation(self):
        """Test PolicyFeatures __str__ method"""
        features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type='HEALTH',
            annual_limit_per_member=Decimal('25000.00'),
            monthly_household_income=Decimal('5000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        expected_str = f"{self.health_policy.name} - Health Policies Features"
        self.assertEqual(str(features), expected_str)
    
    def test_additional_features_string_representation(self):
        """Test AdditionalFeatures __str__ method"""
        feature = AdditionalFeatures.objects.create(
            policy=self.health_policy,
            title='24/7 Support',
            description='Round the clock customer support'
        )
        
        expected_str = f"24/7 Support - {self.health_policy.name}"
        self.assertEqual(str(feature), expected_str)