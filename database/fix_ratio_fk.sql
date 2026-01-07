-- Remove foreign key constraint from stock.ratio table
-- This allows inserting ratios data before company information

ALTER TABLE stock.ratio DROP CONSTRAINT IF EXISTS ratio_ticker_fkey;

-- Add a check constraint for ticker format instead
ALTER TABLE stock.ratio ADD CONSTRAINT IF NOT EXISTS check_ratio_ticker_format
    CHECK (ticker ~ '^[A-Z0-9]{1,20}$');

-- Verify the change
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'stock.ratio'::regclass;
