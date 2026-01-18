"""
Test configuration and utilities for the Eswatini policy system tests.
"""

import os
import django
from django.test import TestCase
from django.core.management import call_command
from django.db import transaction
from decimal import Decimal
from datetime import date

# Test data constants
TEST_ORGANIZATION_DATA = {
    'name': 'Test Insurance Company',
    'slug': 'test-insurance',
    'email': 'test@insurance.co.sz',
    'phone': '+268123456789',
    'is_verified': True
}

TEST_HEALTH_CATEGORY_DATA = {
    'name': 'Health Insurance',
    'slug': 'health',
    'description': 'Health and medical insurance policies'
}

TEST_FUNERAL_CATEGORY_DATA = {
    'name': 'Funeral Insurance',
    'slug': 'funeral',
    'description': 'Funeral and burial insurance policies'
}

TEST_HEALTH_SURVEY_DATA = {
    'first_name': 'John',
    'last_name': 'Doe',
    'date_of_birth': date(1990, 1, 1),
    'email': 'john.doe@example.com',
    'phone': '+268123456789',
    'insurance_type': 'HEALTH',
    'preferred_annual_limit': Decimal('75000.00'),
    'household_income': Decimal('12000.00'),
    'wants_in_hospital_benefit': True,
    'wants_out_hospital_benefit': True,
    'needs_chronic_medication': False
}

TEST_FUNERAL_SURVEY_DATA = {
    'first_name': 'Jane',
    'last_name': 'Smith',
    'date_of_birth': date(1985, 5, 15),
    'email': 'jane.smith@example.com',
    'phone': '+268987654321',
    'insurance_type': 'FUNERAL',
    'preferred_cover_amount': Decimal('50000.00'),
    'marital_status': 'Married',
    'gender': 'Female',
    'net_income': Decimal('10000.00')
}


class BaseTestCase(TestCase):
    """Base test case with common setup and utilities."""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level test data."""
        super().setUpClass()
        
        # Import here to avoid circular imports
        from organizations.models import Organization
        from policies.models import PolicyCategory, PolicyType
        
        # Create test organization
        cls.organization = Organization.objects.create(**TEST_ORGANIZATION_DATA)
        
        # Create test categories
        cls.health_category = PolicyCategory.objects.create(**TEST_HEALTH_CATEGORY_DATA)
        cls.funeral_category = PolicyCategory.objects.create(**TEST_FUNERAL_CATEGORY_DATA)
        
        # Create test policy types
        cls.health_comprehensive = PolicyType.objects.create(
            category=cls.health_category,
            name='Comprehensive',
            slug='comprehensive',
            description='Comprehensive health coverage'
        )
        
        cls.funeral_family = PolicyType.objects.create(
            category=cls.funeral_category,
            name='Family',
            slug='family',
            description='Family funeral coverage'
        )
    
    def create_test_health_policy(self, name_suffix="", **kwargs):
        """Create a test health policy with default values."""
        from policies.models import BasePolicy
        
        defaults = {
            'organization': self.organization,
            'category': self.health_category,
            'policy_type': self.health_comprehensive,
            'name': f'Test Health Policy{name_suffix}',
            'policy_number': f'TEST-HEALTH-{abs(hash(name_suffix)) % 1000:03d}',
            'description': f'Test health policy{name_suffix}',
            'short_description': f'Test health{name_suffix}',
            'base_premium': Decimal('500.00'),
            'coverage_amount': Decimal('100000.00'),
            'minimum_age': 18,
            'maximum_age': 65,
            'terms_and_conditions': 'Test terms and conditions'
        }
        defaults.update(kwargs)
        
        return BasePolicy.objects.create(**defaults)
    
    def create_test_funeral_policy(self, name_suffix="", **kwargs):
        """Create a test funeral policy with default values."""
        from policies.models import BasePolicy
        
        defaults = {
            'organization': self.organization,
            'category': self.funeral_category,
            'policy_type': self.funeral_family,
            'name': f'Test Funeral Policy{name_suffix}',
            'policy_number': f'TEST-FUNERAL-{abs(hash(name_suffix)) % 1000:03d}',
            'description': f'Test funeral policy{name_suffix}',
            'short_description': f'Test funeral{name_suffix}',
            'base_premium': Decimal('200.00'),
            'coverage_amount': Decimal('50000.00'),
            'minimum_age': 18,
            'maximum_age': 75,
            'terms_and_conditions': 'Test terms and conditions'
        }
        defaults.update(kwargs)
        
        return BasePolicy.objects.create(**defaults)
    
    def create_test_health_features(self, policy, **kwargs):
        """Create test health policy features."""
        from policies.models import PolicyFeatures
        
        defaults = {
            'policy': policy,
            'insurance_type': PolicyFeatures.InsuranceType.HEALTH,
            'annual_limit_per_member': Decimal('75000.00'),
            'monthly_household_income': Decimal('12000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': True,
            'chronic_medication_availability': False
        }
        defaults.update(kwargs)
        
        return PolicyFeatures.objects.create(**defaults)
    
    def create_test_funeral_features(self, policy, **kwargs):
        """Create test funeral policy features."""
        from policies.models import PolicyFeatures
        
        defaults = {
            'policy': policy,
            'insurance_type': PolicyFeatures.InsuranceType.FUNERAL,
            'cover_amount': Decimal('45000.00'),
            'marital_status_requirement': 'Any',
            'gender_requirement': 'Any',
            'monthly_net_income': Decimal('10000.00')
        }
        defaults.update(kwargs)
        
        return PolicyFeatures.objects.create(**defaults)
    
    def create_test_health_survey(self, **kwargs):
        """Create a test health survey."""
        from simple_surveys.models import SimpleSurvey
        
        data = TEST_HEALTH_SURVEY_DATA.copy()
        data.update(kwargs)
        
        return SimpleSurvey.objects.create(**data)
    
    def create_test_funeral_survey(self, **kwargs):
        """Create a test funeral survey."""
        from simple_surveys.models import SimpleSurvey
        
        data = TEST_FUNERAL_SURVEY_DATA.copy()
        data.update(kwargs)
        
        return SimpleSurvey.objects.create(**data)
    
    def assertDecimalEqual(self, first, second, places=2):
        """Assert that two decimal values are equal within specified decimal places."""
        self.assertEqual(round(first, places), round(second, places))
    
    def assertScoreInRange(self, score, min_score, max_score):
        """Assert that a compatibility score is within expected range."""
        self.assertGreaterEqual(score, min_score, f"Score {score} is below minimum {min_score}")
        self.assertLessEqual(score, max_score, f"Score {score} is above maximum {max_score}")


class TestDataFactory:
    """Factory for creating test data objects."""
    
    @staticmethod
    def create_comprehensive_health_policy_set(organization, category, policy_type):
        """Create a comprehensive set of health policies for testing."""
        from policies.models import BasePolicy, PolicyFeatures, AdditionalFeatures
        
        policies = []
        
        # Premium policy
        premium_policy = BasePolicy.objects.create(
            organization=organization,
            category=category,
            policy_type=policy_type,
            name='Premium Health Plan',
            policy_number='PREM-001',
            description='Premium health insurance with comprehensive coverage',
            short_description='Premium health plan',
            base_premium=Decimal('800.00'),
            coverage_amount=Decimal('200000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions='Premium health plan terms'
        )
        
        PolicyFeatures.objects.create(
            policy=premium_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('150000.00'),
            monthly_household_income=Decimal('20000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        AdditionalFeatures.objects.create(
            policy=premium_policy,
            title='24/7 Medical Helpline',
            description='Round-the-clock medical assistance',
            is_highlighted=True,
            display_order=1
        )
        
        policies.append(premium_policy)
        
        # Standard policy
        standard_policy = BasePolicy.objects.create(
            organization=organization,
            category=category,
            policy_type=policy_type,
            name='Standard Health Plan',
            policy_number='STD-001',
            description='Standard health insurance with good coverage',
            short_description='Standard health plan',
            base_premium=Decimal('500.00'),
            coverage_amount=Decimal('100000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions='Standard health plan terms'
        )
        
        PolicyFeatures.objects.create(
            policy=standard_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('80000.00'),
            monthly_household_income=Decimal('12000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=False
        )
        
        policies.append(standard_policy)
        
        # Basic policy
        basic_policy = BasePolicy.objects.create(
            organization=organization,
            category=category,
            policy_type=policy_type,
            name='Basic Health Plan',
            policy_number='BASIC-001',
            description='Basic health insurance with essential coverage',
            short_description='Basic health plan',
            base_premium=Decimal('300.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions='Basic health plan terms'
        )
        
        PolicyFeatures.objects.create(
            policy=basic_policy,
            insurance_type=PolicyFeatures.InsuranceType.HEALTH,
            annual_limit_per_member=Decimal('40000.00'),
            monthly_household_income=Decimal('8000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=False,
            chronic_medication_availability=False
        )
        
        policies.append(basic_policy)
        
        return policies
    
    @staticmethod
    def create_comprehensive_funeral_policy_set(organization, category, policy_type):
        """Create a comprehensive set of funeral policies for testing."""
        from policies.models import BasePolicy, PolicyFeatures, AdditionalFeatures
        
        policies = []
        
        # Comprehensive policy
        comprehensive_policy = BasePolicy.objects.create(
            organization=organization,
            category=category,
            policy_type=policy_type,
            name='Comprehensive Funeral Plan',
            policy_number='COMP-FUN-001',
            description='Comprehensive funeral insurance with additional benefits',
            short_description='Comprehensive funeral plan',
            base_premium=Decimal('250.00'),
            coverage_amount=Decimal('75000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions='Comprehensive funeral plan terms'
        )
        
        PolicyFeatures.objects.create(
            policy=comprehensive_policy,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('60000.00'),
            marital_status_requirement='Any',
            gender_requirement='Any',
            monthly_net_income=Decimal('15000.00')
        )
        
        AdditionalFeatures.objects.create(
            policy=comprehensive_policy,
            title='Repatriation Services',
            description='Transportation of deceased to home country',
            is_highlighted=True,
            display_order=1
        )
        
        policies.append(comprehensive_policy)
        
        # Basic policy
        basic_policy = BasePolicy.objects.create(
            organization=organization,
            category=category,
            policy_type=policy_type,
            name='Basic Funeral Plan',
            policy_number='BASIC-FUN-001',
            description='Basic funeral insurance coverage',
            short_description='Basic funeral plan',
            base_premium=Decimal('150.00'),
            coverage_amount=Decimal('35000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions='Basic funeral plan terms'
        )
        
        PolicyFeatures.objects.create(
            policy=basic_policy,
            insurance_type=PolicyFeatures.InsuranceType.FUNERAL,
            cover_amount=Decimal('30000.00'),
            marital_status_requirement='Married',
            gender_requirement='Any',
            monthly_net_income=Decimal('8000.00')
        )
        
        policies.append(basic_policy)
        
        return policies


def run_test_with_coverage():
    """Run tests with coverage reporting if available."""
    try:
        import coverage
        cov = coverage.Coverage()
        cov.start()
        
        # Run tests here
        result = True  # Placeholder
        
        cov.stop()
        cov.save()
        
        print("Coverage Report:")
        cov.report()
        
        return result
    except ImportError:
        print("Coverage.py not available. Running tests without coverage.")
        return True


def setup_test_database():
    """Set up test database with initial data if needed."""
    try:
        call_command('migrate', verbosity=0, interactive=False)
        print("Test database migrations completed.")
    except Exception as e:
        print(f"Error setting up test database: {e}")
        raise


if __name__ == '__main__':
    # This can be used to set up test environment
    setup_test_database()
    print("Test configuration loaded successfully.")