#!/usr/bin/env python
"""
Script to check survey data and identify redirect loop issues.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from policies.models import PolicyCategory
from surveys.models import SurveyQuestion, SurveyTemplate
from comparison.models import ComparisonSession

def check_survey_data():
    """Check survey data to identify issues."""
    print("🔍 Checking survey data...")
    
    # Check categories
    print("\n📋 Policy Categories:")
    categories = PolicyCategory.objects.all()
    for cat in categories:
        print(f"  - {cat.name} (slug: {cat.slug}, active: {cat.is_active})")
    
    # Check survey templates
    print("\n📝 Survey Templates:")
    templates = SurveyTemplate.objects.all()
    if templates:
        for template in templates:
            print(f"  - {template.name} (category: {template.category.slug})")
    else:
        print("  ❌ No survey templates found!")
    
    # Check survey questions
    print("\n❓ Survey Questions:")
    for cat in categories:
        questions = SurveyQuestion.objects.filter(category=cat)
        print(f"  {cat.name}: {questions.count()} questions")
        if questions.count() == 0:
            print(f"    ❌ No questions found for {cat.name}!")
    
    # Check recent sessions
    print("\n🔄 Recent Sessions:")
    recent_sessions = ComparisonSession.objects.order_by('-created_at')[:5]
    for session in recent_sessions:
        print(f"  - {session.session_key} ({session.category.slug}, status: {session.status})")
    
    # Check for redirect loop causes
    print("\n🔍 Potential Issues:")
    
    # Issue 1: No survey questions
    for cat in categories:
        if SurveyQuestion.objects.filter(category=cat).count() == 0:
            print(f"  ❌ Category '{cat.slug}' has no survey questions - this will cause redirect loops!")
    
    # Issue 2: No survey templates
    if SurveyTemplate.objects.count() == 0:
        print("  ❌ No survey templates found - surveys cannot be initialized!")
    
    print("\n✅ Survey data check complete!")

if __name__ == '__main__':
    check_survey_data()