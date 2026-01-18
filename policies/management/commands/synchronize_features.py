"""
Management command to synchronize features across all modules.
"""

from django.core.management.base import BaseCommand, CommandError
from policies.integration import SystemIntegrationManager, FeatureSynchronizationManager
import json


class Command(BaseCommand):
    help = 'Synchronize features across policies, surveys, and comparison modules'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--insurance-type',
            choices=['health', 'funeral', 'all'],
            default='all',
            help='Insurance type to synchronize (default: all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--format',
            choices=['text', 'json'],
            default='text',
            help='Output format (default: text)'
        )
    
    def handle(self, *args, **options):
        insurance_type = options['insurance_type']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting feature synchronization for {insurance_type}...')
        )
        
        try:
            if insurance_type == 'all':
                results = self._synchronize_all(dry_run)
            elif insurance_type == 'health':
                results = self._synchronize_type('HEALTH', dry_run)
            elif insurance_type == 'funeral':
                results = self._synchronize_type('FUNERAL', dry_run)
            
            if options['format'] == 'json':
                self.stdout.write(json.dumps(results, indent=2))
            else:
                self._display_results(results, dry_run)
        
        except Exception as e:
            raise CommandError(f'Feature synchronization failed: {str(e)}')
    
    def _synchronize_all(self, dry_run=False):
        """Synchronize features for all insurance types."""
        if dry_run:
            return {
                'health': self._check_synchronization_needed('HEALTH'),
                'funeral': self._check_synchronization_needed('FUNERAL'),
                'dry_run': True
            }
        else:
            return SystemIntegrationManager.synchronize_all_features()
    
    def _synchronize_type(self, insurance_type, dry_run=False):
        """Synchronize features for a specific insurance type."""
        if dry_run:
            return {
                insurance_type.lower(): self._check_synchronization_needed(insurance_type),
                'dry_run': True
            }
        else:
            return {
                insurance_type.lower(): FeatureSynchronizationManager.synchronize_survey_questions(insurance_type)
            }
    
    def _check_synchronization_needed(self, insurance_type):
        """Check what synchronization would be needed without making changes."""
        from simple_surveys.models import SimpleSurveyQuestion
        
        feature_mapping = FeatureSynchronizationManager.get_feature_mapping(insurance_type)
        category = insurance_type.lower()
        
        results = {
            'would_create': 0,
            'would_update': 0,
            'existing_questions': 0,
            'features_to_sync': []
        }
        
        existing_questions = SimpleSurveyQuestion.objects.filter(category=category)
        existing_field_names = set(existing_questions.values_list('field_name', flat=True))
        results['existing_questions'] = existing_questions.count()
        
        for feature_code, mapping in feature_mapping.items():
            field_name = mapping['survey_field']
            
            if field_name not in existing_field_names:
                results['would_create'] += 1
                results['features_to_sync'].append({
                    'action': 'create',
                    'field_name': field_name,
                    'display_name': mapping['display_name']
                })
            else:
                # Check if update would be needed
                question = existing_questions.get(field_name=field_name)
                if question.validation_rules != mapping['validation_rules']:
                    results['would_update'] += 1
                    results['features_to_sync'].append({
                        'action': 'update',
                        'field_name': field_name,
                        'display_name': mapping['display_name']
                    })
        
        return results
    
    def _display_results(self, results, dry_run=False):
        """Display synchronization results in text format."""
        
        if dry_run:
            self.stdout.write('\n--- Synchronization Preview ---')
            
            for insurance_type, type_results in results.items():
                if insurance_type == 'dry_run':
                    continue
                
                self.stdout.write(f'\n{insurance_type.title()} Insurance:')
                
                if type_results.get('would_create', 0) > 0:
                    self.stdout.write(f'  Would create: {type_results["would_create"]} survey questions')
                
                if type_results.get('would_update', 0) > 0:
                    self.stdout.write(f'  Would update: {type_results["would_update"]} survey questions')
                
                if type_results.get('existing_questions', 0) > 0:
                    self.stdout.write(f'  Existing questions: {type_results["existing_questions"]}')
                
                # Show specific features that would be synced
                features_to_sync = type_results.get('features_to_sync', [])
                if features_to_sync:
                    self.stdout.write('  Features to synchronize:')
                    for feature in features_to_sync:
                        action = feature['action']
                        name = feature['display_name']
                        field = feature['field_name']
                        self.stdout.write(f'    - {action.title()}: {name} ({field})')
        
        else:
            self.stdout.write('\n--- Synchronization Results ---')
            
            overall_success = results.get('overall_success', False)
            
            if overall_success:
                self.stdout.write(
                    self.style.SUCCESS('✓ Feature synchronization completed successfully')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Feature synchronization completed with errors')
                )
            
            # Show detailed results for each insurance type
            for insurance_type in ['health', 'funeral']:
                if insurance_type in results:
                    type_results = results[insurance_type]
                    
                    self.stdout.write(f'\n{insurance_type.title()} Insurance:')
                    
                    created = type_results.get('created', 0)
                    updated = type_results.get('updated', 0)
                    errors = type_results.get('errors', [])
                    
                    if created > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Created: {created} survey questions')
                        )
                    
                    if updated > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Updated: {updated} survey questions')
                        )
                    
                    if errors:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ Errors: {len(errors)}')
                        )
                        for error in errors:
                            self.stdout.write(f'    - {error}')
                    
                    if created == 0 and updated == 0 and not errors:
                        self.stdout.write('  - No changes needed')
            
            # Show system error if present
            if 'system_error' in results:
                self.stdout.write(
                    self.style.ERROR(f'\nSystem Error: {results["system_error"]}')
                )