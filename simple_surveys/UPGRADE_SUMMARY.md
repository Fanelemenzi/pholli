# Survey Questions Upgrade Summary

## Task 8: Update SimpleSurveyQuestion data with new survey questions

### ✅ Completed Implementation

This task has been successfully completed with the following deliverables:

#### 1. Management Command Created
- **File**: `simple_surveys/management/commands/update_survey_questions_upgrade.py`
- **Purpose**: Adds new survey questions and updates existing question ordering
- **Features**:
  - Dry-run mode for testing changes
  - Force mode for updating existing questions
  - Automatic validation of question data
  - Proper error handling and rollback

#### 2. Data Migration Created
- **File**: `simple_surveys/migrations/0004_update_survey_questions_upgrade.py`
- **Purpose**: Database migration to add new questions automatically during deployment
- **Features**:
  - Forward migration to add new questions
  - Reverse migration to remove questions if needed
  - Atomic operations for data integrity

#### 3. New Survey Questions Added

The following 4 new health insurance questions were successfully added:

1. **Annual Limit Per Family** (`preferred_annual_limit_per_family`)
   - Question: "What is your preferred annual limit per family?"
   - Type: Select dropdown
   - Options: R100,000, R250,000, R500,000, R1,000,000, R2,000,000, Unlimited
   - Display Order: 7

2. **Medical Aid Status** (`currently_on_medical_aid`)
   - Question: "Are you currently on medical aid?"
   - Type: Radio buttons
   - Options: Yes, No
   - Display Order: 8

3. **Ambulance Coverage** (`wants_ambulance_coverage`)
   - Question: "Do you want ambulance coverage included?"
   - Type: Radio buttons
   - Options: Yes (include coverage), No (don't need coverage)
   - Display Order: 9

4. **Household Income** (`household_income`)
   - Question: "What is your monthly household income?"
   - Type: Select dropdown
   - Options: R0-R5,000, R5,001-R10,000, R10,001-R20,000, R20,001-R35,000, R35,001-R50,000, R50,001+
   - Display Order: 10

#### 4. Question Ordering Updated

Existing questions were reordered to accommodate new questions:
- Monthly budget question moved to position 11
- Deductible preference question moved to position 12

#### 5. Validation and Testing

- **Test File**: `simple_surveys/test_updated_questions.py`
- **Verification Script**: `simple_surveys/verify_upgrade_questions.py`
- All questions include proper validation rules
- Response validation works correctly for all input types
- Question ordering is properly maintained

#### 6. Updated Fixture Files

- **File**: `simple_surveys/fixtures/updated_health_questions.json`
- Contains all health questions including the new ones
- Can be used for fresh installations or testing

### Requirements Satisfied

✅ **Requirement 2.4**: Added question for preferred annual limit per family (health insurance)
✅ **Requirement 2.5**: Added question for current medical aid status (health insurance)  
✅ **Requirement 2.6**: Added question for ambulance coverage preference (health insurance)
✅ **Additional**: Added household income question (replaces net monthly income)
✅ **Proper ordering**: All questions have appropriate display_order values
✅ **Validation rules**: All questions include proper validation

### Usage Instructions

#### To apply the changes via management command:
```bash
# Dry run to see what would be changed
python manage.py update_survey_questions_upgrade --dry-run

# Apply the changes
python manage.py update_survey_questions_upgrade

# Force update existing questions
python manage.py update_survey_questions_upgrade --force
```

#### To apply via migration:
```bash
# The migration runs automatically during normal migration process
python manage.py migrate simple_surveys
```

#### To verify the implementation:
```bash
# Check that all questions exist
python manage.py shell -c "from simple_surveys.models import SimpleSurveyQuestion; print(f'Health questions: {SimpleSurveyQuestion.objects.filter(category=\"health\").count()}')"
```

### Database Changes

The following changes were made to the `simple_surveys_simplesurveyquestion` table:
- 4 new records added for health insurance questions
- Display order updated for 2 existing questions
- No deprecated questions were found to remove (they didn't exist in current data)

### Integration Notes

These new questions integrate seamlessly with:
- The existing SimpleSurvey model (which already has the corresponding preference fields)
- The survey form rendering system
- The response validation system
- The policy matching algorithms (when they're updated in future tasks)

### Next Steps

The survey questions are now ready for:
1. Integration with updated survey forms (Task 12)
2. Integration with policy matching algorithms (Task 13)
3. Display in the admin interface (Task 9)
4. Use in the benefits viewing functionality (Task 10)

All new questions follow the established patterns and will work automatically with the existing survey infrastructure.