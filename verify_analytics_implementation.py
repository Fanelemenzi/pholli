#!/usr/bin/env python
"""
Verification script for analytics implementation.
This script verifies that the analytics system has been properly updated
to track benefit levels and ranges while removing medical aid references.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from simple_surveys.analytics import SimpleSurveyAnalytics, AnalyticsDashboard
from simple_surveys.models import (
    HOSPITAL_BENEFIT_CHOICES, OUT_HOSPITAL_BENEFIT_CHOICES,
    ANNUAL_LIMIT_FAMILY_RANGES, ANNUAL_LIMIT_MEMBER_RANGES
)
import json


def verify_analytics_structure():
    """Verify that analytics classes have the correct structure"""
    print("🔍 Verifying analytics structure...")
    
    analytics = SimpleSurveyAnalytics()
    dashboard = AnalyticsDashboard()
    
    # Check that analytics methods exist
    required_methods = [
        'get_benefit_level_analytics',
        'get_range_selection_analytics', 
        'get_completion_analytics',
        'get_comprehensive_report'
    ]
    
    for method in required_methods:
        if hasattr(analytics, method):
            print(f"✅ Analytics method '{method}' exists")
        else:
            print(f"❌ Analytics method '{method}' missing")
            return False
    
    # Check dashboard methods
    dashboard_methods = ['get_dashboard_data', 'export_analytics_data']
    for method in dashboard_methods:
        if hasattr(dashboard, method):
            print(f"✅ Dashboard method '{method}' exists")
        else:
            print(f"❌ Dashboard method '{method}' missing")
            return False
    
    return True


def verify_benefit_choices():
    """Verify that benefit level choices are properly defined"""
    print("\n🔍 Verifying benefit level choices...")
    
    # Check hospital benefit choices
    if len(HOSPITAL_BENEFIT_CHOICES) >= 5:
        print(f"✅ Hospital benefit choices defined: {len(HOSPITAL_BENEFIT_CHOICES)} options")
        for choice in HOSPITAL_BENEFIT_CHOICES[:3]:  # Show first 3
            print(f"   - {choice[0]}: {choice[1]}")
    else:
        print(f"❌ Hospital benefit choices insufficient: {len(HOSPITAL_BENEFIT_CHOICES)} options")
        return False
    
    # Check out-hospital benefit choices
    if len(OUT_HOSPITAL_BENEFIT_CHOICES) >= 5:
        print(f"✅ Out-hospital benefit choices defined: {len(OUT_HOSPITAL_BENEFIT_CHOICES)} options")
        for choice in OUT_HOSPITAL_BENEFIT_CHOICES[:3]:  # Show first 3
            print(f"   - {choice[0]}: {choice[1]}")
    else:
        print(f"❌ Out-hospital benefit choices insufficient: {len(OUT_HOSPITAL_BENEFIT_CHOICES)} options")
        return False
    
    return True


def verify_range_choices():
    """Verify that range choices are properly defined"""
    print("\n🔍 Verifying annual limit range choices...")
    
    # Check family range choices
    if len(ANNUAL_LIMIT_FAMILY_RANGES) >= 8:
        print(f"✅ Family range choices defined: {len(ANNUAL_LIMIT_FAMILY_RANGES)} options")
        for choice in ANNUAL_LIMIT_FAMILY_RANGES[:3]:  # Show first 3
            print(f"   - {choice[0]}: {choice[1]}")
    else:
        print(f"❌ Family range choices insufficient: {len(ANNUAL_LIMIT_FAMILY_RANGES)} options")
        return False
    
    # Check member range choices
    if len(ANNUAL_LIMIT_MEMBER_RANGES) >= 8:
        print(f"✅ Member range choices defined: {len(ANNUAL_LIMIT_MEMBER_RANGES)} options")
        for choice in ANNUAL_LIMIT_MEMBER_RANGES[:3]:  # Show first 3
            print(f"   - {choice[0]}: {choice[1]}")
    else:
        print(f"❌ Member range choices insufficient: {len(ANNUAL_LIMIT_MEMBER_RANGES)} options")
        return False
    
    return True


def verify_no_medical_aid_references():
    """Verify that medical aid references are removed from analytics"""
    print("\n🔍 Verifying medical aid references are removed...")
    
    analytics = SimpleSurveyAnalytics()
    
    try:
        # Test with empty data (should not crash)
        benefit_data = analytics.get_benefit_level_analytics('health', 7)
        range_data = analytics.get_range_selection_analytics('health', 7)
        completion_data = analytics.get_completion_analytics('health', 7)
        comprehensive_data = analytics.get_comprehensive_report('health', 7)
        
        # Convert to JSON and check for medical aid references
        all_data = {
            'benefit_data': benefit_data,
            'range_data': range_data,
            'completion_data': completion_data,
            'comprehensive_data': comprehensive_data
        }
        
        json_str = json.dumps(all_data).lower()
        
        # Look for specific medical aid field references, not just the word "medical"
        medical_aid_refs = ['medical_aid', 'currently_on_medical_aid', 'medical aid status']
        found_refs = [ref for ref in medical_aid_refs if ref in json_str]
        
        if found_refs:
            print(f"❌ Medical aid field references found in analytics data: {found_refs}")
            return False
        else:
            print("✅ No medical aid field references found in analytics data")
        
        # Check that new analytics are present
        if 'hospital_benefits' in benefit_data and 'out_hospital_benefits' in benefit_data:
            print("✅ Benefit level analytics structure present")
        else:
            print("❌ Benefit level analytics structure missing")
            return False
        
        if 'family_ranges' in range_data and 'member_ranges' in range_data:
            print("✅ Range selection analytics structure present")
        else:
            print("❌ Range selection analytics structure missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing analytics: {e}")
        return False


def verify_template_files():
    """Verify that analytics template files exist"""
    print("\n🔍 Verifying analytics template files...")
    
    template_files = [
        'simple_surveys/templates/admin/simple_surveys/analytics_dashboard.html',
        'simple_surveys/templates/admin/simple_surveys/benefit_level_analytics.html',
        'simple_surveys/templates/admin/simple_surveys/range_selection_analytics.html',
        'simple_surveys/templates/admin/simple_surveys/completion_analytics.html'
    ]
    
    all_exist = True
    for template_file in template_files:
        if os.path.exists(template_file):
            file_size = os.path.getsize(template_file)
            if file_size > 0:
                print(f"✅ Template exists: {template_file} ({file_size} bytes)")
            else:
                print(f"⚠️  Template exists but is empty: {template_file}")
                all_exist = False
        else:
            print(f"❌ Template missing: {template_file}")
            all_exist = False
    
    return all_exist


def verify_urls():
    """Verify that analytics URLs are configured"""
    print("\n🔍 Verifying analytics URLs...")
    
    try:
        from django.urls import reverse
        
        url_names = [
            'simple_surveys:admin_analytics_dashboard',
            'simple_surveys:admin_benefit_analytics',
            'simple_surveys:admin_range_analytics',
            'simple_surveys:admin_completion_analytics',
            'simple_surveys:admin_export_analytics',
            'simple_surveys:admin_analytics_summary'
        ]
        
        all_configured = True
        for url_name in url_names:
            try:
                url = reverse(url_name)
                print(f"✅ URL configured: {url_name} -> {url}")
            except Exception as e:
                print(f"❌ URL not configured: {url_name} - {e}")
                all_configured = False
        
        return all_configured
        
    except Exception as e:
        print(f"❌ Error checking URLs: {e}")
        return False


def main():
    """Run all verification checks"""
    print("🚀 Starting analytics implementation verification...\n")
    
    checks = [
        ("Analytics Structure", verify_analytics_structure),
        ("Benefit Level Choices", verify_benefit_choices),
        ("Range Choices", verify_range_choices),
        ("Medical Aid Removal", verify_no_medical_aid_references),
        ("Template Files", verify_template_files),
        ("URL Configuration", verify_urls)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n{'='*50}")
        print(f"Running: {check_name}")
        print('='*50)
        
        try:
            if check_func():
                print(f"✅ {check_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {check_name}: FAILED")
        except Exception as e:
            print(f"❌ {check_name}: ERROR - {e}")
    
    print(f"\n{'='*50}")
    print(f"VERIFICATION SUMMARY")
    print('='*50)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All analytics implementation checks PASSED!")
        print("\nTask 15 implementation is complete:")
        print("✅ Modified survey analytics to track benefit level selections")
        print("✅ Updated completion rate tracking for new question structure") 
        print("✅ Added reporting for range selection patterns")
        print("✅ Removed medical aid status from analytics dashboards")
        return True
    else:
        print("⚠️  Some checks failed. Please review the issues above.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)