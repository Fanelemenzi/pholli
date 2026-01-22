# Design Document

## Overview

This design document outlines the enhancements to the existing policy management system to support the upgrades specified in upgrade2.md. The system will be modified to include new policy features (annual family limits, medical aid status, ambulance coverage), a new rewards system, enhanced coverage details, and improved UI for viewing policy benefits.

The design builds upon the existing Django-based architecture with models for BasePolicy, PolicyFeatures, AdditionalFeatures, and SimpleSurvey, extending them with new fields and functionality while maintaining backward compatibility.

## Architecture

### Current System Components
- **BasePolicy**: Core policy model with basic information
- **PolicyFeatures**: Feature-specific data for health and funeral policies
- **AdditionalFeatures**: Extra benefits and features for policies
- **SimpleSurvey**: Survey system for collecting user preferences
- **Admin Interface**: Django admin for policy management
- **Comparison Engine**: Policy matching and ranking system

### Enhanced Components
- **Enhanced PolicyFeatures**: Updated with new fields for annual family limits, medical aid status, and ambulance coverage
- **New Rewards Model**: Standalone model for managing policy rewards and incentives
- **Enhanced AdditionalFeatures**: Updated with coverage details field
- **Updated Admin Interface**: Forms and displays updated to include new fields
- **Enhanced Survey System**: Updated to collect new preference data
- **Improved Results Templates**: Enhanced UI for viewing policy benefits

## Components and Interfaces

### 1. Enhanced PolicyFeatures Model

**Purpose**: Extend the existing PolicyFeatures model with new fields while maintaining existing functionality.

**Changes**:
- Add `annual_limit_per_family` field (DecimalField)
- Remove `net_monthly_income` field (deprecated)
- Add `currently_on_medical_aid` field (BooleanField)
- Add `ambulance_coverage` field (BooleanField)

**Field Specifications**:
```python
# New fields to add
annual_limit_per_family = models.DecimalField(
    max_digits=12, 
    decimal_places=2, 
    null=True, 
    blank=True,
    help_text="Annual limit per family (replaces per member limit)"
)

currently_on_medical_aid = models.BooleanField(
    null=True, 
    blank=True,
    help_text="Whether the applicant is currently on medical aid"
)

ambulance_coverage = models.BooleanField(
    null=True, 
    blank=True,
    help_text="Whether ambulance coverage is included"
)

# Field to remove
# net_monthly_income - will be handled via migration
```

**Migration Strategy**:
- Create migration to add new fields
- Create migration to remove `net_monthly_income` field
- Update existing data handling methods

### 2. New Rewards Model

**Purpose**: Create a new model to manage rewards and incentives associated with policies.

**Model Structure**:
```python
class Rewards(models.Model):
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='rewards'
    )
    
    title = models.CharField(
        max_length=255,
        help_text="Reward title (e.g., 'Cashback Program', 'Loyalty Discount')"
    )
    
    description = models.TextField(
        help_text="Detailed description of the reward"
    )
    
    reward_type = models.CharField(
        max_length=50,
        choices=[
            ('CASHBACK', 'Cashback'),
            ('DISCOUNT', 'Discount'),
            ('BENEFIT', 'Additional Benefit'),
            ('POINTS', 'Loyalty Points'),
            ('OTHER', 'Other'),
        ],
        help_text="Type of reward offered"
    )
    
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monetary value of reward (if applicable)"
    )
    
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage value of reward (if applicable)"
    )
    
    eligibility_criteria = models.TextField(
        blank=True,
        help_text="Criteria for earning this reward"
    )
    
    terms_and_conditions = models.TextField(
        blank=True,
        help_text="Terms and conditions for the reward"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this reward is currently active"
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for displaying rewards"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 3. Enhanced AdditionalFeatures Model

**Purpose**: Add coverage details field to provide comprehensive coverage descriptions.

**Changes**:
```python
# New field to add
coverage_details = models.TextField(
    blank=True,
    help_text="Detailed coverage information and descriptions"
)
```

### 4. Updated SimpleSurvey Model

**Purpose**: Update survey model to collect preferences for new policy features.

**Changes**:
```python
# New fields to add for health policies
preferred_annual_limit_per_family = models.DecimalField(
    max_digits=12,
    decimal_places=2,
    null=True,
    blank=True,
    help_text="Preferred annual limit per family"
)

currently_on_medical_aid = models.BooleanField(
    null=True,
    blank=True,
    help_text="Are you currently on medical aid?"
)

wants_ambulance_coverage = models.BooleanField(
    null=True,
    blank=True,
    help_text="Do you want ambulance coverage?"
)

# Field to remove
# net_monthly_income - will be handled via migration
```

### 5. Admin Interface Updates

**Purpose**: Update Django admin to support new fields and models.

**Components**:
- **PolicyFeaturesAdmin**: Add new fields to fieldsets and forms
- **RewardsAdmin**: New admin interface for rewards management
- **AdditionalFeaturesAdmin**: Add coverage_details field
- **SimpleSurveyAdmin**: Update to include new survey fields

**Admin Configuration**:
```python
# PolicyFeatures admin updates
fieldsets = [
    ('Basic Information', {
        'fields': ['policy', 'insurance_type']
    }),
    ('Health Policy Features', {
        'fields': [
            'annual_limit_per_family',  # Updated field
            'monthly_household_income',
            'currently_on_medical_aid',  # New field
            'ambulance_coverage',        # New field
            'in_hospital_benefit',
            'out_hospital_benefit',
            'chronic_medication_availability',
        ],
        'classes': ['collapse'],
    }),
    # ... other fieldsets
]

# New Rewards admin
class RewardsAdmin(admin.ModelAdmin):
    list_display = ['title', 'policy', 'reward_type', 'value', 'is_active']
    list_filter = ['reward_type', 'is_active', 'policy__category']
    search_fields = ['title', 'description', 'policy__name']
    ordering = ['policy', 'display_order']
```

### 6. Survey System Updates

**Purpose**: Update survey questions and processing to handle new fields.

**Components**:
- **SimpleSurveyQuestion**: Add new questions for enhanced features
- **Survey Forms**: Update form fields and validation
- **Response Processing**: Update matching algorithms to use new fields

**New Survey Questions**:
```python
# Health insurance questions to add/update
{
    'category': 'health',
    'question_text': 'What is your preferred annual limit per family?',
    'field_name': 'preferred_annual_limit_per_family',
    'input_type': 'number',
    'is_required': True,
}
{
    'category': 'health',
    'question_text': 'Are you currently on medical aid?',
    'field_name': 'currently_on_medical_aid',
    'input_type': 'radio',
    'choices': [('yes', 'Yes'), ('no', 'No')],
    'is_required': True,
}
{
    'category': 'health',
    'question_text': 'Do you want ambulance coverage?',
    'field_name': 'wants_ambulance_coverage',
    'input_type': 'radio',
    'choices': [('yes', 'Yes'), ('no', 'No')],
    'is_required': True,
}
```

### 7. Enhanced Results Templates

**Purpose**: Add "View Benefits Covered" functionality to policy comparison results.

**Components**:
- **Policy Card Template**: Add "View Benefits" button
- **Benefits Modal/Detail View**: Display comprehensive benefit information
- **Benefits Data Aggregation**: Combine data from multiple sources

**Template Structure**:
```html
<!-- Policy card with benefits button -->
<div class="policy-card">
    <!-- Existing policy information -->
    <div class="policy-actions">
        <button class="btn btn-info view-benefits" 
                data-policy-id="{{ policy.id }}">
            View Benefits Covered
        </button>
    </div>
</div>

<!-- Benefits modal/detail view -->
<div class="benefits-modal" id="benefits-{{ policy.id }}">
    <div class="benefits-content">
        <h3>Benefits Covered - {{ policy.name }}</h3>
        
        <div class="benefits-section">
            <h4>Core Features</h4>
            <!-- Display PolicyFeatures data -->
        </div>
        
        <div class="benefits-section">
            <h4>Additional Features</h4>
            <!-- Display AdditionalFeatures with coverage_details -->
        </div>
        
        <div class="benefits-section">
            <h4>Available Rewards</h4>
            <!-- Display Rewards data -->
        </div>
    </div>
</div>
```

## Data Models

### Updated PolicyFeatures Model
```python
class PolicyFeatures(models.Model):
    # Existing fields remain unchanged
    policy = models.OneToOneField(BasePolicy, ...)
    insurance_type = models.CharField(...)
    
    # Health Policy Features - Updated
    annual_limit_per_family = models.DecimalField(...)  # New field
    monthly_household_income = models.DecimalField(...)  # Existing
    currently_on_medical_aid = models.BooleanField(...)  # New field
    ambulance_coverage = models.BooleanField(...)        # New field
    in_hospital_benefit = models.BooleanField(...)       # Existing
    out_hospital_benefit = models.BooleanField(...)      # Existing
    chronic_medication_availability = models.BooleanField(...)  # Existing
    
    # Funeral Policy Features - Unchanged
    cover_amount = models.DecimalField(...)
    marital_status_requirement = models.CharField(...)
    gender_requirement = models.CharField(...)
    # net_monthly_income field removed
    
    # Metadata - Unchanged
    created_at = models.DateTimeField(...)
    updated_at = models.DateTimeField(...)
```

### New Rewards Model
```python
class Rewards(models.Model):
    policy = models.ForeignKey(BasePolicy, ...)
    title = models.CharField(...)
    description = models.TextField(...)
    reward_type = models.CharField(...)
    value = models.DecimalField(...)
    percentage = models.DecimalField(...)
    eligibility_criteria = models.TextField(...)
    terms_and_conditions = models.TextField(...)
    is_active = models.BooleanField(...)
    display_order = models.PositiveIntegerField(...)
    created_at = models.DateTimeField(...)
    updated_at = models.DateTimeField(...)
```

### Updated AdditionalFeatures Model
```python
class AdditionalFeatures(models.Model):
    # Existing fields remain unchanged
    policy = models.ForeignKey(BasePolicy, ...)
    title = models.CharField(...)
    description = models.TextField(...)
    icon = models.CharField(...)
    is_highlighted = models.BooleanField(...)
    display_order = models.PositiveIntegerField(...)
    
    # New field
    coverage_details = models.TextField(...)  # New field
    
    # Metadata - Unchanged
    created_at = models.DateTimeField(...)
```

## Error Handling

### Migration Safety
- **Backward Compatibility**: Ensure existing data is preserved during field removal
- **Default Values**: Provide appropriate defaults for new fields
- **Data Validation**: Validate existing data against new constraints

### Form Validation
- **Required Fields**: Ensure new required fields are properly validated
- **Data Types**: Validate decimal fields for proper formatting
- **Business Logic**: Ensure medical aid and ambulance coverage logic is consistent

### API Error Handling
- **Missing Data**: Handle cases where new fields may not be populated
- **Legacy Support**: Maintain compatibility with existing API consumers
- **Graceful Degradation**: Ensure system works even if new features are not fully configured

## Testing Strategy

### Unit Tests
- **Model Tests**: Test new fields, validation, and relationships
- **Admin Tests**: Verify admin interface functionality for new fields
- **Survey Tests**: Test updated survey logic and validation
- **Migration Tests**: Ensure migrations work correctly

### Integration Tests
- **End-to-End Survey Flow**: Test complete survey process with new fields
- **Policy Matching**: Test matching algorithms with enhanced features
- **Benefits Display**: Test benefits viewing functionality
- **Admin Workflow**: Test complete admin workflow for managing enhanced features

### Data Migration Tests
- **Field Addition**: Test adding new fields to existing records
- **Field Removal**: Test safe removal of deprecated fields
- **Data Integrity**: Ensure no data loss during migrations

### Performance Tests
- **Query Performance**: Ensure new fields don't impact query performance
- **Template Rendering**: Test benefits modal performance with large datasets
- **Admin Interface**: Test admin performance with enhanced forms

### User Acceptance Tests
- **Survey Experience**: Test user experience with new survey questions
- **Benefits Viewing**: Test benefits viewing functionality from user perspective
- **Admin Usability**: Test admin interface usability with new features
- **Mobile Compatibility**: Ensure new features work on mobile devices