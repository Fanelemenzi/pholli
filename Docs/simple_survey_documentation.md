# Simple Survey System Documentation

## Overview

The Simple Survey System is a streamlined insurance quotation platform that collects user preferences through dynamic surveys and generates personalized policy recommendations. The system supports two insurance categories: **Health Insurance** and **Funeral Insurance**.

## System Architecture

### Core Components

1. **Survey Engine** (`simple_surveys/engine.py`) - Handles question delivery and response processing
2. **Models** (`simple_surveys/models.py`) - Data structure for questions, responses, and sessions
3. **Views** (`simple_surveys/views.py`) - Web interface and AJAX endpoints
4. **Comparison Adapter** (`simple_surveys/comparison_adapter.py`) - Converts responses to quotation criteria
5. **Session Manager** (`simple_surveys/session_manager.py`) - Manages user sessions and data cleanup

### Data Flow

```
User Input → Survey Questions → Response Validation → Criteria Processing → Policy Matching → Quotation Results
```

## Question System

### Question Types and Rendering

The system supports 5 input types for collecting user responses:

#### 1. Text Input (`input_type: "text"`)
```html
<input type="text" class="form-control" name="field_name" required>
```
- Used for: Open-ended text responses
- Validation: Max length, pattern matching

#### 2. Number Input (`input_type: "number"`)
```html
<input type="number" class="form-control" name="field_name" min="18" max="80" required>
```
- Used for: Age, family size, budget amounts
- Validation: Min/max values, numeric format
- Examples: Age (18-80), Budget (R200-R5000)

#### 3. Dropdown Select (`input_type: "select"`)
```html
<select class="form-select" name="field_name" required>
    <option value="">Select an option...</option>
    <option value="hhohho">Hhohho</option>
    <option value="manzini">Manzini</option>
</select>
```
- Used for: Location selection, single-choice options
- Validation: Must match available choices

#### 4. Radio Buttons (`input_type: "radio"`)
```html
<div class="form-check">
    <input type="radio" name="field_name" value="excellent" required>
    <label>Excellent</label>
</div>
```
- Used for: Health status, coverage priorities, service preferences
- Validation: Single selection required

#### 5. Checkboxes (`input_type: "checkbox"`)
```html
<div class="form-check">
    <input type="checkbox" name="field_name" value="diabetes">
    <label>Diabetes</label>
</div>
```
- Used for: Multiple selections (chronic conditions)
- Validation: Array of selected values

### Question Configuration

Each question is defined with the following structure:

```python
{
    "category": "health|funeral",           # Insurance category
    "question_text": "What is your age?",   # Display text
    "field_name": "age",                    # Database field name
    "input_type": "number",                 # Input control type
    "choices": [],                          # Options for select/radio/checkbox
    "is_required": true,                    # Validation requirement
    "display_order": 1,                     # Question sequence
    "validation_rules": {                   # Input validation
        "min": 18,
        "max": 80
    }
}
```

## Health Insurance Questions

### Question Flow and Weighting

1. **Age** (`age`) - Weight: 15%
   - Input: Number (18-80)
   - Impact: Determines policy eligibility and premium calculations

2. **Location** (`location`) - Weight: 10%
   - Input: Select dropdown (9 provinces)
   - Impact: Regional policy availability and pricing

3. **Family Size** (`family_size`) - Weight: 20%
   - Input: Number (1-10 members)
   - Impact: Premium scaling and family coverage options

4. **Health Status** (`health_status`) - Weight: 25%
   - Input: Radio buttons (Excellent/Good/Fair/Poor)
   - Impact: Risk assessment and policy eligibility

5. **Chronic Conditions** (`chronic_conditions`) - Weight: 20%
   - Input: Checkboxes (Diabetes, Hypertension, Heart Disease, Asthma, None)
   - Impact: Specialized coverage requirements and premium adjustments

6. **Coverage Priority** (`coverage_priority`) - Weight: 25%
   - Input: Radio buttons (Hospital/Day-to-day/Comprehensive)
   - Impact: Policy type matching and benefit prioritization

7. **Monthly Budget** (`monthly_budget`) - Weight: 30%
   - Input: Number (R200-R5000)
   - Impact: Primary filter for policy recommendations

8. **Preferred Deductible** (`preferred_deductible`) - Weight: 10%
   - Input: Radio buttons (None/R1000/R2500/R5000)
   - Impact: Cost-sharing preference and premium adjustment

### Health Insurance Weighting Algorithm

```python
default_weights = {
    'base_premium': 30,        # Budget constraint (highest priority)
    'coverage_priority': 25,   # Coverage type preference
    'health_status': 20,       # Risk assessment
    'chronic_conditions': 15,  # Specialized needs
    'deductible_amount': 10    # Cost-sharing preference
}
```

## Funeral Insurance Questions

### Question Flow and Weighting

1. **Age** (`age`) - Weight: 15%
   - Input: Number (18-80)
   - Impact: Premium calculations and waiting periods

2. **Location** (`location`) - Weight: 10%
   - Input: Select dropdown (9 provinces)
   - Impact: Regional service availability

3. **Family Members to Cover** (`family_members_to_cover`) - Weight: 25%
   - Input: Number (1-15 members)
   - Impact: Coverage scope and premium scaling

4. **Coverage Amount** (`coverage_amount`) - Weight: 30%
   - Input: Radio buttons (R25k/R50k/R100k/R200k+)
   - Impact: Benefit level and premium determination

5. **Service Preference** (`service_preference`) - Weight: 20%
   - Input: Radio buttons (Basic/Standard/Premium)
   - Impact: Service level matching and benefit selection

6. **Monthly Budget** (`monthly_budget`) - Weight: 35%
   - Input: Number (R50-R500)
   - Impact: Primary affordability filter

7. **Waiting Period Tolerance** (`waiting_period`) - Weight: 15%
   - Input: Radio buttons (None/3 months/6 months/12 months)
   - Impact: Policy eligibility and immediate coverage needs

### Funeral Insurance Weighting Algorithm

```python
default_weights = {
    'base_premium': 35,        # Budget constraint (highest priority)
    'coverage_amount': 30,     # Benefit level requirement
    'service_level': 20,       # Service preference
    'waiting_period_days': 15  # Immediate coverage needs
}
```

## Response Processing and Quotation Generation

### 1. Response Validation

Each response undergoes validation based on question type:

```python
def validate_response(self, response_value):
    errors = []
    
    # Required field validation
    if self.is_required and not response_value:
        errors.append("This field is required")
    
    # Type-specific validation
    if self.input_type == 'number':
        # Numeric range validation
    elif self.input_type in ['select', 'radio']:
        # Choice validation
    elif self.input_type == 'checkbox':
        # Multiple selection validation
    
    return errors
```

### 2. Criteria Conversion

Survey responses are converted to comparison engine criteria:

```python
def _convert_survey_responses_to_criteria(self, session_key):
    # Map survey fields to comparison criteria
    field_mappings = {
        'age': 'age',
        'monthly_budget': 'base_premium',
        'family_size': 'family_size',
        'health_status': 'health_status',
        'chronic_conditions': 'chronic_conditions'
    }
    
    # Apply value transformations
    # Add default weights
    # Return processed criteria
```

### 3. Policy Matching Algorithm

The system uses a weighted scoring algorithm:

```python
# Scoring weights for different factors
CRITERIA_WEIGHT = 0.70    # 70% - User criteria match
VALUE_WEIGHT = 0.20       # 20% - Value for money
REVIEW_WEIGHT = 0.05      # 5% - Customer reviews
ORGANIZATION_WEIGHT = 0.05 # 5% - Provider reputation
```

### 4. Quotation Ranking

Policies are ranked by:
1. **Criteria Match Score** (70%) - How well the policy matches user requirements
2. **Value Score** (20%) - Premium vs. benefits ratio
3. **Review Score** (5%) - Customer satisfaction ratings
4. **Organization Score** (5%) - Provider reputation and verification

## Session Management

### Session Lifecycle

1. **Creation**: New session created when user starts survey
2. **Validation**: Session validated on each request
3. **Extension**: Session extended on user activity (24-hour lifetime)
4. **Completion**: Session marked complete after quotation generation
5. **Cleanup**: Expired sessions automatically removed

### Session Data Structure

```python
class QuotationSession(models.Model):
    session_key = CharField(max_length=100)      # Django session identifier
    category = CharField(max_length=20)          # health|funeral
    user_criteria = JSONField(default=dict)      # Processed survey responses
    is_completed = BooleanField(default=False)   # Survey completion status
    expires_at = DateTimeField()                 # 24-hour expiry
```

### Response Storage

```python
class SimpleSurveyResponse(models.Model):
    session_key = CharField(max_length=100)      # Links to session
    category = CharField(max_length=20)          # Insurance category
    question = ForeignKey(SimpleSurveyQuestion)  # Question reference
    response_value = JSONField()                 # User's answer (any type)
```

## AJAX Integration

### Real-time Response Saving

Responses are saved immediately as users interact with the form:

```javascript
// Auto-save on input change
form.addEventListener('change', function(e) {
    if (e.target.matches('input, select')) {
        saveResponse(e.target);
    }
});

function saveResponse(element) {
    fetch('/simple-surveys/ajax/save-response/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            question_id: questionId,
            response_value: responseValue,
            category: category
        })
    });
}
```

### Progress Tracking

Survey completion is tracked and displayed in real-time:

```javascript
function updateProgress(status) {
    const progressBar = document.querySelector('.progress-bar');
    progressBar.style.width = status.percentage + '%';
    progressBar.textContent = status.completed_questions + '/' + 
                             status.total_questions + ' Complete';
}
```

## URL Structure

```
/                                    # Home page
/health/                            # Health insurance landing page
/funerals/                          # Funeral insurance landing page
/direct/{category}/                 # Direct survey entry
/survey/{category}/                 # Survey form
/survey/{category}/process/         # Process completed survey
/survey/{category}/results/         # Display quotations
/ajax/save-response/               # AJAX response saving
/ajax/survey-status/{category}/    # AJAX progress check
```

## Error Handling

### Session Validation Errors
- **No Session**: Redirect to survey start
- **Expired Session**: Clean up data, start new session
- **Invalid Session**: Show error message with restart option

### Response Validation Errors
- **Required Field**: Highlight missing fields
- **Invalid Format**: Show format requirements
- **Out of Range**: Display acceptable ranges

### System Errors
- **Database Errors**: Graceful fallback with user notification
- **Processing Errors**: Retry mechanism with error logging
- **Network Errors**: Client-side retry with timeout handling

## Performance Optimizations

### Database Queries
- Prefetch related objects for policy comparisons
- Index on session_key and category fields
- Batch processing for expired session cleanup

### Caching Strategy
- Cache question sets by category
- Session-based response caching
- Policy comparison result caching

### Frontend Optimizations
- Progressive form loading
- Debounced AJAX requests
- Optimistic UI updates

## Security Considerations

### Data Protection
- Session-based anonymous user tracking
- Automatic data expiry (24 hours)
- No personally identifiable information storage

### Input Validation
- Server-side validation for all responses
- CSRF protection on all forms
- SQL injection prevention through ORM

### Session Security
- Secure session configuration
- Session key rotation
- Automatic cleanup of expired data

## Monitoring and Analytics

### Key Metrics
- Survey completion rates by category
- Average time to completion
- Most common drop-off points
- Quotation generation success rates

### Error Tracking
- Response validation failures
- Session management errors
- Policy matching failures
- System performance issues

## Maintenance Tasks

### Regular Cleanup
```python
# Run daily via cron job
python manage.py cleanup_expired_sessions

# Manual cleanup with statistics
stats = SessionManager.cleanup_expired_sessions(batch_size=100)
```

### Data Monitoring
```python
# Get current system statistics
stats = SessionManager.get_session_stats()
```

### Question Management
- Add new questions via Django admin
- Update validation rules through model updates
- Modify weighting algorithms in comparison adapter

## Future Enhancements

### Planned Features
1. **Multi-language Support** - Translate questions and responses
2. **Advanced Filtering** - Additional policy filtering options
3. **Comparison Tools** - Side-by-side policy comparison
4. **User Accounts** - Optional registration for saved preferences
5. **Mobile App** - Native mobile application
6. **AI Recommendations** - Machine learning-based suggestions

### Technical Improvements
1. **Microservices Architecture** - Split into independent services
2. **Real-time Updates** - WebSocket-based live updates
3. **Advanced Analytics** - Detailed user behavior tracking
4. **A/B Testing** - Question flow optimization
5. **API Integration** - Third-party insurance provider APIs

This documentation provides a comprehensive overview of how the Simple Survey System works, from question rendering to quotation generation, including the weighting algorithms used to match users with the most suitable insurance policies.