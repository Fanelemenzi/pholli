"""
Management command to create survey questions for health and funeral insurance categories.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from surveys.models import SurveyQuestion, QuestionDependency
from policies.models import PolicyCategory


class Command(BaseCommand):
    help = 'Create survey questions for health and funeral insurance categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            choices=['health', 'funeral', 'all'],
            default='all',
            help='Create questions for specific category or all categories'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing questions before creating new ones'
        )

    def handle(self, *args, **options):
        category = options['category']
        clear_existing = options['clear']

        with transaction.atomic():
            if clear_existing:
                self.stdout.write('Clearing existing survey questions...')
                SurveyQuestion.objects.all().delete()
                QuestionDependency.objects.all().delete()

            if category in ['health', 'all']:
                self.create_health_questions()
                
            if category in ['funeral', 'all']:
                self.create_funeral_questions()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created survey questions for {category}')
        )

    def create_health_questions(self):
        """Create comprehensive health insurance survey questions."""
        self.stdout.write('Creating health insurance survey questions...')
        
        try:
            health_category = PolicyCategory.objects.get(slug='health')
        except PolicyCategory.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Health category not found. Please create it first.')
            )
            return

        health_questions = [
            # Personal Information Section
            {
                'section': 'Personal Information',
                'question_text': 'What is your age?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'age',
                'validation_rules': {'min': 18, 'max': 80},
                'weight_impact': 1.5,
                'help_text': 'Your age affects premium calculations and policy eligibility.',
                'display_order': 1,
                'is_required': True
            },
            {
                'section': 'Personal Information',
                'question_text': 'Which region do you live in?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'location',
                'choices': [
                    {'value': 'hhohho', 'text': 'Hhohho'},
                    {'value': 'manzini', 'text': 'Manzini'},
                    {'value': 'shiselweni', 'text': 'Shiselweni'},
                    {'value': 'lubombo', 'text': 'Lubombo'}
                ],
                'weight_impact': 1.0,
                'help_text': 'Location affects policy availability and regional pricing.',
                'display_order': 2,
                'is_required': True
            },
            {
                'section': 'Personal Information',
                'question_text': 'How many family members need coverage (including yourself)?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'family_size',
                'validation_rules': {'min': 1, 'max': 10},
                'weight_impact': 2.0,
                'help_text': 'Family size determines premium scaling and coverage options.',
                'display_order': 3,
                'is_required': True
            },
            
            # Health Status Section
            {
                'section': 'Health Status',
                'question_text': 'How would you describe your current overall health?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'health_status',
                'choices': [
                    {'value': 'excellent', 'text': 'Excellent - No health issues, very active'},
                    {'value': 'good', 'text': 'Good - Minor issues, generally healthy'},
                    {'value': 'fair', 'text': 'Fair - Some health concerns, managing conditions'},
                    {'value': 'poor', 'text': 'Poor - Significant health issues requiring regular care'}
                ],
                'weight_impact': 2.5,
                'help_text': 'Your health status affects risk assessment and policy eligibility.',
                'display_order': 4,
                'is_required': True
            },
            {
                'section': 'Health Status',
                'question_text': 'Do you have any of the following chronic conditions? (Select all that apply)',
                'question_type': SurveyQuestion.QuestionType.MULTI_CHOICE,
                'field_name': 'chronic_conditions',
                'choices': [
                    {'value': 'diabetes', 'text': 'Diabetes (Type 1 or 2)'},
                    {'value': 'hypertension', 'text': 'High Blood Pressure'},
                    {'value': 'heart_disease', 'text': 'Heart Disease'},
                    {'value': 'asthma', 'text': 'Asthma'},
                    {'value': 'arthritis', 'text': 'Arthritis'},
                    {'value': 'depression', 'text': 'Depression/Anxiety'},
                    {'value': 'kidney_disease', 'text': 'Kidney Disease'},
                    {'value': 'cancer_history', 'text': 'Cancer (current or history)'},
                    {'value': 'none', 'text': 'None of the above'}
                ],
                'weight_impact': 2.0,
                'help_text': 'Chronic conditions may require specialized coverage and affect premiums.',
                'display_order': 5,
                'is_required': True
            },
            {
                'section': 'Health Status',
                'question_text': 'Do you currently take chronic medication?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'chronic_medication_needed',
                'weight_impact': 1.8,
                'help_text': 'Chronic medication coverage is an important benefit to consider.',
                'display_order': 6,
                'is_required': True
            }
        ]

        # Create health questions
        for q_data in health_questions:
            question = SurveyQuestion.objects.create(
                category=health_category,
                section=q_data['section'],
                question_text=q_data['question_text'],
                question_type=q_data['question_type'],
                field_name=q_data['field_name'],
                choices=q_data.get('choices', []),
                validation_rules=q_data.get('validation_rules', {}),
                weight_impact=q_data['weight_impact'],
                help_text=q_data['help_text'],
                display_order=q_data['display_order'],
                is_required=q_data['is_required']
            )
            self.stdout.write(f'Created health question: {question.question_text[:50]}...')

    def create_funeral_questions(self):
        """Create comprehensive funeral insurance survey questions."""
        self.stdout.write('Creating funeral insurance survey questions...')
        
        try:
            funeral_category = PolicyCategory.objects.get(slug='funeral')
        except PolicyCategory.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Funeral category not found. Please create it first.')
            )
            return

        funeral_questions = [
            # Personal Information Section
            {
                'section': 'Personal Information',
                'question_text': 'What is your age?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'age',
                'validation_rules': {'min': 18, 'max': 80},
                'weight_impact': 1.5,
                'help_text': 'Age affects premium calculations and waiting periods.',
                'display_order': 1,
                'is_required': True
            },
            {
                'section': 'Personal Information',
                'question_text': 'Which region do you live in?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'location',
                'choices': [
                    {'value': 'hhohho', 'text': 'Hhohho'},
                    {'value': 'manzini', 'text': 'Manzini'},
                    {'value': 'shiselweni', 'text': 'Shiselweni'},
                    {'value': 'lubombo', 'text': 'Lubombo'}
                ],
                'weight_impact': 1.0,
                'help_text': 'Location affects service provider availability and regional preferences.',
                'display_order': 2,
                'is_required': True
            },
            {
                'section': 'Personal Information',
                'question_text': 'How many family members do you want to cover with funeral insurance?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'family_members_to_cover',
                'validation_rules': {'min': 1, 'max': 15},
                'weight_impact': 2.5,
                'help_text': 'Include yourself and all family members you want covered.',
                'display_order': 3,
                'is_required': True
            },
            
            # Coverage Requirements Section
            {
                'section': 'Coverage Requirements',
                'question_text': 'What coverage amount do you need per person?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'coverage_amount',
                'choices': [
                    {'value': '25000', 'text': 'R25,000 - Basic funeral coverage'},
                    {'value': '50000', 'text': 'R50,000 - Standard funeral coverage'},
                    {'value': '100000', 'text': 'R100,000 - Comprehensive funeral coverage'},
                    {'value': '200000', 'text': 'R200,000 - Premium funeral coverage'},
                    {'value': '300000', 'text': 'R300,000+ - Luxury funeral coverage'}
                ],
                'weight_impact': 3.0,
                'help_text': 'Higher coverage amounts provide more options for funeral arrangements.',
                'display_order': 4,
                'is_required': True
            },
            {
                'section': 'Coverage Requirements',
                'question_text': 'What level of funeral service do you prefer?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'service_preference',
                'choices': [
                    {'value': 'basic', 'text': 'Basic - Simple, dignified funeral service'},
                    {'value': 'standard', 'text': 'Standard - Traditional funeral with common extras'},
                    {'value': 'premium', 'text': 'Premium - Enhanced service with additional benefits'},
                    {'value': 'luxury', 'text': 'Luxury - Top-tier service with all amenities'}
                ],
                'weight_impact': 2.0,
                'help_text': 'Service level affects the types of policies and benefits available.',
                'display_order': 5,
                'is_required': True
            },
            {
                'section': 'Financial Preferences',
                'question_text': 'What is your maximum monthly budget for funeral insurance?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'monthly_budget',
                'validation_rules': {'min': 50, 'max': 500},
                'weight_impact': 3.5,
                'help_text': 'Enter amount in Rands. This is the primary factor in finding suitable options.',
                'display_order': 6,
                'is_required': True
            }
        ]

        # Create funeral questions
        for q_data in funeral_questions:
            question = SurveyQuestion.objects.create(
                category=funeral_category,
                section=q_data['section'],
                question_text=q_data['question_text'],
                question_type=q_data['question_type'],
                field_name=q_data['field_name'],
                choices=q_data.get('choices', []),
                validation_rules=q_data.get('validation_rules', {}),
                weight_impact=q_data['weight_impact'],
                help_text=q_data['help_text'],
                display_order=q_data['display_order'],
                is_required=q_data['is_required']
            )
            self.stdout.write(f'Created funeral question: {question.question_text[:50]}...')