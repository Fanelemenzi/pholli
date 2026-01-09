"""
Management command to load predefined survey questions from fixtures.
"""
import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from simple_surveys.models import SimpleSurveyQuestion


class Command(BaseCommand):
    help = 'Load predefined survey questions from fixtures'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            choices=['health', 'funeral', 'all'],
            default='all',
            help='Load questions for specific category or all categories'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing questions before loading new ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be loaded without actually loading'
        )

    def handle(self, *args, **options):
        category = options['category']
        clear_existing = options['clear']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Determine which fixtures to load
        fixtures_to_load = []
        if category in ['health', 'all']:
            fixtures_to_load.append(('health', 'health_questions.json'))
        if category in ['funeral', 'all']:
            fixtures_to_load.append(('funeral', 'funeral_questions.json'))

        if not fixtures_to_load:
            raise CommandError(f'No fixtures found for category: {category}')

        # Clear existing questions if requested
        if clear_existing:
            if category == 'all':
                count = SimpleSurveyQuestion.objects.count()
                if not dry_run:
                    SimpleSurveyQuestion.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(f'Cleared {count} existing questions')
                )
            else:
                count = SimpleSurveyQuestion.objects.filter(category=category).count()
                if not dry_run:
                    SimpleSurveyQuestion.objects.filter(category=category).delete()
                self.stdout.write(
                    self.style.WARNING(f'Cleared {count} existing {category} questions')
                )

        # Load fixtures
        total_loaded = 0
        for cat, fixture_file in fixtures_to_load:
            loaded_count = self._load_fixture(cat, fixture_file, dry_run)
            total_loaded += loaded_count

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Would load {total_loaded} questions')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully loaded {total_loaded} questions')
            )

    def _load_fixture(self, category, fixture_file, dry_run=False):
        """Load questions from a specific fixture file"""
        # Get the fixture file path
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures',
            fixture_file
        )

        if not os.path.exists(fixture_path):
            raise CommandError(f'Fixture file not found: {fixture_path}')

        # Load and parse the fixture
        try:
            with open(fixture_path, 'r', encoding='utf-8') as f:
                fixture_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise CommandError(f'Error reading fixture {fixture_file}: {e}')

        if not isinstance(fixture_data, list):
            raise CommandError(f'Invalid fixture format in {fixture_file}')

        # Process questions
        loaded_count = 0
        with transaction.atomic():
            for item in fixture_data:
                if not isinstance(item, dict) or 'model' not in item or 'fields' not in item:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping invalid item in {fixture_file}')
                    )
                    continue

                if item['model'] != 'simple_surveys.simplesurveyquestion':
                    self.stdout.write(
                        self.style.WARNING(f'Skipping non-question item in {fixture_file}')
                    )
                    continue

                fields = item['fields']
                
                # Validate required fields
                required_fields = ['category', 'question_text', 'field_name', 'input_type', 'display_order']
                missing_fields = [f for f in required_fields if f not in fields]
                if missing_fields:
                    self.stdout.write(
                        self.style.ERROR(f'Skipping question with missing fields: {missing_fields}')
                    )
                    continue

                # Validate category matches expected
                if fields['category'] != category:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Question category {fields["category"]} does not match expected {category}'
                        )
                    )

                if dry_run:
                    self.stdout.write(f'Would load: {fields["question_text"][:50]}...')
                else:
                    # Create or update the question
                    question, created = SimpleSurveyQuestion.objects.update_or_create(
                        category=fields['category'],
                        field_name=fields['field_name'],
                        defaults={
                            'question_text': fields['question_text'],
                            'input_type': fields['input_type'],
                            'choices': fields.get('choices', []),
                            'is_required': fields.get('is_required', True),
                            'display_order': fields['display_order'],
                            'validation_rules': fields.get('validation_rules', {}),
                        }
                    )
                    
                    action = 'Created' if created else 'Updated'
                    self.stdout.write(f'{action}: {question.question_text[:50]}...')

                loaded_count += 1

        return loaded_count

    def _validate_question_data(self, fields):
        """Validate question data before loading"""
        errors = []
        
        # Validate input type
        valid_input_types = ['text', 'number', 'select', 'radio', 'checkbox']
        if fields.get('input_type') not in valid_input_types:
            errors.append(f'Invalid input_type: {fields.get("input_type")}')
        
        # Validate choices for select/radio/checkbox
        if fields.get('input_type') in ['select', 'radio', 'checkbox']:
            choices = fields.get('choices', [])
            if not choices:
                errors.append(f'Choices required for input_type: {fields.get("input_type")}')
            elif not isinstance(choices, list):
                errors.append('Choices must be a list')
        
        # Validate validation rules
        validation_rules = fields.get('validation_rules', {})
        if validation_rules and not isinstance(validation_rules, dict):
            errors.append('Validation rules must be a dictionary')
        
        return errors