-- Migration: Fix user_id type in subscriptions and alerts tables
-- Date: 2026-01-12
-- Purpose: Change user_id from bigint to VARCHAR to support string user IDs (Claude Desktop, Discord, etc.)

-- Fix subscriptions table
ALTER TABLE public.subscriptions
    ALTER COLUMN user_id TYPE VARCHAR(255) USING user_id::VARCHAR;

-- Fix alerts table
ALTER TABLE public.alerts
    ALTER COLUMN user_id TYPE VARCHAR(255) USING user_id::VARCHAR;

-- Add comments
COMMENT ON COLUMN public.subscriptions.user_id IS 'User ID (string format - supports Claude Desktop, Discord, Telegram, etc.)';
COMMENT ON COLUMN public.alerts.user_id IS 'User ID (string format - supports Claude Desktop, Discord, Telegram, etc.)';

-- Verify changes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('subscriptions', 'alerts')
  AND column_name = 'user_id';
