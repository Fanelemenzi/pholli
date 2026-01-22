-- Manual SQL to add the missing monthly_net_income column
-- Run this directly in your database if you can't run Django migrations

ALTER TABLE policies_policyfeatures 
ADD COLUMN monthly_net_income DECIMAL(10,2) NULL;

-- Add a comment to the column (optional, depending on your database)
COMMENT ON COLUMN policies_policyfeatures.monthly_net_income IS 'Monthly net income requirement for funeral policy';

-- Verify the column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'policies_policyfeatures' 
AND column_name = 'monthly_net_income';