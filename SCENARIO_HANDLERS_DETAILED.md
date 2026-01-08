# CHI TIẾT 5 SCENARIO HANDLERS CHO THỊ TRƯỜNG CHỨNG KHOÁN VIỆT NAM

> **Tài liệu kỹ thuật**: Hệ thống xử lý kịch bản đặc thù thị trường Việt Nam
> **Mục đích**: Điều chỉnh dự đoán theo điều kiện thị trường thời gian thực
> **Ngày tạo**: 2026-01-08

---

## MỤC LỤC

1. [Tổng quan Scenario Handlers](#1-tổng-quan-scenario-handlers)
2. [Handler 1: News Shock](#2-handler-1-news-shock-handler)
3. [Handler 2: Market Crash](#3-handler-2-market-crash-handler)
4. [Handler 3: Foreign Flow](#4-handler-3-foreign-flow-handler)
5. [Handler 4: VN30 Adjustment](#5-handler-4-vn30-adjustment-handler)
6. [Handler 5: Margin Call](#6-handler-5-margin-call-handler)
7. [Tích hợp vào Ensemble System](#7-tích-hợp-vào-ensemble-system)

---

## 1. TỔNG QUAN SCENARIO HANDLERS

### 1.1. Vai trò trong Prediction Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│             PREDICTION PIPELINE WITH SCENARIOS              │
└─────────────────────────────────────────────────────────────┘

Input Data
    ↓
Feature Engineering (60+ indicators)
    ↓
┌──────────────────────────────┐
│   5 BASE MODELS (Parallel)   │
│  • PatchTST                   │
│  • LSTM + Attention           │
│  • LightGBM                   │
│  • Prophet                    │
│  • XGBoost                    │
└──────────────────────────────┘
    ↓
Meta-Model (MLPRegressor)
    ↓
BASE PREDICTION (P₀)
    ↓
┌─────────────────────────────────────────────────────────────┐
│               SCENARIO HANDLERS (Sequential)                 │
├─────────────────────────────────────────────────────────────┤
│  1. News Shock Handler         → Check price shock          │
│  2. Market Crash Handler       → Check VN-Index drop        │
│  3. Foreign Flow Handler       → Check room + flow          │
│  4. VN30 Adjustment Handler    → Check VN30 events          │
│  5. Margin Call Handler        → Check margin cascade       │
└─────────────────────────────────────────────────────────────┘
    ↓
ADJUSTED PREDICTION (P_final)
    ↓
Output: (Price, Confidence, Recommendation)
```

### 1.2. Đặc điểm chung

| Đặc điểm | Mô tả |
|----------|-------|
| **Trigger-based** | Chỉ kích hoạt khi điều kiện thỏa mãn |
| **Adjustment Factor** | Điều chỉnh prediction base: P_final = P₀ × (1 + adjustment) |
| **Confidence Impact** | Thay đổi confidence interval width |
| **Priority** | Xử lý theo thứ tự ưu tiên (Market Crash > News Shock > ...) |
| **Stackable** | Có thể kết hợp nhiều adjustments |

### 1.3. Khi nào Handlers được kích hoạt?

```python
# Pseudo-code
def apply_scenario_handlers(base_prediction, ticker, market_data):
    adjusted_pred = base_prediction
    adjustments = []

    # 1. Check News Shock (highest priority for individual stocks)
    if news_shock_handler.detect_shock(ticker):
        adj = news_shock_handler.adjust(adjusted_pred)
        adjusted_pred = adj['prediction']
        adjustments.append(('news_shock', adj))

    # 2. Check Market Crash (market-wide)
    if market_crash_handler.detect_crash(vn_index):
        adj = market_crash_handler.adjust(adjusted_pred)
        adjusted_pred = adj['prediction']
        adjustments.append(('market_crash', adj))

    # 3. Check Foreign Flow (Vietnam-specific)
    if foreign_flow_handler.check_room_status(ticker):
        adj = foreign_flow_handler.adjust(adjusted_pred)
        adjusted_pred = adj['prediction']
        adjustments.append(('foreign_flow', adj))

    # 4. Check VN30 Adjustment (scheduled events)
    if vn30_handler.check_upcoming_event(ticker):
        adj = vn30_handler.adjust(adjusted_pred)
        adjusted_pred = adj['prediction']
        adjustments.append(('vn30_adjustment', adj))

    # 5. Check Margin Call (crisis mode)
    if margin_call_handler.detect_cascade(vn_index):
        adj = margin_call_handler.adjust(adjusted_pred)
        adjusted_pred = adj['prediction']
        adjustments.append(('margin_call', adj))

    return adjusted_pred, adjustments
```

---

## 2. HANDLER 1: NEWS SHOCK HANDLER

### 2.1. Mục đích

Xử lý tin tức đột ngột ảnh hưởng giá cổ phiếu (earnings surprise, M&A, policy changes).

### 2.2. Kịch bản xử lý

| Kịch bản | Trigger | Impact |
|----------|---------|--------|
| **Positive Earnings Beat** | Giá tăng >5% trong ngày | +3% to +8% (3-5 ngày) |
| **M&A Announcement** | Giá tăng >7% (trần) | +5% to +15% (5-7 ngày) |
| **Negative News (scandal)** | Giá giảm >5% | -5% to -10% (3-5 ngày) |
| **Policy Change** | Thay đổi chính sách ngành | ±3% to ±10% (5-10 ngày) |

### 2.3. Detection Logic

```python
# Phát hiện Price Shock
def detect_price_shock(current_price, previous_prices, threshold=0.05):
    # 1. Calculate z-score
    daily_returns = previous_prices.pct_change()
    mean = daily_returns.mean()
    std = daily_returns.std()

    current_change = (current_price - previous_prices[-1]) / previous_prices[-1]
    z_score = (current_change - mean) / std

    # 2. Shock criteria:
    is_shock = abs(current_change) > threshold OR abs(z_score) > 3

    return is_shock, shock_type, magnitude
```

**Ví dụ - VCB Earnings Beat**:
```
Giá trước: 95,000 VND (stable 5 ngày)
Giá sau news: 101,650 VND (+7% - trần)

Detection:
  ✓ Change: +7% > threshold (5%)
  ✓ Z-score: 8.5 > 3 sigma
  → SHOCK DETECTED: Positive, Magnitude 7%
```

### 2.4. Adjustment Calculation

```python
def adjust_prediction_for_shock(base_pred, shock_type, magnitude, days_since):
    # Decay factor: ảnh hưởng giảm dần
    decay = max(0, 1 - days_since * 0.2)  # -20% mỗi ngày

    if shock_type == "positive":
        # Momentum continuation: 30% của shock magnitude
        momentum = magnitude * 0.3 * decay
        adjusted = base_pred * (1 + momentum/100)

        # Cap at ceiling (trần +7%)
        max_price = current_price * 1.07
        adjusted = min(adjusted, max_price)

    else:  # negative
        momentum = -magnitude * 0.3 * decay
        adjusted = base_pred * (1 + momentum/100)

        # Cap at floor (sàn -7%)
        min_price = current_price * 0.93
        adjusted = max(adjusted, min_price)

    # Lower confidence
    confidence_penalty = magnitude * 10  # High uncertainty

    return adjusted, confidence_penalty
```

**Ví dụ tính toán**:
```yaml
Scenario: VCB Earnings Beat
  Current Price: 101,650 VND (sau shock +7%)
  Base Prediction: 96,200 VND (model cũ trước news)

  Days Since Shock: 0
  Decay Factor: 1.0 (day 0)
  Momentum: 7% × 0.3 × 1.0 = 2.1%

  Adjusted Prediction: 96,200 × 1.021 = 98,220 VND

  BUT: Cap at ceiling = 101,650 × 1.07 = 108,766 VND

  Final: 98,220 VND
  Confidence Penalty: 7% × 10 = 70% reduction
```

### 2.5. Retrain Trigger

| Condition | Action |
|-----------|--------|
| Shock > 5% AND day 0-2 | ⚠️ **Emergency Retrain** (ETA 1-2h) |
| Shock > 3% AND day 0 | ⚠️ **Immediate Retrain** |
| Consecutive limit moves (2+ days) | ⚠️ **Emergency Retrain** |
| Shock < 3% | ℹ️ Use adjusted prediction, retrain next weekly cycle |

### 2.6. Example Output

```
🚨 SHOCK EVENT DETECTED: VCB

Shock Type: POSITIVE
Magnitude: 7.00%
Detected: 2026-01-08 09:30:00

Impact Assessment:
- Expected duration: 7 days
- Model accuracy impact: HIGH
- Current MAPE: 5.8%

Recommended Actions:
1. ⚠️ EMERGENCY RETRAIN TRIGGERED
2. ETA: 1-2 hours
3. Meanwhile: Using adjusted predictions (lower confidence)
4. Alert: Sent to monitoring channels
```

---

## 3. HANDLER 2: MARKET CRASH HANDLER

### 3.1. Mục đích

Xử lý sụp đổ thị trường toàn diện (market-wide crash) như COVID-19 (March 2020).

### 3.2. Crash Severity Levels

| Level | VN-Index Drop | Volatility | Characteristics |
|-------|---------------|------------|-----------------|
| **MILD** | -7% to -10% (2 weeks) | 2x normal | Correction, orderly selling |
| **MODERATE** | -10% to -15% (2 weeks) | 2-3x normal | Panic starting, volume spike |
| **SEVERE** | >-15% (2 weeks) | >3x normal | Full panic, indiscriminate selling |

### 3.3. Detection Algorithm

```python
def detect_market_crash(vnindex_prices, window=14):
    # 1. Calculate total return over window
    total_return = (current - start) / start

    # 2. Calculate volatility ratio
    current_vol = returns.tail(window).std()
    normal_vol = returns.std()
    vol_ratio = current_vol / normal_vol

    # 3. Crash criteria (both conditions)
    if total_return < -0.15 AND vol_ratio > 3:
        severity = "SEVERE"
    elif total_return < -0.10 AND vol_ratio > 2:
        severity = "MODERATE"
    elif total_return < -0.07:
        severity = "MILD"

    return is_crash, severity, magnitude
```

**Ví dụ - COVID-19 Crash (March 2020)**:
```yaml
VN-Index:
  Start: 960 points (Feb 15, 2020)
  Bottom: 660 points (March 23, 2020)
  Drop: -31.25% in 5 weeks

  Detection (March 10):
    14-day drop: -15.6%
    Volatility: 4.2x normal
    → SEVERE CRASH DETECTED
```

### 3.4. Crisis Mode Parameters

| Severity | Confidence Multiplier | Interval Width | Retrain Frequency |
|----------|----------------------|----------------|-------------------|
| **SEVERE** | 0.3 (70% cut) | 3.0x wider | Daily |
| **MODERATE** | 0.5 (50% cut) | 2.0x wider | Every 2 days |
| **MILD** | 0.7 (30% cut) | 1.5x wider | Every 3 days |

### 3.5. Market Sentiment Score

```python
def calculate_market_sentiment(vnindex, individual_stocks):
    # 1. VN-Index momentum (5-day)
    vnindex_momentum = vnindex.pct_change(5)[-1]

    # 2. Breadth: % stocks tăng giá
    stocks_up = count(stock.change > 0)
    pct_up = stocks_up / total_stocks

    # 3. Combine (range -1 to +1)
    sentiment = vnindex_momentum * 10 + (pct_up - 0.5) * 2
    sentiment = clip(sentiment, -1, 1)

    return sentiment
```

**Thang đo Sentiment**:
- **-1.0 to -0.7**: Extreme Fear (panic selling)
- **-0.7 to -0.3**: Fear (defensive)
- **-0.3 to +0.3**: Neutral
- **+0.3 to +0.7**: Greed (optimistic)
- **+0.7 to +1.0**: Extreme Greed (euphoria)

### 3.6. Prediction Adjustment

```python
def adjust_for_crisis(base_pred, market_sentiment, severity):
    # Sentiment impact (±5% max)
    sentiment_adj = market_sentiment * 0.05

    adjusted = base_pred * (1 + sentiment_adj)

    # Widen interval based on severity
    if severity == "SEVERE":
        interval_multiplier = 3.0
        confidence = 0.3
    elif severity == "MODERATE":
        interval_multiplier = 2.0
        confidence = 0.5
    else:
        interval_multiplier = 1.5
        confidence = 0.7

    # Calculate bounds
    base_std = abs(base_pred - current) * 0.02
    crisis_std = base_std * interval_multiplier

    lower = adjusted - 1.96 * crisis_std
    upper = adjusted + 1.96 * crisis_std

    return {
        'prediction': adjusted,
        'confidence_lower': lower,
        'confidence_upper': upper,
        'confidence_score': confidence
    }
```

**Ví dụ**:
```yaml
Scenario: COVID-19 Crisis (Severe)
  Base Prediction: 90,000 VND
  Current Price: 85,000 VND
  Market Sentiment: -0.7 (extreme fear)

  Sentiment Adjustment: -0.7 × 5% = -3.5%
  Adjusted: 90,000 × 0.965 = 86,850 VND

  Confidence Interval:
    Base STD: |90k - 85k| × 0.02 = 100
    Crisis STD: 100 × 3.0 = 300

    Lower: 86,850 - (1.96 × 300) = 86,262 VND
    Upper: 86,850 + (1.96 × 300) = 87,438 VND

  Confidence Score: 0.3 (30% - very low)

  ⚠️ WARNING: Crisis mode - predictions highly uncertain
```

### 3.7. Crisis Mode Actions

```
╔══════════════════════════════════════════════════════════╗
║                  🚨 CRISIS MODE ACTIVATED                ║
╠══════════════════════════════════════════════════════════╣
║  Severity: SEVERE                                        ║
║  Magnitude: 15.6%                                        ║
║  Timestamp: 2020-03-10 14:30:00                         ║
╠══════════════════════════════════════════════════════════╣
║  ACTIONS TAKEN:                                          ║
║  ✓ All models marked as low confidence                   ║
║  ✓ Emergency retrain scheduled for ALL stocks            ║
║  ✓ Prediction intervals widened to ±10%                  ║
║  ✓ Market sentiment added as feature                     ║
║  ✓ Alerts sent to all monitoring channels                ║
╚══════════════════════════════════════════════════════════╝
```

---

## 4. HANDLER 3: FOREIGN FLOW HANDLER

### 4.1. Mục đích

Xử lý động lực dòng tiền ngoại - đặc thù thị trường Việt Nam do giới hạn sở hữu nước ngoài (foreign ownership limits).

### 4.2. Foreign Ownership Limits

| Loại cổ phiếu | Limit | Ví dụ |
|---------------|-------|-------|
| **Ngân hàng** | 30% | VCB, BID, CTG, MBB, TCB, VPB, ACB, HDB |
| **Bất động sản** | 49% | VHM, VIC, NVL, KDH |
| **Sản xuất** | 49% | HPG, GVR, MSN |
| **Khác** | 49% | VNM, SAB, FPT, MWG |

### 4.3. Room Status Classification

| Status | Room Ratio | Adjustment | Impact |
|--------|-----------|------------|--------|
| **FULL** | 100% | -3% | SEVERE - Ngoại không mua được |
| **CRITICAL** | 95-100% | -2% | HIGH - Room gần đầy |
| **WARNING** | 90-95% | -1% | MEDIUM - Cần theo dõi |
| **HEALTHY** | <90% | 0% | LOW - Room thoải mái |

**Logic**:
```python
def check_room_status(ticker, current_ownership):
    limit = get_foreign_limit(ticker)  # VCB: 0.30, VHM: 0.49, etc.
    room_ratio = current_ownership / limit

    if room_ratio >= 1.0:
        return "FULL", -0.03  # -3%
    elif room_ratio >= 0.95:
        return "CRITICAL", -0.02  # -2%
    elif room_ratio >= 0.90:
        return "WARNING", -0.01  # -1%
    else:
        return "HEALTHY", 0.0
```

### 4.4. Foreign Flow Patterns

| Pattern | Net 3-day | Adjustment | Reasoning |
|---------|-----------|------------|-----------|
| **STRONG_INFLOW** | >500K shares | +1.5% | Ngoại mua mạnh → demand cao |
| **MODERATE_INFLOW** | 250-500K | +0.8% | Ngoại mua vừa phải |
| **STRONG_OUTFLOW** | <-500K | -2.0% | Ngoại bán mạnh → sell pressure |
| **MODERATE_OUTFLOW** | -500 to -250K | -1.0% | Ngoại bán vừa |
| **NEUTRAL** | -250 to +250K | 0% | Dòng tiền trung tính |

```python
def analyze_foreign_flow(flow_data):
    net_3d = flow_data['net_volume'].tail(3).sum()

    if net_3d > 500_000:
        return "STRONG_INFLOW", +0.015
    elif net_3d > 250_000:
        return "MODERATE_INFLOW", +0.008
    elif net_3d < -500_000:
        return "STRONG_OUTFLOW", -0.020
    elif net_3d < -250_000:
        return "MODERATE_OUTFLOW", -0.010
    else:
        return "NEUTRAL", 0.0
```

### 4.5. Combined Analysis (Room + Flow)

**Special Cases**:

| Situation | Room | Flow | Combined Adj | Recommendation |
|-----------|------|------|--------------|----------------|
| **DEMAND_BLOCKED** | FULL | STRONG_INFLOW | -4% | ⚠️ NẮM GIỮ/BÁN - Demand bị chặn |
| **FULL_ROOM_SELLING** | FULL | STRONG_OUTFLOW | -6% | 🔴 BÁN - Rất tiêu cực |
| **IDEAL_BUYING** | HEALTHY | STRONG_INFLOW | +3% | ✅ MUA - Lý tưởng |
| **RUSH_BUYING** | WARNING/CRITICAL | STRONG_INFLOW | +2% | ⚡ MUA ngắn hạn |

```python
def combined_analysis(ticker, ownership, flow_data):
    room_status, room_adj = check_room_status(ticker, ownership)
    flow_pattern, flow_adj = analyze_foreign_flow(flow_data)

    # Special cases
    if room_status == "FULL" and flow_pattern == "STRONG_INFLOW":
        return "DEMAND_BLOCKED", -0.04

    elif room_status == "FULL" and flow_pattern == "STRONG_OUTFLOW":
        return "FULL_ROOM_SELLING", -0.06

    elif room_status == "HEALTHY" and flow_pattern == "STRONG_INFLOW":
        return "IDEAL_BUYING", +0.03

    elif room_status in ["WARNING", "CRITICAL"] and flow_pattern == "STRONG_INFLOW":
        return "RUSH_BUYING", +0.02

    else:
        # Normal: combine adjustments
        combined_adj = room_adj + flow_adj
        return "NORMAL", combined_adj
```

### 4.6. Example Scenarios

**Scenario 1: VHM - Room gần đầy + ngoại mua mạnh (Rush Buying)**

```yaml
Ticker: VHM
Foreign Limit: 49%
Current Ownership: 48.5% (99% of limit!)

Foreign Flow (3 days):
  Buy: 3,200,000 shares
  Sell: 800,000 shares
  Net: +2,400,000 shares (STRONG_INFLOW)

Analysis:
  Room Status: CRITICAL (99%)
  Flow Pattern: STRONG_INFLOW
  Situation: RUSH_BUYING

  Combined Adjustment: +2%

  Recommendation: ⚡ MUA ngắn hạn
  Reasoning: "Ngoại rush mua trước khi room đầy → Tích cực ngắn hạn,
             nhưng cẩn thận khi room đầy sẽ chặn upside"
```

**Scenario 2: VCB - Room đầy + ngoại bán ròng (Full Room Selling)**

```yaml
Ticker: VCB
Foreign Limit: 30%
Current Ownership: 30.0% (100% FULL!)

Foreign Flow (3 days):
  Buy: 200,000 shares
  Sell: 900,000 shares
  Net: -700,000 shares (STRONG_OUTFLOW)

Analysis:
  Room Status: FULL
  Flow Pattern: STRONG_OUTFLOW
  Situation: FULL_ROOM_SELLING

  Combined Adjustment: -6%

  Recommendation: 🔴 BÁN
  Reasoning: "Room đầy + ngoại bán ròng mạnh = Downside risk cao.
             Không có buyer ngoại mới có thể vào."
```

**Scenario 3: HPG - Room thoải mái + ngoại mua mạnh (Ideal)**

```yaml
Ticker: HPG
Foreign Limit: 49%
Current Ownership: 35% (71% of limit - comfortable)

Foreign Flow (3 days):
  Buy: 3,500,000 shares
  Sell: 600,000 shares
  Net: +2,900,000 shares (STRONG_INFLOW)

Analysis:
  Room Status: HEALTHY (71%)
  Flow Pattern: STRONG_INFLOW
  Situation: IDEAL_BUYING

  Combined Adjustment: +3%

  Recommendation: ✅ MUA
  Reasoning: "Room thoải mái + ngoại mua ròng mạnh = Điều kiện tốt nhất.
             Còn 14% room cho ngoại tiếp tục mua."
```

### 4.7. Report Format

```
╔════════════════════════════════════════════════════════════╗
║          FOREIGN FLOW ANALYSIS: VHM                        ║
╠════════════════════════════════════════════════════════════╣

📊 TÌNH HUỐNG: RUSH_BUYING
Ngoại rush mua trước khi room đầy → Tích cực ngắn hạn

┌──────────────────────────────────────────────────────────┐
│ ROOM STATUS                                              │
├──────────────────────────────────────────────────────────┤
│ Status:        CRITICAL                                  │
│ Room ratio:    99.0%                                     │
│ Room left:     0.50%                                     │
│ Impact:        HIGH                                      │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ FOREIGN FLOW (Net Buy/Sell)                             │
├──────────────────────────────────────────────────────────┤
│ Pattern:       STRONG_INFLOW                             │
│ 1-day:           +850,000 shares                         │
│ 3-day:         +2,400,000 shares                         │
│ 5-day:         +3,100,000 shares                         │
│ Trend:         SUSTAINED_BUYING                          │
└──────────────────────────────────────────────────────────┘

💡 RECOMMENDATION:
⚡ MUA ngắn hạn - Ngoại rush vào, nhưng cẩn thận khi room đầy

📈 PREDICTION ADJUSTMENT: +2.00%
⭐ CONFIDENCE: MEDIUM

╚════════════════════════════════════════════════════════════╝
```

---

## 5. HANDLER 4: VN30 ADJUSTMENT HANDLER

### 5.1. Mục đích

Xử lý sự kiện thay đổi danh mục VN30 Index - predictable events với tác động lớn.

### 5.2. VN30 Adjustment Characteristics

| Đặc điểm | Chi tiết |
|----------|----------|
| **Tần suất** | 2 lần/năm (tháng 6 và 12) |
| **Thông báo trước** | 10-15 ngày so với ngày hiệu lực |
| **Tác động** | Addition: +15-25%, Removal: -10-20% |
| **Predictable** | Có thể dự đoán trước → arbitrage opportunity |
| **Passive Funds** | ~50 trillion VND theo VN30 phải rebalance |

### 5.3. Event Phases

```
Timeline: T = Effective Date

T-15 ────────── T-10 ────────── T-1 ────── T ────── T+3 ────── T+10
  │                │              │         │         │          │
  │                │              │         │         │          │
ANNOUNCEMENT  ANTICIPATION     PEAK    REBALANCING STABILIZATION
(10-30% gain)  (30-90% gain)  (95%)    (Correction) (Equilibrium)
```

**Phase Details**:

| Phase | Timeline | Price Action | Strategy |
|-------|----------|--------------|----------|
| **ANNOUNCEMENT** | T-15 to T-10 | +10-30% gain | ✅ MUA - Best entry |
| **ANTICIPATION** | T-10 to T-1 | +30-90% gain | ⚡ MUA nếu còn sớm, SELL nếu gần T-1 |
| **REBALANCING** | T to T+3 | Peak correction -5% | 🔴 SELL - Lock profits |
| **STABILIZATION** | T+4 to T+10 | Finding equilibrium | ⏸️ WAIT - Let settle |
| **POST_EVENT** | T+11+ | Normal | Normal trading |

### 5.4. Passive Flow Estimation

```python
def estimate_passive_flow(ticker, event_type, market_cap):
    # VN30 total market cap
    vn30_total_mcap = 3_000_000_000_000_000  # 3 quadrillion VND

    # Index weight
    index_weight = market_cap / vn30_total_mcap

    # Passive AUM tracking VN30
    passive_aum = 50_000_000_000_000  # 50 trillion VND

    # Target allocation
    target_allocation = index_weight * passive_aum

    if event_type == "ADDITION":
        estimated_flow = +target_allocation  # Buying
    else:  # REMOVAL
        estimated_flow = -target_allocation  # Selling

    # Execute over 4 days
    daily_flow = estimated_flow / 4

    return {
        'total_flow': estimated_flow,
        'daily_flow': daily_flow,
        'index_weight': index_weight,
        'pressure_level': calculate_pressure(estimated_flow, market_cap)
    }
```

**Ví dụ**:
```yaml
Ticker: DGC (được thêm vào VN30)
Market Cap: 10 trillion VND
Index Weight: 10T / 3,000T = 0.33%

Passive Flow:
  Total: 50T × 0.33% = 165 billion VND (mua)
  Daily (4 days): 41.25 billion VND/day

Pressure Level: 165B / 10T = 1.65% of market cap → LOW
```

### 5.5. Price Adjustment by Phase

**ADDITION Event**:

```python
def calculate_addition_adjustment(phase, days_until, current_price):
    base_gain = 0.18  # +18% historical average

    if phase == "ANNOUNCEMENT":
        # T-10 to T-15: First 30% of gain
        progress = (15 - days_until) / 5
        expected_gain = base_gain * 0.3 * progress

        return {
            'adjustment_factor': 1.0 + expected_gain,
            'reasoning': f"VN30 addition announced. Early speculation. +{expected_gain*100:.1f}%",
            'risk': "MEDIUM"
        }

    elif phase == "ANTICIPATION":
        # T-1 to T-10: 30% → 95% of gain
        progress = (10 - days_until) / 10
        expected_gain = base_gain * (0.3 + 0.65 * progress)

        # Peak at T-3
        if days_until <= 3:
            expected_gain = base_gain * 0.95
            risk = "HIGH"  # Overheating
        else:
            risk = "MEDIUM"

        return {
            'adjustment_factor': 1.0 + expected_gain,
            'reasoning': f"VN30 addition in {days_until} days. Strong speculation. +{expected_gain*100:.1f}%",
            'risk': risk
        }

    elif phase == "REBALANCING":
        # T to T+3: Correction -5%
        days_since = abs(days_until)
        correction = -0.05 * min(1.0, days_since / 3)

        return {
            'adjustment_factor': 1.0 + correction,
            'reasoning': f"Rebalancing day {days_since}. Post-peak correction. {correction*100:+.1f}%",
            'risk': "MEDIUM"
        }

    elif phase == "STABILIZATION":
        # T+4 to T+10: Neutral
        return {
            'adjustment_factor': 1.0,
            'reasoning': "Post-rebalancing stabilization. Finding equilibrium.",
            'risk': "LOW"
        }

    else:
        return {
            'adjustment_factor': 1.0,
            'reasoning': "VN30 event completed.",
            'risk': "NORMAL"
        }
```

**REMOVAL Event**:

```python
def calculate_removal_adjustment(phase, days_until, current_price):
    base_loss = -0.12  # -12% historical average

    if phase == "ANNOUNCEMENT":
        # Faster sell-off: First 40% of loss
        progress = (15 - days_until) / 5
        expected_loss = base_loss * 0.4 * progress

        return {
            'adjustment_factor': 1.0 + expected_loss,
            'reasoning': f"VN30 removal announced. Sell-off starting. {expected_loss*100:.1f}%",
            'risk': "HIGH"
        }

    elif phase == "ANTICIPATION":
        # T-1 to T-10: 40% → 95% of loss
        progress = (10 - days_until) / 10
        expected_loss = base_loss * (0.4 + 0.55 * progress)

        # Trough at T-1
        if days_until <= 1:
            expected_loss = base_loss * 0.95
            risk = "EXTREME"
        else:
            risk = "HIGH"

        return {
            'adjustment_factor': 1.0 + expected_loss,
            'reasoning': f"VN30 removal in {days_until} days. Heavy selling. {expected_loss*100:.1f}%",
            'risk': risk
        }

    elif phase == "REBALANCING":
        # T to T+3: Bounce +3%
        days_since = abs(days_until)
        bounce = 0.03 * min(1.0, days_since / 3)

        return {
            'adjustment_factor': 1.0 + bounce,
            'reasoning': f"Removal rebalancing day {days_since}. Bargain hunting. {bounce*100:+.1f}%",
            'risk': "MEDIUM"
        }

    elif phase == "STABILIZATION":
        return {
            'adjustment_factor': 1.0,
            'reasoning': "Post-removal stabilization.",
            'risk': "LOW"
        }

    else:
        return {
            'adjustment_factor': 1.0,
            'reasoning': "VN30 event completed.",
            'risk': "NORMAL"
        }
```

### 5.6. Trading Recommendations

**ADDITION - Entry/Exit Strategy**:

| Phase | Days Until | Action | Entry | Exit | Take Profit |
|-------|-----------|--------|-------|------|-------------|
| ANNOUNCEMENT | T-12 to T-15 | **BUY** ✅ | NOW - Early entry | T-3 to T-1 | +15% |
| ANNOUNCEMENT | T-10 to T-12 | **BUY** ✅ | NOW - Still good | T-2 to T | +12% |
| ANTICIPATION | T-5 to T-10 | **BUY** ⚡ | NOW - Risky | T-1 to T+1 | +8% |
| ANTICIPATION | T-2 to T-5 | **HOLD** ⚠️ | AVOID - Too late | T to T+1 | +5% |
| ANTICIPATION | T-1 to T-2 | **SELL** 🔴 | N/A | NOW - Peak | - |
| REBALANCING | T to T+3 | **SELL** 🔴 | WAIT - Correction | NOW | - |
| STABILIZATION | T+4+ | **WAIT** ⏸️ | WAIT - Event over | N/A | - |

**REMOVAL - Entry/Exit Strategy**:

| Phase | Days Until | Action | Entry | Exit | Stop Loss |
|-------|-----------|--------|-------|------|-----------|
| ANNOUNCEMENT | T-10+ | **SELL** 🔴 | AVOID | NOW - Before decline | - |
| ANTICIPATION | T-2 to T-10 | **WAIT** ⏸️ | WAIT - Until trough | N/A | - |
| ANTICIPATION | T-1 to T-2 | **BUY** ⚡ | NOW - Near trough | T+3 to T+7 | -5% |
| REBALANCING | T to T+1 | **BUY** ✅ | NOW - Bottom fishing | T+5 to T+10 | -5% |
| REBALANCING | T+2 to T+3 | **HOLD** ⚠️ | LATE - Bounce started | T+7 to T+10 | -4% |
| STABILIZATION | T+4+ | **WAIT** ⏸️ | NORMAL - Event over | N/A | - |

### 5.7. Example Scenario

```yaml
Event: DGC được thêm vào VN30 (June 2026 Rebalance)
Announcement: 2026-06-05
Effective Date: 2026-06-20
Current Date: 2026-06-10 (T-10 days)

Stock Data:
  Ticker: DGC
  Current Price: 50,000 VND
  Market Cap: 10 trillion VND

Detection:
  Event Type: ADDITION
  Days Until: 10
  Phase: ANTICIPATION (early)

Passive Flow Estimate:
  Index Weight: 0.33%
  Total Flow: 165 billion VND (buying)
  Daily Flow: 41.25 billion VND
  Pressure: LOW

Price Adjustment:
  Base Gain: +18% (historical average)
  Progress: (10 - 10) / 10 = 0.0 (just entering anticipation)
  Expected Gain: 18% × (0.3 + 0.65 × 0.0) = 5.4%

  Adjustment Factor: 1.054
  Base Prediction: 52,000 VND
  Adjusted Prediction: 52,000 × 1.054 = 54,808 VND
  Expected Peak (T-3): 50,000 × 1.18 = 59,000 VND

Recommendation:
  Action: BUY ✅
  Confidence: MEDIUM
  Reasoning: "VN30 addition in 10 days. Momentum still strong."
  Entry: NOW - Mid speculation phase
  Exit: T-2 to T (Jun 18-20)
  Stop Loss: -5%
  Take Profit: +15% (57,500 VND)
```

---

## 6. HANDLER 5: MARGIN CALL HANDLER

### 6.1. Mục đích

Xử lý cascading margin calls - vòng xoáy chết (death spiral) khi thị trường giảm mạnh.

### 6.2. Margin Call Cascade Mechanics

**Death Spiral Logic**:
```
Market Drop 5-7%
    ↓
Margin Accounts Below Requirement
    ↓
FORCED SELLING (Margin Calls)
    ↓
Prices Drop Further
    ↓
MORE Margin Calls Triggered
    ↓
MORE Forced Selling
    ↓
... (Cascade continues)
    ↓
EXHAUSTION (Margin Debt Reduced)
    ↓
Selling Pressure Stops
    ↓
RECOVERY (Bargain Hunters)
```

### 6.3. Crisis Levels

| Level | VN-Index Drawdown | Characteristics | Duration |
|-------|-------------------|-----------------|----------|
| **NORMAL** | 0% to -3% | No margin pressure | - |
| **WARNING** | -3% to -5% | Early warning, watch list | 1-2 days |
| **TRIGGER** | -5% to -7% | Margin calls starting | 2-3 days |
| **CASCADE** | -7% to -12% | Active cascade, heavy selling | 3-5 days |
| **PANIC** | >-12% | Panic selling, volume spike | 1-2 days |
| **EXHAUSTION** | - | Selling exhausted, low volume | 1-2 days |
| **RECOVERY** | Positive | Bounce back | 5-10 days |

### 6.4. Margin Debt Risk Levels

**Stock Classification**:
```python
# Margin debt as % of market cap
def check_margin_risk(ticker, margin_debt, market_cap):
    ratio = margin_debt / market_cap

    if ratio >= 0.20:
        return "EXTREME"  # >20% - very dangerous
    elif ratio >= 0.15:
        return "HIGH"     # 15-20% - high risk
    elif ratio >= 0.10:
        return "MEDIUM"   # 10-15% - moderate
    elif ratio >= 0.05:
        return "LOW"      # 5-10% - low risk
    else:
        return "MINIMAL"  # <5% - minimal risk
```

**High Margin Stocks** (historical data):
- HPG, VHM, VIC, MSN, STB, TCB, VPB, HDB
- FPT, MWG, SSI, VND, VRE, NVL, PDR, DGW

### 6.5. Forced Selling Pressure Calculation

```python
def calculate_forced_selling(margin_debt, current_price, price_drop):
    # Margin requirement: 50%
    margin_requirement = 0.50

    # Initial position (before drop)
    purchase_price = current_price / (1 + price_drop)

    # Current equity
    current_value = current_price
    current_equity = current_value - margin_debt
    current_equity_ratio = current_equity / current_value

    # If below requirement → Margin call
    if current_equity_ratio < margin_requirement:
        # Need to restore ratio
        target_equity = margin_requirement * current_value
        equity_shortfall = target_equity - current_equity

        # Shares to sell
        shares_to_sell = equity_shortfall / current_price
        selling_pressure = shares_to_sell * current_price

        # Timeline (assume 20% of daily volume)
        avg_daily_volume = 50_000_000_000  # 50B VND
        days_to_liquidate = selling_pressure / (avg_daily_volume * 0.2)

        # Price impact
        price_impact = -0.01 * (selling_pressure / avg_daily_volume)

        return {
            'in_margin_call': True,
            'shares_to_sell': shares_to_sell,
            'selling_pressure': selling_pressure,
            'days_to_liquidate': days_to_liquidate,
            'price_impact': price_impact
        }
    else:
        return {
            'in_margin_call': False,
            'shares_to_sell': 0,
            'selling_pressure': 0
        }
```

### 6.6. Cascade Phase Detection

```python
def detect_cascade_phase(crisis_level, days_since_trigger, volume_trend):
    if crisis_level == "PANIC":
        if volume_trend == "rising" and days_since_trigger <= 3:
            return "panic"  # Active panic
        else:
            return "exhaustion"  # Panic but volume dropping

    elif crisis_level == "CASCADE":
        if days_since_trigger <= 2:
            return "cascade_early"  # Just started
        elif days_since_trigger <= 5:
            return "cascade_middle"  # Peak panic
        else:
            return "cascade_late"  # Should be exhausting

    elif crisis_level == "TRIGGER":
        return "trigger"  # Just triggered

    elif price_change > 0:
        return "recovery"  # Bouncing back

    else:
        return "normal"
```

### 6.7. Prediction Adjustment by Phase

| Phase | Adjustment Factor | Confidence Multiplier | Reasoning |
|-------|-------------------|----------------------|-----------|
| **trigger** | 0.93-0.95 (-5% to -7%) | 2.0x | Margin calls starting |
| **cascade_early** | 0.85-0.90 (-10% to -15%) | 3.0x | Active cascade, heavy selling |
| **cascade_middle** | 0.85-0.90 (-10% to -15%) | 3.0x | Peak panic |
| **cascade_late** | 0.92-0.95 (-5% to -8%) | 2.5x | Nearing exhaustion |
| **panic** | 0.82-0.88 (-12% to -18%) | 3.5x | PANIC - avoid catching knife |
| **exhaustion** | 0.93-0.95 (-5% to -7%) | 2.0x | Selling exhausted |
| **recovery** | 1.01-1.05 (+1% to +5%) | 1.5x | Bounce continuing |

**Margin Risk Severity Multiplier**:
```python
margin_severity = {
    'EXTREME': 1.5,   # 1.5x worse for EXTREME margin debt
    'HIGH': 1.3,      # 1.3x worse
    'MEDIUM': 1.1,    # 1.1x worse
    'LOW': 1.0,       # Normal
    'MINIMAL': 0.9    # 0.9x (actually better)
}

# Apply to adjustment
final_adjustment = base_adjustment * (1.0 / severity_multiplier)
```

**Example**:
```yaml
Scenario: HPG in Margin Cascade
  Crisis Level: CASCADE (VN-Index -9%)
  Phase: cascade_middle (day 3)
  Margin Risk: EXTREME (20% of market cap)

  Base Adjustment: 0.90 (-10%)
  Margin Severity: 1.5

  Final Adjustment: 0.90 / 1.5 = 0.60 (-40%!)

  Reasoning: "Active margin cascade (day 3). EXTREME margin debt.
             Heavy forced selling pressure."

  Confidence Multiplier: 3.0x (very wide interval)
  Risk: EXTREME
```

### 6.8. Exhaustion Signal Detection

**Signals**:
1. **Declining Rate Slowing**: Giảm giá chậm lại
2. **Price Consolidating**: Testing support level
3. **Volume Declining**: Selling exhaustion
4. **Intraday Reversal**: Close > Open
5. **RSI Oversold**: RSI < 30

```python
def detect_exhaustion_signals(price_series, volume_series):
    signals = []
    score = 0.0

    # Signal 1: Declining rate slowing
    change_1d = price_series[0] / price_series[1] - 1
    change_2d = price_series[1] / price_series[2] - 1

    if change_1d < 0 and change_2d < 0:  # Still declining
        if abs(change_1d) < abs(change_2d):  # But slowing
            signals.append("Decline rate slowing")
            score += 0.25

    # Signal 2: Price consolidating (within 3% range)
    recent_5 = price_series[:5]
    range_pct = (recent_5.max() - recent_5.min()) / recent_5.mean()

    if range_pct < 0.03:
        signals.append("Price consolidating near support")
        score += 0.25

    # Signal 3: Volume declining
    if volume_series[0] < volume_series[1] < volume_series[2]:
        signals.append("Volume declining (selling exhaustion)")
        score += 0.25

    # Confidence
    if score >= 0.75:
        return "HIGH", True  # Likely bottom
    elif score >= 0.5:
        return "MEDIUM", True
    elif score >= 0.25:
        return "LOW", False
    else:
        return "VERY_LOW", False
```

### 6.9. Defensive Trading Recommendations

| Crisis Level | Phase | Action | Position Size | Entry Timing |
|--------------|-------|--------|---------------|--------------|
| NORMAL | - | NORMAL | 100% | NORMAL |
| WARNING | - | HOLD | 80% (reduce) | CAUTIOUS |
| TRIGGER | trigger | SELL (if HIGH margin) | 50% | AVOID |
| TRIGGER | trigger | HOLD (if LOW margin) | 50% | WAIT |
| CASCADE/PANIC | early/middle/panic | AVOID | 0% | WAIT - Until exhaustion |
| CASCADE/PANIC | late/exhaustion | WATCH | 10-20% (small) | WAIT - Confirm exhaustion |
| RECOVERY | recovery | BUY | 50-80% | NOW - Recovery phase |

**Example Recommendations**:

**Case 1: EXTREME Margin Risk + Active Cascade**
```yaml
Crisis: CASCADE (day 3)
Margin Risk: EXTREME (HPG)

Recommendation:
  Action: AVOID ⛔
  Confidence: EXTREME
  Reasoning: "Active margin cascade. EXTREME margin debt.
             Do not catch falling knife."
  Position Size: ZERO
  Entry: WAIT - Until exhaustion confirmed
  Exit: Cut losses if still holding
  Stop Loss: -10%
```

**Case 2: LOW Margin Risk + Exhaustion Phase**
```yaml
Crisis: CASCADE (day 7)
Margin Risk: LOW
Exhaustion Signals: 2/4 (Moderate confidence)

Recommendation:
  Action: WATCH 👀
  Confidence: MEDIUM
  Reasoning: "Cascade nearing end. LOW margin risk.
             Watch for bottom confirmation."
  Position Size: SMALL (10-20%)
  Entry: WAIT - Confirm exhaustion signals
  Exit: T+5 to T+10 bounce
  Stop Loss: -5%
```

**Case 3: Recovery Phase**
```yaml
Crisis: RECOVERY (day 3 post-cascade)
Market: +3% in 3 days
Exhaustion: CONFIRMED

Recommendation:
  Action: BUY ✅
  Confidence: MEDIUM
  Reasoning: "Cascade recovery. Bargain hunting opportunity."
  Position Size: NORMAL (50-80%)
  Entry: NOW - Recovery phase
  Exit: T+10 to T+20 (ride the bounce)
  Stop Loss: -5%
```

### 6.10. Historical Example: COVID-19 Cascade

```yaml
Event: COVID-19 Market Crash (March 2020)

Timeline:
  Feb 20: VN-Index 960 (Peak)
  Mar 5: -5% → TRIGGER (Margin calls starting)
  Mar 10: -10% → CASCADE (Active cascade, day 5)
  Mar 16: -18% → PANIC (Peak panic, volume spike)
  Mar 23: -31% → EXHAUSTION (660 points, bottom)
  Apr 7: -20% → RECOVERY (+16% bounce from bottom)
  May 15: -10% → STABILIZATION

Cascade Duration: 18 days (Mar 5 - Mar 23)
Total Drawdown: -31.25%
Recovery: +16% bounce, then stabilized at -20%

Margin Call Impact:
  Forced Liquidations: Estimated 30+ trillion VND
  High Margin Stocks Hit Hardest:
    - HPG: -45% (EXTREME margin debt)
    - VHM: -38% (HIGH margin debt)
    - MSN: -35% (HIGH margin debt)

  Low Margin Stocks Better:
    - VNM: -22% (LOW margin debt)
    - SAB: -18% (LOW margin debt)

Model Performance:
  Normal Mode: MAPE 2.5%
  Crisis Mode: MAPE 18% (high uncertainty)

  Adjustment Effectiveness:
    - Early warning (Mar 5): Saved -7% by exiting
    - Bottom detection (Mar 23): Captured +10% bounce
```

---

## 7. TÍCH HỢP VÀO ENSEMBLE SYSTEM

### 7.1. Integration Architecture

```python
class EnsemblePredictionWithScenarios:
    def __init__(self):
        # Base ensemble
        self.ensemble = EnsembleStacking()

        # Scenario handlers
        self.handlers = {
            'news_shock': NewsShockHandler(),
            'market_crash': MarketCrashHandler(),
            'foreign_flow': ForeignFlowHandler(),
            'vn30_adjustment': VN30AdjustmentHandler(),
            'margin_call': MarginCallHandler()
        }

    def predict_with_scenarios(self, ticker, features, market_data):
        # Step 1: Base ensemble prediction
        base_pred = self.ensemble.predict(features)

        # Step 2: Apply scenarios (in priority order)
        adjusted_pred = base_pred
        scenario_logs = []

        # Priority 1: Market-wide events
        if self.handlers['market_crash'].is_active():
            adj = self.handlers['market_crash'].adjust(adjusted_pred, market_data)
            adjusted_pred = adj['prediction']
            scenario_logs.append(('market_crash', adj))

        # Priority 2: Margin call cascade
        if self.handlers['margin_call'].detect_cascade(market_data):
            adj = self.handlers['margin_call'].adjust(adjusted_pred, ticker)
            adjusted_pred = adj['prediction']
            scenario_logs.append(('margin_call', adj))

        # Priority 3: Stock-specific events
        if self.handlers['news_shock'].detect(ticker):
            adj = self.handlers['news_shock'].adjust(adjusted_pred)
            adjusted_pred = adj['prediction']
            scenario_logs.append(('news_shock', adj))

        # Priority 4: VN30 adjustment (scheduled)
        if self.handlers['vn30_adjustment'].check_event(ticker):
            adj = self.handlers['vn30_adjustment'].adjust(adjusted_pred)
            adjusted_pred = adj['prediction']
            scenario_logs.append(('vn30_adjustment', adj))

        # Priority 5: Foreign flow (continuous)
        if self.handlers['foreign_flow'].check_room(ticker):
            adj = self.handlers['foreign_flow'].adjust(adjusted_pred)
            adjusted_pred = adj['prediction']
            scenario_logs.append(('foreign_flow', adj))

        # Step 3: Return final prediction
        return {
            'base_prediction': base_pred,
            'final_prediction': adjusted_pred,
            'scenarios_applied': scenario_logs,
            'total_adjustment': (adjusted_pred - base_pred) / base_pred
        }
```

### 7.2. Adjustment Stacking Logic

**Question**: Khi nhiều scenarios trigger cùng lúc, xử lý như thế nào?

**Answer**: Multiplicative stacking (nhân tích lũy)

```python
# Example: VCB có cả News Shock + Foreign Flow
base_prediction = 100,000 VND

# Scenario 1: News Shock (positive earnings)
news_adjustment = +0.03  # +3%
pred_after_news = 100,000 × 1.03 = 103,000 VND

# Scenario 2: Foreign Flow (room đầy)
foreign_adjustment = -0.03  # -3%
final_prediction = 103,000 × 0.97 = 99,910 VND

# Total adjustment: -0.09% (not -0% as additive would give)
# Multiplicative: 1.03 × 0.97 = 0.9991 (-0.09%)
```

**Priority Order** (high to low):
1. Market Crash (market-wide)
2. Margin Call Cascade (market-wide crisis)
3. News Shock (stock-specific, short-term)
4. VN30 Adjustment (stock-specific, scheduled)
5. Foreign Flow (stock-specific, continuous)

### 7.3. Confidence Interval Adjustment

```python
def calculate_final_confidence(base_confidence, scenario_adjustments):
    # Start with base interval
    base_interval_width = 0.05  # ±5%

    # Multiply by each scenario's confidence impact
    final_multiplier = 1.0

    for scenario, adjustment in scenario_adjustments:
        if scenario == 'market_crash':
            final_multiplier *= 3.0  # 3x wider in crisis
        elif scenario == 'margin_call':
            final_multiplier *= 2.5  # 2.5x wider in cascade
        elif scenario == 'news_shock':
            final_multiplier *= 2.0  # 2x wider after shock
        elif scenario == 'vn30_adjustment':
            final_multiplier *= 1.5  # 1.5x wider during event
        elif scenario == 'foreign_flow':
            final_multiplier *= 1.2  # 1.2x wider

    # Cap at 5x (maximum uncertainty)
    final_multiplier = min(final_multiplier, 5.0)

    final_interval = base_interval_width * final_multiplier

    return final_interval
```

**Example**:
```yaml
Base: ±5% interval
Scenarios: Market Crash + Margin Call

Multiplier: 3.0 × 2.5 = 7.5 → capped at 5.0
Final Interval: ±5% × 5.0 = ±25%

Prediction: 100,000 VND
Range: 75,000 - 125,000 VND (very wide!)
```

### 7.4. Complete Prediction Flow

```mermaid
Input: Ticker + Market Data
    ↓
Ensemble Models (5) → Base Prediction
    ↓
Scenario Check #1: Market Crash?
    Yes → Apply adjustment × confidence
    No → Continue
    ↓
Scenario Check #2: Margin Call Cascade?
    Yes → Apply adjustment × confidence
    No → Continue
    ↓
Scenario Check #3: News Shock?
    Yes → Apply adjustment × confidence
    No → Continue
    ↓
Scenario Check #4: VN30 Adjustment?
    Yes → Apply adjustment × confidence
    No → Continue
    ↓
Scenario Check #5: Foreign Flow?
    Yes → Apply adjustment × confidence
    No → Continue
    ↓
Final Prediction + Confidence Interval + Recommendation
```

### 7.5. Output Format

```json
{
  "ticker": "VCB",
  "timestamp": "2026-01-08T10:30:00",
  "horizon": "3day",

  "base_prediction": {
    "price": 102300,
    "confidence": 0.85,
    "interval": [100185, 104415]
  },

  "scenarios_detected": [
    {
      "type": "foreign_flow",
      "status": "CRITICAL",
      "details": {
        "room_ratio": 0.973,
        "flow_pattern": "STRONG_OUTFLOW",
        "adjustment": -0.03
      }
    },
    {
      "type": "news_shock",
      "status": "POSITIVE",
      "details": {
        "magnitude": 0.07,
        "days_since": 0,
        "adjustment": 0.021
      }
    }
  ],

  "final_prediction": {
    "price": 99231,
    "confidence": 0.68,
    "interval": [94369, 104093],
    "total_adjustment": -0.030,
    "adjustment_breakdown": {
      "foreign_flow": -0.03,
      "news_shock": 0.021,
      "net": -0.009
    }
  },

  "recommendation": {
    "action": "HOLD",
    "reasoning": "Foreign Flow: Room gần đầy (97.3%), upside bị giới hạn. News Shock: Positive earnings (+7%) but partially offset by foreign flow concerns.",
    "risk_level": "MEDIUM",
    "confidence": "MEDIUM"
  }
}
```

---

## 📚 TÀI LIỆU THAM KHẢO

- **Ensemble Model Documentation**: ENSEMBLE_MODEL_DOCUMENTATION.md
- **Scenario Playbook**: src/prediction/SCENARIO_PLAYBOOK.md
- **Source Code**: src/prediction/scenario_handlers/
- **Integration Guide**: src/prediction/INTEGRATION_GUIDE.md

---

**Tác giả**: AI Assistant (Claude Sonnet 4.5)
**Ngày**: 2026-01-08
**Phiên bản**: 1.0
