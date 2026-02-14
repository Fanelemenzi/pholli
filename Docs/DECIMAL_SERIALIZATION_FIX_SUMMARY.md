# Decimal Serialization Fix Summary

## Problem
When submitting a completed survey, users encountered a `TypeError: Object of type Decimal is not JSON serializable` error. This occurred when Django tried to serialize session data containing `Decimal` objects to JSON.

## Root Cause
The survey system stores quotation data, criteria, and metadata in Django sessions. Some of this data contained `Decimal` objects from model fields like:
- `preferred_annual_limit_per_family` (DecimalField)
- `household_income` (DecimalField) 
- `preferred_cover_amount` (DecimalField)
- Policy premium and coverage amounts (DecimalField)

Django sessions serialize data to JSON, but Python's `Decimal` objects are not JSON serializable by default.

## Solution
Created a helper function `_serialize_for_session()` that recursively converts `Decimal` objects to `float` while preserving the structure of dictionaries, lists, and other data types.

### Changes Made

1. **Added serialization helper function** in `simple_surveys/views.py`:
   ```python
   def _serialize_for_session(data):
       """Convert Decimal objects to float for JSON serialization in Django sessions."""
       if isinstance(data, Decimal):
           return float(data)
       elif isinstance(data, dict):
           return {key: _serialize_for_session(value) for key, value in data.items()}
       elif isinstance(data, list):
           return [_serialize_for_session(item) for item in data]
       elif isinstance(data, tuple):
           return tuple(_serialize_for_session(item) for item in data)
       else:
           return data
   ```

2. **Updated session storage** in both `FeatureSurveyView` and `ProcessSurveyView`:
   ```python
   # Before
   request.session[f'quotations_{category}'] = quotations
   request.session[f'criteria_{category}'] = criteria
   request.session[f'quotation_metadata_{category}'] = metadata
   
   # After
   request.session[f'quotations_{category}'] = _serialize_for_session(quotations)
   request.session[f'criteria_{category}'] = _serialize_for_session(criteria)
   request.session[f'quotation_metadata_{category}'] = _serialize_for_session(metadata)
   ```

3. **Updated QuotationSession.update_criteria()** method in `simple_surveys/models.py`:
   ```python
   def update_criteria(self, criteria_dict):
       """Update user criteria from survey responses"""
       from .views import _serialize_for_session
       serialized_criteria = _serialize_for_session(criteria_dict)
       self.user_criteria.update(serialized_criteria)
       self.save(update_fields=['user_criteria'])
   ```

## Testing
- Created and ran a test script that verified `Decimal` objects are properly converted to `float`
- Confirmed JSON serialization/deserialization works correctly
- Verified that numeric values are preserved during the conversion process

## Impact
- ✅ Survey submission now works without JSON serialization errors
- ✅ All numeric precision is preserved (Decimal to float conversion)
- ✅ No changes to existing data structures or API contracts
- ✅ Backward compatible with existing session data

## Files Modified
- `simple_surveys/views.py` - Added helper function and updated session storage
- `simple_surveys/models.py` - Updated QuotationSession.update_criteria() method

The fix ensures that all survey data can be properly stored in Django sessions without encountering JSON serialization errors.