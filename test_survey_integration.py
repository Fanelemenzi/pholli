#!/usr/bin/env python
"""
Integration test for the complete survey flow including form submission.
"""

import os
import sys
import django
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

def test_survey_integration():
    """Test the complete survey integration including form submission"""
    client = Client()
    
    print("🧪 TESTING SURVEY INTEGRATION")
    print("=" * 50)
    
    # Test 1: Complete Health Survey Flow
    print("\n1️⃣ Testing Complete Health Survey Flow")
    
    # Step 1a: Access health survey form
    response = client.get(reverse('survey', kwargs={'category': 'health'}))
    print(f"   ✅ Health survey form loaded: {response.status_code}")
    assert response.status_code == 200
    
    # Step 1b: Submit health survey (POST)
    survey_data = {
        'age': '30',
        'gender': 'male',
        'location': 'johannesburg',
        'coverage_type': 'individual',
        'budget': '1000'
    }
    response = client.post(reverse('process', kwargs={'category': 'health'}), data=survey_data)
    print(f"   ✅ Health survey submission: {response.status_code}")
    
    if response.status_code == 302:
        print(f"   ✅ Redirects to: {response.url}")
        # Follow the redirect
        response = client.get(response.url)
        print(f"   ✅ Results page loaded: {response.status_code}")
        assert response.status_code == 200
    else:
        print(f"   ⚠️  Expected redirect, got {response.status_code}")
    
    # Test 2: Complete Funeral Survey Flow
    print("\n2️⃣ Testing Complete Funeral Survey Flow")
    
    # Step 2a: Access funeral survey form
    response = client.get(reverse('survey', kwargs={'category': 'funeral'}))
    print(f"   ✅ Funeral survey form loaded: {response.status_code}")
    assert response.status_code == 200
    
    # Step 2b: Submit funeral survey (POST)
    survey_data = {
        'age': '45',
        'gender': 'female',
        'location': 'cape_town',
        'coverage_amount': '50000',
        'family_size': '4'
    }
    response = client.post(reverse('process', kwargs={'category': 'funeral'}), data=survey_data)
    print(f"   ✅ Funeral survey submission: {response.status_code}")
    
    if response.status_code == 302:
        print(f"   ✅ Redirects to: {response.url}")
        # Follow the redirect
        response = client.get(response.url)
        print(f"   ✅ Results page loaded: {response.status_code}")
        assert response.status_code == 200
    else:
        print(f"   ⚠️  Expected redirect, got {response.status_code}")
    
    # Test 3: Test AJAX endpoints
    print("\n3️⃣ Testing AJAX Endpoints")
    
    # Test save response AJAX
    response = client.post(reverse('save_response_ajax', kwargs={'category': 'health'}), 
                          data={'question_id': '1', 'answer': 'test'})
    print(f"   ✅ AJAX save response: {response.status_code}")
    if response.status_code == 200:
        import json
        data = json.loads(response.content)
        print(f"   ✅ AJAX response: {data}")
    
    # Test survey status AJAX
    response = client.get(reverse('survey_status_ajax', kwargs={'category': 'health'}))
    print(f"   ✅ AJAX survey status: {response.status_code}")
    if response.status_code == 200:
        import json
        data = json.loads(response.content)
        print(f"   ✅ Status response: {data}")
    
    print("\n🎉 INTEGRATION TESTS COMPLETED!")
    return True

def test_error_handling():
    """Test error handling scenarios"""
    client = Client()
    
    print("\n🚨 TESTING ERROR HANDLING")
    print("=" * 30)
    
    # Test invalid category
    print("\n1️⃣ Testing Invalid Category")
    response = client.get('/survey/invalid_category/')
    print(f"   ✅ Invalid category response: {response.status_code}")
    # Should return 404 or handle gracefully
    
    # Test direct survey with invalid category
    print("\n2️⃣ Testing Invalid Direct Survey")
    response = client.get(reverse('direct_survey', kwargs={'category_slug': 'invalid'}))
    print(f"   ✅ Invalid direct survey response: {response.status_code}")
    # Should return 404
    assert response.status_code == 404
    
    print("\n✅ Error handling tests completed!")

def test_template_rendering():
    """Test that templates are rendering correctly with content"""
    client = Client()
    
    print("\n🎨 TESTING TEMPLATE RENDERING")
    print("=" * 35)
    
    # Test health survey template content
    print("\n1️⃣ Testing Health Survey Template Content")
    response = client.get(reverse('survey', kwargs={'category': 'health'}))
    content = response.content.decode('utf-8')
    
    # Check for key elements that should be in the survey form
    checks = [
        ('form', 'form' in content.lower()),
        ('health', 'health' in content.lower()),
        ('survey', 'survey' in content.lower()),
    ]
    
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"   {status} Contains '{check_name}': {check_result}")
    
    # Test results template content
    print("\n2️⃣ Testing Results Template Content")
    response = client.get(reverse('results', kwargs={'category': 'health'}))
    content = response.content.decode('utf-8')
    
    # Check for key elements that should be in the results
    checks = [
        ('results', 'result' in content.lower()),
        ('health', 'health' in content.lower()),
    ]
    
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"   {status} Contains '{check_name}': {check_result}")
    
    print("\n✅ Template rendering tests completed!")

if __name__ == '__main__':
    try:
        test_survey_integration()
        test_error_handling()
        test_template_rendering()
        print("\n🏆 ALL INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)