# System Integration Documentation

This document describes the system integration implementation for the Eswatini Policy System, which ensures consistency across policies, surveys, and comparison modules.

## Overview

The system integration module provides:

1. **Cross-module validation** - Ensures data consistency between policies, surveys, and comparisons
2. **Feature synchronization** - Keeps feature definitions synchronized across all modules
3. **System health monitoring** - Tracks system integrity and provides alerts
4. **Admin integration** - Provides admin interface tools for system management

## Components

### 1. Integration Manager (`policies/integration.py`)

#### FeatureSynchronizationManager
- Manages synchronization of features across policies, surveys, and comparisons
- Provides feature mappings between different model fields
- Validates feature consistency across modules
- Synchronizes survey questions with policy feature definitions

#### CrossModuleValidator
- Validates policy features for completeness and consistency
- Validates survey completeness based on insurance type
- Validates comparison result consistency
- Provides field-level validation with detailed error messages

#### SystemIntegrationManager
- Coordinates overall system integration tasks
- Performs comprehensive system health checks
- Manages feature synchronization across all insurance types
- Validates system integrity

### 2. Signal Handlers (`policies/signals.py`)

Automatic validation and monitoring through Django signals:

- **Policy Features Validation** - Validates features when saved
- **Survey Validation** - Validates surveys when saved
- **Comparison Result Validation** - Validates comparison results
- **Insurance Type Consistency** - Ensures consistent insurance types
- **System Health Monitoring** - Tracks system changes and health metrics

### 3. Management Commands

#### `check_system_integration`
```bash
python manage.py check_system_integration [--format json] [--fix] [--verbose]
```
- Performs comprehensive system integration check
- Shows validation results for all modules
- Can attempt automatic fixes with `--fix` flag

#### `synchronize_features`
```bash
python manage.py synchronize_features [--insurance-type health|funeral|all] [--dry-run]
```
- Synchronizes features across all modules
- Can target specific insurance types
- Supports dry-run mode to preview changes

#### `validate_policy_features`
```bash
python manage.py validate_policy_features [--fix-issues]
```
- Validates all policy features for consistency
- Can attempt to fix common issues

### 4. Admin Integration (`policies/admin_integration.py`)

Enhanced admin interface with integration features:

- **System Integration Dashboard** - Overview of system health
- **Validation Status Display** - Shows validation errors in admin lists
- **Integration Actions** - Bulk validation and synchronization actions
- **API Endpoints** - JSON API for integration status

### 5. Feature Mappings

The system uses standardized feature mappings to ensure consistency:

#### Health Insurance Features
- `annual_limit_per_member` ↔ `preferred_annual_limit`
- `monthly_household_income` ↔ `household_income`
- `in_hospital_benefit` ↔ `wants_in_hospital_benefit`
- `out_hospital_benefit` ↔ `wants_out_hospital_benefit`
- `chronic_medication_availability` ↔ `needs_chronic_medication`

#### Funeral Insurance Features
- `cover_amount` ↔ `preferred_cover_amount`
- `marital_status_requirement` ↔ `marital_status`
- `gender_requirement` ↔ `gender`
- `monthly_net_income` ↔ `net_income`

## Usage

### Basic System Check

```python
from policies.integration import SystemIntegrationManager

# Perform full system check
results = SystemIntegrationManager.perform_full_system_check()
print(f"System status: {results['overall_status']}")
```

### Feature Synchronization

```python
from policies.integration import FeatureSynchronizationManager

# Synchronize health features
results = FeatureSynchronizationManager.synchronize_survey_questions('HEALTH')
print(f"Created {results['created']} questions, updated {results['updated']}")
```

### Validation

```python
from policies.integration import CrossModuleValidator
from policies.models import BasePolicy

# Validate a specific policy
policy = BasePolicy.objects.get(id=1)
errors = CrossModuleValidator.validate_policy_features(policy)
if errors:
    print(f"Validation errors: {errors}")
else:
    print("Policy is valid")
```

### Admin Integration

Access the system integration dashboard at:
```
/admin/integration/
```

Or use the API endpoints:
```
/admin/integration/api/?action=status
/admin/integration/api/?action=health
/admin/integration/api/?action=validate_policy&policy_id=1
```

## Requirements Addressed

This implementation addresses the following requirements from the specification:

### Requirement 6.1-6.8 (System Integration)
- ✅ **6.1** - Health policy feature updates reflect in surveys and comparisons immediately
- ✅ **6.2** - Funeral policy feature updates reflect in surveys and comparisons immediately  
- ✅ **6.3** - Health survey questions maintain consistency with policy features
- ✅ **6.4** - Funeral survey questions maintain consistency with policy features
- ✅ **6.5** - Comparison criteria updates affect matching algorithms appropriately
- ✅ **6.6** - Consistent terminology across all interfaces within insurance categories
- ✅ **6.7** - Cross-module validation using same rules
- ✅ **6.8** - Consistent formatting across all interfaces within insurance categories

## Testing

Run the integration tests:

```bash
# Run all integration tests
python manage.py test policies.tests_integration

# Run system verification
python verify_integration.py

# Check system integration via management command
python manage.py check_system_integration --verbose
```

## Monitoring and Maintenance

### System Health Metrics

The system tracks:
- Policy changes per day
- Validation error counts
- Feature synchronization status
- Cache health status

### Automatic Monitoring

Signal handlers automatically:
- Validate data on save
- Cache validation errors
- Update health metrics
- Clean up related data on deletion

### Manual Maintenance

Regular maintenance tasks:
1. Run system integration checks weekly
2. Synchronize features after model changes
3. Clear validation caches after fixes
4. Monitor system health metrics

## Troubleshooting

### Common Issues

1. **Feature Consistency Errors**
   - Run `python manage.py synchronize_features`
   - Check model field definitions match feature mappings

2. **Validation Errors**
   - Check cached validation errors in admin
   - Run `python manage.py check_system_integration --fix`

3. **Performance Issues**
   - Clear caches: `python manage.py clear_cache`
   - Check database indexes on integration-related fields

### Error Messages

- **"Policy has no associated PolicyFeatures record"** - Create PolicyFeatures for the policy
- **"Insurance type mismatch"** - Ensure survey and policy have same insurance type
- **"Required feature missing"** - Fill in all required fields for the insurance type
- **"Feature synchronization needed"** - Run feature synchronization command

## Future Enhancements

Potential improvements:
1. Real-time validation using WebSockets
2. Advanced caching strategies
3. Integration with external validation services
4. Automated testing of integration points
5. Performance monitoring and optimization
6. Integration with CI/CD pipelines

## Support

For issues or questions about system integration:
1. Check the admin integration dashboard
2. Run system integration checks
3. Review validation error logs
4. Consult this documentation