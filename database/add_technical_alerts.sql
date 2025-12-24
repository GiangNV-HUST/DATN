-- ===================================================
-- ADD TECHNICAL ALERTS TABLE
-- Bảng lưu trữ các cảnh báo kỹ thuật tự động do hệ thống phát hiện
-- ===================================================

-- Tạo bảng technical_alerts
CREATE TABLE IF NOT EXISTS stock.technical_alerts (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- rsi_overbought, rsi_oversold, golden_cross, death_cross, volume_spike, macd_bullish, macd_bearish
    alert_level VARCHAR(20) NOT NULL, -- critical, warning, info
    message TEXT NOT NULL,
    indicator_value DOUBLE PRECISION, -- Giá trị chỉ báo tại thời điểm phát hiện
    price_at_alert DOUBLE PRECISION, -- Giá cổ phiếu tại thời điểm phát hiện
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE, -- Cảnh báo còn hiệu lực hay không

    CONSTRAINT check_alert_type CHECK (
        alert_type IN (
            'rsi_overbought', 'rsi_oversold',
            'golden_cross', 'death_cross',
            'volume_spike', 'volume_low',
            'macd_bullish', 'macd_bearish',
            'bb_squeeze', 'bb_breakout'
        )
    ),
    CONSTRAINT check_alert_level CHECK (
        alert_level IN ('critical', 'warning', 'info')
    ),
    FOREIGN KEY (ticker) REFERENCES stock.information(ticker) ON DELETE CASCADE
);

-- Tạo index để tăng tốc truy vấn
CREATE INDEX idx_technical_alerts_ticker ON stock.technical_alerts(ticker);
CREATE INDEX idx_technical_alerts_created_at ON stock.technical_alerts(created_at DESC);
CREATE INDEX idx_technical_alerts_type ON stock.technical_alerts(alert_type);
CREATE INDEX idx_technical_alerts_level ON stock.technical_alerts(alert_level);
CREATE INDEX idx_technical_alerts_active ON stock.technical_alerts(is_active);

-- Composite index cho query phổ biến
CREATE INDEX idx_technical_alerts_ticker_active_created ON stock.technical_alerts(ticker, is_active, created_at DESC);

-- Comment mô tả bảng
COMMENT ON TABLE stock.technical_alerts IS 'Cảnh báo kỹ thuật tự động được hệ thống phát hiện dựa trên các chỉ báo kỹ thuật';
COMMENT ON COLUMN stock.technical_alerts.alert_type IS 'Loại cảnh báo: rsi_overbought, rsi_oversold, golden_cross, death_cross, volume_spike, macd_bullish, macd_bearish';
COMMENT ON COLUMN stock.technical_alerts.alert_level IS 'Mức độ: critical (nghiêm trọng), warning (cảnh báo), info (thông tin)';
COMMENT ON COLUMN stock.technical_alerts.is_active IS 'Cảnh báo còn hiệu lực (true) hay đã hết hiệu lực (false)';
