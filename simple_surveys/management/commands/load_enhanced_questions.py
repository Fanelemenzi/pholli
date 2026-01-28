"""
Management command to load enhanced survey questions with benefit levels and ranges.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from simple_surveys.models import SimpleSurveyQuestion
import os


class Command(BaseCommand):
    help = 'Load enhanced survey questions with benefit levels and annual limit ranges'
    
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
        """Load enhanced survey questions"""
        
        if options['replace']:
            self.stdout.write('Removing existing survey questions...')
            if options['category']:
                SimpleSurveyQuestion.objects.filter(category=options['category']).delete()
                self.stdout.write(f'Removed existing {options["category"]} questions')
            else:
                SimpleSurveyQuestion.objects.all().delete()
                self.stdout.write('Removed all existing questions')
        
        # Load enhanced health questions
        if not options['category'] or options['category'] == 'health':
            self.stdout.write('Loading enhanced health questions...')
            try:
                call_command('loaddata', 'simple_surveys/fixtures/enhanced_health_questions.json')
                self.stdout.write(
                    self.style.SUCCESS('Successfully loaded enhanced health questions')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error loading health questions: {e}')
                )
        
        # Load funeral questions (if they exist)
        if not options['category'] or options['category'] == 'funeral':
            funeral_fixture = 'simple_surveys/fixtures/funeral_questions.json'
            if os.path.exists(funeral_fixture):
                self.stdout.write('Loading funeral questions...')
                try:
                    call_command('loaddata', funeral_fixture)
                    self.stdout.write(
                        self.style.SUCCESS('Successfully loaded funeral questions')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading funeral questions: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('Funeral questions fixture not found, skipping...')
                )
        
        # Display summary
        health_count = SimpleSurveyQuestion.objects.filter(category='health').count()
        funeral_count = SimpleSurveyQuestion.objects.filter(category='funeral').count()
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write('SURVEY QUESTIONS SUMMARY')
        self.stdout.write('='*50)
        self.stdout.write(f'Health questions: {health_count}')
        self.stdout.write(f'Funeral questions: {funeral_count}')
        self.stdout.write(f'Total questions: {health_count + funeral_count}')
        
        # Show new benefit level questions
        benefit_questions = SimpleSurveyQuestion.objects.filter(
            field_name__in=[
                'in_hospital_benefit_level',
                'out_hospital_benefit_level',
                'annual_limit_family_range',
                'annual_limit_member_range'
            ]
        )
        
        if benefit_questions.exists():
            self.stdout.write('\nNew benefit level and range questions:')
            for question in benefit_questions:
                self.stdout.write(f'  - {question.question_text} ({question.field_name})')
        
        self.stdout.write('\n' + self.style.SUCCESS('Enhanced survey questions loaded successfully!'))