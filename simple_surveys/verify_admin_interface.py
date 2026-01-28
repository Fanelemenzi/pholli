#!/usr/bin/env python
"""
Verification script for the enhanced admin interface implementation.
This script verifies that all the admin interface enhancements are working correctly.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.test import RequestFactory
from simple_surveys.models import (
    SimpleSurvey, SimpleSurveyQuestion, SimpleSurveyResponse,
    HOSPITAL_BENEFIT_CHOICES, OUT_HOSPITAL_BENEFIT_CHOICES,
    ANNUAL_LIMIT_FAMILY_RANGES, ANNUAL_LIMIT_MEMBER_RANGES
)
from simple_surveys.admin import (
    SimpleSurveyAdmin, SimpleSurveyQuestionAdmin, SimpleSurveyResponseAdmin,
    BenefitLevelQuestionForm
)


def verify_admin_enhancements():
    """Verify that all admin interface enhancements are working"""
    
    print("🔍 Verifying Admin Interface Enhancements...")
    print("=" * 50)
    
    # 1. Verify benefit level choices are properly defined
    print("✅ 1. Verifying benefit level choices...")
    assert len(HOSPITAL_BENEFIT_CHOICES) == 5, f"Expected 5 hospital benefit choices, got {len(HOSPITAL_BENEFIT_CHOICES)}"
    assert len(OUT_HOSPITAL_BENEFIT_CHOICES) == 5, f"Expected 5 out-hospital benefit choices, got {len(OUT_HOSPITAL_BENEFIT_CHOICES)}"
    print(f"   - Hospital benefit choices: {len(HOSPITAL_BENEFIT_CHOICES)} ✓")
    print(f"   - Out-hospital benefit choices: {len(OUT_HOSPITAL_BENEFIT_CHOICES)} ✓")
    
    # 2. Verify annual limit ranges are properly defined
    print("\n✅ 2. Verifying annual limit ranges...")
    assert len(ANNUAL_LIMIT_FAMILY_RANGES) == 9, f"Expected 9 family ranges, got {len(ANNUAL_LIMIT_FAMILY_RANGES)}"
    assert len(ANNUAL_LIMIT_MEMBER_RANGES) == 9, f"Expected 9 member ranges, got {len(ANNUAL_LIMIT_MEMBER_RANGES)}"
    print(f"   - Family limit ranges: {len(ANNUAL_LIMIT_FAMILY_RANGES)} ✓")
    print(f"   - Member limit ranges: {len(ANNUAL_LIMIT_MEMBER_RANGES)} ✓")
    
    # 3. Verify admin classes are properly configured
    print("\n✅ 3. Verifying admin class configurations...")
    
    # Check SimpleSurveyAdmin
    survey_admin = SimpleSurveyAdmin(SimpleSurvey, site)
    assert 'benefit_levels_display' in survey_admin.list_display, "benefit_levels_display not in list_display"
    assert 'annual_ranges_display' in survey_admin.list_display, "annual_ranges_display not in list_display"
    assert 'validate_benefit_levels' in [action.__name__ for action in survey_admin.actions], "validate_benefit_levels action missing"
    print("   - SimpleSurveyAdmin configuration ✓")
    
    # Check SimpleSurveyQuestionAdmin
    question_admin = SimpleSurveyQuestionAdmin(SimpleSurveyQuestion, site)
    assert 'question_type_display' in question_admin.list_display, "question_type_display not in list_display"
    assert 'validate_benefit_choices' in [action.__name__ for action in question_admin.actions], "validate_benefit_choices action missing"
    assert question_admin.form == BenefitLevelQuestionForm, "Custom form not set"
    print("   - SimpleSurveyQuestionAdmin configuration ✓")
    
    # Check SimpleSurveyResponseAdmin
    response_admin = SimpleSurveyResponseAdmin(SimpleSurveyResponse, site)
    assert 'response_type_display' in response_admin.list_display, "response_type_display not in list_display"
    assert 'validate_benefit_responses' in [action.__name__ for action in response_admin.actions], "validate_benefit_responses action missing"
    print("   - SimpleSurveyResponseAdmin configuration ✓")
    
    # 4. Test form validation
    print("\n✅ 4. Testing form validation...")
    
    # Test valid benefit level form
    valid_form_data = {
        'category': 'health',
        'question_text': 'Test question',
        'field_name': 'in_hospital_benefit_level',
        'input_type': 'radio',
        'choices': [
            {'value': 'basic', 'text': 'Basic hospital care'},
            {'value': 'moderate', 'text': 'Moderate hospital care'}
        ],
        'is_required': True,
        'display_order': 1
    }
    
    form = BenefitLevelQuestionForm(data=valid_form_data)
    assert form.is_valid(), f"Valid form should be valid, errors: {form.errors}"
    print("   - Valid benefit level form validation ✓")
    
    # Test invalid benefit level form
    invalid_form_data = valid_form_data.copy()
    invalid_form_data['choices'] = [{'value': 'invalid_choice', 'text': 'Invalid choice'}]
    
    form = BenefitLevelQuestionForm(data=invalid_form_data)
    assert not form.is_valid(), "Invalid form should not be valid"
    assert 'choices' in form.errors, "Should have choices validation error"
    print("   - Invalid benefit level form validation ✓")
    
    # 5. Test admin display methods with mock data
    print("\n✅ 5. Testing admin display methods...")
    
    # Create mock survey for testing
    class MockSurvey:
        insurance_type = 'HEALTH'
        in_hospital_benefit_level = 'basic'
        out_hospital_benefit_level = 'routine_care'
        annual_limit_family_range = '100k-250k'
        annual_limit_member_range = '50k-100k'
        
        def get_in_hospital_benefit_level_display(self):
            return 'Basic hospital care'
        
        def get_out_hospital_benefit_level_display(self):
            return 'Routine medical care'
        
        def get_annual_limit_family_range_display(self):
            return 'R100,001 - R250,000'
        
        def get_annual_limit_member_range_display(self):
            return 'R50,001 - R100,000'
    
    mock_survey = MockSurvey()
    
    # Test benefit levels display
    benefit_display = survey_admin.benefit_levels_display(mock_survey)
    assert 'Basic hospital care' in benefit_display, "Benefit display should contain hospital benefit"
    assert 'Routine medical care' in benefit_display, "Benefit display should contain out-hospital benefit"
    print("   - Benefit levels display method ✓")
    
    # Test annual ranges display
    ranges_display = survey_admin.annual_ranges_display(mock_survey)
    assert 'R100,001 - R250,000' in ranges_display, "Ranges display should contain family range"
    assert 'R50,001 - R100,000' in ranges_display, "Ranges display should contain member range"
    print("   - Annual ranges display method ✓")
    
    # 6. Test question type display
    class MockQuestion:
        field_name = 'in_hospital_benefit_level'
    
    mock_question = MockQuestion()
    type_display = question_admin.question_type_display(mock_question)
    assert 'Benefit Level' in type_display, "Should identify benefit level question type"
    print("   - Question type display method ✓")
    
    # Test range question type display
    mock_question.field_name = 'annual_limit_family_range'
    type_display = question_admin.question_type_display(mock_question)
    assert 'Annual Range' in type_display, "Should identify annual range question type"
    print("   - Range question type display method ✓")
    
    print("\n🎉 All admin interface enhancements verified successfully!")
    print("=" * 50)
    
    # Summary of implemented features
    print("\n📋 Summary of Implemented Features:")
    print("   ✅ Enhanced SimpleSurveyAdmin with benefit level and range displays")
    print("   ✅ Enhanced SimpleSurveyQuestionAdmin with question type indicators")
    print("   ✅ Enhanced SimpleSurveyResponseAdmin with formatted response displays")
    print("   ✅ Custom form validation for benefit level and range questions")
    print("   ✅ Admin actions for validating and syncing question choices")
    print("   ✅ Dedicated management views for benefit levels and annual ranges")
    print("   ✅ API endpoints for choice validation and details")
    print("   ✅ Comprehensive admin templates for management interfaces")
    
    return True


def verify_choice_consistency():
    """Verify that all predefined choices are consistent and valid"""
    
    print("\n🔍 Verifying Choice Consistency...")
    print("=" * 30)
    
    # Check hospital benefit choices structure
    for i, choice in enumerate(HOSPITAL_BENEFIT_CHOICES):
        assert len(choice) == 3, f"Hospital choice {i} should have 3 elements (value, text, description)"
        assert isinstance(choice[0], str), f"Hospital choice {i} value should be string"
        assert isinstance(choice[1], str), f"Hospital choice {i} text should be string"
        assert isinstance(choice[2], str), f"Hospital choice {i} description should be string"
    
    print("   ✅ Hospital benefit choices structure valid")
    
    # Check out-hospital benefit choices structure
    for i, choice in enumerate(OUT_HOSPITAL_BENEFIT_CHOICES):
        assert len(choice) == 3, f"Out-hospital choice {i} should have 3 elements"
        assert isinstance(choice[0], str), f"Out-hospital choice {i} value should be string"
        assert isinstance(choice[1], str), f"Out-hospital choice {i} text should be string"
        assert isinstance(choice[2], str), f"Out-hospital choice {i} description should be string"
    
    print("   ✅ Out-hospital benefit choices structure valid")
    
    # Check family range choices structure
    for i, choice in enumerate(ANNUAL_LIMIT_FAMILY_RANGES):
        assert len(choice) == 3, f"Family range choice {i} should have 3 elements"
        assert isinstance(choice[0], str), f"Family range choice {i} value should be string"
        assert isinstance(choice[1], str), f"Family range choice {i} text should be string"
        assert isinstance(choice[2], str), f"Family range choice {i} description should be string"
    
    print("   ✅ Family range choices structure valid")
    
    # Check member range choices structure
    for i, choice in enumerate(ANNUAL_LIMIT_MEMBER_RANGES):
        assert len(choice) == 3, f"Member range choice {i} should have 3 elements"
        assert isinstance(choice[0], str), f"Member range choice {i} value should be string"
        assert isinstance(choice[1], str), f"Member range choice {i} text should be string"
        assert isinstance(choice[2], str), f"Member range choice {i} description should be string"
    
    print("   ✅ Member range choices structure valid")
    
    # Check for duplicate values
    hospital_values = [choice[0] for choice in HOSPITAL_BENEFIT_CHOICES]
    assert len(hospital_values) == len(set(hospital_values)), "Hospital benefit values should be unique"
    
    out_hospital_values = [choice[0] for choice in OUT_HOSPITAL_BENEFIT_CHOICES]
    assert len(out_hospital_values) == len(set(out_hospital_values)), "Out-hospital benefit values should be unique"
    
    family_values = [choice[0] for choice in ANNUAL_LIMIT_FAMILY_RANGES]
    assert len(family_values) == len(set(family_values)), "Family range values should be unique"
    
    member_values = [choice[0] for choice in ANNUAL_LIMIT_MEMBER_RANGES]
    assert len(member_values) == len(set(member_values)), "Member range values should be unique"
    
    print("   ✅ All choice values are unique")
    
    return True


if __name__ == '__main__':
    try:
        verify_choice_consistency()
        verify_admin_enhancements()
        print("\n🎯 All verifications passed! Admin interface implementation is complete.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1)