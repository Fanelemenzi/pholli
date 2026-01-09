"""
Management command to update survey analytics data.
This should be run periodically (e.g., via cron job) to keep analytics current.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from surveys.analytics import SurveyAnalyticsCollector
from surveys.models import SurveyQuestion, SurveyAnalytics
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update survey analytics data for all active questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            help='Update analytics for specific category only',
        )
        parser.add_argument(
            '--question-ids',
            nargs='+',
            type=int,
            help='Update analytics for specific question IDs only',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if analytics were recently updated',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information',
        )

    def handle(self, *args, **options):
        collector = SurveyAnalyticsCollector()
        
        # Determine which questions to update
        questions = SurveyQuestion.objects.filter(is_active=True)
        
        if options['category']:
            questions = questions.filter(category__slug=options['category'])
            self.stdout.write(f"Filtering by category: {options['category']}")
        
        if options['question_ids']:
            questions = questions.filter(id__in=options['question_ids'])
            self.stdout.write(f"Filtering by question IDs: {options['question_ids']}")
        
        question_ids = list(questions.values_list('id', flat=True))
        
        if not question_ids:
            self.stdout.write(
                self.style.WARNING('No questions found matching the criteria.')
            )
            return
        
        # Check if we should skip recently updated analytics
        if not options['force']:
            recent_threshold = timezone.now() - timezone.timedelta(hours=1)
            recently_updated = SurveyAnalytics.objects.filter(
                question_id__in=question_ids,
                last_updated__gte=recent_threshold
            ).values_list('question_id', flat=True)
            
            if recently_updated:
                question_ids = [qid for qid in question_ids if qid not in recently_updated]
                self.stdout.write(
                    f"Skipping {len(recently_updated)} questions updated in the last hour. "
                    f"Use --force to update anyway."
                )
        
        if not question_ids:
            self.stdout.write(
                self.style.SUCCESS('All analytics are up to date.')
            )
            return
        
        self.stdout.write(f"Updating analytics for {len(question_ids)} questions...")
        
        # Update analytics
        start_time = timezone.now()
        result = collector.bulk_update_analytics(question_ids)
        end_time = timezone.now()
        
        duration = (end_time - start_time).total_seconds()
        
        # Report results
        if result['updated'] > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated analytics for {result['updated']} questions "
                    f"in {duration:.2f} seconds."
                )
            )
        
        if result['errors'] > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"Encountered {result['errors']} errors during update."
                )
            )
        
        if options['verbose']:
            self.stdout.write("\nDetailed Results:")
            self.stdout.write(f"  Total questions processed: {result['total']}")
            self.stdout.write(f"  Successfully updated: {result['updated']}")
            self.stdout.write(f"  Errors encountered: {result['errors']}")
            self.stdout.write(f"  Processing time: {duration:.2f} seconds")
            self.stdout.write(f"  Average time per question: {duration/max(result['total'], 1):.3f} seconds")
        
        # Log completion
        logger.info(
            f"Survey analytics update completed. "
            f"Updated: {result['updated']}, Errors: {result['errors']}, "
            f"Duration: {duration:.2f}s"
        )