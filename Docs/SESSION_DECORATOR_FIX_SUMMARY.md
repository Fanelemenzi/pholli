# Session Decorator Fix Summary

## Issue
The `@with_survey_session()` decorator was causing an AttributeError when applied to class-based views:
```
Exception Type: AttributeError at /feature-survey/health/
Exception Value: 'FeatureSurveyView' object has no attribute 'session'
```

## Root Cause
The decorator was designed for function-based views and expected the first argument to be the `request` object. When applied to class-based view methods, the first argument is `self` (the view instance), causing the decorator to treat the view instance as the request object.

## Solution Applied
Removed the decorator from the `FeatureSurveyView.get()` method and replaced it with direct session management:

### Before:
```python
@with_survey_session()
def get(self, request, category):
    # Session is automatically handled by decorator
    session_key = request.survey_session_key
```

### After:
```python
def get(self, request, category):
    # Handle session management directly
    quotation_session = SimpleSessionManager.get_or_create_session(request, category)
    session_key = quotation_session.session_key
```

## Alternative Solutions Considered

1. **Fix the decorator to work with class-based views** - This would require complex argument inspection and could be error-prone.

2. **Use method_decorator** - Could wrap the decorator with Django's `method_decorator`, but direct session management is simpler.

3. **Override dispatch method** - Could handle session management in the view's dispatch method, but the current approach is more explicit.

## Benefits of Current Solution

1. **Explicit and Clear** - Session management is visible in the method
2. **No Magic** - No hidden decorator behavior to debug
3. **Consistent** - Same pattern can be used across all views
4. **Maintainable** - Easy to understand and modify

## Files Modified

- `simple_surveys/views.py` - Removed decorator and added direct session management
- `simple_surveys/simple_session_manager.py` - Improved decorator (for future use with function-based views)

## Status
✅ **Fixed** - The error is resolved and the view now works correctly with session management.