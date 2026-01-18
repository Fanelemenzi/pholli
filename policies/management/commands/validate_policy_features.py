from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _
from policies.models import PolicyFeatures, BasePolicy
from policies.forms import PolicyFeaturesAdminForm


class Command(BaseCommand):
    help = 'Validate all policy features and report any issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix issues where possible',
        )
        parser.add_argument(
            '--insurance-type',
            type=str,
            choices=['HEALTH', 'FUNERAL'],
            help='Only validate features for specific insurance type',
        )
        parser.add_argument(
            '--policy-id',
            type=int,
            help='Only validate features for specific policy ID',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting policy features validation...')
        )
        
        # Build queryset based on options
        queryset = PolicyFeatures.objects.all()
        
        if options['insurance_type']:
            queryset = queryset.filter(insurance_type=options['insurance_type'])
            self.stdout.write(f"Filtering by insurance type: {options['insurance_type']}")
        
        if options['policy_id']:
            queryset = queryset.filter(policy_id=options['policy_id'])
            self.stdout.write(f"Filtering by policy ID: {options['policy_id']}")
        
        queryset = queryset.select_related('policy', 'policy__organization', 'policy__category')
        
        total_features = queryset.count()
        valid_features = 0
        invalid_features = 0
        fixed_features = 0
        
        self.stdout.write(f"Found {total_features} policy features to validate")
        
        for feature in queryset:
            self.stdout.write(f"\nValidating: {feature.policy.name} ({feature.get_insurance_type_display()})")
            
            errors = self._validate_feature(feature)
            
            if not errors:
                valid_features += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Valid")
                )
            else:
                invalid_features += 1
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {len(errors)} validation errors:")
                )
                
                for error in errors:
                    self.stdout.write(f"    - {error}")
                
                # Try to fix if requested
                if options['fix']:
                    fixed = self._fix_feature(feature, errors)
                    if fixed:
                        fixed_features += 1
                        self.stdout.write(
                            self.style.WARNING(f"  → Fixed automatically")
                        )
        
        # Summary
        self.stdout.write(f"\n" + "="*50)
        self.stdout.write(f"VALIDATION SUMMARY")
        self.stdout.write(f"="*50)
        self.stdout.write(f"Total features validated: {total_features}")
        self.stdout.write(
            self.style.SUCCESS(f"Valid features: {valid_features}")
        )
        self.stdout.write(
            self.style.ERROR(f"Invalid features: {invalid_features}")
        )
        
        if options['fix']:
            self.stdout.write(
                self.style.WARNING(f"Features fixed: {fixed_features}")
            )
        
        if invalid_features > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\nRun with --fix to automatically resolve fixable issues"
                )
            )
    
    def _validate_feature(self, feature):
        """Validate a single PolicyFeatures instance"""
        errors = []
        
        if feature.insurance_type == 'HEALTH':
            # Check that health features are filled and funeral features are empty
            health_features = [
                ('annual_limit_per_member', feature.annual_limit_per_member),
                ('monthly_household_income', feature.monthly_household_income),
                ('in_hospital_benefit', feature.in_hospital_benefit),
                ('out_hospital_benefit', feature.out_hospital_benefit),
                ('chronic_medication_availability', feature.chronic_medication_availability)
            ]
            
            # Check for missing required health features
            missing_health = [name for name, value in health_features if value is None]
            if missing_health:
                errors.append(f"Missing health features: {', '.join(missing_health)}")
            
            # Check for incorrectly filled funeral features
            funeral_features = [
                ('cover_amount', feature.cover_amount),
                ('marital_status_requirement', feature.marital_status_requirement),
                ('gender_requirement', feature.gender_requirement),
                ('monthly_net_income', feature.monthly_net_income)
            ]
            filled_funeral = [name for name, value in funeral_features if value is not None]
            if filled_funeral:
                errors.append(f"Funeral features should be empty: {', '.join(filled_funeral)}")
                
        elif feature.insurance_type == 'FUNERAL':
            # Check that funeral features are filled and health features are empty
            funeral_features = [
                ('cover_amount', feature.cover_amount),
                ('marital_status_requirement', feature.marital_status_requirement),
                ('gender_requirement', feature.gender_requirement),
                ('monthly_net_income', feature.monthly_net_income)
            ]
            
            # Check for missing required funeral features
            missing_funeral = [name for name, value in funeral_features if value is None]
            if missing_funeral:
                errors.append(f"Missing funeral features: {', '.join(missing_funeral)}")
            
            # Check for incorrectly filled health features
            health_features = [
                ('annual_limit_per_member', feature.annual_limit_per_member),
                ('monthly_household_income', feature.monthly_household_income),
                ('in_hospital_benefit', feature.in_hospital_benefit),
                ('out_hospital_benefit', feature.out_hospital_benefit),
                ('chronic_medication_availability', feature.chronic_medication_availability)
            ]
            filled_health = [name for name, value in health_features if value is not None]
            if filled_health:
                errors.append(f"Health features should be empty: {', '.join(filled_health)}")
        
        # Validate numeric values
        if feature.annual_limit_per_member is not None and feature.annual_limit_per_member <= 0:
            errors.append("Annual limit per member must be positive")
        if feature.monthly_household_income is not None and feature.monthly_household_income <= 0:
            errors.append("Monthly household income must be positive")
        if feature.cover_amount is not None and feature.cover_amount <= 0:
            errors.append("Cover amount must be positive")
        if feature.monthly_net_income is not None and feature.monthly_net_income <= 0:
            errors.append("Monthly net income must be positive")
            
        return errors
    
    def _fix_feature(self, feature, errors):
        """Attempt to automatically fix feature issues"""
        fixed = False
        
        # Fix: Clear irrelevant features based on insurance type
        if feature.insurance_type == 'HEALTH':
            if (feature.cover_amount is not None or 
                feature.marital_status_requirement is not None or
                feature.gender_requirement is not None or
                feature.monthly_net_income is not None):
                
                feature.cover_amount = None
                feature.marital_status_requirement = None
                feature.gender_requirement = None
                feature.monthly_net_income = None
                feature.save()
                fixed = True
                
        elif feature.insurance_type == 'FUNERAL':
            if (feature.annual_limit_per_member is not None or
                feature.monthly_household_income is not None or
                feature.in_hospital_benefit is not None or
                feature.out_hospital_benefit is not None or
                feature.chronic_medication_availability is not None):
                
                feature.annual_limit_per_member = None
                feature.monthly_household_income = None
                feature.in_hospital_benefit = None
                feature.out_hospital_benefit = None
                feature.chronic_medication_availability = None
                feature.save()
                fixed = True
        
        return fixed