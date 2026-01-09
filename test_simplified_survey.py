#!/usr/bin/env python
"""
Test script for simplified survey functionality.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from policies.models import PolicyCategory
from surveys.models import SurveyQuestion

def test_survey_flow():
    """Test the simplified survey flow."""
    print("🧪 Testing simplified survey flow...")
    
    client = Client()
    
    # Test 1: Direct survey access
    print("\n1️⃣ Testing direct survey access...")
    response = client.get('/surveys/health/direct/')
    print(f"   Status: {response.status_code}")
    if response.status_code == 302:
        print(f"   Redirects to: {response.url}")
    
    # Test 2: Check if health questions exist
    print("\n2️⃣ Checking health survey questions...")
    health_category = PolicyCategory.objects.get(slug='health')
    questions = SurveyQuestion.objects.filter(category=health_category, is_active=True).order_by('display_order')
    print(f"   Found {questions.count()} active health questions")
    
    if questions.exists():
        first_question = questions.first()
        print(f"   First question: {first_question.question_text}")
        print(f"   Question type: {first_question.question_type}")
    
    # Test 3: Try to access survey form directly
    print("\n3️⃣ Testing survey form access...")
    try:
        response = client.get('/surveys/health/?session=test-session-123')
        print(f"   Status: {response.status_code}")
        if response.status_code == 302:
            print(f"   Redirects to: {response.url}")
        elif response.status_code == 404:
            print("   Session not found (expected)")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✅ Test complete!")

if __name__ == '__main__':
    test_survey_flow()