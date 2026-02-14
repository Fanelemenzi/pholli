#!/usr/bin/env python
"""
Debug script to check the actual HTML content of the survey.
"""

import os
import sys
import django
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

def debug_survey_content():
    """Debug the survey content to see what's being rendered"""
    client = Client()
    
    print("🔍 DEBUGGING SURVEY CONTENT")
    print("=" * 40)
    
    # Get health survey content
    response = client.get(reverse('survey', kwargs={'category': 'health'}))
    content = response.content.decode('utf-8')
    
    # Look for radio and checkbox sections
    print("\n📋 Looking for radio button sections...")
    if 'radio-group' in content:
        print("✅ Found radio-group class")
        # Find the gender question section
        start = content.find('What is your gender?')
        if start != -1:
            end = content.find('</div>', start + 500)  # Look for end of question card
            gender_section = content[start:end]
            print("🎯 Gender question section:")
            print(gender_section[:500] + "..." if len(gender_section) > 500 else gender_section)
    else:
        print("❌ No radio-group class found")
    
    print("\n📋 Looking for checkbox sections...")
    if 'checkbox-group' in content:
        print("✅ Found checkbox-group class")
        # Find the chronic conditions question section
        start = content.find('Do you have any chronic conditions?')
        if start != -1:
            end = content.find('</div>', start + 500)  # Look for end of question card
            chronic_section = content[start:end]
            print("🎯 Chronic conditions question section:")
            print(chronic_section[:500] + "..." if len(chronic_section) > 500 else chronic_section)
    else:
        print("❌ No checkbox-group class found")
    
    # Check if the questions are being processed correctly
    print("\n📋 Checking question types in content...")
    question_types = ['input_type', 'radio', 'checkbox', 'select', 'number']
    for qtype in question_types:
        if qtype in content:
            print(f"✅ Found '{qtype}' in content")
        else:
            print(f"❌ '{qtype}' not found in content")

if __name__ == '__main__':
    debug_survey_content()