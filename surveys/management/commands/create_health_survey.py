from django.core.management.base import BaseCommand
from django.db import transaction
from policies.models import PolicyCategory
from surveys.models import SurveyTemplate, SurveyQuestion, TemplateQuestion, QuestionDependency


class Command(BaseCommand):
    """Management command to create comprehensive health insurance survey template and questions."""
    
    help = 'Create health insurance survey template with comprehensive questions and conditional logic'
    
    def handle(self, *args, **options):
        """Create health insurance survey template and questions."""
        with transaction.atomic():
            self.stdout.write('Creating health insurance survey template and questions...')
            
            # Get or create health insurance category
            health_category, created = PolicyCategory.objects.get_or_create(
                slug='health',
                defaults={
                    'name': 'Health Insurance',
                    'description': 'Health insurance policies for medical coverage',
                    'icon': 'health',
                    'display_order': 1,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created health category: {health_category.name}')
            else:
                self.stdout.write(f'Using existing health category: {health_category.name}')
            
            # Create health insurance survey template
            health_template, created = SurveyTemplate.objects.get_or_create(
                category=health_category,
                name='Health Insurance Needs Assessment',
                version='1.0',
                defaults={
                    'description': 'Comprehensive survey to assess health insurance needs and preferences',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created health survey template: {health_template.name}')
            else:
                self.stdout.write(f'Using existing health survey template: {health_template.name}')
            
            # Define comprehensive health insurance questions
            health_questions = self._get_health_questions()
            
            # Create questions and add to template
            created_questions = []
            for question_data in health_questions:
                question, created = SurveyQuestion.objects.get_or_create(
                    category=health_category,
                    field_name=question_data['field_name'],
                    defaults=question_data
                )
                
                if created:
                    self.stdout.write(f'Created question: {question.question_text[:50]}...')
                    created_questions.append(question)
                
                # Add to template if not already added
                template_question, created = TemplateQuestion.objects.get_or_create(
                    template=health_template,
                    question=question,
                    defaults={'display_order': question_data['display_order']}
                )
            
            # Create conditional question logic
            self._create_question_dependencies(health_category)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created health insurance survey with {len(health_questions)} questions!'
                )
            )
    
    def _get_health_questions(self):
        """Define comprehensive health insurance survey questions."""
        return [
            # Personal Information Section
            {
                'section': 'Personal Information',
                'question_text': 'What is your age?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'age',
                'validation_rules': {
                    'min': 18,
                    'max': 100,
                    'required': True,
                    'error_message': 'Age must be between 18 and 100'
                },
                'weight_impact': 2.5,
                'help_text': 'Your age is a key factor in determining premium rates and coverage options',
                'is_required': True,
                'display_order': 1
            },
            {
                'section': 'Personal Information',
                'question_text': 'What is your gender?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'gender',
                'choices': ['Male', 'Female', 'Other', 'Prefer not to say'],
                'validation_rules': {'required': True},
                'weight_impact': 1.2,
                'help_text': 'Gender may affect certain coverage options and premium calculations',
                'is_required': True,
                'display_order': 2
            },
            {
                'section': 'Personal Information',
                'question_text': 'In which province do you live?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'province',
                'choices': [
                    'Eastern Cape', 'Free State', 'Gauteng', 'KwaZulu-Natal',
                    'Limpopo', 'Mpumalanga', 'Northern Cape', 'North West', 'Western Cape'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 1.5,
                'help_text': 'Location affects available healthcare providers and premium rates',
                'is_required': True,
                'display_order': 3
            },
            {
                'section': 'Personal Information',
                'question_text': 'What is your employment status?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'employment_status',
                'choices': ['Employed full-time', 'Employed part-time', 'Self-employed', 'Unemployed', 'Retired', 'Student'],
                'validation_rules': {'required': True},
                'weight_impact': 1.8,
                'help_text': 'Employment status affects eligibility for certain plans and group discounts',
                'is_required': True,
                'display_order': 4
            },
            {
                'section': 'Personal Information',
                'question_text': 'How many dependents do you want to include in your coverage?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'dependents_count',
                'validation_rules': {
                    'min': 0,
                    'max': 10,
                    'required': True
                },
                'weight_impact': 2.0,
                'help_text': 'Number of dependents significantly affects premium costs',
                'is_required': True,
                'display_order': 5
            },
            
            # Health Status & History Section
            {
                'section': 'Health Status',
                'question_text': 'How would you rate your current overall health?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'health_rating',
                'choices': ['Excellent', 'Very Good', 'Good', 'Fair', 'Poor'],
                'validation_rules': {'required': True},
                'weight_impact': 2.5,
                'help_text': 'Your health status helps us recommend appropriate coverage levels',
                'is_required': True,
                'display_order': 6
            },
            {
                'section': 'Health Status',
                'question_text': 'Do you currently smoke tobacco products?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'smoker',
                'validation_rules': {'required': True},
                'weight_impact': 3.0,
                'help_text': 'Smoking status significantly affects premium rates',
                'is_required': True,
                'display_order': 7
            },
            {
                'section': 'Health Status',
                'question_text': 'Do you have any chronic medical conditions?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'has_chronic_conditions',
                'validation_rules': {'required': True},
                'weight_impact': 2.8,
                'help_text': 'Chronic conditions may require specialized coverage',
                'is_required': True,
                'display_order': 8
            },
            {
                'section': 'Health Status',
                'question_text': 'Which chronic conditions do you have? (Select all that apply)',
                'question_type': SurveyQuestion.QuestionType.MULTI_CHOICE,
                'field_name': 'chronic_conditions_list',
                'choices': [
                    'Diabetes', 'Hypertension', 'Heart Disease', 'Asthma', 'Arthritis',
                    'Cancer (in remission)', 'Kidney Disease', 'Mental Health Conditions',
                    'Other', 'Prefer not to say'
                ],
                'validation_rules': {'required': False},
                'weight_impact': 2.5,
                'help_text': 'This helps us find plans with appropriate coverage for your conditions',
                'is_required': False,
                'display_order': 9
            },
            {
                'section': 'Health Status',
                'question_text': 'Are you currently taking any prescription medications?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'takes_medications',
                'validation_rules': {'required': True},
                'weight_impact': 2.0,
                'help_text': 'Medication needs affect coverage requirements',
                'is_required': True,
                'display_order': 10
            },
            {
                'section': 'Health Status',
                'question_text': 'Have you had any surgeries or major medical procedures in the past 5 years?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'recent_procedures',
                'validation_rules': {'required': True},
                'weight_impact': 2.2,
                'help_text': 'Recent procedures may affect waiting periods and coverage',
                'is_required': True,
                'display_order': 11
            },
            {
                'section': 'Health Status',
                'question_text': 'Do you have a family history of serious medical conditions?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'family_history',
                'validation_rules': {'required': True},
                'weight_impact': 1.8,
                'help_text': 'Family history helps assess future health risks',
                'is_required': True,
                'display_order': 12
            },
            
            # Coverage Preferences Section
            {
                'section': 'Coverage Preferences',
                'question_text': 'What type of health coverage is most important to you?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'coverage_priority',
                'choices': [
                    'Hospital and surgical cover',
                    'Day-to-day medical expenses',
                    'Comprehensive (hospital + day-to-day)',
                    'Emergency cover only',
                    'Preventive care focus'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 3.0,
                'help_text': 'This determines which type of medical scheme options we prioritize',
                'is_required': True,
                'display_order': 13
            },
            {
                'section': 'Coverage Preferences',
                'question_text': 'Do you have preferred hospitals or healthcare providers?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'has_preferred_providers',
                'validation_rules': {'required': True},
                'weight_impact': 2.2,
                'help_text': 'Provider preferences affect network coverage requirements',
                'is_required': True,
                'display_order': 14
            },
            {
                'section': 'Coverage Preferences',
                'question_text': 'How important is dental coverage to you?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'dental_importance',
                'choices': ['Very important', 'Somewhat important', 'Not important', 'Already covered elsewhere'],
                'validation_rules': {'required': True},
                'weight_impact': 1.5,
                'help_text': 'Dental coverage varies significantly between plans',
                'is_required': True,
                'display_order': 15
            },
            {
                'section': 'Coverage Preferences',
                'question_text': 'How important is optical (eye care) coverage to you?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'optical_importance',
                'choices': ['Very important', 'Somewhat important', 'Not important', 'Already covered elsewhere'],
                'validation_rules': {'required': True},
                'weight_impact': 1.5,
                'help_text': 'Optical benefits vary between medical scheme options',
                'is_required': True,
                'display_order': 16
            },
            {
                'section': 'Coverage Preferences',
                'question_text': 'Are you interested in alternative medicine coverage (e.g., homeopathy, naturopathy)?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'alternative_medicine',
                'choices': ['Very interested', 'Somewhat interested', 'Not interested', 'Unsure'],
                'validation_rules': {'required': True},
                'weight_impact': 1.2,
                'help_text': 'Some plans offer coverage for alternative treatments',
                'is_required': True,
                'display_order': 17
            },
            {
                'section': 'Coverage Preferences',
                'question_text': 'How important is maternity coverage to you?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'maternity_importance',
                'choices': ['Very important', 'Somewhat important', 'Not applicable', 'Not needed'],
                'validation_rules': {'required': True},
                'weight_impact': 2.0,
                'help_text': 'Maternity benefits have specific waiting periods and coverage levels',
                'is_required': True,
                'display_order': 18
            },
            
            # Financial Considerations Section
            {
                'section': 'Financial',
                'question_text': 'What is your preferred monthly premium budget?',
                'question_type': SurveyQuestion.QuestionType.RANGE,
                'field_name': 'premium_budget',
                'validation_rules': {
                    'min': 500,
                    'max': 8000,
                    'step': 100,
                    'required': True
                },
                'weight_impact': 3.0,
                'help_text': 'Your budget helps us filter options within your price range',
                'is_required': True,
                'display_order': 19
            },
            {
                'section': 'Financial',
                'question_text': 'What annual deductible/threshold are you comfortable with?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'deductible_preference',
                'choices': [
                    'No deductible preferred',
                    'R5,000 - R10,000',
                    'R10,000 - R20,000',
                    'R20,000 - R50,000',
                    'Higher deductible for lower premiums'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 2.5,
                'help_text': 'Higher deductibles typically mean lower monthly premiums',
                'is_required': True,
                'display_order': 20
            },
            {
                'section': 'Financial',
                'question_text': 'How comfortable are you with co-payments for doctor visits?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'copayment_comfort',
                'choices': [
                    'Prefer no co-payments',
                    'Comfortable with small co-payments (R100-R300)',
                    'Comfortable with moderate co-payments (R300-R500)',
                    'Willing to pay higher co-payments for lower premiums'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 2.0,
                'help_text': 'Co-payment preferences affect plan selection',
                'is_required': True,
                'display_order': 21
            },
            {
                'section': 'Financial',
                'question_text': 'Do you have a medical savings account or want one included?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'savings_account_preference',
                'choices': [
                    'Yes, I want a medical savings account',
                    'No, I prefer comprehensive benefits',
                    'I already have one',
                    'I\'m not sure what this is'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 2.2,
                'help_text': 'Medical savings accounts affect how day-to-day expenses are covered',
                'is_required': True,
                'display_order': 22
            },
            {
                'section': 'Financial',
                'question_text': 'How important is it to have predictable monthly costs?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'cost_predictability',
                'choices': [
                    'Very important - I prefer fixed costs',
                    'Somewhat important',
                    'Not important - I can handle variable costs',
                    'I prefer lower premiums even with variable costs'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 1.8,
                'help_text': 'This affects whether we recommend comprehensive or hospital-only plans',
                'is_required': True,
                'display_order': 23
            }
        ]
    
    def _create_question_dependencies(self, health_category):
        """Create conditional question logic for health-specific scenarios."""
        self.stdout.write('Creating conditional question dependencies...')
        
        try:
            # Get questions for dependency creation
            has_chronic_conditions = SurveyQuestion.objects.get(
                category=health_category,
                field_name='has_chronic_conditions'
            )
            chronic_conditions_list = SurveyQuestion.objects.get(
                category=health_category,
                field_name='chronic_conditions_list'
            )
            
            # Show chronic conditions list only if user has chronic conditions
            dependency1, created = QuestionDependency.objects.get_or_create(
                parent_question=has_chronic_conditions,
                child_question=chronic_conditions_list,
                defaults={
                    'condition_value': True,
                    'condition_operator': QuestionDependency.ConditionOperator.EQUALS,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created dependency: chronic conditions list shows when user has chronic conditions')
            
        except SurveyQuestion.DoesNotExist as e:
            self.stdout.write(f'Warning: Could not create some dependencies - {e}')
        
        self.stdout.write('Completed conditional question dependencies')