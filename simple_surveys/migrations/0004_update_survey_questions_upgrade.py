# Generated migration for policy features upgrade
from django.db import migrations


def add_new_survey_questions(apps, schema_editor):
    """Add new survey questions for policy features upgrade"""
    SimpleSurveyQuestion = apps.get_model('simple_surveys', 'SimpleSurveyQuestion')
    
    # New questions to add
    new_questions = [
        {
            'category': 'health',
            'question_text': 'What is your preferred annual limit per family?',
            'field_name': 'preferred_annual_limit_per_family',
            'input_type': 'select',
            'choices': [
                ['100000', 'R100,000'],
                ['250000', 'R250,000'],
                ['500000', 'R500,000'],
                ['1000000', 'R1,000,000'],
                ['2000000', 'R2,000,000'],
                ['unlimited', 'Unlimited']
            ],
            'is_required': True,
            'display_order': 7,
            'validation_rules': {}
        },
        {
            'category': 'health',
            'question_text': 'Are you currently on medical aid?',
            'field_name': 'currently_on_medical_aid',
            'input_type': 'radio',
            'choices': [
                ['yes', 'Yes'],
                ['no', 'No']
            ],
            'is_required': True,
            'display_order': 8,
            'validation_rules': {}
        },
        {
            'category': 'health',
            'question_text': 'Do you want ambulance coverage included?',
            'field_name': 'wants_ambulance_coverage',
            'input_type': 'radio',
            'choices': [
                ['yes', 'Yes, include ambulance coverage'],
                ['no', 'No, I don\'t need ambulance coverage']
            ],
            'is_required': True,
            'display_order': 9,
            'validation_rules': {}
        },
        {
            'category': 'health',
            'question_text': 'What is your monthly household income?',
            'field_name': 'household_income',
            'input_type': 'select',
            'choices': [
                ['0-5000', 'R0 - R5,000'],
                ['5001-10000', 'R5,001 - R10,000'],
                ['10001-20000', 'R10,001 - R20,000'],
                ['20001-35000', 'R20,001 - R35,000'],
                ['35001-50000', 'R35,001 - R50,000'],
                ['50001+', 'R50,001+']
            ],
            'is_required': True,
            'display_order': 10,
            'validation_rules': {}
        }
    ]
    
    # Create new questions
    for question_data in new_questions:
        SimpleSurveyQuestion.objects.get_or_create(
            category=question_data['category'],
            field_name=question_data['field_name'],
            defaults=question_data
        )
    
    # Update display order for existing questions
    updates = [
        {'field_name': 'monthly_budget', 'new_order': 11},
        {'field_name': 'preferred_deductible', 'new_order': 12},
    ]
    
    for update in updates:
        SimpleSurveyQuestion.objects.filter(
            category='health',
            field_name=update['field_name']
        ).update(display_order=update['new_order'])


def remove_new_survey_questions(apps, schema_editor):
    """Remove the new survey questions (reverse migration)"""
    SimpleSurveyQuestion = apps.get_model('simple_surveys', 'SimpleSurveyQuestion')
    
    # Remove the new questions
    new_field_names = [
        'preferred_annual_limit_per_family',
        'currently_on_medical_aid',
        'wants_ambulance_coverage',
        'household_income'
    ]
    
    SimpleSurveyQuestion.objects.filter(
        category='health',
        field_name__in=new_field_names
    ).delete()
    
    # Restore original display order
    original_orders = [
        {'field_name': 'monthly_budget', 'original_order': 7},
        {'field_name': 'preferred_deductible', 'original_order': 8},
    ]
    
    for restore in original_orders:
        SimpleSurveyQuestion.objects.filter(
            category='health',
            field_name=restore['field_name']
        ).update(display_order=restore['original_order'])


class Migration(migrations.Migration):

    dependencies = [
        ('simple_surveys', '0003_add_new_preference_fields'),
    ]

    operations = [
        migrations.RunPython(
            add_new_survey_questions,
            remove_new_survey_questions,
            atomic=True
        ),
    ]