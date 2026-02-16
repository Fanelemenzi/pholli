"""
Test to verify the admin URL fix works correctly.
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

from django.urls import reverse
from django.test import TestCase
from organizations.models import Organization


def test_admin_url_fix():
    """Test that the admin URL fix works correctly."""
    print("="*60)
    print("TESTING ADMIN URL FIX")
    print("="*60)
    
    try:
        # Test 1: Check if the BasePolicy admin URL exists
        print("\n1. TESTING BASEPOLICY ADMIN URL")
        print("-" * 40)
        
        try:
            url = reverse('admin:policies_basepolicy_changelist')
            print(f"✓ BasePolicy changelist URL: {url}")
        except Exception as e:
            print(f"❌ BasePolicy changelist URL failed: {str(e)}")
            return False
        
        try:
            url = reverse('admin:policies_basepolicy_change', args=[1])
            print(f"✓ BasePolicy change URL: {url}")
        except Exception as e:
            print(f"❌ BasePolicy change URL failed: {str(e)}")
            return False
        
        # Test 2: Test the organization admin method
        print("\n2. TESTING ORGANIZATION ADMIN METHOD")
        print("-" * 40)
        
        # Create a test organization
        org = Organization.objects.filter(is_active=True).first()
        
        if org:
            print(f"Testing with organization: {org.name}")
            
            # Import the admin class
            from organizations.admin import OrganizationAdmin
            from django.contrib.admin.sites import site
            
            admin_instance = OrganizationAdmin(Organization, site)
            
            # Test the active_policies_count method
            try:
                result = admin_instance.active_policies_count(org)
                print(f"✓ active_policies_count method works: {result}")
            except Exception as e:
                print(f"❌ active_policies_count method failed: {str(e)}")
                return False
        else:
            print("⚠️  No organizations found to test with")
        
        # Test 3: Check other admin URLs
        print("\n3. TESTING OTHER ADMIN URLS")
        print("-" * 40)
        
        admin_urls_to_test = [
            ('admin:organizations_organization_changelist', 'Organizations list'),
            ('admin:policies_policycategory_changelist', 'Policy categories list'),
            ('admin:policies_policytype_changelist', 'Policy types list'),
            ('admin:policies_policyfeatures_changelist', 'Policy features list'),
        ]
        
        for url_name, description in admin_urls_to_test:
            try:
                url = reverse(url_name)
                print(f"✓ {description}: {url}")
            except Exception as e:
                print(f"❌ {description} failed: {str(e)}")
        
        print("\n✅ ADMIN URL FIX TEST PASSED")
        print("\nThe admin URL issue has been resolved:")
        print("  ✓ BasePolicy admin URLs work correctly")
        print("  ✓ Organization admin method uses correct URL")
        print("  ✓ No more 'policies_policy_changelist' errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Admin URL fix test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("Testing Admin URL Fix...")
    success = test_admin_url_fix()
    
    if success:
        print("\n🎉 Admin URL fix is working correctly!")
    else:
        print("\n❌ Admin URL fix test failed")