#!/usr/bin/env python
"""
Test script to verify the survey fix works.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from django.test import Client
from django.urls import reverse

def test_survey_redirect_fix():
    """Test that the survey redirect fix works."""
    print("🧪 Testing survey redirect fix...")
    
    client = Client()
    
    # Test 1: Direct funeral survey access
    print("\n1️⃣ Testing funeral survey redirect...")
    try:
        response = client.get('/surveys/funeral/direct/', follow=True)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Funeral survey redirect working!")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Direct health survey access
    print("\n2️⃣ Testing health survey redirect...")
    try:
        response = client.get('/surveys/health/direct/', follow=True)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Health survey redirect working!")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Check URL generation
    print("\n3️⃣ Testing URL generation...")
    try:
        funeral_url = reverse('surveys:direct_survey', kwargs={'category_slug': 'funeral'})
        health_url = reverse('surveys:direct_survey', kwargs={'category_slug': 'health'})
        print(f"   Funeral URL: {funeral_url}")
        print(f"   Health URL: {health_url}")
        print("   ✅ URL generation working!")
    except Exception as e:
        print(f"   ❌ URL generation error: {e}")
    
    print("\n✅ Test complete!")

if __name__ == '__main__':
    test_survey_redirect_fix()