#!/usr/bin/env python
"""
Verification script to confirm that all survey question updates for the 
policy features upgrade have been successfully implemented.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from simple_surveys.models import SimpleSurveyQuestion


def verify_new_questions():
    """Verify that all new questions have been added"""
    print("=== Verifying New Survey Questions ===")
    
    required_questions = [
        {
            'field_name': 'preferred_annual_limit_per_family',
            'question_text': 'What is your preferred annual limit per family?',
            'input_type': 'select',
            'category': 'health'
        },
        {
            'field_name': 'currently_on_medical_aid',
            'question_text': 'Are you currently on medical aid?',
            'input_type': 'radio',
            'category': 'health'
        },
        {
            'field_name': 'wants_ambulance_coverage',
            'question_text': 'Do you want ambulance coverage included?',
            'input_type': 'radio',
            'category': 'health'
        },
        {
            'field_name': 'household_income',
            'question_text': 'What is your monthly household income?',
            'input_type': 'select',
            'category': 'health'
        }
    ]
    
    all_passed = True
    
    for req_question in required_questions:
        try:
            question = SimpleSurveyQuestion.objects.get(
                field_name=req_question['field_name'],
                category=req_question['category']
            )
            
            # Verify question properties
            checks = [
                (question.input_type == req_question['input_type'], 'input_type'),
                (question.is_required == True, 'is_required'),
                (len(question.choices) > 0, 'has_choices'),
                (question.category == req_question['category'], 'category')
            ]
            
            passed_checks = all(check[0] for check in checks)
            
            if passed_checks:
                print(f"✓ {req_question['field_name']}: PASSED")
                print(f"  - Question: {question.question_text}")
                print(f"  - Type: {question.input_type}")
                print(f"  - Choices: {len(question.choices)} options")
                print(f"  - Display Order: {question.display_order}")
            else:
                print(f"✗ {req_question['field_name']}: FAILED")
                for check, name in checks:
                    if not check:
                        print(f"  - Failed check: {name}")
                all_passed = False
                
        except SimpleSurveyQuestion.DoesNotExist:
            print(f"✗ {req_question['field_name']}: NOT FOUND")
            all_passed = False
        
        print()
    
    return all_passed


def verify_question_ordering():
    """Verify that questions are properly ordered"""
    print("=== Verifying Question Ordering ===")
    
    health_questions = SimpleSurveyQuestion.objects.filter(
        category='health'
    ).order_by('display_order')
    
    print("Current health question order:")
    for i, question in enumerate(health_questions, 1):
        print(f"{question.display_order:2d}. {question.field_name}")
    
    # Check that new questions are in expected positions
    expected_positions = {
        'preferred_annual_limit_per_family': 7,
        'currently_on_medical_aid': 8,
        'wants_ambulance_coverage': 9,
        'household_income': 10
    }
    
    all_ordered_correctly = True
    
    for field_name, expected_order in expected_positions.items():
        try:
            question = SimpleSurveyQuestion.objects.get(
                field_name=field_name,
                category='health'
            )
            if question.display_order == expected_order:
                print(f"✓ {field_name} at position {expected_order}")
            else:
                print(f"✗ {field_name} at position {question.display_order}, expected {expected_order}")
                all_ordered_correctly = False
        except SimpleSurveyQuestion.DoesNotExist:
            print(f"✗ {field_name} not found")
            all_ordered_correctly = False
    
    return all_ordered_correctly


def verify_question_validation():
    """Verify that question validation works correctly"""
    print("\n=== Verifying Question Validation ===")
    
    test_cases = [
        {
            'field_name': 'preferred_annual_limit_per_family',
            'valid_responses': ['100000', '500000', 'unlimited'],
            'invalid_responses': ['invalid', '999999', '']
        },
        {
            'field_name': 'currently_on_medical_aid',
            'valid_responses': ['yes', 'no'],
            'invalid_responses': ['maybe', 'sometimes', '']
        },
        {
            'field_name': 'wants_ambulance_coverage',
            'valid_responses': ['yes', 'no'],
            'invalid_responses': ['maybe', 'sometimes', '']
        },
        {
            'field_name': 'household_income',
            'valid_responses': ['0-5000', '20001-35000', '50001+'],
            'invalid_responses': ['invalid-range', '999999', '']
        }
    ]
    
    all_validation_passed = True
    
    for test_case in test_cases:
        try:
            question = SimpleSurveyQuestion.objects.get(
                field_name=test_case['field_name'],
                category='health'
            )
            
            print(f"\nTesting {test_case['field_name']}:")
            
            # Test valid responses
            for valid_response in test_case['valid_responses']:
                errors = question.validate_response(valid_response)
                if len(errors) == 0:
                    print(f"  ✓ '{valid_response}' - valid")
                else:
                    print(f"  ✗ '{valid_response}' - should be valid but got errors: {errors}")
                    all_validation_passed = False
            
            # Test invalid responses
            for invalid_response in test_case['invalid_responses']:
                errors = question.validate_response(invalid_response)
                if len(errors) > 0:
                    print(f"  ✓ '{invalid_response}' - correctly rejected")
                else:
                    print(f"  ✗ '{invalid_response}' - should be invalid but was accepted")
                    all_validation_passed = False
                    
        except SimpleSurveyQuestion.DoesNotExist:
            print(f"✗ Question {test_case['field_name']} not found")
            all_validation_passed = False
    
    return all_validation_passed


def verify_deprecated_questions_removed():
    """Verify that deprecated questions have been removed"""
    print("\n=== Verifying Deprecated Questions Removed ===")
    
    deprecated_fields = [
        'net_monthly_income',
        'monthly_income',
        'income'
    ]
    
    all_removed = True
    
    for field_name in deprecated_fields:
        deprecated_questions = SimpleSurveyQuestion.objects.filter(
            field_name=field_name
        )
        
        if deprecated_questions.exists():
            print(f"✗ Deprecated question still exists: {field_name}")
            all_removed = False
        else:
            print(f"✓ Deprecated question removed: {field_name}")
    
    return all_removed


def main():
    """Run all verification checks"""
    print("Survey Questions Upgrade Verification")
    print("=" * 50)
    
    checks = [
        ("New Questions Added", verify_new_questions),
        ("Question Ordering", verify_question_ordering),
        ("Question Validation", verify_question_validation),
        ("Deprecated Questions Removed", verify_deprecated_questions_removed)
    ]
    
    results = []
    
    for check_name, check_function in checks:
        print(f"\n{check_name}")
        print("-" * len(check_name))
        result = check_function()
        results.append((check_name, result))
    
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for check_name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {check_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Survey questions upgrade is complete.")
        return 0
    else:
        print("❌ SOME CHECKS FAILED! Please review the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())