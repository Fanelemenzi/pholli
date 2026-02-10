"""
Management command to load complete survey questions with all available fields and options.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from simple_surveys.models import SimpleSurveyQuestion
import os


class Command(BaseCommand):
    help = 'Load complete survey questions with all available fields and options'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Replace existing questions with new ones',
        )
        parser.add_argument(
            '--category',
            type=str,
            choices=['health', 'funeral'],
            help='Load questions for specific category only',
        )
    
    def handle(self, *args, **options):
        """Load complete survey questions"""
        
        if options['replace']:
            self.stdout.write('Removing existing survey questions...')
            if options['category']:
                SimpleSurveyQuestion.objects.filter(category=options['category']).delete()
                self.stdout.write(f'Removed existing {options["category"]} questions')
            else:
                SimpleSurveyQuestion.objects.all().delete()
                self.stdout.write('Removed all existing questions')
        
        # Load complete health questions
        if not options['category'] or options['category'] == 'health':
            self.stdout.write('Loading complete health questions...')
            try:
                call_command('loaddata', 'simple_surveys/fixtures/complete_health_questions.json')
                self.stdout.write(
                    self.style.SUCCESS('Successfully loaded complete health questions')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error loading health questions: {e}')
                )
        
        # Load complete funeral questions
        if not options['category'] or options['category'] == 'funeral':
            funeral_fixture = 'simple_surveys/fixtures/complete_funeral_questions.json'
            if os.path.exists(funeral_fixture):
                self.stdout.write('Loading complete funeral questions...')
                try:
                    call_command('loaddata', funeral_fixture)
                    self.stdout.write(
                        self.style.SUCCESS('Successfully loaded complete funeral questions')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading funeral questions: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('Complete funeral questions fixture not found, skipping...')
                )
        
        # Display summary
        health_count = SimpleSurveyQuestion.objects.filter(category='health').count()
        funeral_count = SimpleSurveyQuestion.objects.filter(category='funeral').count()
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('COMPLETE SURVEY QUESTIONS SUMMARY')
        self.stdout.write('='*50)
        self.stdout.write(f'Health questions: {health_count}')
        self.stdout.write(f'Funeral questions: {funeral_count}')
        self.stdout.write(f'Total questions: {health_count + funeral_count}')
        
        # Show key question types
        key_questions = SimpleSurveyQuestion.objects.filter(
            field_name__in=[
                'in_hospital_benefit_level',
                'out_hospital_benefit_level',
                'annual_limit_family_range',
                'annual_limit_member_range',
                'preferred_cover_amount',
                'marital_status',
                'gender'
            ]
        )
        
        if key_questions.exists():
            self.stdout.write('\nKey question types loaded:')
            for question in key_questions:
                self.stdout.write(f'  - {question.question_text} ({question.field_name})')
        
        self.stdout.write('\n' + self.style.SUCCESS('Complete survey questions loaded successfully!'))