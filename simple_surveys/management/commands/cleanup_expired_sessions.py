"""
Management command to clean up expired survey sessions and associated data.
This command should be run periodically (e.g., via cron job) to maintain database cleanliness.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import logging

from simple_surveys.session_manager import SessionManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up expired survey sessions and associated response data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of sessions to process in each batch (default: 100)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation prompt'
        )
        
        parser.add_argument(
            '--older-than-hours',
            type=int,
            default=0,
            help='Only clean up sessions older than specified hours (0 = all expired)'
        )
        
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='Only show session statistics without performing cleanup'
        )
    
    def handle(self, *args, **options):
        """Execute the cleanup command."""
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        force = options['force']
        older_than_hours = options['older_than_hours']
        stats_only = options['stats_only']
        
        # Set up logging
        if options['verbosity'] >= 2:
            logging.basicConfig(level=logging.DEBUG)
        elif options['verbosity'] >= 1:
            logging.basicConfig(level=logging.INFO)
        
        try:
            # Show current statistics
            self.stdout.write(self.style.SUCCESS('=== Session Statistics ==='))
            stats = SessionManager.get_session_stats()
            
            if 'error' in stats:
                raise CommandError(f"Error getting session stats: {stats['error']}")
            
            self._display_stats(stats)
            
            if stats_only:
                return
            
            # Calculate cutoff time if older_than_hours is specified
            cutoff_time = None
            if older_than_hours > 0:
                cutoff_time = timezone.now() - timedelta(hours=older_than_hours)
                self.stdout.write(
                    f"Only cleaning sessions older than {older_than_hours} hours "
                    f"(before {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})"
                )
            
            # Check if there's anything to clean up
            expired_count = stats['quotation_sessions']['expired']
            if expired_count == 0:
                self.stdout.write(self.style.SUCCESS('No expired sessions to clean up.'))
                return
            
            # Confirmation prompt (unless force or dry-run)
            if not force and not dry_run:
                confirm = input(
                    f"\nThis will delete {expired_count} expired sessions and their data. "
                    f"Continue? [y/N]: "
                )
                if confirm.lower() not in ['y', 'yes']:
                    self.stdout.write('Cleanup cancelled.')
                    return
            
            # Perform cleanup
            if dry_run:
                self.stdout.write(self.style.WARNING('\n=== DRY RUN MODE ==='))
                self.stdout.write(f"Would clean up {expired_count} expired sessions")
            else:
                self.stdout.write(self.style.SUCCESS('\n=== Starting Cleanup ==='))
                
                total_stats = {
                    'quotation_sessions_deleted': 0,
                    'responses_deleted': 0,
                    'django_sessions_deleted': 0,
                    'errors': []
                }
                
                # Process in batches
                processed = 0
                while processed < expired_count:
                    batch_stats = SessionManager.cleanup_expired_sessions(batch_size)
                    
                    # Accumulate stats
                    total_stats['quotation_sessions_deleted'] += batch_stats['quotation_sessions_deleted']
                    total_stats['responses_deleted'] += batch_stats['responses_deleted']
                    total_stats['django_sessions_deleted'] += batch_stats['django_sessions_deleted']
                    total_stats['errors'].extend(batch_stats['errors'])
                    
                    processed += batch_stats['quotation_sessions_deleted']
                    
                    if batch_stats['quotation_sessions_deleted'] == 0:
                        # No more sessions to process
                        break
                    
                    if options['verbosity'] >= 1:
                        self.stdout.write(
                            f"Processed batch: {batch_stats['quotation_sessions_deleted']} sessions, "
                            f"{batch_stats['responses_deleted']} responses"
                        )
                
                # Display final results
                self._display_cleanup_results(total_stats)
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR('\nCleanup interrupted by user.'))
        except Exception as e:
            raise CommandError(f"Cleanup failed: {e}")
    
    def _display_stats(self, stats):
        """Display session statistics in a formatted way."""
        qs = stats['quotation_sessions']
        rs = stats['responses']
        ds = stats['django_sessions']
        
        self.stdout.write(f"Quotation Sessions:")
        self.stdout.write(f"  Total: {qs['total']}")
        self.stdout.write(f"  Active: {qs['active']}")
        self.stdout.write(f"  Expired: {qs['expired']}")
        self.stdout.write(f"  Completed: {qs['completed']}")
        
        self.stdout.write(f"\nSurvey Responses:")
        self.stdout.write(f"  Total: {rs['total']}")
        
        self.stdout.write(f"\nDjango Sessions:")
        self.stdout.write(f"  Total: {ds['total']}")
        self.stdout.write(f"  Expired: {ds['expired']}")
        
        self.stdout.write(f"\nTimestamp: {stats['timestamp']}")
    
    def _display_cleanup_results(self, stats):
        """Display cleanup results."""
        self.stdout.write(self.style.SUCCESS('\n=== Cleanup Results ==='))
        
        self.stdout.write(f"Quotation sessions deleted: {stats['quotation_sessions_deleted']}")
        self.stdout.write(f"Survey responses deleted: {stats['responses_deleted']}")
        self.stdout.write(f"Django sessions deleted: {stats['django_sessions_deleted']}")
        
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f"\nErrors encountered: {len(stats['errors'])}"))
            for error in stats['errors']:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        else:
            self.stdout.write(self.style.SUCCESS("No errors encountered."))
        
        # Show updated statistics
        self.stdout.write(self.style.SUCCESS('\n=== Updated Statistics ==='))
        updated_stats = SessionManager.get_session_stats()
        if 'error' not in updated_stats:
            self._display_stats(updated_stats)