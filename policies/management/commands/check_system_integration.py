"""
Management command to check system integration and consistency.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from policies.integration import SystemIntegrationManager
import json


class Command(BaseCommand):
    help = 'Check system integration and consistency across all modules'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix issues found during check'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting system integration check...')
        )
        
        try:
            # Perform system check
            results = SystemIntegrationManager.perform_full_system_check()
            
            if options['format'] == 'json':
                self.stdout.write(json.dumps(results, indent=2))
                return
            
            # Display results in text format
            self._display_text_results(results, options['verbose'])
            
            # Attempt fixes if requested
            if options['fix'] and results['synchronization_needed']:
                self.stdout.write(
                    self.style.WARNING('\nAttempting to fix issues...')
                )
                self._attempt_fixes(results)
        
        except Exception as e:
            raise CommandError(f'System integration check failed: {str(e)}')
    
    def _display_text_results(self, results, verbose=False):
        """Display results in human-readable text format."""
        
        # Overall status
        status = results['overall_status']
        if status == 'healthy':
            self.stdout.write(
                self.style.SUCCESS(f'\n✓ System Status: HEALTHY')
            )
        elif status == 'warning':
            self.stdout.write(
                self.style.WARNING(f'\n⚠ System Status: WARNING')
            )
        elif status == 'critical':
            self.stdout.write(
                self.style.ERROR(f'\n✗ System Status: CRITICAL')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'\n✗ System Status: ERROR')
            )
        
        # Feature consistency
        self.stdout.write('\n--- Feature Consistency ---')
        health_errors = results['feature_consistency']['health']
        funeral_errors = results['feature_consistency']['funeral']
        
        if not health_errors:
            self.stdout.write(self.style.SUCCESS('✓ Health features: Consistent'))
        else:
            self.stdout.write(self.style.ERROR('✗ Health features: Issues found'))
            if verbose:
                for error in health_errors:
                    self.stdout.write(f'  - {error}')
        
        if not funeral_errors:
            self.stdout.write(self.style.SUCCESS('✓ Funeral features: Consistent'))
        else:
            self.stdout.write(self.style.ERROR('✗ Funeral features: Issues found'))
            if verbose:
                for error in funeral_errors:
                    self.stdout.write(f'  - {error}')
        
        # Policy validation
        self.stdout.write('\n--- Policy Validation ---')
        health_policies = results['health_policies']
        funeral_policies = results['funeral_policies']
        
        self.stdout.write(
            f'Health Policies: {health_policies["valid"]}/{health_policies["total"]} valid'
        )
        if health_policies['errors'] and verbose:
            for error in health_policies['errors'][:5]:  # Show first 5 errors
                self.stdout.write(f'  - {error}')
            if len(health_policies['errors']) > 5:
                self.stdout.write(f'  ... and {len(health_policies["errors"]) - 5} more')
        
        self.stdout.write(
            f'Funeral Policies: {funeral_policies["valid"]}/{funeral_policies["total"]} valid'
        )
        if funeral_policies['errors'] and verbose:
            for error in funeral_policies['errors'][:5]:  # Show first 5 errors
                self.stdout.write(f'  - {error}')
            if len(funeral_policies['errors']) > 5:
                self.stdout.write(f'  ... and {len(funeral_policies["errors"]) - 5} more')
        
        # Survey validation
        self.stdout.write('\n--- Survey Validation ---')
        health_surveys = results['health_surveys']
        funeral_surveys = results['funeral_surveys']
        
        self.stdout.write(
            f'Health Surveys: {health_surveys["valid"]}/{health_surveys["total"]} valid'
        )
        if health_surveys['errors'] and verbose:
            for error in health_surveys['errors'][:5]:
                self.stdout.write(f'  - {error}')
            if len(health_surveys['errors']) > 5:
                self.stdout.write(f'  ... and {len(health_surveys["errors"]) - 5} more')
        
        self.stdout.write(
            f'Funeral Surveys: {funeral_surveys["valid"]}/{funeral_surveys["total"]} valid'
        )
        if funeral_surveys['errors'] and verbose:
            for error in funeral_surveys['errors'][:5]:
                self.stdout.write(f'  - {error}')
            if len(funeral_surveys['errors']) > 5:
                self.stdout.write(f'  ... and {len(funeral_surveys["errors"]) - 5} more')
        
        # Comparison results validation
        self.stdout.write('\n--- Comparison Results Validation ---')
        comparison_results = results['comparison_results']
        
        self.stdout.write(
            f'Comparison Results: {comparison_results["valid"]}/{comparison_results["total"]} valid'
        )
        if comparison_results['errors'] and verbose:
            for error in comparison_results['errors'][:5]:
                self.stdout.write(f'  - {error}')
            if len(comparison_results['errors']) > 5:
                self.stdout.write(f'  ... and {len(comparison_results["errors"]) - 5} more')
        
        # Synchronization status
        if results['synchronization_needed']:
            self.stdout.write(
                self.style.WARNING('\n⚠ Synchronization needed - run with --fix to attempt repairs')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✓ No synchronization needed')
            )
    
    def _attempt_fixes(self, results):
        """Attempt to fix issues found during the check."""
        
        try:
            # Attempt feature synchronization
            sync_results = SystemIntegrationManager.synchronize_all_features()
            
            if sync_results['overall_success']:
                self.stdout.write(
                    self.style.SUCCESS('✓ Feature synchronization completed successfully')
                )
                
                # Show sync details
                health_sync = sync_results['health_sync']
                funeral_sync = sync_results['funeral_sync']
                
                if health_sync.get('created', 0) > 0:
                    self.stdout.write(f'  - Created {health_sync["created"]} health survey questions')
                
                if health_sync.get('updated', 0) > 0:
                    self.stdout.write(f'  - Updated {health_sync["updated"]} health survey questions')
                
                if funeral_sync.get('created', 0) > 0:
                    self.stdout.write(f'  - Created {funeral_sync["created"]} funeral survey questions')
                
                if funeral_sync.get('updated', 0) > 0:
                    self.stdout.write(f'  - Updated {funeral_sync["updated"]} funeral survey questions')
            
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Feature synchronization failed')
                )
                
                # Show sync errors
                health_errors = sync_results['health_sync'].get('errors', [])
                funeral_errors = sync_results['funeral_sync'].get('errors', [])
                
                for error in health_errors + funeral_errors:
                    self.stdout.write(f'  - {error}')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Fix attempt failed: {str(e)}')
            )