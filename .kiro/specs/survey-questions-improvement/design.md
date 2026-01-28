# Design Document

## Overview

This design outlines the improvements to the survey question system to replace binary yes/no questions with more nuanced options for in-hospital and out-of-hospital benefits, add range-based selections for annual limits, and remove unnecessary medical aid status questions. The solution will enhance the existing Django-based survey system while maintaining compatibility with the current comparison engine.

## Architecture

The improvements will be implemented across multiple layers of the existing Django application:

### Data Layer
- **SimpleSurveyQuestion Model**: Update choices field to support new benefit level options
- **SimpleSurvey Model**: Remove `currently_on_medical_aid` field and update benefit fields
- **SurveyQuestion Model**: Add new questions with appropriate choice configurations

### Form Layer
- **SimpleSurveyForm**: Update form fields and validation logic
- **SurveyResponseForm**: Handle new choice types and range selections

### Comparison Layer
- **Comparison Engine**: Update matching logic to work with benefit levels and ranges
- **Feature Matching**: Modify algorithms to score policies based on coverage levels

### Template Layer
- **Survey Templates**: Update UI to display new question types with appropriate styling
- **JavaScript**: Add client-side logic for range selection guidance

## Components and Interfaces

### 1. Question Configuration Component

**Purpose**: Manage the new question types and their options

**Interface**:
```python
class BenefitLevelQuestion:
    question_type: str = "CHOICE"
    choices: List[Dict] = [
        {"value": "no_cover", "text": "No hospital cover", "description": "..."},
        {"value": "basic", "text": "Basic hospital care", "description": "..."},
        # ... additional levels
    ]
    
class RangeQuestion:
    question_type: str = "CHOICE" 
    choices: List[Dict] = [
        {"value": "500k-1m", "text": "R500,000-R1,000,000", "tooltip": "..."},
        # ... additional ranges
    ]
```

### 2. Response Processing Component

**Purpose**: Convert user responses to comparison criteria

**Interface**:
```python
class ResponseProcessor:
    def process_benefit_level(self, response_value: str) -> Dict:
        """Convert benefit level to comparison weights"""
        
    def process_annual_limit_range(self, response_value: str) -> Dict:
        """Convert range selection to min/max values for matching"""
```

### 3. Comparison Matching Component

**Purpose**: Match policies based on new question types

**Interface**:
```python
class BenefitMatcher:
    def match_hospital_benefits(self, user_level: str, policy_benefits: Dict) -> float:
        """Score policy based on hospital benefit level match"""
        
    def match_annual_limits(self, user_range: Dict, policy_limits: Dict) -> float:
        """Score policy based on annual limit range compatibility"""
```

## Data Models

### Updated SimpleSurvey Model

```python
class SimpleSurvey(models.Model):
    # Remove this field entirely
    # currently_on_medical_aid = models.BooleanField(...)
    
    # Update these fields to use choice-based selections
    in_hospital_benefit_level = models.CharField(
        max_length=50,
        choices=[
            ('no_cover', 'No hospital cover'),
            ('basic', 'Basic hospital care'),
            ('moderate', 'Moderate hospital care'),
            ('extensive', 'Extensive hospital care'),
            ('comprehensive', 'Comprehensive hospital care'),
        ],
        null=True,
        blank=True
    )
    
    out_hospital_benefit_level = models.CharField(
        max_length=50,
        choices=[
            ('no_cover', 'No out-of-hospital cover'),
            ('basic_visits', 'Basic clinic visits'),
            ('routine_care', 'Routine medical care'),
            ('extended_care', 'Extended medical care'),
            ('comprehensive_care', 'Comprehensive day-to-day care'),
        ],
        null=True,
        blank=True
    )
    
    annual_limit_family_range = models.CharField(
        max_length=50,
        choices=[
            ('10k-50k', 'R10,000-R50,000'),
            ('50k-100k', 'R50,001-R100,000'),
            ('100k-250k', 'R100,001-R250,000'),
            ('250k-500k', 'R250,001-R500,000'),
            ('500k-1m', 'R500,001-R1,000,000'),
            ('1m-2m', 'R1,000,001-R2,000,000'),
            ('2m-5m', 'R2,000,001-R5,000,000'),
            ('5m-plus', 'R5,000,001+'),
            ('unlimited', 'Unlimited coverage preferred'),
        ],
        null=True,
        blank=True
    )
    
    annual_limit_member_range = models.CharField(
        max_length=50,
        choices=[
            ('10k-25k', 'R10,000-R25,000'),
            ('25k-50k', 'R25,001-R50,000'),
            ('50k-100k', 'R50,001-R100,000'),
            ('100k-200k', 'R100,001-R200,000'),
            ('200k-500k', 'R200,001-R500,000'),
            ('500k-1m', 'R500,001-R1,000,000'),
            ('1m-2m', 'R1,000,001-R2,000,000'),
            ('2m-plus', 'R2,000,001+'),
            ('unlimited', 'Unlimited coverage preferred'),
        ],
        null=True,
        blank=True
    )
```

### New Question Configurations

```python
HOSPITAL_BENEFIT_QUESTIONS = [
    {
        'field_name': 'in_hospital_benefit_level',
        'question_text': 'What level of in-hospital cover do you need?',
        'input_type': 'radio',
        'choices': [
            {'value': 'no_cover', 'text': 'No hospital cover', 'description': 'I do not need cover for hospital admission'},
            {'value': 'basic', 'text': 'Basic hospital care', 'description': 'Covers admission and standard hospital treatment'},
            {'value': 'moderate', 'text': 'Moderate hospital care', 'description': 'Covers admission, procedures, and specialist treatment'},
            {'value': 'extensive', 'text': 'Extensive hospital care', 'description': 'Covers most hospital needs, including major procedures'},
            {'value': 'comprehensive', 'text': 'Comprehensive hospital care', 'description': 'Covers all hospital-related treatment and services'},
        ]
    }
]
```

## Error Handling

### Validation Strategy
- **Form Level**: Validate that benefit level selections are from allowed choices
- **Model Level**: Ensure range selections have valid format and values
- **Migration Level**: Handle existing binary responses during data migration

### Error Recovery
- **Invalid Responses**: Provide clear error messages and suggest valid alternatives
- **Migration Failures**: Implement rollback procedures for data migration issues
- **Comparison Failures**: Graceful degradation when new question types can't be processed

### Logging
- **Response Changes**: Log when users change from binary to level-based responses
- **Comparison Impact**: Track how new question types affect policy matching accuracy
- **Performance**: Monitor query performance with new choice-based filtering

## Testing Strategy

### Unit Tests
- **Model Validation**: Test new field choices and validation rules
- **Form Processing**: Verify form handling of new question types
- **Response Migration**: Test conversion of existing binary responses

### Integration Tests
- **Survey Flow**: End-to-end testing of updated survey experience
- **Comparison Engine**: Verify policy matching works with new response types
- **Data Migration**: Test migration scripts with realistic data sets

### User Acceptance Tests
- **Survey Completion**: Users can complete surveys with new question types
- **Policy Matching**: Verify that policy recommendations improve with more nuanced responses
- **Performance**: Ensure survey completion time doesn't increase significantly

### A/B Testing
- **Question Effectiveness**: Compare completion rates between old and new question formats
- **Matching Accuracy**: Measure improvement in user satisfaction with policy recommendations
- **User Experience**: Track user feedback on new question types

## Migration Strategy

### Phase 1: Database Schema Updates
1. Add new fields to SimpleSurvey model
2. Create migration to add new choice fields
3. Preserve existing binary fields temporarily for rollback

### Phase 2: Data Migration
1. Convert existing binary responses to appropriate benefit levels:
   - `wants_in_hospital_benefit=True` → `in_hospital_benefit_level='basic'`
   - `wants_in_hospital_benefit=False` → `in_hospital_benefit_level='no_cover'`
2. Remove `currently_on_medical_aid` data
3. Set default ranges for existing annual limit values

### Phase 3: Form and Template Updates
1. Update SimpleSurveyForm to use new fields
2. Modify survey templates to display new question types
3. Add JavaScript for range selection guidance

### Phase 4: Comparison Engine Updates
1. Update matching algorithms to handle benefit levels
2. Modify scoring logic for range-based annual limits
3. Remove medical aid status from comparison criteria

### Phase 5: Cleanup
1. Remove old binary fields after successful migration
2. Update documentation and admin interfaces
3. Deploy monitoring for new question performance

## Performance Considerations

### Database Optimization
- **Indexing**: Add indexes on new choice fields for faster filtering
- **Query Optimization**: Ensure comparison queries perform well with choice-based filtering
- **Data Size**: Monitor impact of longer choice values on storage

### Caching Strategy
- **Question Choices**: Cache question choice configurations
- **Comparison Results**: Update caching keys to include new question types
- **User Sessions**: Optimize session storage for new response formats