"""
Simple test to retrieve all policies (health and funeral) from the database.
This test works with existing data and demonstrates various query patterns.
"""

import os
import sys
import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from policies.models import BasePolicy, PolicyCategory, PolicyType, PolicyFeatures
from health_policies.models import HealthPolicy
from funeral_policies.models import FuneralPolicy
from organizations.models import Organization


def test_get_all_policies():
    """Test retrieving all policies from the database."""
    print("="*60)
    print("TESTING POLICY RETRIEVAL FROM DATABASE")
    print("="*60)
    
    # 1. Get all policies using BasePolicy
    print("\n1. ALL POLICIES (using BasePolicy):")
    print("-" * 40)
    
    all_policies = BasePolicy.objects.select_related(
        'organization', 'category', 'policy_type'
    ).all()
    
    print(f"Total policies found: {all_policies.count()}")
    
    if all_policies.exists():
        for policy in all_policies[:10]:  # Show first 10
            print(f"  - {policy.policy_number}: {policy.name}")
            print(f"    Category: {policy.category.name}")
            print(f"    Organization: {policy.organization.name}")
            print(f"    Premium: R{policy.base_premium}/month")
            print(f"    Coverage: R{policy.coverage_amount}")
            print(f"    Active: {'Yes' if policy.is_active else 'No'}")
            print()
    else:
        print("  No policies found in database")
    
    # 2. Get health policies specifically
    print("2. HEALTH POLICIES (using HealthPolicy model):")
    print("-" * 40)
    
    health_policies = HealthPolicy.objects.select_related(
        'organization', 'category'
    ).all()
    
    print(f"Health policies found: {health_policies.count()}")
    
    if health_policies.exists():
        for health_policy in health_policies[:5]:  # Show first 5
            print(f"  - {health_policy.name}")
            print(f"    Coverage Level: {health_policy.get_coverage_level_display()}")
            print(f"    Hospital Network: {health_policy.hospital_network_type}")
            print(f"    Hospital Cover: {'Yes' if health_policy.includes_hospital_cover else 'No'}")
            print(f"    Outpatient Cover: {'Yes' if health_policy.includes_outpatient_cover else 'No'}")
            print(f"    Ambulance Cover: {'Yes' if health_policy.ambulance_cover else 'No'}")
            print()
    else:
        print("  No health policies found")
    
    # 3. Get funeral policies specifically
    print("3. FUNERAL POLICIES (using FuneralPolicy model):")
    print("-" * 40)
    
    funeral_policies = FuneralPolicy.objects.select_related(
        'organization', 'category'
    ).all()
    
    print(f"Funeral policies found: {funeral_policies.count()}")
    
    if funeral_policies.exists():
        for funeral_policy in funeral_policies[:5]:  # Show first 5
            print(f"  - {funeral_policy.name}")
            print(f"    Cover Type: {funeral_policy.get_cover_type_display()}")
            print(f"    Service Type: {funeral_policy.get_service_type_display()}")
            print(f"    Main Member Cover: R{funeral_policy.main_member_cover_amount}")
            print(f"    Spouse Cover: {'Yes' if funeral_policy.includes_spouse_cover else 'No'}")
            print(f"    Children Cover: {'Yes' if funeral_policy.includes_children_cover else 'No'}")
            print()
    else:
        print("  No funeral policies found")
    
    # 4. Get policies by category
    print("4. POLICIES BY CATEGORY:")
    print("-" * 40)
    
    categories = PolicyCategory.objects.all()
    for category in categories:
        category_policies = BasePolicy.objects.filter(category=category)
        print(f"{category.name}: {category_policies.count()} policies")
        
        # Show a few examples
        for policy in category_policies[:3]:
            print(f"  - {policy.name} (R{policy.base_premium}/month)")
    
    # 5. Get active policies only
    print("\n5. ACTIVE POLICIES ONLY:")
    print("-" * 40)
    
    active_policies = BasePolicy.objects.filter(is_active=True)
    print(f"Active policies: {active_policies.count()}")
    
    # 6. Get approved policies only
    print("\n6. APPROVED POLICIES ONLY:")
    print("-" * 40)
    
    approved_policies = BasePolicy.objects.filter(
        approval_status=BasePolicy.ApprovalStatus.APPROVED
    )
    print(f"Approved policies: {approved_policies.count()}")
    
    # 7. Get policies with features
    print("\n7. POLICIES WITH FEATURES:")
    print("-" * 40)
    
    policies_with_features = BasePolicy.objects.filter(
        policy_features__isnull=False
    ).select_related('policy_features')
    
    print(f"Policies with features: {policies_with_features.count()}")
    
    for policy in policies_with_features[:5]:
        features = policy.policy_features
        print(f"  - {policy.name}: {features.insurance_type} features")
        
        if features.insurance_type == 'HEALTH':
            summary = features.get_health_features_summary()
            if summary:
                print(f"    Health: {summary}")
        elif features.insurance_type == 'FUNERAL':
            summary = features.get_funeral_features_summary()
            if summary:
                print(f"    Funeral: {summary}")
    
    # 8. Get policies ordered by premium
    print("\n8. POLICIES ORDERED BY PREMIUM (Top 5 Most Expensive):")
    print("-" * 40)
    
    expensive_policies = BasePolicy.objects.order_by('-base_premium')[:5]
    for policy in expensive_policies:
        print(f"  - {policy.name}: R{policy.base_premium}/month")
    
    print("\n9. POLICIES ORDERED BY PREMIUM (Top 5 Most Affordable):")
    print("-" * 40)
    
    affordable_policies = BasePolicy.objects.order_by('base_premium')[:5]
    for policy in affordable_policies:
        print(f"  - {policy.name}: R{policy.base_premium}/month")
    
    # 10. Summary statistics
    print("\n10. SUMMARY STATISTICS:")
    print("-" * 40)
    
    total_policies = BasePolicy.objects.count()
    total_health = HealthPolicy.objects.count()
    total_funeral = FuneralPolicy.objects.count()
    total_active = BasePolicy.objects.filter(is_active=True).count()
    total_approved = BasePolicy.objects.filter(
        approval_status=BasePolicy.ApprovalStatus.APPROVED
    ).count()
    total_organizations = Organization.objects.count()
    
    print(f"Total Policies: {total_policies}")
    print(f"Health Policies: {total_health}")
    print(f"Funeral Policies: {total_funeral}")
    print(f"Active Policies: {total_active}")
    print(f"Approved Policies: {total_approved}")
    print(f"Organizations: {total_organizations}")
    
    # Verify the counts make sense
    if total_health + total_funeral <= total_policies:
        print("✓ Policy counts are consistent")
    else:
        print("⚠ Warning: Policy counts seem inconsistent")
    
    print("\n" + "="*60)
    print("POLICY RETRIEVAL TEST COMPLETED")
    print("="*60)
    
    return {
        'total_policies': total_policies,
        'health_policies': total_health,
        'funeral_policies': total_funeral,
        'active_policies': total_active,
        'approved_policies': total_approved
    }


def demonstrate_query_patterns():
    """Demonstrate different query patterns for retrieving policies."""
    print("\n" + "="*60)
    print("DEMONSTRATING QUERY PATTERNS")
    print("="*60)
    
    # Pattern 1: Basic retrieval
    print("\n1. BASIC RETRIEVAL:")
    print("-" * 30)
    all_policies = BasePolicy.objects.all()
    print(f"BasePolicy.objects.all() -> {all_policies.count()} policies")
    
    # Pattern 2: With related data (optimized)
    print("\n2. OPTIMIZED RETRIEVAL WITH RELATED DATA:")
    print("-" * 30)
    optimized_policies = BasePolicy.objects.select_related(
        'organization', 'category', 'policy_type'
    ).prefetch_related('policy_features')
    print(f"With select_related and prefetch_related -> {optimized_policies.count()} policies")
    
    # Pattern 3: Filtering
    print("\n3. FILTERING EXAMPLES:")
    print("-" * 30)
    
    # By status
    active_policies = BasePolicy.objects.filter(is_active=True)
    print(f"Active policies: {active_policies.count()}")
    
    # By approval status
    approved_policies = BasePolicy.objects.filter(
        approval_status=BasePolicy.ApprovalStatus.APPROVED
    )
    print(f"Approved policies: {approved_policies.count()}")
    
    # By premium range
    mid_range_policies = BasePolicy.objects.filter(
        base_premium__gte=500,
        base_premium__lte=2000
    )
    print(f"Mid-range policies (R500-R2000): {mid_range_policies.count()}")
    
    # Pattern 4: Specific model queries
    print("\n4. SPECIFIC MODEL QUERIES:")
    print("-" * 30)
    
    health_policies = HealthPolicy.objects.all()
    funeral_policies = FuneralPolicy.objects.all()
    print(f"HealthPolicy.objects.all() -> {health_policies.count()} policies")
    print(f"FuneralPolicy.objects.all() -> {funeral_policies.count()} policies")
    
    # Pattern 5: Complex queries
    print("\n5. COMPLEX QUERIES:")
    print("-" * 30)
    
    # Health policies with hospital cover
    health_with_hospital = HealthPolicy.objects.filter(
        includes_hospital_cover=True
    )
    print(f"Health policies with hospital cover: {health_with_hospital.count()}")
    
    # Funeral policies with family cover
    family_funeral = FuneralPolicy.objects.filter(
        cover_type=FuneralPolicy.CoverType.FAMILY
    )
    print(f"Family funeral policies: {family_funeral.count()}")
    
    # Policies from verified organizations
    verified_org_policies = BasePolicy.objects.filter(
        organization__verification_status=Organization.VerificationStatus.VERIFIED
    )
    print(f"Policies from verified organizations: {verified_org_policies.count()}")
    
    print("\n" + "="*60)
    print("QUERY PATTERNS DEMONSTRATION COMPLETED")
    print("="*60)


if __name__ == '__main__':
    try:
        # Run the main test
        results = test_get_all_policies()
        
        # Demonstrate query patterns
        demonstrate_query_patterns()
        
        print(f"\n✅ Test completed successfully!")
        print(f"Found {results['total_policies']} total policies in the database")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()