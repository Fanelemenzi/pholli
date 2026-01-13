# Policy Matching System Documentation

## Overview

The policy matching system is a sophisticated engine that converts simple survey responses into personalized insurance policy recommendations. It uses a multi-stage process involving data collection, validation, criteria conversion, policy filtering, scoring, and ranking to deliver the most relevant insurance options to users.

## System Architecture

```
Survey Questions → User Responses → Criteria Conversion → Policy Filtering → Scoring & Ranking → Results
```

## 1. Survey Question to Criteria Mapping

### Health Insurance Questions Mapping

| Survey Question | Field Name | Comparison Criteria | Weight | Purpose |
|----------------|------------|-------------------|--------|---------|
| **Age** | `age` | `age` | 1.5 | Risk assessment, premium calculation |
| **Location** | `location` | `location` | 1.0 | Provider network availability |
| **Family Size** | `family_size` | `family_size` | 2.0 | Premium scaling, plan eligibility |
| **Health Status** | `health_status` | `health_status` | 2.5 | Risk assessment, policy eligibility |
| **Chronic Conditions** | `chronic_conditions` | `chronic_conditions` | 2.0 | Specialized coverage needs |
| **Coverage Priority** | `coverage_priority` | `coverage_priority` | 2.5 | Policy type matching |
| **Monthly Budget** | `monthly_budget` | `base_premium` | 3.5 | Primary affordability filter |
| **Deductible Preference** | `preferred_deductible` | `deductible_amount` | 1.8 | Cost vs. out-of-pocket balance |

### Funeral Insurance Questions Mapping

| Survey Question | Field Name | Comparison Criteria | Weight | Purpose |
|----------------|------------|-------------------|--------|---------|
| **Age** | `age` | `age` | 1.5 | Premium calculation, waiting periods |
| **Location** | `location` | `location` | 1.0 | Service provider availability |
| **Family Coverage** | `family_members_to_cover` | `family_size` | 2.5 | Coverage scaling |
| **Coverage Amount** | `coverage_amount` | `coverage_amount` | 3.0 | Primary matching criterion |
| **Service Preference** | `service_preference` | `service_level` | 2.0 | Policy type matching |
| **Monthly Budget** | `monthly_budget` | `base_premium` | 3.5 | Primary affordability filter |
| **Waiting Period** | `waiting_period` | `waiting_period_days` | 2.0 | Urgency vs. cost balance |

## 2. Data Flow and Processing

### Stage 1: Survey Response Collection

```python
# SimpleSurveyEngine.save_response()
def save_response(self, session_key: str, question_id: int, response: Any) -> Dict[str, Any]:
    # 1. Validate response format and content
    validation_result = self.validate_response(question_id, response)
    
    # 2. Clean and normalize response value
    cleaned_value = self._clean_response_value(question, response)
    
    # 3. Save to database with session tracking
    response_obj = SimpleSurveyResponse.objects.update_or_create(...)
    
    # 4. Return success/error status
    return {'success': True, 'response_id': response_obj.id}
```

### Stage 2: Criteria Conversion

```python
# SimpleSurveyComparisonAdapter._convert_survey_responses_to_criteria()
def _convert_survey_responses_to_criteria(self, session_key: str) -> Dict[str, Any]:
    # 1. Get all survey responses for session
    processed_responses = self.survey_engine.process_responses(session_key)
    
    # 2. Map survey fields to comparison fields
    field_mappings = self._get_field_mappings()
    
    # 3. Convert response values to comparison format
    criteria = {}
    for survey_field, response_value in processed_responses.items():
        if survey_field in field_mappings:
            comparison_field = field_mappings[survey_field]
            criteria[comparison_field] = self._convert_response_value(survey_field, response_value)
    
    # 4. Add default weights and category-specific processing
    criteria['weights'] = self._get_default_weights(criteria)
    criteria = self._apply_category_specific_processing(criteria)
    
    return criteria
```

### Stage 3: Policy Filtering

```python
# SimpleSurveyComparisonAdapter._get_eligible_policy_ids()
def _get_eligible_policy_ids(self, criteria: Dict[str, Any]) -> List[int]:
    # 1. Base query for active, approved policies
    queryset = BasePolicy.objects.filter(
        category=category,
        is_active=True,
        approval_status='APPROVED'
    )
    
    # 2. Apply budget filtering (20% tolerance)
    if 'base_premium' in criteria:
        max_premium = criteria['base_premium'] * 1.2
        queryset = queryset.filter(base_premium__lte=max_premium)
    
    # 3. Apply age eligibility filtering
    if 'age' in criteria:
        age = criteria['age']
        queryset = queryset.filter(
            minimum_age__lte=age,
            maximum_age__gte=age
        )
    
    # 4. Apply coverage amount filtering (20% tolerance)
    if 'coverage_amount' in criteria:
        min_coverage = criteria['coverage_amount'] * 0.8
        queryset = queryset.filter(coverage_amount__gte=min_coverage)
    
    return list(queryset.values_list('id', flat=True))
```

## 3. Scoring Algorithm

### Simplified Scoring Weights

```python
# SimplifiedPolicyComparisonEngine scoring weights
CRITERIA_WEIGHT = Decimal('0.70')    # 70% - Criteria match
VALUE_WEIGHT = Decimal('0.20')       # 20% - Value for money
REVIEW_WEIGHT = Decimal('0.05')      # 5% - Customer reviews
ORGANIZATION_WEIGHT = Decimal('0.05') # 5% - Provider reputation
```

### Criteria Scoring Process

```python
def _score_policy_simplified(self, policy: BasePolicy, user_criteria: Dict[str, Any]) -> Dict[str, Any]:
    criteria_scores = {}
    total_weighted_score = Decimal('0')
    total_weight = Decimal('0')
    
    # Score each criterion
    for field_name, weight in self.weights.items():
        if field_name in user_criteria:
            score = self._score_criterion(policy, field_name, user_criteria[field_name])
            criteria_scores[field_name] = score
            total_weighted_score += score * weight
            total_weight += weight
    
    # Calculate overall criteria score
    criteria_score = (total_weighted_score / total_weight) if total_weight > 0 else Decimal('0')
    
    # Calculate value score (premium vs. benefits ratio)
    value_score = self._calculate_value_score(policy, user_criteria)
    
    # Calculate final score
    overall_score = (
        criteria_score * self.CRITERIA_WEIGHT +
        value_score * self.VALUE_WEIGHT +
        # ... other components
    )
    
    return {
        'overall_score': float(overall_score),
        'criteria_score': float(criteria_score),
        'value_score': float(value_score),
        'criteria_scores': {k: float(v) for k, v in criteria_scores.items()}
    }
```

## 4. Error Handling System

### Input Validation Errors

#### Question-Level Validation

```python
# SimpleSurveyQuestion.validate_response()
def validate_response(self, response_value):
    errors = []
    
    # Required field validation
    if self.is_required and (response_value is None or response_value == ''):
        errors.append("This field is required")
        return errors
    
    # Type-specific validation
    if self.input_type == 'number':
        try:
            num_value = float(response_value)
            if 'min' in self.validation_rules and num_value < self.validation_rules['min']:
                errors.append(f"Value must be at least {self.validation_rules['min']}")
            if 'max' in self.validation_rules and num_value > self.validation_rules['max']:
                errors.append(f"Value must be at most {self.validation_rules['max']}")
        except (ValueError, TypeError):
            errors.append("Please enter a valid number")
    
    elif self.input_type in ['select', 'radio']:
        valid_choices = [choice[0] for choice in self.get_choices_list()]
        if response_value not in valid_choices:
            errors.append("Please select a valid option")
    
    elif self.input_type == 'checkbox':
        if not isinstance(response_value, list):
            errors.append("Invalid checkbox response format")
        else:
            valid_choices = [choice[0] for choice in self.get_choices_list()]
            for value in response_value:
                if value not in valid_choices:
                    errors.append(f"Invalid choice: {value}")
                    break
    
    return errors
```

#### Session Management Errors

```python
# SessionManager.validate_session()
def validate_session(session_key: str, category: str) -> Dict[str, Any]:
    try:
        session = QuotationSession.objects.get(
            session_key=session_key,
            category=category
        )
        
        if session.is_expired():
            return {
                'valid': False,
                'error': 'Session has expired',
                'error_type': 'expired'
            }
        
        return {
            'valid': True,
            'session': session
        }
        
    except QuotationSession.DoesNotExist:
        return {
            'valid': False,
            'error': 'Session not found',
            'error_type': 'not_found'
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f'Session validation failed: {str(e)}',
            'error_type': 'validation_error'
        }
```

### Processing Errors

#### Survey Completion Validation

```python
# SimpleSurveyEngine.is_survey_complete()
def is_survey_complete(self, session_key: str) -> bool:
    try:
        # Get count of required questions
        required_count = SimpleSurveyQuestion.objects.filter(
            category=self.category,
            is_required=True
        ).count()
        
        # Get count of answered required questions
        answered_count = SimpleSurveyResponse.objects.filter(
            session_key=session_key,
            category=self.category,
            question__is_required=True
        ).count()
        
        return answered_count >= required_count
        
    except Exception as e:
        logger.error(f"Error checking survey completion: {e}")
        return False
```

#### Policy Matching Errors

```python
# SimpleSurveyComparisonAdapter.generate_quotations()
def generate_quotations(self, session_key: str, max_results: int = 5) -> Dict[str, Any]:
    try:
        # Convert survey responses to criteria
        criteria = self._convert_survey_responses_to_criteria(session_key)
        if not criteria:
            return {
                'success': False,
                'error': 'No survey responses found for session',
                'error_type': 'no_responses'
            }
        
        # Get eligible policies
        policy_ids = self._get_eligible_policy_ids(criteria)
        if not policy_ids:
            return {
                'success': False,
                'error': 'No eligible policies found for your criteria',
                'error_type': 'no_policies',
                'criteria': criteria
            }
        
        # Run comparison engine
        comparison_result = self.comparison_engine.compare_policies(...)
        if not comparison_result.get('success'):
            return {
                'success': False,
                'error': comparison_result.get('error', 'Comparison failed'),
                'error_type': 'comparison_failed'
            }
        
        return {
            'success': True,
            'policies': simplified_results['policies'],
            # ... other results
        }
        
    except Exception as e:
        logger.error(f"Error generating quotations: {e}")
        return {
            'success': False,
            'error': f'Failed to generate quotations: {str(e)}',
            'error_type': 'system_error'
        }
```

### Frontend Error Handling

#### AJAX Response Handling

```javascript
// Auto-save response handling
function saveResponse(element) {
    fetch('/simple-surveys/save-response/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({
            question_id: parseInt(questionId),
            response_value: responseValue,
            category: category
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.completion_status) {
            updateProgress(data.completion_status);
        } else if (!data.success) {
            console.error('Error saving response:', data.errors);
            // Could show user-friendly error message
        }
    })
    .catch(error => {
        console.error('Error saving response:', error);
        // Handle network errors
    });
}

// Survey processing error handling
function processSurvey() {
    fetch('/simple-surveys/process/' + category + '/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = data.redirect_url;
        } else {
            alert('Error: ' + data.error);
            // Reset button state
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-search me-2"></i>Get My Quotes';
        }
    })
    .catch(error => {
        console.error('Error processing survey:', error);
        alert('An error occurred. Please try again.');
        // Reset button state
    });
}
```

## 5. Specific Input Processing Examples

### Age Processing

```python
# Input: User enters "35" in age field
# Validation: Check 18 <= age <= 80
# Conversion: int(35)
# Usage: Filter policies where minimum_age <= 35 <= maximum_age
# Scoring: Exact match = 100%, outside range = 0%
```

### Budget Processing

```python
# Input: User enters "500" for monthly budget
# Validation: Check min <= budget <= max (category-specific)
# Conversion: int(500)
# Usage: Filter policies where base_premium <= 500 * 1.2 (20% tolerance)
# Scoring: 
#   - Premium <= budget: 100%
#   - Premium <= budget * 1.1: 90%
#   - Premium <= budget * 1.2: 70%
#   - Premium > budget * 1.2: 0% (filtered out)
```

### Chronic Conditions Processing

```python
# Input: User selects ["diabetes", "hypertension"]
# Validation: Check all values are in valid choices
# Conversion: List remains as-is
# Usage: Match policies that cover these conditions
# Scoring:
#   - Policy covers all conditions: 100%
#   - Policy covers some conditions: 60%
#   - Policy covers no conditions: 20%
#   - Policy excludes conditions: 0%
```

### Location Processing

```python
# Input: User selects "gauteng"
# Validation: Check value is in province list
# Conversion: String remains as-is
# Usage: Filter policies available in Gauteng
# Scoring:
#   - Policy available in location: 100%
#   - Policy not available: 0% (filtered out)
```

## 6. Category-Specific Processing

### Health Insurance Adjustments

```python
def _apply_category_specific_processing(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
    if self.category == 'health':
        # Adjust premium range based on family size
        if 'family_size' in criteria and 'base_premium' in criteria:
            family_size = criteria['family_size']
            base_budget = criteria['base_premium']
            
            if family_size > 4:
                criteria['base_premium'] = int(base_budget * 1.2)  # 20% increase
            elif family_size > 2:
                criteria['base_premium'] = int(base_budget * 1.1)  # 10% increase
        
        # Increase coverage priority weight for chronic conditions
        if 'chronic_conditions' in criteria:
            conditions = criteria['chronic_conditions']
            if isinstance(conditions, list) and len(conditions) > 0 and 'none' not in conditions:
                if 'weights' in criteria:
                    criteria['weights']['coverage_priority'] += 10
    
    return criteria
```

### Funeral Insurance Adjustments

```python
def _apply_category_specific_processing(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
    if self.category == 'funeral':
        # Adjust coverage based on family size
        if 'family_size' in criteria and 'coverage_amount' in criteria:
            family_size = criteria['family_size']
            base_coverage = criteria['coverage_amount']
            
            if family_size > 10:
                criteria['coverage_amount'] = max(base_coverage, 100000)
            elif family_size > 5:
                criteria['coverage_amount'] = max(base_coverage, 50000)
    
    return criteria
```

## 7. Performance Optimizations

### Database Query Optimization

```python
# Efficient policy filtering with indexed queries
queryset = BasePolicy.objects.filter(
    category=category,
    is_active=True,
    approval_status='APPROVED'
).select_related(
    'organization', 'category', 'policy_type'
).prefetch_related(
    'features'
).order_by('base_premium')

# Limit results early to avoid processing too many policies
policy_ids = list(queryset.values_list('id', flat=True)[:max_results * 2])
```

### Caching Strategy

```python
# Session-based result caching
request.session[f'quotations_{category}'] = quotations
request.session[f'criteria_{category}'] = criteria
request.session[f'quotation_metadata_{category}'] = metadata

# Cache expiry: 24 hours
quotation_session.expires_at = timezone.now() + timedelta(hours=24)
```

## 8. Monitoring and Logging

### Error Tracking

```python
import logging
logger = logging.getLogger(__name__)

# Log validation errors
logger.error(f"Validation failed for question {question_id}: {errors}")

# Log processing errors
logger.error(f"Error generating quotations for session {session_key}: {e}")

# Log performance metrics
logger.info(f"Processed {len(criteria)} responses for session {session_key[:8]}")
logger.info(f"Found {len(policy_ids)} eligible policies for {category} category")
```

### Success Metrics

```python
# Track completion rates
completion_status = engine.get_completion_status(session_key)
logger.info(f"Survey completion: {completion_status['completion_percentage']}%")

# Track matching success
logger.info(f"Generated {len(quotations)} quotations from {total_policies} policies")
```

## 9. User Experience Flow

### Happy Path

1. **User starts survey** → Session created
2. **User answers questions** → Responses auto-saved and validated
3. **Progress tracked** → Real-time completion percentage
4. **Survey completed** → All required questions answered
5. **Processing triggered** → Criteria conversion and policy matching
6. **Results displayed** → Top 5 ranked policies with clear comparisons

### Error Recovery Paths

1. **Validation Error** → Show inline error, allow correction
2. **Session Expired** → Redirect to restart with friendly message
3. **No Policies Found** → Show message with suggestion to adjust criteria
4. **System Error** → Show generic error with retry option

## 10. Future Enhancements

### Planned Improvements

1. **Machine Learning Integration** → Learn from user selections to improve matching
2. **Advanced Filtering** → More sophisticated policy filtering options
3. **Real-time Pricing** → Integration with provider APIs for live quotes
4. **Comparison Analytics** → Track which factors matter most to users
5. **A/B Testing** → Test different question flows and scoring algorithms

This comprehensive system ensures that users receive accurate, personalized insurance recommendations while maintaining robust error handling and optimal performance throughout the entire process.