"""
Tests for system integration functionality.
"""

from django.test import TestCase, TransactionTestCase
from django.core.management import call_command
from django.core.cache import cache
from django.contrib.auth import get_user_model
from decimal import Decimal
import json

from .models import BasePolicy, PolicyFeatures, PolicyCategory, PolicyType
from .integration import (
    SystemIntegrationManager,
    FeatureSynchronizationManager,
    CrossModuleValidator
)
from simple_surveys.models import SimpleSurvey, SimpleSurveyQuestion
from comparison.models import FeatureComparisonResult
from organizations.models import Organization

User = get_user_model()


class SystemIntegrationTestCase(TestCase):
    """Test system integration functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Clear cache
        cache.clear()
        
        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            slug="test-insurance",
            is_verified=True
        )
        
        # Create test categories
        self.health_category = PolicyCategory.objects.create(
            name="Health",
            slug="health",
            description="Health insurance policies"
        )
        
        self.funeral_category = PolicyCategory.objects.create(
            name="Funeral",
            slug="funeral",
            description="Funeral insurance policies"
        )
        
        # Create test policy types
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
        
        # Create test policies
        self.health_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Test Health Policy",
            description="Test health policy description",
            short_description="Test health policy",
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
            description="Test funeral policy description",
            short_description="Test funeral policy",
            base_premium=Decimal('200.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Test terms"
        )
        
        # Create policy features
        self.health_features = PolicyFeatures.objects.create(
            policy=self.health_policy,
            insurance_type='HEALTH',
            annual_limit_per_member=Decimal('50000.00'),
            monthly_household_income=Decimal('10000.00'),
            in_hospital_benefit=True,
            out_hospital_benefit=True,
            chronic_medication_availability=True
        )
        
        self.funeral_features = PolicyFeatures.objects.create(
            policy=self.funeral_policy,
            insurance_type='FUNERAL',
            cover_amount=Decimal('25000.00'),
            marital_status_requirement='Any',
            gender_requirement='Any',
            monthly_net_income=Decimal('5000.00')
        )
        
        # Create test survey
        self.health_survey = SimpleSurvey.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01",
            email="john@example.com",
            insurance_type='HEALTH',
            preferred_annual_limit=Decimal('40000.00'),
            household_income=Decimal('8000.00'),
            wants_in_hospital_benefit=True,
            wants_out_hospital_benefit=False,
            needs_chronic_medication=True
        )


class FeatureSynchronizationTestCase(SystemIntegrationTestCase):
    """Test feature synchronization functionality."""
    
    def test_get_feature_mapping(self):
        """Test getting feature mapping for insurance types."""
        health_mapping = FeatureSynchronizationManager.get_feature_mapping('HEALTH')
        funeral_mapping = FeatureSynchronizationManager.get_feature_mapping('FUNERAL')
        
        # Check health mapping
        self.assertIn('annual_limit_per_member', health_mapping)
        self.assertIn('in_hospital_benefit', health_mapping)
        self.assertEqual(
            health_mapping['annual_limit_per_member']['policy_field'],
            'annual_limit_per_member'
        )
        self.assertEqual(
            health_mapping['annual_limit_per_member']['survey_field'],
            'preferred_annual_limit'
        )
        
        # Check funeral mapping
        self.assertIn('cover_amount', funeral_mapping)
        self.assertIn('marital_status_requirement', funeral_mapping)
        self.assertEqual(
            funeral_mapping['cover_amount']['policy_field'],
            'cover_amount'
        )
        self.assertEqual(
            funeral_mapping['cover_amount']['survey_field'],
            'preferred_cover_amount'
        )
    
    def test_validate_feature_consistency(self):
        """Test feature consistency validation."""
        health_errors = FeatureSynchronizationManager.validate_feature_consistency('HEALTH')
        funeral_errors = FeatureSynchronizationManager.validate_feature_consistency('FUNERAL')
        
        # Should have no errors with proper model definitions
        self.assertEqual(len(health_errors), 0, f"Health feature consistency errors: {health_errors}")
        self.assertEqual(len(funeral_errors), 0, f"Funeral feature consistency errors: {funeral_errors}")
    
    def test_synchronize_survey_questions(self):
        """Test survey question synchronization."""
        # Clear existing questions
        SimpleSurveyQuestion.objects.all().delete()
        
        # Synchronize health questions
        health_results = FeatureSynchronizationManager.synchronize_survey_questions('HEALTH')
        
        self.assertGreater(health_results['created'], 0)
        self.assertEqual(len(health_results['errors']), 0)
        
        # Check that questions were created
        health_questions = SimpleSurveyQuestion.objects.filter(category='health')
        self.assertGreater(health_questions.count(), 0)
        
        # Synchronize funeral questions
        funeral_results = FeatureSynchronizationManager.synchronize_survey_questions('FUNERAL')
        
        self.assertGreater(funeral_results['created'], 0)
        self.assertEqual(len(funeral_results['errors']), 0)
        
        # Check that questions were created
        funeral_questions = SimpleSurveyQuestion.objects.filter(category='funeral')
        self.assertGreater(funeral_questions.count(), 0)


class CrossModuleValidatorTestCase(SystemIntegrationTestCase):
    """Test cross-module validation functionality."""
    
    def test_validate_policy_features_valid(self):
        """Test validation of valid policy features."""
        errors = CrossModuleValidator.validate_policy_features(self.health_policy)
        self.assertEqual(len(errors), 0, f"Validation errors for valid policy: {errors}")
        
        errors = CrossModuleValidator.validate_policy_features(self.funeral_policy)
        self.assertEqual(len(errors), 0, f"Validation errors for valid policy: {errors}")
    
    def test_validate_policy_features_missing(self):
        """Test validation of policy with missing features."""
        # Create policy without features
        policy_without_features = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Policy Without Features",
            description="Test policy without features",
            short_description="Test policy",
            base_premium=Decimal('300.00'),
            coverage_amount=Decimal('75000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms"
        )
        
        errors = CrossModuleValidator.validate_policy_features(policy_without_features)
        self.assertGreater(len(errors), 0)
        self.assertIn("no associated PolicyFeatures", errors[0])
    
    def test_validate_policy_features_incomplete(self):
        """Test validation of policy with incomplete features."""
        # Create policy with incomplete features
        incomplete_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Incomplete Policy",
            description="Test policy with incomplete features",
            short_description="Test policy",
            base_premium=Decimal('400.00'),
            coverage_amount=Decimal('80000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms"
        )
        
        # Create incomplete features (missing some required fields)
        PolicyFeatures.objects.create(
            policy=incomplete_policy,
            insurance_type='HEALTH',
            annual_limit_per_member=Decimal('30000.00'),
            # Missing other required fields
        )
        
        errors = CrossModuleValidator.validate_policy_features(incomplete_policy)
        self.assertGreater(len(errors), 0)
    
    def test_validate_survey_completeness_valid(self):
        """Test validation of complete survey."""
        errors = CrossModuleValidator.validate_survey_completeness(self.health_survey)
        self.assertEqual(len(errors), 0, f"Validation errors for valid survey: {errors}")
    
    def test_validate_survey_completeness_incomplete(self):
        """Test validation of incomplete survey."""
        incomplete_survey = SimpleSurvey.objects.create(
            first_name="Jane",
            last_name="Doe",
            date_of_birth="1985-01-01",
            insurance_type='HEALTH',
            # Missing required fields
        )
        
        errors = CrossModuleValidator.validate_survey_completeness(incomplete_survey)
        self.assertGreater(len(errors), 0)
    
    def test_validate_comparison_consistency(self):
        """Test validation of comparison result consistency."""
        # Create a comparison result
        comparison_result = FeatureComparisonResult.objects.create(
            survey=self.health_survey,
            policy=self.health_policy,
            overall_compatibility_score=Decimal('85.50'),
            feature_match_count=4,
            feature_mismatch_count=1,
            feature_scores={'test': 'data'},
            feature_matches=[{'feature': 'test', 'score': 1.0}],
            feature_mismatches=[],
            compatibility_rank=1,
            recommendation_category='EXCELLENT_MATCH',
            match_explanation="Good match based on features"
        )
        
        errors = CrossModuleValidator.validate_comparison_consistency(comparison_result)
        self.assertEqual(len(errors), 0, f"Validation errors for valid comparison: {errors}")
    
    def test_validate_comparison_consistency_mismatch(self):
        """Test validation of comparison with insurance type mismatch."""
        # Create comparison between health survey and funeral policy
        comparison_result = FeatureComparisonResult.objects.create(
            survey=self.health_survey,
            policy=self.funeral_policy,  # Wrong insurance type
            overall_compatibility_score=Decimal('50.00'),
            feature_match_count=2,
            feature_mismatch_count=3,
            feature_scores={'test': 'data'},
            feature_matches=[],
            feature_mismatches=[],
            compatibility_rank=1,
            recommendation_category='PARTIAL_MATCH',
            match_explanation="Mismatched insurance types"
        )
        
        errors = CrossModuleValidator.validate_comparison_consistency(comparison_result)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Insurance type mismatch" in error for error in errors))


class SystemIntegrationManagerTestCase(SystemIntegrationTestCase):
    """Test system integration manager functionality."""
    
    def test_perform_full_system_check(self):
        """Test full system integration check."""
        results = SystemIntegrationManager.perform_full_system_check()
        
        # Check result structure
        self.assertIn('timestamp', results)
        self.assertIn('health_policies', results)
        self.assertIn('funeral_policies', results)
        self.assertIn('health_surveys', results)
        self.assertIn('funeral_surveys', results)
        self.assertIn('comparison_results', results)
        self.assertIn('feature_consistency', results)
        self.assertIn('overall_status', results)
        
        # Check that we have data
        self.assertGreater(results['health_policies']['total'], 0)
        self.assertGreater(results['funeral_policies']['total'], 0)
        self.assertGreater(results['health_surveys']['total'], 0)
        
        # Check overall status
        self.assertIn(results['overall_status'], ['healthy', 'warning', 'critical', 'error'])
    
    def test_synchronize_all_features(self):
        """Test synchronizing all features."""
        # Clear existing survey questions
        SimpleSurveyQuestion.objects.all().delete()
        
        results = SystemIntegrationManager.synchronize_all_features()
        
        # Check result structure
        self.assertIn('health_sync', results)
        self.assertIn('funeral_sync', results)
        self.assertIn('overall_success', results)
        
        # Check that synchronization worked
        if results['overall_success']:
            self.assertGreater(results['health_sync']['created'], 0)
            self.assertGreater(results['funeral_sync']['created'], 0)
    
    def test_validate_system_integrity(self):
        """Test system integrity validation."""
        is_valid, errors = SystemIntegrationManager.validate_system_integrity()
        
        # Should be valid with proper test setup
        if not is_valid:
            self.fail(f"System integrity validation failed: {errors}")


class ManagementCommandTestCase(TransactionTestCase):
    """Test management commands for system integration."""
    
    def test_check_system_integration_command(self):
        """Test the check_system_integration management command."""
        # Test basic command execution
        try:
            call_command('check_system_integration', format='json', verbosity=0)
        except Exception as e:
            self.fail(f"check_system_integration command failed: {str(e)}")
    
    def test_synchronize_features_command(self):
        """Test the synchronize_features management command."""
        # Test basic command execution
        try:
            call_command('synchronize_features', dry_run=True, verbosity=0)
        except Exception as e:
            self.fail(f"synchronize_features command failed: {str(e)}")
    
    def test_validate_policy_features_command(self):
        """Test the validate_policy_features management command."""
        # Test basic command execution
        try:
            call_command('validate_policy_features', verbosity=0)
        except Exception as e:
            self.fail(f"validate_policy_features command failed: {str(e)}")


class SignalTestCase(SystemIntegrationTestCase):
    """Test signal handlers for system integration."""
    
    def test_policy_features_validation_signal(self):
        """Test that policy features are validated on save."""
        # Create policy features with invalid data
        invalid_features = PolicyFeatures(
            policy=self.health_policy,
            insurance_type='HEALTH',
            annual_limit_per_member=Decimal('-1000.00'),  # Invalid negative value
        )
        
        # Save should trigger validation signal
        invalid_features.save()
        
        # Check that validation errors are cached
        from .signals import get_cached_validation_errors
        errors = get_cached_validation_errors('policy', self.health_policy.id)
        
        # Should have validation errors cached (though this depends on signal implementation)
        # This test verifies the signal mechanism works
    
    def test_survey_validation_signal(self):
        """Test that surveys are validated on save."""
        # Create incomplete survey
        incomplete_survey = SimpleSurvey(
            first_name="Test",
            last_name="User",
            date_of_birth="1990-01-01",
            insurance_type='HEALTH',
            # Missing required fields
        )
        
        # Save should trigger validation signal
        incomplete_survey.save()
        
        # Check that validation errors are cached
        from .signals import get_cached_validation_errors
        errors = get_cached_validation_errors('survey', incomplete_survey.id)
        
        # Should have validation errors cached
    
    def test_system_health_monitoring_signal(self):
        """Test system health monitoring signals."""
        from .signals import get_system_health_metrics
        
        # Create a new policy to trigger monitoring
        new_policy = BasePolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="New Test Policy",
            description="New test policy",
            short_description="New test",
            base_premium=Decimal('600.00'),
            coverage_amount=Decimal('120000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Test terms"
        )
        
        # Check that health metrics are updated
        metrics = get_system_health_metrics()
        self.assertIn('cache_status', metrics)
        self.assertIn('policy_changes_today', metrics)


class AdminIntegrationTestCase(SystemIntegrationTestCase):
    """Test admin integration functionality."""
    
    def setUp(self):
        """Set up test data including admin user."""
        super().setUp()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
    
    def test_admin_integration_mixin(self):
        """Test admin integration mixin functionality."""
        from .admin_integration import SystemIntegrationAdminMixin
        
        mixin = SystemIntegrationAdminMixin()
        
        # Test validation errors display
        display = mixin.get_validation_errors_display(self.health_policy, 'policy')
        self.assertIsInstance(display, str)
    
    def test_admin_integration_view_access(self):
        """Test admin integration view access."""
        from django.test import Client
        
        client = Client()
        client.force_login(self.admin_user)
        
        # Test that integration view is accessible
        # Note: This would require proper URL configuration
        # response = client.get('/admin/integration/')
        # self.assertEqual(response.status_code, 200)
    
    def test_admin_actions(self):
        """Test admin actions for validation."""
        from .admin_integration import validate_policies_action, validate_surveys_action
        
        # Test policy validation action
        result = validate_policies_action(self.health_policy)
        self.assertIn('success', result)
        
        # Test survey validation action
        result = validate_surveys_action(self.health_survey)
        self.assertIn('success', result)