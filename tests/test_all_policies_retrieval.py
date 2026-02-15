"""
Test module for retrieving all policies (health and funeral) from the database.
This test demonstrates how to query and retrieve all available policies.
"""

import os
import sys
import django
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

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


class AllPoliciesRetrievalTest(TestCase):
    """Test class for retrieving all policies from the database."""
    
    def setUp(self):
        """Set up test data."""
        # Get or create test organization
        self.organization, _ = Organization.objects.get_or_create(
            registration_number="REG123456TEST",
            defaults={
                "name": "Test Insurance Company",
                "description": "A test insurance company",
                "email": "test@insurance.com",
                "phone": "+27123456789",
                "address_line1": "123 Test Street",
                "city": "Cape Town",
                "state_province": "Western Cape",
                "postal_code": "8001",
                "license_number": "LIC789012TEST",
                "verification_status": Organization.VerificationStatus.VERIFIED,
                "is_active": True
            }
        )
        
        # Get or create policy categories
        self.health_category, _ = PolicyCategory.objects.get_or_create(
            slug="health-test",
            defaults={
                "name": "Health Insurance Test",
                "description": "Medical and health insurance policies",
                "is_active": True
            }
        )
        
        self.funeral_category, _ = PolicyCategory.objects.get_or_create(
            slug="funeral-test",
            defaults={
                "name": "Funeral Insurance Test",
                "description": "Funeral cover and burial insurance policies",
                "is_active": True
            }
        )
        
        # Get or create policy types
        self.health_type, _ = PolicyType.objects.get_or_create(
            category=self.health_category,
            slug="comprehensive-test",
            defaults={
                "name": "Comprehensive Health Test",
                "description": "Full health coverage",
                "is_active": True
            }
        )
        
        self.funeral_type, _ = PolicyType.objects.get_or_create(
            category=self.funeral_category,
            slug="family-test",
            defaults={
                "name": "Family Funeral Test",
                "description": "Family funeral coverage",
                "is_active": True
            }
        )
        
        # Create test health policies
        self.health_policy_1 = HealthPolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Premium Health Plan",
            policy_number="HP001TEST",
            description="Comprehensive health coverage with all benefits",
            short_description="Premium health plan with full coverage",
            base_premium=Decimal('1500.00'),
            coverage_amount=Decimal('500000.00'),
            minimum_age=18,
            maximum_age=65,
            terms_and_conditions="Standard terms and conditions apply",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            coverage_level=HealthPolicy.CoverageLevel.COMPREHENSIVE,
            hospital_network_type="Private and Public",
            includes_hospital_cover=True,
            includes_outpatient_cover=True,
            includes_dental_cover=True,
            includes_optical_cover=True,
            includes_maternity_cover=True,
            ambulance_cover=True,
            emergency_room_cover=True
        )
        
        self.health_policy_2 = HealthPolicy.objects.create(
            organization=self.organization,
            category=self.health_category,
            policy_type=self.health_type,
            name="Basic Health Plan",
            policy_number="HP002TEST",
            description="Basic health coverage for essential needs",
            short_description="Affordable basic health coverage",
            base_premium=Decimal('800.00'),
            coverage_amount=Decimal('200000.00'),
            minimum_age=18,
            maximum_age=70,
            terms_and_conditions="Standard terms and conditions apply",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            coverage_level=HealthPolicy.CoverageLevel.BASIC,
            hospital_network_type="Public",
            includes_hospital_cover=True,
            includes_outpatient_cover=False,
            ambulance_cover=True,
            emergency_room_cover=True
        )
        
        # Create test funeral policies
        self.funeral_policy_1 = FuneralPolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_type,
            name="Family Funeral Cover",
            policy_number="FP001TEST",
            description="Comprehensive funeral cover for the whole family",
            short_description="Complete family funeral protection",
            base_premium=Decimal('250.00'),
            coverage_amount=Decimal('50000.00'),
            minimum_age=18,
            maximum_age=75,
            terms_and_conditions="Standard funeral terms apply",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            cover_type=FuneralPolicy.CoverType.FAMILY,
            service_type=FuneralPolicy.FuneralService.MANAGED_SERVICE,
            main_member_cover_amount=Decimal('50000.00'),
            includes_spouse_cover=True,
            spouse_cover_amount=Decimal('50000.00'),
            includes_children_cover=True,
            child_cover_amount=Decimal('25000.00'),
            includes_parents_cover=True,
            parent_cover_amount=Decimal('30000.00'),
            includes_coffin=True,
            includes_transport=True,
            includes_venue=True,
            includes_catering=True
        )
        
        self.funeral_policy_2 = FuneralPolicy.objects.create(
            organization=self.organization,
            category=self.funeral_category,
            policy_type=self.funeral_type,
            name="Individual Funeral Cover",
            policy_number="FP002TEST",
            description="Individual funeral cover with cash payout",
            short_description="Simple individual funeral protection",
            base_premium=Decimal('150.00'),
            coverage_amount=Decimal('25000.00'),
            minimum_age=18,
            maximum_age=80,
            terms_and_conditions="Standard funeral terms apply",
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            is_active=True,
            cover_type=FuneralPolicy.CoverType.INDIVIDUAL,
            service_type=FuneralPolicy.FuneralService.CASH_PAYOUT,
            main_member_cover_amount=Decimal('25000.00'),
            includes_spouse_cover=False,
            includes_children_cover=False,
            includes_parents_cover=False
        )
        
        # Create policy features for better testing
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
            includes_catering=True,
            repatriation_covered=True,
            grocery_benefit=True,
            grocery_benefit_amount=Decimal('2000.00'),
            claim_payout_hours=48
        )
    
    def test_get_all_policies_basic(self):
        """Test retrieving all policies using BasePolicy model."""
        # Get all policies
        all_policies = BasePolicy.objects.all()
        
        # Verify we have the expected number of policies
        self.assertEqual(all_policies.count(), 4)
        
        # Verify policy types are mixed (health and funeral)
        policy_numbers = [policy.policy_number for policy in all_policies]
        self.assertIn('HP001TEST', policy_numbers)
        self.assertIn('HP002TEST', policy_numbers)
        self.assertIn('FP001TEST', policy_numbers)
        self.assertIn('FP002TEST', policy_numbers)
        
        print(f"✓ Found {all_policies.count()} total policies")
        for policy in all_policies:
            print(f"  - {policy.policy_number}: {policy.name} ({policy.category.name})")
    
    def test_get_all_active_policies(self):
        """Test retrieving only active policies."""
        # Get only active policies
        active_policies = BasePolicy.objects.filter(is_active=True)
        
        # All our test policies are active
        self.assertEqual(active_policies.count(), 4)
        
        # Verify all returned policies are active
        for policy in active_policies:
            self.assertTrue(policy.is_active)
        
        print(f"✓ Found {active_policies.count()} active policies")
    
    def test_get_all_approved_policies(self):
        """Test retrieving only approved policies."""
        # Get only approved policies
        approved_policies = BasePolicy.objects.filter(
            approval_status=BasePolicy.ApprovalStatus.APPROVED
        )
        
        # All our test policies are approved
        self.assertEqual(approved_policies.count(), 4)
        
        # Verify all returned policies are approved
        for policy in approved_policies:
            self.assertEqual(policy.approval_status, BasePolicy.ApprovalStatus.APPROVED)
        
        print(f"✓ Found {approved_policies.count()} approved policies")
    
    def test_get_policies_by_category(self):
        """Test retrieving policies grouped by category."""
        # Get health policies
        health_policies = BasePolicy.objects.filter(category__slug='health-test')
        self.assertEqual(health_policies.count(), 2)
        
        # Get funeral policies
        funeral_policies = BasePolicy.objects.filter(category__slug='funeral-test')
        self.assertEqual(funeral_policies.count(), 2)
        
        print(f"✓ Found {health_policies.count()} health policies")
        print(f"✓ Found {funeral_policies.count()} funeral policies")
        
        # Verify category separation
        for policy in health_policies:
            self.assertEqual(policy.category.slug, 'health-test')
        
        for policy in funeral_policies:
            self.assertEqual(policy.category.slug, 'funeral-test')
    
    def test_get_specific_policy_types(self):
        """Test retrieving specific policy types (HealthPolicy and FuneralPolicy)."""
        # Get health policies using HealthPolicy model
        health_policies = HealthPolicy.objects.all()
        self.assertEqual(health_policies.count(), 2)
        
        # Get funeral policies using FuneralPolicy model
        funeral_policies = FuneralPolicy.objects.all()
        self.assertEqual(funeral_policies.count(), 2)
        
        print(f"✓ Found {health_policies.count()} HealthPolicy instances")
        print(f"✓ Found {funeral_policies.count()} FuneralPolicy instances")
        
        # Test health-specific fields
        for health_policy in health_policies:
            self.assertIsNotNone(health_policy.coverage_level)
            self.assertIsNotNone(health_policy.hospital_network_type)
        
        # Test funeral-specific fields
        for funeral_policy in funeral_policies:
            self.assertIsNotNone(funeral_policy.cover_type)
            self.assertIsNotNone(funeral_policy.service_type)
    
    def test_get_policies_with_features(self):
        """Test retrieving policies with their features."""
        # Get policies with features
        policies_with_features = BasePolicy.objects.filter(
            policy_features__isnull=False
        ).select_related('policy_features')
        
        # We created features for 2 policies
        self.assertEqual(policies_with_features.count(), 2)
        
        print(f"✓ Found {policies_with_features.count()} policies with features")
        
        for policy in policies_with_features:
            features = policy.policy_features
            self.assertIsNotNone(features)
            print(f"  - {policy.name}: {features.insurance_type} features")
            
            if features.insurance_type == 'HEALTH':
                self.assertIsNotNone(features.annual_limit_family_range)
                print(f"    Health features: {features.get_health_features_summary()}")
            elif features.insurance_type == 'FUNERAL':
                self.assertIsNotNone(features.cover_amount_range)
                print(f"    Funeral features: {features.get_funeral_features_summary()}")
    
    def test_get_policies_with_organization_details(self):
        """Test retrieving policies with organization information."""
        # Get policies with organization details
        policies_with_org = BasePolicy.objects.select_related('organization').all()
        
        self.assertEqual(policies_with_org.count(), 4)
        
        print(f"✓ Found {policies_with_org.count()} policies with organization details")
        
        for policy in policies_with_org:
            self.assertIsNotNone(policy.organization)
            self.assertEqual(policy.organization.name, "Test Insurance Company")
            print(f"  - {policy.name} by {policy.organization.name}")
    
    def test_get_policies_ordered_by_premium(self):
        """Test retrieving policies ordered by premium."""
        # Get policies ordered by premium (ascending)
        policies_by_premium_asc = BasePolicy.objects.order_by('base_premium')
        
        # Get policies ordered by premium (descending)
        policies_by_premium_desc = BasePolicy.objects.order_by('-base_premium')
        
        print("✓ Policies ordered by premium (ascending):")
        for policy in policies_by_premium_asc:
            print(f"  - {policy.name}: R{policy.base_premium}")
        
        print("✓ Policies ordered by premium (descending):")
        for policy in policies_by_premium_desc:
            print(f"  - {policy.name}: R{policy.base_premium}")
        
        # Verify ordering
        premiums_asc = [policy.base_premium for policy in policies_by_premium_asc]
        self.assertEqual(premiums_asc, sorted(premiums_asc))
        
        premiums_desc = [policy.base_premium for policy in policies_by_premium_desc]
        self.assertEqual(premiums_desc, sorted(premiums_desc, reverse=True))
    
    def test_get_policies_with_coverage_range(self):
        """Test retrieving policies within a specific coverage range."""
        # Get policies with coverage between R100k and R300k
        policies_in_range = BasePolicy.objects.filter(
            coverage_amount__gte=Decimal('100000.00'),
            coverage_amount__lte=Decimal('300000.00')
        )
        
        print(f"✓ Found {policies_in_range.count()} policies with coverage R100k-R300k")
        
        for policy in policies_in_range:
            self.assertGreaterEqual(policy.coverage_amount, Decimal('100000.00'))
            self.assertLessEqual(policy.coverage_amount, Decimal('300000.00'))
            print(f"  - {policy.name}: R{policy.coverage_amount}")
    
    def test_comprehensive_policy_retrieval(self):
        """Comprehensive test that demonstrates various ways to retrieve all policies."""
        print("\n" + "="*60)
        print("COMPREHENSIVE POLICY RETRIEVAL TEST")
        print("="*60)
        
        # 1. Get all policies with basic info
        all_policies = BasePolicy.objects.select_related(
            'organization', 'category', 'policy_type'
        ).prefetch_related('policy_features').all()
        
        print(f"\n1. TOTAL POLICIES IN DATABASE: {all_policies.count()}")
        print("-" * 40)
        
        for policy in all_policies:
            print(f"Policy: {policy.name}")
            print(f"  Number: {policy.policy_number}")
            print(f"  Category: {policy.category.name}")
            print(f"  Type: {policy.policy_type.name}")
            print(f"  Organization: {policy.organization.name}")
            print(f"  Premium: R{policy.base_premium}/month")
            print(f"  Coverage: R{policy.coverage_amount}")
            print(f"  Status: {policy.get_approval_status_display()}")
            print(f"  Active: {'Yes' if policy.is_active else 'No'}")
            
            # Show features if available
            if hasattr(policy, 'policy_features') and policy.policy_features:
                features = policy.policy_features
                if features.insurance_type == 'HEALTH':
                    print(f"  Health Features: {features.get_health_features_summary()}")
                elif features.insurance_type == 'FUNERAL':
                    print(f"  Funeral Features: {features.get_funeral_features_summary()}")
            
            print()
        
        # 2. Get policies by specific criteria
        print("2. POLICIES BY CATEGORY:")
        print("-" * 40)
        
        categories = PolicyCategory.objects.all()
        for category in categories:
            category_policies = all_policies.filter(category=category)
            print(f"{category.name}: {category_policies.count()} policies")
            for policy in category_policies:
                print(f"  - {policy.name} (R{policy.base_premium}/month)")
        
        # 3. Get health-specific policies
        print("\n3. HEALTH POLICIES (with health-specific fields):")
        print("-" * 40)
        
        health_policies = HealthPolicy.objects.select_related(
            'organization', 'category'
        ).all()
        
        for health_policy in health_policies:
            print(f"Health Policy: {health_policy.name}")
            print(f"  Coverage Level: {health_policy.get_coverage_level_display()}")
            print(f"  Hospital Network: {health_policy.hospital_network_type}")
            print(f"  Hospital Cover: {'Yes' if health_policy.includes_hospital_cover else 'No'}")
            print(f"  Outpatient Cover: {'Yes' if health_policy.includes_outpatient_cover else 'No'}")
            print(f"  Dental Cover: {'Yes' if health_policy.includes_dental_cover else 'No'}")
            print(f"  Ambulance Cover: {'Yes' if health_policy.ambulance_cover else 'No'}")
            print()
        
        # 4. Get funeral-specific policies
        print("4. FUNERAL POLICIES (with funeral-specific fields):")
        print("-" * 40)
        
        funeral_policies = FuneralPolicy.objects.select_related(
            'organization', 'category'
        ).all()
        
        for funeral_policy in funeral_policies:
            print(f"Funeral Policy: {funeral_policy.name}")
            print(f"  Cover Type: {funeral_policy.get_cover_type_display()}")
            print(f"  Service Type: {funeral_policy.get_service_type_display()}")
            print(f"  Main Member Cover: R{funeral_policy.main_member_cover_amount}")
            print(f"  Spouse Cover: {'Yes' if funeral_policy.includes_spouse_cover else 'No'}")
            print(f"  Children Cover: {'Yes' if funeral_policy.includes_children_cover else 'No'}")
            print(f"  Parents Cover: {'Yes' if funeral_policy.includes_parents_cover else 'No'}")
            print(f"  Includes Coffin: {'Yes' if funeral_policy.includes_coffin else 'No'}")
            print(f"  Includes Transport: {'Yes' if funeral_policy.includes_transport else 'No'}")
            print()
        
        # Verify we got all our test data
        self.assertEqual(all_policies.count(), 4)
        self.assertEqual(health_policies.count(), 2)
        self.assertEqual(funeral_policies.count(), 2)
        
        print("✓ All policy retrieval tests completed successfully!")


if __name__ == '__main__':
    # Run the test
    import unittest
    unittest.main(verbosity=2)