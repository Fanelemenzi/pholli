# Migration Fix Guide: Missing monthly_net_income Column

## Problem
The error occurs because the `monthly_net_income` field exists in the Django model but not in the database table. This is a common migration issue.

## Error Details
```
Exception Value: column policies_policyfeatures.monthly_net_income does not exist
```

## Solutions (Choose One)

### Solution 1: Run Django Migration (Recommended)
If you can connect to your database:

```bash
# Check migration status
python manage.py showmigrations policies

# Apply the migration
python manage.py migrate policies

# Or run the specific migration
python manage.py migrate policies 0008_add_monthly_net_income_field
```

### Solution 2: Manual SQL Fix
If you have direct database access but can't run Django migrations:

```sql
-- Add the missing column
ALTER TABLE policies_policyfeatures 
ADD COLUMN monthly_net_income DECIMAL(10,2) NULL;

-- Verify the column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'policies_policyfeatures' 
AND column_name = 'monthly_net_income';
```

### Solution 3: Temporary Workaround (Applied)
I've temporarily commented out references to `monthly_net_income` in:
- `policies/admin.py` - Admin interface fields
- `policies/forms.py` - Form validation

This allows the admin to work while you fix the database issue.

## Database Connection Issues
Your error shows database connection problems:
```
could not translate host name "ep-dawn-fog-a8mxgcsn-pooler.eastus2.azure.neon.tech" to address: Name or service not known
```

### Fix Database Connection:
1. Check your `DATABASE_URL` environment variable
2. Ensure your internet connection is working
3. Verify the Neon database is accessible
4. Check if the hostname is correct

### Set DATABASE_URL:
```bash
# Windows CMD
set DATABASE_URL=postgresql://username:password@ep-dawn-fog-a8mxgcsn-pooler.eastus2.azure.neon.tech/database_name

# Windows PowerShell
$env:DATABASE_URL="postgresql://username:password@ep-dawn-fog-a8mxgcsn-pooler.eastus2.azure.neon.tech/database_name"
```

## After Fixing the Database

1. **Revert the temporary changes** by uncommenting the `monthly_net_income` references
2. **Run the migration**: `python manage.py migrate policies`
3. **Test the admin interface** to ensure everything works

## Files Modified (Temporary Fix)
- `policies/admin.py` - Commented out monthly_net_income field references
- `policies/forms.py` - Commented out monthly_net_income form field and validation

## Migration File
The migration already exists: `policies/migrations/0008_add_monthly_net_income_field.py`

This migration adds the field with the correct definition:
```python
field=models.DecimalField(
    blank=True,
    decimal_places=2,
    help_text="Monthly net income requirement for funeral policy",
    max_digits=10,
    null=True,
)
```

## Next Steps
1. Fix your database connection
2. Run the migration
3. Uncomment the temporarily disabled code
4. Test the admin interface