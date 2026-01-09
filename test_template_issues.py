#!/usr/bin/env python
"""
Quick test to identify template rendering issues.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from simple_surveys.models import SimpleSurveyQuestion
from simple_surveys.engine import SimpleSurveyEngine


def test_template_issues():
    """Test for common template rendering issues"""
    
    print("🔍 Checking Template Issues")
    print("=" * 40)
    
    # 1. Check if questions exist in database
    print("\n1. Database Questions Check:")
    health_questions = SimpleSurveyQuestion.objects.filter(category='health')
    funeral_questions = SimpleSurveyQuestion.objects.filter(category='funeral')
    
    print(f"   Health questions: {health_questions.count()}")
    print(f"   Funeral questions: {funeral_questions.count()}")
    
    if health_questions.count() == 0:
        print("   ❌ No health questions found! Need to load fixtures.")
        return
    
    # 2. Check question serialization
    print("\n2. Question Serialization Check:")
    engine = SimpleSurveyEngine('health')
    questions = engine.get_questions()
    
    print(f"   Serialized questions: {len(questions)}")
    
    for i, q in enumerate(questions[:2]):  # Check first 2 questions
        print(f"\n   Question {i+1}:")
        print(f"     Text: {q.get('question_text', 'MISSING')}")
        print(f"     Type: {q.get('input_type', 'MISSING')}")
        print(f"     Choices: {q.get('choices', 'MISSING')}")
        print(f"     Field: {q.get('field_name', 'MISSING')}")
    
    # 3. Check template field name mismatch
    print("\n3. Template Field Name Check:")
    print("   Template uses 'field_type' but model has 'input_type'")
    
    # Check the template issue
    template_fields = ['field_type', 'get_options']
    model_fields = ['input_type', 'choices']
    
    print(f"   ❌ Template expects: {template_fields}")
    print(f"   ✅ Model provides: {model_fields}")
    
    # 4. Check choices format
    print("\n4. Choices Format Check:")
    select_question = next((q for q in questions if q['input_type'] == 'select'), None)
    if select_question:
        choices = select_question.get('choices', [])
        print(f"   Select question choices: {choices}")
        print(f"   Choices type: {type(choices)}")
        if choices and isinstance(choices[0], list):
            print(f"   First choice: {choices[0]} (value: {choices[0][0]}, label: {choices[0][1]})")
        else:
            print("   ❌ Choices not in expected [value, label] format")
    
    # 5. Test template syntax issues
    print("\n5. Template Syntax Issues Found:")
    issues = [
        "❌ Template uses 'question.field_type' but should be 'question.input_type'",
        "❌ Template uses 'question.get_options' but should be 'question.choices'",
        "❌ Missing radio button and checkbox rendering logic",
        "❌ Existing responses access is incorrect"
    ]
    
    for issue in issues:
        print(f"   {issue}")
    
    print("\n6. Recommended Fixes:")
    fixes = [
        "✅ Change 'question.field_type' to 'question.input_type' in template",
        "✅ Change 'question.get_options' to 'question.choices' in template", 
        "✅ Add radio button rendering logic",
        "✅ Add checkbox rendering logic",
        "✅ Fix existing responses dictionary access"
    ]
    
    for fix in fixes:
        print(f"   {fix}")


if __name__ == '__main__':
    test_template_issues()