# Admin Features Alignment Summary

## Overview
Updated the policies admin interface to align with comparison engine requirements and survey questions, ensuring all three systems work together seamlessly.

## Changes Made

### 1. PolicyFeaturesInline Updates

#### Health Policy Features
**Before:** 8 basic fields
**After:** 12 comprehensive fields including:
- `annual_limit_per_member` and `annual_limit_per_family` (legacy numeric fields)
- `annual_limit_family_range` and `annual_limit_member_range` (new range fields)
- `monthly_household_income`
- `currently_on_medical_aid`
- `ambulance_coverage`
- `in_hospital_benefit` and `in_hospital_benefit_level` (legacy boolean + new level field)
- `out_hospital_benefit` and `out_hospital_benefit_level` (legacy boolean + new level field)
- `chronic_medication_availability`

#### Funeral Policy Features
**Before:** 3 basic fields
**After:** 9 comprehensive fields including:
- `cover_amount` and `cover_amount_range` (numeric + range for flexible matching)
- `marital_status_requirement` and `gender_requirement`
- `funeral_service_type`
- `family_coverage_type`
- `max_family_members`
- `waiting_period_natural_death` and `waiting_period_accidental_death`

### 2. PolicyFeaturesAdmin Updates

#### Feature Summary Display
- Health: Now shows "💊 X/12 features" instead of "💊 X/8 features"
- Funeral: Now shows "⚱️ X/9 features" instead of "⚱️ X/3 features"

#### Validation Logic
- Updated to validate all new fields
- More flexible validation (requires at least some core features rather than all)
- Separate validation for health vs funeral features
- Numeric validation for positive values

#### Admin Actions
- `clear_irrelevant_features`: Updated to clear all new fields
- `duplicate_features_to_similar_policies`: Updated to copy all new fields

### 3. New Survey Question Fixtures

#### Complete Health Questions (`complete_health_questions.json`)
Added missing questions required by comparison engine:
- `coverage_priority` - What type of coverage is most important
- `monthly_budget` - Monthly budget for health insurance
- `preferred_deductible` - Deductible preference
- `preferred_annual_limit_per_family` - Specific annual limit preference
- `currently_on_medical_aid` - Current medical aid status

#### Complete Funeral Questions (`complete_funeral_questions.json`)
Added missing questions required by comparison engine:
- `preferred_cover_amount` - Specific cover amount preference
- `marital_status` - Marital status for eligibility
- `gender` - Gender for eligibility
- Updated `coverage_amount` to `coverage_amount_needed` for consistency

## Field Mapping Alignment

### Health Insurance
| Survey Field | Comparison Engine Field | Policy Feature Field |
|-------------|------------------------|---------------------|
| `age` | `age` | N/A |
| `location` | `location` | N/A |
| `family_size` | `family_size` | N/A |
| `health_status` | `health_status` | N/A |
| `chronic_conditions` | `chronic_conditions` | N/A |
| `coverage_priority` | `coverage_priority` | N/A |
| `monthly_budget` | `base_premium` | N/A |
| `preferred_deductible` | `deductible_amount` | N/A |
| `preferred_annual_limit_per_family` | `annual_limit_per_family` | `annual_limit_per_family` |
| `household_income` | `monthly_household_income` | `monthly_household_income` |
| `currently_on_medical_aid` | `currently_on_medical_aid` | `currently_on_medical_aid` |
| `wants_ambulance_coverage` | `ambulance_coverage` | `ambulance_coverage` |
| `in_hospital_benefit_level` | `in_hospital_benefit_level` | `in_hospital_benefit_level` |
| `out_hospital_benefit_level` | `out_hospital_benefit_level` | `out_hospital_benefit_level` |
| `annual_limit_family_range` | `annual_limit_family_range` | `annual_limit_family_range` |
| `annual_limit_member_range` | `annual_limit_member_range` | `annual_limit_member_range` |
| `needs_chronic_medication` | `chronic_medication_availability` | `chronic_medication_availability` |

### Funeral Insurance
| Survey Field | Comparison Engine Field | Policy Feature Field |
|-------------|------------------------|---------------------|
| `age` | `age` | N/A |
| `location` | `location` | N/A |
| `family_members_to_cover` | `family_size` | `max_family_members` |
| `coverage_amount_needed` | `coverage_amount` | `cover_amount` |
| `preferred_cover_amount` | `cover_amount` | `cover_amount` |
| `marital_status` | `marital_status_requirement` | `marital_status_requirement` |
| `gender` | `gender_requirement` | `gender_requirement` |
| `service_preference` | `service_level` | `funeral_service_type` |
| `monthly_budget` | `base_premium` | N/A |
| `waiting_period_tolerance` | `waiting_period_days` | `waiting_period_natural_death` |

## Benefits

1. **Complete Alignment**: All three systems (surveys, comparison engine, policy features) now use consistent field names and data structures.

2. **Enhanced Admin Interface**: Policy administrators can now configure all fields needed by the comparison engine directly in the admin interface.

3. **Better Validation**: More comprehensive validation ensures data quality and prevents mismatched configurations.

4. **Flexible Matching**: Both legacy fields and new range/level fields are supported for backward compatibility and enhanced matching.

5. **Complete Survey Coverage**: New survey fixtures include all questions needed for full comparison engine functionality.

## Next Steps

1. Load the new survey question fixtures into the database
2. Update existing policies to use the new field structure
3. Test the complete flow from survey → comparison → policy matching
4. Update comparison adapter field mappings if needed
5. Verify all admin actions work correctly with the new field structure

## Files Modified

- `policies/admin.py` - Updated PolicyFeaturesInline and PolicyFeaturesAdmin
- `simple_surveys/fixtures/complete_health_questions.json` - New complete health survey
- `simple_surveys/fixtures/complete_funeral_questions.json` - New complete funeral survey