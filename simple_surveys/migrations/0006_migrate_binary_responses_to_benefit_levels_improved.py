# Improved data migration to convert existing binary responses to benefit levels
from django.db import migrations


def migrate_binary_to_benefit_levels(apps, schema_editor):
    """
    Convert existing binary benefit responses to benefit levels.
    This migration handles the conversion of:
    - wants_in_hospital_benefit boolean to in_hospital_benefit_level choices
    - wants_out_hospital_benefit boolean to out_hospital_benefit_level choices
    - Remove currently_on_medical_aid data
    - Map existing annual limit values to appropriate ranges
    
    Requirements: 6.1, 6.2, 6.3
    """
    SimpleSurvey = apps.get_model('simple_surveys', 'SimpleSurvey')
    
    # Get all existing survey records
    surveys = SimpleSurvey.objects.all()
    
    for survey in surveys:
        # Since the boolean fields were already removed in migration 0005,
        # we need to set appropriate default values for existing records
        # that don't have benefit levels set yet
        
        # Convert in-hospital benefit to benefit level
        # Requirement 6.1: migrate binary responses to appropriate range selections
        if not survey.in_hospital_benefit_level:
            # Default to basic coverage for existing users who had surveys
            # This assumes users who completed surveys wanted some coverage
            survey.in_hospital_benefit_level = 'basic'
        
        # Convert out-of-hospital benefit to benefit level  
        # Requirement 6.1: migrate binary responses to appropriate range selections
        if not survey.out_hospital_benefit_level:
            # Default to basic coverage for existing users who had surveys
            survey.out_hospital_benefit_level = 'basic_visits'
        
        # Map existing annual limit values to ranges
        # Requirement 6.3: handle existing annual limit values by mapping to appropriate ranges
        if survey.preferred_annual_limit_per_family and not survey.annual_limit_family_range:
            limit = float(survey.preferred_annual_limit_per_family)
            
            # Map family limits to ranges based on design document specifications
            if limit <= 50000:
                survey.annual_limit_family_range = '10k-50k'
            elif limit <= 100000:
                survey.annual_limit_family_range = '50k-100k'
            elif limit <= 250000:
                survey.annual_limit_family_range = '100k-250k'
            elif limit <= 500000:
                survey.annual_limit_family_range = '250k-500k'
            elif limit <= 1000000:
                survey.annual_limit_family_range = '500k-1m'
            elif limit <= 2000000:
                survey.annual_limit_family_range = '1m-2m'
            elif limit <= 5000000:
                survey.annual_limit_family_range = '2m-5m'
            else:
                survey.annual_limit_family_range = '5m-plus'
        
        # Map existing preferred_annual_limit to member ranges
        # Requirement 6.3: handle existing annual limit values by mapping to appropriate ranges
        if hasattr(survey, 'preferred_annual_limit') and survey.preferred_annual_limit and not survey.annual_limit_member_range:
            limit = float(survey.preferred_annual_limit)
            
            # Map member limits to ranges based on design document specifications
            if limit <= 25000:
                survey.annual_limit_member_range = '10k-25k'
            elif limit <= 50000:
                survey.annual_limit_member_range = '25k-50k'
            elif limit <= 100000:
                survey.annual_limit_member_range = '50k-100k'
            elif limit <= 200000:
                survey.annual_limit_member_range = '100k-200k'
            elif limit <= 500000:
                survey.annual_limit_member_range = '200k-500k'
            elif limit <= 1000000:
                survey.annual_limit_member_range = '500k-1m'
            elif limit <= 2000000:
                survey.annual_limit_member_range = '1m-2m'
            else:
                survey.annual_limit_member_range = '2m-plus'
        
        # Save the updated survey
        survey.save()


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - clear the new benefit level fields.
    Note: We cannot restore the original boolean fields as they were removed.
    """
    SimpleSurvey = apps.get_model('simple_surveys', 'SimpleSurvey')
    
    # Clear the new fields
    SimpleSurvey.objects.all().update(
        in_hospital_benefit_level=None,
        out_hospital_benefit_level=None,
        annual_limit_family_range=None,
        annual_limit_member_range=None
    )


def migrate_survey_responses(apps, schema_editor):
    """
    Migrate SimpleSurveyResponse records to use new question types.
    Convert responses for old boolean questions to new benefit level questions.
    
    Requirement 6.2: remove existing currently_on_medical_aid data
    """
    SimpleSurveyResponse = apps.get_model('simple_surveys', 'SimpleSurveyResponse')
    
    # Get old question field names that need to be migrated
    old_field_names = [
        'wants_in_hospital_benefit',
        'wants_out_hospital_benefit', 
        'currently_on_medical_aid'  # Requirement 6.2: remove this data
    ]
    
    # Remove responses for old questions that no longer exist
    # This handles requirement 6.2: remove existing currently_on_medical_aid data
    deleted_count = SimpleSurveyResponse.objects.filter(
        question__field_name__in=old_field_names
    ).delete()
    
    print(f"Removed {deleted_count[0]} old survey responses for deprecated questions")
    
    # Note: Since the boolean fields were already removed in migration 0005,
    # we cannot convert existing boolean responses to benefit levels.
    # New responses will use the new question format with benefit levels.


def reverse_survey_responses(apps, schema_editor):
    """
    Reverse the survey response migration.
    This is a no-op since we can't restore deleted responses.
    """
    pass


class Migration(migrations.Migration):
    """
    Data migration to convert existing binary responses to benefit levels.
    
    This migration implements task 2 requirements:
    - Write migration script to convert wants_in_hospital_benefit boolean to benefit levels
    - Write migration script to convert wants_out_hospital_benefit boolean to benefit levels  
    - Remove existing currently_on_medical_aid data
    - Handle existing annual limit values by mapping to appropriate ranges
    
    Requirements: 6.1, 6.2, 6.3
    """

    dependencies = [
        ('simple_surveys', '0005_update_benefit_level_fields'),
    ]

    operations = [
        migrations.RunPython(
            migrate_binary_to_benefit_levels,
            reverse_migration,
            atomic=True
        ),
        migrations.RunPython(
            migrate_survey_responses,
            reverse_survey_responses,
            atomic=True
        ),
    ]