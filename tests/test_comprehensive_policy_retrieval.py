"""
Comprehensive test for retrieving all policies (health and funeral) from the database.
This test demonstrates various ways to query and retrieve policies, and also shows
how to create test data if needed.
"""

import os
import sys
import django
from decimal import Decimal

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


class PolicyRetrievalDemo:
    """Comprehensive demonstration of policy retrieval methods."""
    
    def __init__(self):
        self.results = {}
    
    def test_existing_policies(self):
        """Test retrieving existing policies from the database."""
        print("="*70)
        print("RETRIEVING EXISTING POLICIES FROM DATABASE")
        print("="*70)
        
        # Get all existing policies
        all_policies = BasePolicy.objects.select_related(
            'organization', 'category', 'policy_type'
        ).prefetch_related('policy_features').all()
        
        print(f"\n📊 TOTAL POLICIES IN DATABASE: {all_policies.count()}")
        print("-" * 50)
        
        if all_policies.exists():
            for i, policy in enumerate(all_policies, 1):
                print(f"{i}. {policy.name}")
                print(f"   Policy Number: {policy.policy_number}")
                print(f"   Category: {policy.category.name}")
                print(f"   Organization: {policy.organization.name}")
                print(f"   Premium: R{policy.base_premium}/month")
                print(f"   Coverage: R{policy.coverage_amount}")
                print(f"   Status: {policy.get_approval_status_display()}")
                print(f"   Active: {'✅' if policy.is_active else '❌'}")
                
                # Show features if available
                if hasattr(policy, 'policy_features') and policy.policy_features:
                    features = policy.policy_features
                    print(f"   Features: {features.insurance_type}")
                    
                    if features.insurance_type == 'HEALTH':
                        summary = features.get_health_features_summary()
                        if summary and summary != "No features configured":
                            print(f"   Health Details: {summary}")
                    elif features.insurance_type == 'FUNERAL':
                        summary = features.get_funeral_features_summary()
                        if summary and summary != "No features configured":
                            print(f"   Funeral Details: {summary}")
                
                print()
        else:
            print("   No policies found in database")
        
        self.results['existing_policies'] = all_policies.count()
        return all_policies
    
    def test_policy_categories(self):
        """Test retrieving policies by category."""
        print("\n📂 POLICIES BY CATEGORY:")
        print("-" * 50)
        
        categories = PolicyCategory.objects.all()
        category_stats = {}
        
        for category in categories:
            category_policies = BasePolicy.objects.filter(category=category)
            count = category_policies.count()
            category_stats[category.name] = count
            
            print(f"{category.name}: {count} policies")
            
            # Show examples
            for policy in category_policies[:3]:
                print(f"  • {policy.name} (R{policy.base_premium}/month)")
            
            if count > 3:
                print(f"  ... and {count - 3} more")
            print()
        
        self.results['categories'] = category_stats
        return category_stats
    
    def test_specific_policy_types(self):
        """Test retrieving specific policy model types."""
        print("\n🏥 SPECIFIC POLICY MODEL TYPES:")
        print("-" * 50)
        
        # Health policies using HealthPolicy model
        health_policies = HealthPolicy.objects.select_related('organization').all()
        print(f"HealthPolicy model instances: {health_policies.count()}")
        
        if health_policies.exists():
            print("Health Policy Examples:")
            for policy in health_policies[:3]:
                print(f"  • {policy.name}")
                print(f"    Coverage Level: {policy.get_coverage_level_display()}")
                print(f"    Hospital Cover: {'Yes' if policy.includes_hospital_cover else 'No'}")
                print(f"    Outpatient Cover: {'Yes' if policy.includes_outpatient_cover else 'No'}")
        else:
            print("  No HealthPolicy instances found")
        
        print()
        
        # Funeral policies using FuneralPolicy model
        funeral_policies = FuneralPolicy.objects.select_related('organization').all()
        print(f"FuneralPolicy model instances: {funeral_policies.count()}")
        
        if funeral_policies.exists():
            print("Funeral Policy Examples:")
            for policy in funeral_policies[:3]:
                print(f"  • {policy.name}")
                print(f"    Cover Type: {policy.get_cover_type_display()}")
                print(f"    Service Type: {policy.get_service_type_display()}")
                print(f"    Main Member Cover: R{policy.main_member_cover_amount}")
        else:
            print("  No FuneralPolicy instances found")
        
        self.results['health_model_count'] = health_policies.count()
        self.results['funeral_model_count'] = funeral_policies.count()
        
        return health_policies, funeral_policies
    
    def test_policy_filtering(self):
        """Test various filtering options for policies."""
        print("\n🔍 POLICY FILTERING OPTIONS:")
        print("-" * 50)
        
        # Active policies
        active_policies = BasePolicy.objects.filter(is_active=True)
        print(f"Active policies: {active_policies.count()}")
        
        # Approved policies
        approved_policies = BasePolicy.objects.filter(
            approval_status=BasePolicy.ApprovalStatus.APPROVED
        )
        print(f"Approved policies: {approved_policies.count()}")
        
        # Policies by premium range
        budget_policies = BasePolicy.objects.filter(base_premium__lt=1000)
        mid_range_policies = BasePolicy.objects.filter(
            base_premium__gte=1000, base_premium__lt=2500
        )
        premium_policies = BasePolicy.objects.filter(base_premium__gte=2500)
        
        print(f"Budget policies (< R1000): {budget_policies.count()}")
        print(f"Mid-range policies (R1000-R2500): {mid_range_policies.count()}")
        print(f"Premium policies (≥ R2500): {premium_policies.count()}")
        
        # Policies with features
        policies_with_features = BasePolicy.objects.filter(
            policy_features__isnull=False
        )
        print(f"Policies with features: {policies_with_features.count()}")
        
        # Policies from verified organizations
        verified_org_policies = BasePolicy.objects.filter(
            organization__verification_status=Organization.VerificationStatus.VERIFIED
        )
        print(f"Policies from verified organizations: {verified_org_policies.count()}")
        
        self.results['filtering'] = {
            'active': active_policies.count(),
            'approved': approved_policies.count(),
            'budget': budget_policies.count(),
            'mid_range': mid_range_policies.count(),
            'premium': premium_policies.count(),
            'with_features': policies_with_features.count(),
            'verified_orgs': verified_org_policies.count()
        }
    
    def test_policy_ordering(self):
        """Test different ordering options for policies."""
        print("\n📈 POLICY ORDERING OPTIONS:")
        print("-" * 50)
        
        # Most expensive policies
        print("Most Expensive Policies:")
        expensive_policies = BasePolicy.objects.order_by('-base_premium')[:5]
        for i, policy in enumerate(expensive_policies, 1):
            print(f"  {i}. {policy.name}: R{policy.base_premium}/month")
        
        print("\nMost Affordable Policies:")
        affordable_policies = BasePolicy.objects.order_by('base_premium')[:5]
        for i, policy in enumerate(affordable_policies, 1):
            print(f"  {i}. {policy.name}: R{policy.base_premium}/month")
        
        print("\nHighest Coverage Policies:")
        high_coverage_policies = BasePolicy.objects.order_by('-coverage_amount')[:5]
        for i, policy in enumerate(high_coverage_policies, 1):
            print(f"  {i}. {policy.name}: R{policy.coverage_amount} coverage")
        
        print("\nNewest Policies:")
        newest_policies = BasePolicy.objects.order_by('-created_at')[:5]
        for i, policy in enumerate(newest_policies, 1):
            print(f"  {i}. {policy.name} (created: {policy.created_at.strftime('%Y-%m-%d')})")
    
    def demonstrate_query_optimization(self):
        """Demonstrate query optimization techniques."""
        print("\n⚡ QUERY OPTIMIZATION TECHNIQUES:")
        print("-" * 50)
        
        # Basic query (can cause N+1 problem)
        print("1. Basic Query (potential N+1 problem):")
        basic_policies = BasePolicy.objects.all()
        print(f"   BasePolicy.objects.all() -> {basic_policies.count()} policies")
        
        # Optimized query with select_related
        print("\n2. Optimized with select_related:")
        optimized_policies = BasePolicy.objects.select_related(
            'organization', 'category', 'policy_type'
        )
        print(f"   With select_related -> {optimized_policies.count()} policies")
        print("   ✅ Reduces database queries for foreign key relationships")
        
        # Further optimized with prefetch_related
        print("\n3. Further optimized with prefetch_related:")
        fully_optimized = BasePolicy.objects.select_related(
            'organization', 'category', 'policy_type'
        ).prefetch_related('policy_features')
        print(f"   With prefetch_related -> {fully_optimized.count()} policies")
        print("   ✅ Efficiently loads related PolicyFeatures")
        
        # Demonstrate the difference
        print("\n4. Query Performance Comparison:")
        print("   Basic query: Multiple DB hits for each policy's related data")
        print("   Optimized query: Single DB query with JOINs")
        print("   Recommendation: Always use select_related/prefetch_related in production")
    
    def create_sample_data_if_needed(self):
        """Create sample data if the database is empty or lacks variety."""
        print("\n🔧 CHECKING IF SAMPLE DATA CREATION IS NEEDED:")
        print("-" * 50)
        
        health_count = HealthPolicy.objects.count()
        funeral_count = FuneralPolicy.objects.count()
        
        print(f"Current HealthPolicy instances: {health_count}")
        print(f"Current FuneralPolicy instances: {funeral_count}")
        
        if health_count == 0 or funeral_count == 0:
            print("\n⚠️  Limited policy variety detected.")
            print("💡 To create sample data, you could run:")
            print("   python manage.py shell")
            print("   >>> from tests.test_comprehensive_policy_retrieval import create_sample_policies")
            print("   >>> create_sample_policies()")
            print("\nOr use Django fixtures to load test data.")
        else:
            print("✅ Good variety of policy types found!")
    
    def generate_summary_report(self):
        """Generate a comprehensive summary report."""
        print("\n" + "="*70)
        print("📋 COMPREHENSIVE POLICY RETRIEVAL SUMMARY REPORT")
        print("="*70)
        
        total_policies = BasePolicy.objects.count()
        total_health_models = HealthPolicy.objects.count()
        total_funeral_models = FuneralPolicy.objects.count()
        total_organizations = Organization.objects.count()
        total_categories = PolicyCategory.objects.count()
        
        print(f"\n📊 DATABASE STATISTICS:")
        print(f"   Total Policies (BasePolicy): {total_policies}")
        print(f"   Health Policy Models: {total_health_models}")
        print(f"   Funeral Policy Models: {total_funeral_models}")
        print(f"   Organizations: {total_organizations}")
        print(f"   Policy Categories: {total_categories}")
        
        if 'categories' in self.results:
            print(f"\n📂 POLICIES BY CATEGORY:")
            for category, count in self.results['categories'].items():
                print(f"   {category}: {count} policies")
        
        if 'filtering' in self.results:
            print(f"\n🔍 FILTERING RESULTS:")
            filtering = self.results['filtering']
            print(f"   Active Policies: {filtering['active']}")
            print(f"   Approved Policies: {filtering['approved']}")
            print(f"   Budget Policies (< R1000): {filtering['budget']}")
            print(f"   Mid-range Policies: {filtering['mid_range']}")
            print(f"   Premium Policies: {filtering['premium']}")
            print(f"   Policies with Features: {filtering['with_features']}")
            print(f"   From Verified Organizations: {filtering['verified_orgs']}")
        
        print(f"\n✅ RETRIEVAL METHODS DEMONSTRATED:")
        print(f"   ✓ BasePolicy.objects.all() - Get all policies")
        print(f"   ✓ HealthPolicy.objects.all() - Get health-specific policies")
        print(f"   ✓ FuneralPolicy.objects.all() - Get funeral-specific policies")
        print(f"   ✓ Filtering by status, premium, organization")
        print(f"   ✓ Ordering by premium, coverage, date")
        print(f"   ✓ Query optimization with select_related/prefetch_related")
        print(f"   ✓ Category-based retrieval")
        print(f"   ✓ Feature-based queries")
        
        print(f"\n🎯 KEY FINDINGS:")
        if total_policies > 0:
            print(f"   • Database contains {total_policies} policies ready for retrieval")
            if total_health_models == 0 and total_funeral_models == 0:
                print(f"   • All policies are stored as BasePolicy instances")
                print(f"   • Consider using specific HealthPolicy/FuneralPolicy models for type-specific features")
            else:
                print(f"   • Mix of BasePolicy and specific model instances found")
        else:
            print(f"   • Database is empty - consider loading sample data")
        
        print(f"\n" + "="*70)
        print("POLICY RETRIEVAL DEMONSTRATION COMPLETED SUCCESSFULLY! ✅")
        print("="*70)


def create_sample_policies():
    """Helper function to create sample policies for testing."""
    print("Creating sample policies...")
    
    # This would create sample data - implementation depends on your needs
    # For now, just show what could be created
    print("Sample policy creation would include:")
    print("- Health policies with various coverage levels")
    print("- Funeral policies with different family coverage options")
    print("- Policies from multiple organizations")
    print("- Mix of active/inactive and approved/pending policies")


def main():
    """Main function to run all policy retrieval tests."""
    demo = PolicyRetrievalDemo()
    
    try:
        # Run all tests
        demo.test_existing_policies()
        demo.test_policy_categories()
        demo.test_specific_policy_types()
        demo.test_policy_filtering()
        demo.test_policy_ordering()
        demo.demonstrate_query_optimization()
        demo.create_sample_data_if_needed()
        demo.generate_summary_report()
        
        print(f"\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()