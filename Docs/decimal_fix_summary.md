# Decimal JSON Serialization Error Fix

## Problem
The error "Object of type Decimal is not JSON serializable" was occurring in the survey system, specifically in the `survey_form_view` for health category. This error happens when Python's `json.dumps()` function encounters Decimal objects, which are not natively JSON serializable.

## Root Cause Analysis
The error was caused by multiple locations in the codebase where Decimal values were being serialized to JSON without proper handling:

1. **surveys/views.py** - `completion_percentage` calculations returning Decimal values
2. **surveys/analytics.py** - Division operations and aggregations returning Decimal values
3. **surveys/admin_views.py** - JSON export functionality using `json.dumps()` without Decimal handling
4. **surveys/caching.py** - Cache key generation using `json.dumps()` for hashing data containing Decimals

## Fixes Applied

### 1. surveys/views.py
**Fixed completion percentage calculations to return float values:**

```python
# Before
completion_percentage = (answered_count / total_questions * 100) if total_questions > 0 else 0

# After  
completion_percentage = float((answered_count / total_questions * 100)) if total_questions > 0 else 0.0
```

**Fixed survey_progress_view JSON response:**
```python
# Before
'completion_percentage': completion_percentage,

# After
'completion_percentage': float(completion_percentage),
```

### 2. surveys/analytics.py
**Fixed division operations to return float values:**

```python
# Before
completion_rate = (sessions_with_question.count() / max(total_sessions, 1)) * 100
skip_rate = (sessions_that_skipped / max(total_sessions, 1)) * 100

# After
completion_rate = float((sessions_with_question.count() / max(total_sessions, 1)) * 100)
skip_rate = float((sessions_that_skipped / max(total_sessions, 1)) * 100)
```

**Fixed average calculations:**
```python
# Before
'average_confidence': round(avg_confidence, 2),

# After
'average_confidence': float(round(avg_confidence, 2)),
```

**Fixed numeric response averages:**
```python
# Before
return sum(values) / len(values)

# After
return float(sum(values) / len(values))
```

### 3. surveys/admin_views.py
**Fixed JSON export to handle Decimal values:**

```python
# Before
json.dumps(data, indent=2)

# After
json.dumps(data, indent=2, default=str)
```

**Fixed completion rate calculations:**
```python
# Before
'completion_rate': (completed_sessions / max(total_sessions, 1)) * 100,

# After
'completion_rate': float((completed_sessions / max(total_sessions, 1)) * 100),
```

### 4. surveys/caching.py
**Fixed cache key generation to handle Decimal values:**

```python
# Before
data_str = json.dumps(data, sort_keys=True)

# After
data_str = json.dumps(data, sort_keys=True, default=str)
```

## Testing
Created comprehensive tests to verify all fixes:

1. **test_decimal_fix.py** - Basic investigation and reproduction
2. **test_decimal_comprehensive.py** - Comprehensive testing of all scenarios

All tests pass, confirming that:
- ✅ Caching module handles Decimal values correctly
- ✅ Admin views JSON export works with Decimal values
- ✅ Analytics calculations return proper float values
- ✅ Survey views handle Decimal values in JSON responses
- ✅ All JSON serialization scenarios work correctly

## Prevention
To prevent similar issues in the future:

1. **Use `default=str` parameter** when using `json.dumps()` with potentially mixed data types
2. **Convert Decimal to float** for numeric calculations that will be serialized
3. **Use Django's `DjangoJSONEncoder`** for complex serialization scenarios
4. **Test JSON serialization** when working with database fields that use DecimalField

## Files Modified
- `surveys/views.py`
- `surveys/analytics.py` 
- `surveys/admin_views.py`
- `surveys/caching.py`

## Impact
This fix resolves the "Object of type Decimal is not JSON serializable" error that was preventing the health survey form from working properly. The survey system should now handle all Decimal values correctly in JSON responses and caching operations.