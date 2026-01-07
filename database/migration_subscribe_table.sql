-- Migration: Create stock.subscribe table for subscription management
-- Date: 2026-01-05
-- Purpose: Create subscribe table matching DatabaseTools code

-- Create subscribe table
CREATE TABLE IF NOT EXISTS stock.subscribe (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_name VARCHAR(255) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT subscribe_user_id_ticker_key UNIQUE (user_id, ticker)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_subscribe_ticker ON stock.subscribe(ticker);
CREATE INDEX IF NOT EXISTS idx_subscribe_user_id ON stock.subscribe(user_id);
CREATE INDEX IF NOT EXISTS idx_subscribe_is_active ON stock.subscribe(is_active);
CREATE INDEX IF NOT EXISTS idx_subscribe_user_active ON stock.subscribe(user_id, is_active);

-- Add ticker format validation (no FK constraint to allow any ticker)
ALTER TABLE stock.subscribe DROP CONSTRAINT IF EXISTS subscribe_ticker_fkey;
ALTER TABLE stock.subscribe DROP CONSTRAINT IF EXISTS check_ticker_format;
ALTER TABLE stock.subscribe ADD CONSTRAINT check_ticker_format
    CHECK (ticker ~ '^[A-Z0-9]{1,20}$');

-- Add comments
COMMENT ON TABLE stock.subscribe IS 'User stock subscriptions for monitoring via Discord bot';
COMMENT ON COLUMN stock.subscribe.user_id IS 'Discord user ID (string format)';
COMMENT ON COLUMN stock.subscribe.ticker IS 'Stock ticker symbol to follow';
COMMENT ON COLUMN stock.subscribe.created_at IS 'When the subscription was created';
COMMENT ON COLUMN stock.subscribe.is_active IS 'Whether the subscription is still active';
