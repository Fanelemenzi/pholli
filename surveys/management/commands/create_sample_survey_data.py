from django.core.management.base import BaseCommand
from django.db import transaction
from policies.models import PolicyCategory
from surveys.models import SurveyTemplate, SurveyQuestion, TemplateQuestion


class Command(BaseCommand):
    """Management command to create sample survey data for testing."""
    
    help = 'Create sample survey data for health and funeral insurance categories'
    
    def handle(self, *args, **options):
        """Create sample survey data."""
        with transaction.atomic():
            self.stdout.write('Creating sample survey data...')
            
            # Create or get policy categories
            health_category, created = PolicyCategory.objects.get_or_create(
                slug='health',
                defaults={
                    'name': 'Health Insurance',
                    'description': 'Health insurance policies',
                    'display_order': 1
                }
            )
            if created:
                self.stdout.write(f'Created health category: {health_category.name}')
            
            funeral_category, created = PolicyCategory.objects.get_or_create(
                slug='funeral',
                defaults={
                    'name': 'Funeral Insurance',
                    'description': 'Funeral insurance policies',
                    'display_order': 2
                }
            )
            if created:
                self.stdout.write(f'Created funeral category: {funeral_category.name}')
            
            # Create health insurance survey template
            health_template, created = SurveyTemplate.objects.get_or_create(
                category=health_category,
                name='Health Insurance Survey',
                version='1.0',
                defaults={
                    'description': 'Comprehensive survey for health insurance needs assessment'
                }
            )
            if created:
                self.stdout.write(f'Created health survey template: {health_template.name}')
            
            # Create funeral insurance survey template
            funeral_template, created = SurveyTemplate.objects.get_or_create(
                category=funeral_category,
                name='Funeral Insurance Survey',
                version='1.0',
                defaults={
                    'description': 'Comprehensive survey for funeral insurance needs assessment'
                }
            )
            if created:
                self.stdout.write(f'Created funeral survey template: {funeral_template.name}')
            
            # Create health insurance questions
            health_questions = [
                {
                    'section': 'Personal Information',
                    'question_text': 'What is your age?',
                    'question_type': SurveyQuestion.QuestionType.NUMBER,
                    'field_name': 'age',
                    'validation_rules': {'min': 18, 'max': 100, 'required': True},
                    'weight_impact': 2.0,
                    'help_text': 'Your age affects premium calculations',
                    'is_required': True,
                    'display_order': 1
                },
                {
                    'section': 'Personal Information',
                    'question_text': 'What is your gender?',
                    'question_type': SurveyQuestion.QuestionType.CHOICE,
                    'field_name': 'gender',
                    'choices': ['Male', 'Female', 'Other'],
                    'weight_impact': 1.5,
                    'help_text': 'Gender may affect certain coverage options',
                    'is_required': True,
                    'display_order': 2
                },
                {
                    'section': 'Health Status',
                    'question_text': 'Do you currently smoke?',
                    'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                    'field_name': 'smoker',
                    'weight_impact': 3.0,
                    'help_text': 'Smoking status significantly affects premiums',
                    'is_required': True,
                    'display_order': 3
                },
                {
                    'section': 'Coverage Preferences',
                    'question_text': 'What is your preferred monthly premium range?',
                    'question_type': SurveyQuestion.QuestionType.RANGE,
                    'field_name': 'premium_range',
                    'validation_rules': {'min': 100, 'max': 2000, 'step': 50},
                    'weight_impact': 2.5,
                    'help_text': 'Select your comfortable monthly premium range',
                    'is_required': True,
                    'display_order': 4
                }
            ]
            
            # Create funeral insurance questions
            funeral_questions = [
                {
                    'section': 'Family Information',
                    'question_text': 'How many family members do you want to cover?',
                    'question_type': SurveyQuestion.QuestionType.NUMBER,
                    'field_name': 'family_members',
                    'validation_rules': {'min': 1, 'max': 20, 'required': True},
                    'weight_impact': 2.0,
                    'help_text': 'Number of family members affects coverage amount',
                    'is_required': True,
                    'display_order': 1
                },
                {
                    'section': 'Service Preferences',
                    'question_text': 'Do you prefer burial or cremation?',
                    'question_type': SurveyQuestion.QuestionType.CHOICE,
                    'field_name': 'service_type',
                    'choices': ['Burial', 'Cremation', 'Either'],
                    'weight_impact': 1.5,
                    'help_text': 'Service type affects coverage requirements',
                    'is_required': True,
                    'display_order': 2
                },
                {
                    'section': 'Coverage Requirements',
                    'question_text': 'What coverage amount do you need?',
                    'question_type': SurveyQuestion.QuestionType.CHOICE,
                    'field_name': 'coverage_amount',
                    'choices': ['R10,000 - R25,000', 'R25,000 - R50,000', 'R50,000 - R100,000', 'R100,000+'],
                    'weight_impact': 3.0,
                    'help_text': 'Choose the coverage amount that meets your needs',
                    'is_required': True,
                    'display_order': 3
                }
            ]
            
            # Create health questions
            for question_data in health_questions:
                question, created = SurveyQuestion.objects.get_or_create(
                    category=health_category,
                    field_name=question_data['field_name'],
                    defaults=question_data
                )
                if created:
                    self.stdout.write(f'Created health question: {question.question_text}')
                    
                    # Add to template
                    TemplateQuestion.objects.get_or_create(
                        template=health_template,
                        question=question,
                        defaults={'display_order': question_data['display_order']}
                    )
            
            # Create funeral questions
            for question_data in funeral_questions:
                question, created = SurveyQuestion.objects.get_or_create(
                    category=funeral_category,
                    field_name=question_data['field_name'],
                    defaults=question_data
                )
                if created:
                    self.stdout.write(f'Created funeral question: {question.question_text}')
                    
                    # Add to template
                    TemplateQuestion.objects.get_or_create(
                        template=funeral_template,
                        question=question,
                        defaults={'display_order': question_data['display_order']}
                    )
            
            self.stdout.write(
                self.style.SUCCESS('Successfully created sample survey data!')
            )