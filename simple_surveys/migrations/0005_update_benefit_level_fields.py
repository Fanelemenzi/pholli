# Generated migration for benefit level fields update
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simple_surveys', '0004_update_survey_questions_upgrade'),
    ]

    operations = [
        # Add new benefit level choice fields
        migrations.AddField(
            model_name='simplesurvey',
            name='in_hospital_benefit_level',
            field=models.CharField(
                blank=True,
                choices=[
                    ('no_cover', 'No hospital cover'),
                    ('basic', 'Basic hospital care'),
                    ('moderate', 'Moderate hospital care'),
                    ('extensive', 'Extensive hospital care'),
                    ('comprehensive', 'Comprehensive hospital care'),
                ],
                help_text='Level of in-hospital coverage needed',
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='simplesurvey',
            name='out_hospital_benefit_level',
            field=models.CharField(
                blank=True,
                choices=[
                    ('no_cover', 'No out-of-hospital cover'),
                    ('basic_visits', 'Basic clinic visits'),
                    ('routine_care', 'Routine medical care'),
                    ('extended_care', 'Extended medical care'),
                    ('comprehensive_care', 'Comprehensive day-to-day care'),
                ],
                help_text='Level of out-of-hospital coverage needed',
                max_length=50,
                null=True,
            ),
        ),
        # Add new annual limit range fields
        migrations.AddField(
            model_name='simplesurvey',
            name='annual_limit_family_range',
            field=models.CharField(
                blank=True,
                choices=[
                    ('10k-50k', 'R10,000 - R50,000'),
                    ('50k-100k', 'R50,001 - R100,000'),
                    ('100k-250k', 'R100,001 - R250,000'),
                    ('250k-500k', 'R250,001 - R500,000'),
                    ('500k-1m', 'R500,001 - R1,000,000'),
                    ('1m-2m', 'R1,000,001 - R2,000,000'),
                    ('2m-5m', 'R2,000,001 - R5,000,000'),
                    ('5m-plus', 'R5,000,001+'),
                    ('not_sure', 'Not sure / Need guidance'),
                ],
                help_text='Preferred annual limit range per family',
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='simplesurvey',
            name='annual_limit_member_range',
            field=models.CharField(
                blank=True,
                choices=[
                    ('10k-25k', 'R10,000 - R25,000'),
                    ('25k-50k', 'R25,001 - R50,000'),
                    ('50k-100k', 'R50,001 - R100,000'),
                    ('100k-200k', 'R100,001 - R200,000'),
                    ('200k-500k', 'R200,001 - R500,000'),
                    ('500k-1m', 'R500,001 - R1,000,000'),
                    ('1m-2m', 'R1,000,001 - R2,000,000'),
                    ('2m-plus', 'R2,000,001+'),
                    ('not_sure', 'Not sure / Need guidance'),
                ],
                help_text='Preferred annual limit range per member',
                max_length=50,
                null=True,
            ),
        ),
        # Remove the currently_on_medical_aid field
        migrations.RemoveField(
            model_name='simplesurvey',
            name='currently_on_medical_aid',
        ),
        # Remove the old boolean benefit fields
        migrations.RemoveField(
            model_name='simplesurvey',
            name='wants_in_hospital_benefit',
        ),
        migrations.RemoveField(
            model_name='simplesurvey',
            name='wants_out_hospital_benefit',
        ),
    ]