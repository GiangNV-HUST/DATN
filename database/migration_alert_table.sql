-- Migration: Create/Update stock.alert table for Discord bot
-- Date: 2026-01-05
-- Purpose: Create alert table with schema matching DatabaseTools code

-- Drop existing table if it exists (only if you want fresh start)
-- DROP TABLE IF EXISTS stock.alert CASCADE;

-- Create alert table with correct schema
CREATE TABLE IF NOT EXISTS stock.alert (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    condition VARCHAR(10) NOT NULL,
    value DECIMAL(15, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    triggered_at TIMESTAMPTZ NULL,
    user_name VARCHAR(255) NULL,
    CONSTRAINT check_alert_type CHECK (
        alert_type IN ('price', 'rsi', 'volume', 'ma5', 'ma10', 'ma20', 'ma50', 'ma100', 'macd')
    ),
    CONSTRAINT check_condition CHECK (
        condition IN ('>', '<', '>=', '<=', '=', 'above', 'below', 'cross_above', 'cross_below')
    ),
    FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_alert_ticker ON stock.alert(ticker);
CREATE INDEX IF NOT EXISTS idx_alert_user_id ON stock.alert(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_is_active ON stock.alert(is_active);
CREATE INDEX IF NOT EXISTS idx_alert_user_active ON stock.alert(user_id, is_active);

-- Add comments
COMMENT ON TABLE stock.alert IS 'User price alerts for stock monitoring via Discord bot';
COMMENT ON COLUMN stock.alert.user_id IS 'Discord user ID (string format)';
COMMENT ON COLUMN stock.alert.ticker IS 'Stock ticker symbol';
COMMENT ON COLUMN stock.alert.alert_type IS 'Type of alert: price, rsi, volume, etc.';
COMMENT ON COLUMN stock.alert.condition IS 'Condition operator: >, <, >=, <=, =, above, below';
COMMENT ON COLUMN stock.alert.value IS 'Target value for the alert';
COMMENT ON COLUMN stock.alert.is_active IS 'Whether the alert is still active';
COMMENT ON COLUMN stock.alert.created_at IS 'When the alert was created';
COMMENT ON COLUMN stock.alert.updated_at IS 'Last update time';
COMMENT ON COLUMN stock.alert.triggered_at IS 'When the alert was triggered (if ever)';
