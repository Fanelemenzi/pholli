"""
Management command to update survey questions for the policy features upgrade.
This command adds new questions for annual family limits, medical aid status, 
and ambulance coverage while removing deprecated net monthly income questions.
"""
import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from simple_surveys.models import SimpleSurveyQuestion


class Command(BaseCommand):
    help = 'Update survey questions for policy features upgrade'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if questions already exist'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        try:
            with transaction.atomic():
                # Step 1: Remove deprecated questions
                removed_count = self._remove_deprecated_questions(dry_run)
                
                # Step 2: Add new health insurance questions
                added_count = self._add_new_health_questions(dry_run, force)
                
                # Step 3: Update display order for existing questions
                updated_count = self._update_question_ordering(dry_run)

                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Would remove {removed_count} questions, '
                            f'add {added_count} questions, '
                            f'and update {updated_count} questions'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Successfully removed {removed_count} questions, '
                            f'added {added_count} questions, '
                            f'and updated {updated_count} questions'
                        )
                    )

        except Exception as e:
            raise CommandError(f'Error updating survey questions: {e}')

    def _remove_deprecated_questions(self, dry_run=False):
        """Remove questions related to net monthly income"""
        deprecated_fields = [
            'net_monthly_income',
            'monthly_income',
            'income'
        ]
        
        questions_to_remove = SimpleSurveyQuestion.objects.filter(
            field_name__in=deprecated_fields
        )
        
        count = questions_to_remove.count()
        
        if count > 0:
            if dry_run:
                for question in questions_to_remove:
                    self.stdout.write(f'Would remove: {question.question_text}')
            else:
                for question in questions_to_remove:
                    self.stdout.write(f'Removing: {question.question_text}')
                questions_to_remove.delete()
        
        return count

    def _add_new_health_questions(self, dry_run=False, force=False):
        """Add new health insurance questions"""
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
        
        added_count = 0
        
        for question_data in new_questions:
            # Check if question already exists
            existing = SimpleSurveyQuestion.objects.filter(
                category=question_data['category'],
                field_name=question_data['field_name']
            ).first()
            
            if existing and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f'Question already exists: {question_data["field_name"]} '
                        f'(use --force to update)'
                    )
                )
                continue
            
            if dry_run:
                action = 'Update' if existing else 'Add'
                self.stdout.write(f'{action}: {question_data["question_text"]}')
            else:
                question, created = SimpleSurveyQuestion.objects.update_or_create(
                    category=question_data['category'],
                    field_name=question_data['field_name'],
                    defaults=question_data
                )
                
                action = 'Created' if created else 'Updated'
                self.stdout.write(f'{action}: {question.question_text}')
            
            added_count += 1
        
        return added_count

    def _update_question_ordering(self, dry_run=False):
        """Update display order for existing questions to accommodate new ones"""
        # Update existing questions that need reordering
        updates = [
            # Move monthly budget question to after household income
            {'field_name': 'monthly_budget', 'new_order': 11},
            # Move deductible question to end
            {'field_name': 'preferred_deductible', 'new_order': 12},
        ]
        
        updated_count = 0
        
        for update in updates:
            question = SimpleSurveyQuestion.objects.filter(
                category='health',
                field_name=update['field_name']
            ).first()
            
            if question and question.display_order != update['new_order']:
                if dry_run:
                    self.stdout.write(
                        f'Would update order for {question.field_name}: '
                        f'{question.display_order} -> {update["new_order"]}'
                    )
                else:
                    old_order = question.display_order
                    question.display_order = update['new_order']
                    question.save(update_fields=['display_order'])
                    self.stdout.write(
                        f'Updated order for {question.field_name}: '
                        f'{old_order} -> {update["new_order"]}'
                    )
                
                updated_count += 1
        
        return updated_count

    def _validate_question_data(self, question_data):
        """Validate question data before creating/updating"""
        errors = []
        
        required_fields = ['category', 'question_text', 'field_name', 'input_type', 'display_order']
        for field in required_fields:
            if field not in question_data:
                errors.append(f'Missing required field: {field}')
        
        # Validate input type
        valid_input_types = ['text', 'number', 'select', 'radio', 'checkbox']
        if question_data.get('input_type') not in valid_input_types:
            errors.append(f'Invalid input_type: {question_data.get("input_type")}')
        
        # Validate choices for select/radio/checkbox
        if question_data.get('input_type') in ['select', 'radio', 'checkbox']:
            choices = question_data.get('choices', [])
            if not choices:
                errors.append(f'Choices required for input_type: {question_data.get("input_type")}')
        
        return errors