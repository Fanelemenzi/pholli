from django.core.management.base import BaseCommand
from django.db import transaction
from policies.models import PolicyCategory
from surveys.models import SurveyTemplate, SurveyQuestion, TemplateQuestion, QuestionDependency


class Command(BaseCommand):
    """Management command to create comprehensive funeral insurance survey template and questions."""
    
    help = 'Create funeral insurance survey template with comprehensive questions and conditional logic'
    
    def handle(self, *args, **options):
        """Create funeral insurance survey template and questions."""
        with transaction.atomic():
            self.stdout.write('Creating funeral insurance survey template and questions...')
            
            # Get or create funeral insurance category
            funeral_category, created = PolicyCategory.objects.get_or_create(
                slug='funeral',
                defaults={
                    'name': 'Funeral Insurance',
                    'description': 'Funeral insurance policies for burial and funeral expenses',
                    'icon': 'funeral',
                    'display_order': 2,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created funeral category: {funeral_category.name}')
            else:
                self.stdout.write(f'Using existing funeral category: {funeral_category.name}')
            
            # Create funeral insurance survey template
            funeral_template, created = SurveyTemplate.objects.get_or_create(
                category=funeral_category,
                name='Funeral Insurance Needs Assessment',
                version='1.0',
                defaults={
                    'description': 'Comprehensive survey to assess funeral insurance needs and preferences',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'Created funeral survey template: {funeral_template.name}')
            else:
                self.stdout.write(f'Using existing funeral survey template: {funeral_template.name}')
            
            # Define comprehensive funeral insurance questions
            funeral_questions = self._get_funeral_questions()
            
            # Create questions and add to template
            created_questions = []
            for question_data in funeral_questions:
                question, created = SurveyQuestion.objects.get_or_create(
                    category=funeral_category,
                    field_name=question_data['field_name'],
                    defaults=question_data
                )
                
                if created:
                    self.stdout.write(f'Created question: {question.question_text[:50]}...')
                    created_questions.append(question)
                
                # Add to template if not already added
                template_question, created = TemplateQuestion.objects.get_or_create(
                    template=funeral_template,
                    question=question,
                    defaults={'display_order': question_data['display_order']}
                )
            
            # Create conditional question logic
            self._create_question_dependencies(funeral_category)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created funeral insurance survey with {len(funeral_questions)} questions!'
                )
            )
    
    def _get_funeral_questions(self):
        """Define comprehensive funeral insurance survey questions."""
        return [
            # Family Structure Section
            {
                'section': 'Family Structure',
                'question_text': 'How many family members do you want to cover with funeral insurance?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'family_members_count',
                'validation_rules': {
                    'min': 1,
                    'max': 15,
                    'required': True,
                    'error_message': 'Number of family members must be between 1 and 15'
                },
                'weight_impact': 3.0,
                'help_text': 'This includes yourself and any dependents you want covered',
                'is_required': True,
                'display_order': 1
            },
            {
                'section': 'Family Structure',
                'question_text': 'What is your age?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'main_member_age',
                'validation_rules': {
                    'min': 18,
                    'max': 85,
                    'required': True,
                    'error_message': 'Age must be between 18 and 85'
                },
                'weight_impact': 2.5,
                'help_text': 'Age affects premium rates and coverage options',
                'is_required': True,
                'display_order': 2
            },
            {
                'section': 'Family Structure',
                'question_text': 'What are the ages of your dependents? (Enter ages separated by commas)',
                'question_type': SurveyQuestion.QuestionType.TEXT,
                'field_name': 'dependents_ages',
                'validation_rules': {
                    'required': False,
                    'pattern': r'^(\d{1,2})(,\s*\d{1,2})*$',
                    'error_message': 'Please enter ages separated by commas (e.g., 25, 30, 5)'
                },
                'weight_impact': 2.0,
                'help_text': 'Enter the ages of family members you want to cover (e.g., 25, 30, 5)',
                'is_required': False,
                'display_order': 3
            },
            {
                'section': 'Family Structure',
                'question_text': 'Do you want to include extended family members (parents, siblings)?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'include_extended_family',
                'validation_rules': {'required': True},
                'weight_impact': 1.8,
                'help_text': 'Some policies allow coverage for extended family members',
                'is_required': True,
                'display_order': 4
            },
            {
                'section': 'Family Structure',
                'question_text': 'Which extended family members do you want to include?',
                'question_type': SurveyQuestion.QuestionType.MULTI_CHOICE,
                'field_name': 'extended_family_types',
                'choices': [
                    'Parents',
                    'Siblings',
                    'Grandparents',
                    'In-laws',
                    'Other relatives'
                ],
                'validation_rules': {'required': False},
                'weight_impact': 1.5,
                'help_text': 'Select all extended family types you want to cover',
                'is_required': False,
                'display_order': 5
            },
            {
                'section': 'Family Structure',
                'question_text': 'Are any family members over 65 years old?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'has_elderly_members',
                'validation_rules': {'required': True},
                'weight_impact': 2.2,
                'help_text': 'Age affects premium rates and waiting periods',
                'is_required': True,
                'display_order': 6
            },
            
            # Service Preferences Section
            {
                'section': 'Service Preferences',
                'question_text': 'What is your preferred burial method?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'burial_preference',
                'choices': [
                    'Traditional burial',
                    'Cremation',
                    'No preference',
                    'Religious/cultural requirements',
                    'Eco-friendly burial'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 2.0,
                'help_text': 'Different burial methods have different cost implications',
                'is_required': True,
                'display_order': 7
            },
            {
                'section': 'Service Preferences',
                'question_text': 'Where would you prefer funeral services to be held?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'service_location_preference',
                'choices': [
                    'Funeral home',
                    'Church/religious venue',
                    'Family home',
                    'Community hall',
                    'Graveside only',
                    'No preference'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 1.5,
                'help_text': 'Service location affects logistics and costs',
                'is_required': True,
                'display_order': 8
            },
            {
                'section': 'Service Preferences',
                'question_text': 'Do you have specific cultural or religious requirements for funeral services?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'has_cultural_requirements',
                'validation_rules': {'required': True},
                'weight_impact': 1.8,
                'help_text': 'Cultural and religious requirements may affect service options and costs',
                'is_required': True,
                'display_order': 9
            },
            {
                'section': 'Service Preferences',
                'question_text': 'What cultural or religious requirements do you have?',
                'question_type': SurveyQuestion.QuestionType.TEXT,
                'field_name': 'cultural_requirements_details',
                'validation_rules': {
                    'required': False,
                    'max_length': 500
                },
                'weight_impact': 1.5,
                'help_text': 'Please describe any specific cultural or religious requirements',
                'is_required': False,
                'display_order': 10
            },
            {
                'section': 'Service Preferences',
                'question_text': 'Do you need repatriation coverage (transport to another country/province)?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'needs_repatriation',
                'validation_rules': {'required': True},
                'weight_impact': 2.5,
                'help_text': 'Repatriation coverage significantly affects premium costs',
                'is_required': True,
                'display_order': 11
            },
            {
                'section': 'Service Preferences',
                'question_text': 'Where would repatriation be to?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'repatriation_destination',
                'choices': [
                    'Another province in South Africa',
                    'Neighboring African country',
                    'Other African country',
                    'Outside Africa',
                    'Multiple destinations possible'
                ],
                'validation_rules': {'required': False},
                'weight_impact': 2.0,
                'help_text': 'Distance affects repatriation costs',
                'is_required': False,
                'display_order': 12
            },
            {
                'section': 'Service Preferences',
                'question_text': 'How important is the quality of the casket/coffin to you?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'casket_quality_importance',
                'choices': [
                    'Very important - premium quality',
                    'Somewhat important - good quality',
                    'Standard quality is fine',
                    'Basic quality is acceptable',
                    'Not important'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 1.8,
                'help_text': 'Casket quality affects the overall funeral costs',
                'is_required': True,
                'display_order': 13
            },
            
            # Coverage Requirements Section
            {
                'section': 'Coverage Requirements',
                'question_text': 'What is the minimum coverage amount you need per person?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'minimum_coverage_per_person',
                'choices': [
                    'R10,000 - R20,000',
                    'R20,000 - R30,000',
                    'R30,000 - R50,000',
                    'R50,000 - R75,000',
                    'R75,000 - R100,000',
                    'More than R100,000'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 3.0,
                'help_text': 'Coverage amount directly affects premium costs',
                'is_required': True,
                'display_order': 14
            },
            {
                'section': 'Coverage Requirements',
                'question_text': 'Do you want additional benefits beyond basic funeral costs?',
                'question_type': SurveyQuestion.QuestionType.MULTI_CHOICE,
                'field_name': 'additional_benefits',
                'choices': [
                    'Grocery benefit for family',
                    'Memorial service costs',
                    'Tombstone/headstone',
                    'Flowers and decorations',
                    'Catering for mourners',
                    'Transport for mourners',
                    'Grief counseling',
                    'None - basic coverage only'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 2.2,
                'help_text': 'Additional benefits increase premium but provide more comprehensive coverage',
                'is_required': True,
                'display_order': 15
            },
            {
                'section': 'Coverage Requirements',
                'question_text': 'How long are you willing to wait before full coverage begins?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'waiting_period_tolerance',
                'choices': [
                    'Immediate coverage preferred (higher premium)',
                    '3 months waiting period acceptable',
                    '6 months waiting period acceptable',
                    '12 months waiting period acceptable',
                    'Longer waiting period for lower premium'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 2.5,
                'help_text': 'Longer waiting periods typically mean lower premiums',
                'is_required': True,
                'display_order': 16
            },
            {
                'section': 'Coverage Requirements',
                'question_text': 'How important is fast claim payout to you?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'claim_payout_speed_importance',
                'choices': [
                    'Very important - within 24-48 hours',
                    'Important - within 3-5 days',
                    'Moderate - within 1 week',
                    'Not critical - within 2 weeks',
                    'Not important - standard processing time'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 2.0,
                'help_text': 'Faster payout options may affect premium rates',
                'is_required': True,
                'display_order': 17
            },
            {
                'section': 'Coverage Requirements',
                'question_text': 'Do you want accidental death benefit (higher payout for accidental death)?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'wants_accidental_death_benefit',
                'validation_rules': {'required': True},
                'weight_impact': 1.8,
                'help_text': 'Accidental death benefit provides additional coverage for accidental deaths',
                'is_required': True,
                'display_order': 18
            },
            {
                'section': 'Coverage Requirements',
                'question_text': 'Do you want your coverage to increase with inflation?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'inflation_protection',
                'choices': [
                    'Yes - automatic annual increases',
                    'Yes - but I want to approve increases',
                    'No - fixed coverage amount',
                    'Unsure - need more information'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 1.5,
                'help_text': 'Inflation protection ensures your coverage keeps up with rising funeral costs',
                'is_required': True,
                'display_order': 19
            },
            
            # Budget Section
            {
                'section': 'Budget',
                'question_text': 'What is your preferred monthly premium budget for the main member?',
                'question_type': SurveyQuestion.QuestionType.RANGE,
                'field_name': 'main_member_premium_budget',
                'validation_rules': {
                    'min': 50,
                    'max': 1000,
                    'step': 25,
                    'required': True
                },
                'weight_impact': 3.0,
                'help_text': 'Your budget helps us filter options within your price range',
                'is_required': True,
                'display_order': 20
            },
            {
                'section': 'Budget',
                'question_text': 'What is your budget for each dependent\'s premium?',
                'question_type': SurveyQuestion.QuestionType.RANGE,
                'field_name': 'dependent_premium_budget',
                'validation_rules': {
                    'min': 20,
                    'max': 500,
                    'step': 10,
                    'required': False
                },
                'weight_impact': 2.5,
                'help_text': 'Dependent premiums are typically lower than main member premiums',
                'is_required': False,
                'display_order': 21
            },
            {
                'section': 'Budget',
                'question_text': 'How do you prefer to pay your premiums?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'payment_frequency_preference',
                'choices': [
                    'Monthly',
                    'Quarterly (every 3 months)',
                    'Semi-annually (every 6 months)',
                    'Annually',
                    'Flexible - whatever saves money'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 1.2,
                'help_text': 'Different payment frequencies may offer discounts',
                'is_required': True,
                'display_order': 22
            },
            {
                'section': 'Budget',
                'question_text': 'Are you willing to pay higher premiums for better benefits?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'premium_vs_benefits_preference',
                'choices': [
                    'Yes - I want the best coverage available',
                    'Somewhat - for important benefits only',
                    'No - I prefer basic coverage at low cost',
                    'Depends on the specific benefit',
                    'I need help deciding'
                ],
                'validation_rules': {'required': True},
                'weight_impact': 2.0,
                'help_text': 'This helps us balance cost and coverage in our recommendations',
                'is_required': True,
                'display_order': 23
            },
            {
                'section': 'Budget',
                'question_text': 'Do you have an existing funeral policy that you want to replace?',
                'question_type': SurveyQuestion.QuestionType.BOOLEAN,
                'field_name': 'has_existing_policy',
                'validation_rules': {'required': True},
                'weight_impact': 1.5,
                'help_text': 'Existing policies may affect your options and timing',
                'is_required': True,
                'display_order': 24
            },
            {
                'section': 'Budget',
                'question_text': 'What is your current monthly premium for existing funeral cover?',
                'question_type': SurveyQuestion.QuestionType.NUMBER,
                'field_name': 'current_premium_amount',
                'validation_rules': {
                    'min': 0,
                    'max': 2000,
                    'required': False
                },
                'weight_impact': 1.8,
                'help_text': 'This helps us compare value with your current coverage',
                'is_required': False,
                'display_order': 25
            },
            {
                'section': 'Budget',
                'question_text': 'What is the main reason you want to change your current policy?',
                'question_type': SurveyQuestion.QuestionType.CHOICE,
                'field_name': 'change_reason',
                'choices': [
                    'Too expensive',
                    'Insufficient coverage',
                    'Poor service',
                    'Need additional benefits',
                    'Better options available',
                    'Life circumstances changed',
                    'Other'
                ],
                'validation_rules': {'required': False},
                'weight_impact': 1.5,
                'help_text': 'Understanding your concerns helps us recommend better options',
                'is_required': False,
                'display_order': 26
            }
        ]
    
    def _create_question_dependencies(self, funeral_category):
        """Create conditional question logic for funeral-specific scenarios."""
        self.stdout.write('Creating conditional question dependencies...')
        
        try:
            # Extended family dependencies
            include_extended_family = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='include_extended_family'
            )
            extended_family_types = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='extended_family_types'
            )
            
            # Show extended family types only if user wants to include extended family
            dependency1, created = QuestionDependency.objects.get_or_create(
                parent_question=include_extended_family,
                child_question=extended_family_types,
                defaults={
                    'condition_value': True,
                    'condition_operator': QuestionDependency.ConditionOperator.EQUALS,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created dependency: extended family types shows when including extended family')
            
            # Cultural requirements dependencies
            has_cultural_requirements = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='has_cultural_requirements'
            )
            cultural_requirements_details = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='cultural_requirements_details'
            )
            
            # Show cultural requirements details only if user has cultural requirements
            dependency2, created = QuestionDependency.objects.get_or_create(
                parent_question=has_cultural_requirements,
                child_question=cultural_requirements_details,
                defaults={
                    'condition_value': True,
                    'condition_operator': QuestionDependency.ConditionOperator.EQUALS,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created dependency: cultural requirements details shows when user has cultural requirements')
            
            # Repatriation dependencies
            needs_repatriation = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='needs_repatriation'
            )
            repatriation_destination = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='repatriation_destination'
            )
            
            # Show repatriation destination only if user needs repatriation
            dependency3, created = QuestionDependency.objects.get_or_create(
                parent_question=needs_repatriation,
                child_question=repatriation_destination,
                defaults={
                    'condition_value': True,
                    'condition_operator': QuestionDependency.ConditionOperator.EQUALS,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created dependency: repatriation destination shows when user needs repatriation')
            
            # Existing policy dependencies
            has_existing_policy = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='has_existing_policy'
            )
            current_premium_amount = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='current_premium_amount'
            )
            change_reason = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='change_reason'
            )
            
            # Show current premium amount only if user has existing policy
            dependency4, created = QuestionDependency.objects.get_or_create(
                parent_question=has_existing_policy,
                child_question=current_premium_amount,
                defaults={
                    'condition_value': True,
                    'condition_operator': QuestionDependency.ConditionOperator.EQUALS,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created dependency: current premium amount shows when user has existing policy')
            
            # Show change reason only if user has existing policy
            dependency5, created = QuestionDependency.objects.get_or_create(
                parent_question=has_existing_policy,
                child_question=change_reason,
                defaults={
                    'condition_value': True,
                    'condition_operator': QuestionDependency.ConditionOperator.EQUALS,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created dependency: change reason shows when user has existing policy')
            
            # Family members count dependency for dependents ages
            family_members_count = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='family_members_count'
            )
            dependents_ages = SurveyQuestion.objects.get(
                category=funeral_category,
                field_name='dependents_ages'
            )
            
            # Show dependents ages only if user has more than 1 family member
            dependency6, created = QuestionDependency.objects.get_or_create(
                parent_question=family_members_count,
                child_question=dependents_ages,
                defaults={
                    'condition_value': 1,
                    'condition_operator': QuestionDependency.ConditionOperator.GREATER_THAN,
                    'is_active': True
                }
            )
            if created:
                self.stdout.write('Created dependency: dependents ages shows when family members count > 1')
            
        except SurveyQuestion.DoesNotExist as e:
            self.stdout.write(f'Warning: Could not create some dependencies - {e}')
        
        self.stdout.write('Completed conditional question dependencies')