#!/usr/bin/env python
"""
Test script to verify that survey questions are being displayed correctly.
"""

import os
import sys
import django
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

def test_survey_questions():
    """Test that survey questions are properly displayed"""
    client = Client()
    
    print("🧪 TESTING SURVEY QUESTIONS")
    print("=" * 40)
    
    # Test Health Survey Questions
    print("\n1️⃣ Testing Health Survey Questions")
    response = client.get(reverse('survey', kwargs={'category': 'health'}))
    content = response.content.decode('utf-8')
    
    # Check for specific health survey questions
    health_questions = [
        'What type of health coverage are you looking for?',
        'What is your age?',
        'What is your gender?',
        'Which province are you located in?',
        'What is your monthly budget for health insurance?',
        'Do you have any chronic conditions?',
        'How many dependents do you have?'
    ]
    
    found_questions = 0
    for question in health_questions:
        if question in content:
            found_questions += 1
            print(f"   ✅ Found: {question}")
        else:
            print(f"   ❌ Missing: {question}")
    
    print(f"   📊 Health Survey: {found_questions}/{len(health_questions)} questions found")
    
    # Test Funeral Survey Questions
    print("\n2️⃣ Testing Funeral Survey Questions")
    response = client.get(reverse('survey', kwargs={'category': 'funeral'}))
    content = response.content.decode('utf-8')
    
    # Check for specific funeral survey questions
    funeral_questions = [
        'What type of funeral coverage are you looking for?',
        'What is your age?',
        'What is your gender?',
        'Which province are you located in?',
        'What coverage amount are you looking for?',
        'What is your monthly budget for funeral insurance?',
        'How many family members do you want to cover?'
    ]
    
    found_questions = 0
    for question in funeral_questions:
        if question in content:
            found_questions += 1
            print(f"   ✅ Found: {question}")
        else:
            print(f"   ❌ Missing: {question}")
    
    print(f"   📊 Funeral Survey: {found_questions}/{len(funeral_questions)} questions found")
    
    # Test Feature Survey Questions
    print("\n3️⃣ Testing Feature Survey Questions")
    response = client.get(reverse('feature_survey', kwargs={'category': 'health'}))
    content = response.content.decode('utf-8')
    
    # Check for feature-specific questions
    feature_questions = [
        'Which features are most important to you?',
        'How do you prefer to manage your policy?'
    ]
    
    found_questions = 0
    for question in feature_questions:
        if question in content:
            found_questions += 1
            print(f"   ✅ Found: {question}")
        else:
            print(f"   ❌ Missing: {question}")
    
    print(f"   📊 Feature Survey: {found_questions}/{len(feature_questions)} additional questions found")
    
    # Test Form Elements
    print("\n4️⃣ Testing Form Elements")
    response = client.get(reverse('survey', kwargs={'category': 'health'}))
    content = response.content.decode('utf-8')
    
    form_elements = [
        'form-select',             # Select dropdowns
        'type="number"',           # Number inputs
        'type="radio"',            # Radio buttons
        'type="checkbox"',         # Checkboxes
        'data-question-id='        # Question IDs for AJAX
    ]
    
    found_elements = 0
    for element in form_elements:
        if element in content:
            found_elements += 1
            print(f"   ✅ Found form element: {element}")
        else:
            print(f"   ❌ Missing form element: {element}")
    
    print(f"   📊 Form Elements: {found_elements}/{len(form_elements)} elements found")
    
    # Test Progress Information
    print("\n5️⃣ Testing Progress Information")
    response = client.get(reverse('survey', kwargs={'category': 'health'}))
    content = response.content.decode('utf-8')
    
    # Check for progress-related content
    if 'Survey Progress' in content:
        print("   ✅ Progress section found")
    else:
        print("   ❌ Progress section missing")
    
    if 'questions completed' in content:
        print("   ✅ Progress counter found")
    else:
        print("   ❌ Progress counter missing")
    
    return True

if __name__ == '__main__':
    try:
        test_survey_questions()
        print("\n🏆 SURVEY QUESTIONS TEST COMPLETED!")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)