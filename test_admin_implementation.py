#!/usr/bin/env python
"""
Simple test to verify admin interface implementation
"""

# Test imports
try:
    from simple_surveys.models import (
        HOSPITAL_BENEFIT_CHOICES, OUT_HOSPITAL_BENEFIT_CHOICES,
        ANNUAL_LIMIT_FAMILY_RANGES, ANNUAL_LIMIT_MEMBER_RANGES
    )
    print("✅ Successfully imported choice constants")
    print(f"   - Hospital benefit choices: {len(HOSPITAL_BENEFIT_CHOICES)}")
    print(f"   - Out-hospital benefit choices: {len(OUT_HOSPITAL_BENEFIT_CHOICES)}")
    print(f"   - Family ranges: {len(ANNUAL_LIMIT_FAMILY_RANGES)}")
    print(f"   - Member ranges: {len(ANNUAL_LIMIT_MEMBER_RANGES)}")
except ImportError as e:
    print(f"❌ Failed to import choice constants: {e}")

# Test admin imports
try:
    from simple_surveys.admin import (
        SimpleSurveyAdmin, SimpleSurveyQuestionAdmin, SimpleSurveyResponseAdmin,
        BenefitLevelQuestionForm
    )
    print("✅ Successfully imported admin classes")
except ImportError as e:
    print(f"❌ Failed to import admin classes: {e}")

# Test admin views imports
try:
    from simple_surveys.admin_views import (
        BenefitLevelManagementView, AnnualLimitRangeManagementView
    )
    print("✅ Successfully imported admin views")
except ImportError as e:
    print(f"❌ Failed to import admin views: {e}")

print("\n🎯 Admin interface implementation verification complete!")