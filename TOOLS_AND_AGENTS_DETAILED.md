# 📚 CHI TIẾT CÁC TOOLS VÀ AGENTS TRONG HỆ THỐNG

## I. KIẾN TRÚC TỔNG QUAN

Hệ thống sử dụng **8 Specialized Agents** + **25+ MCP Tools** để phân tích chứng khoán Việt Nam.

```
┌─────────────────────────────────────┐
│   Users (CLI, Discord, Streamlit)   │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│   MCP Orchestrator Server           │
│   - Query Router                    │
│   - Process Manager                 │
└────────────┬────────────────────────┘
             │
      ┌──────┴──────────────────────────────┐
      │                                     │
 ┌────▼────────────┐          ┌────────────▼─────┐
 │ Direct Executor │          │ 8 Agents System  │
 │ (Fast Mode)    │          │ (Complex Mode)   │
 └────────────────┘          └────────────────────┘
       │                            │
       └──────────┬─────────────────┘
                  │
          ┌───────▼────────────┐
          │  25+ MCP Tools     │
          │  (Database Access) │
          └────────────────────┘
```

---

## II. 8 SPECIALIZED AGENTS

### 1. **AnalysisSpecialist** - Phân tích cổ phiếu
**Mục đích**: Phân tích kỹ thuật, cơ bản, dự đoán giá cổ phiếu

**Các tools được phép dùng**:
```
Stock Data:
- get_stock_data (5 calls max)
- get_stock_price_prediction (3 calls max)
- generate_chart_from_data (3 calls max)
- get_stock_details_from_tcbs (10 calls max)

Financial:
- get_financial_data (3 calls max)
- get_financial_ratios (5 calls max)

AI Analysis:
- gemini_summarize (3 calls max)
- gemini_search_and_summarize (2 calls max)

Chart:
- generate_chart_from_data (3 calls max)
```

**Giới hạn**: $0.50/truy vấn, max 0.5 giây

**Ví dụ lệnh**:
- "Phân tích kỹ thuật VCB"
- "Dự đoán giá FPT 7 ngày"
- "Biểu đồ HPG 30 ngày"

---

### 2. **ScreenerSpecialist** - Lọc cổ phiếu
**Mục đích**: Tìm kiếm, lọc, xếp hạng cổ phiếu theo tiêu chí

**Các tools được phép dùng**:
```
Screening:
- screen_stocks (3 calls max)
- get_screener_columns (1 call max)
- filter_stocks_by_criteria (5 calls max)
- rank_stocks_by_score (3 calls max)

Support:
- get_stock_details_from_tcbs (10 calls max)
- get_financial_data (3 calls max)
```

**Giới hạn**: $0.20/truy vấn

**Ví dụ lệnh**:
- "Lọc cổ phiếu P/E < 15, Dividend > 3%"
- "Tìm cổ phiếu growth trong ngành IT"
- "Xếp hạng cổ phiếu theo điểm"

---

### 3. **InvestmentPlanner** - Lập kế hoạch đầu tư
**Mục đích**: Hỗ trợ quy hoạch đầu tư, phân bổ danh mục, chiến lược

**Các tools được phép dùng**:
```
Planning:
- gather_investment_profile (1 call max)
- calculate_portfolio_allocation (1 call max)
- generate_entry_strategy (1 call max)
- generate_risk_management_plan (1 call max)
- generate_monitoring_plan (1 call max)

Support:
- get_stock_data (5 calls max)
- get_financial_data (3 calls max)
```

**Giới hạn**: $0.30/truy vấn

**Ví dụ lệnh**:
- "Lập kế hoạch đầu tư 100 triệu đồng, mức rủi ro cao"
- "Chiến lược vào lệnh cho VCB"
- "Kế hoạch quản lý rủi ro cho danh mục"

---

### 4. **DiscoverySpecialist** - Khám phá cơ hội
**Mục đích**: Tìm kiếm cổ phiếu tiềm năng, recommendations

**Các tools được phép dùng**:
```
Discovery:
- discover_stocks_by_profile (2 calls max)
- search_potential_stocks (3 calls max)
- filter_stocks_by_criteria (5 calls max)
- rank_stocks_by_score (3 calls max)

Support:
- get_stock_details_from_tcbs (10 calls max)
- gemini_search_and_summarize (3 calls max)
- get_stock_data (5 calls max)
```

**Giới hạn**: $0.40/truy vấn

**Ví dụ lệnh**:
- "Tìm cổ phiếu tương tự FPT"
- "Khám phá cổ phiếu tiềm năng tăng trưởng"
- "Recommendation dựa trên hồ sơ đầu tư"

---

### 5. **AlertManager** - Quản lý cảnh báo
**Mục đích**: Tạo, xem, xóa cảnh báo giá

**Các tools được phép dùng**:
```
Alerts:
- create_alert (5 calls max)
- get_user_alerts (3 calls max)
- delete_alert (5 calls max)
```

**Giới hạn**: $0.05/truy vấn

**Ví dụ lệnh**:
- "Cảnh báo khi VCB > 90,000"
- "Xem cảnh báo của tôi"
- "Xóa cảnh báo VCB"

---

### 6. **SubscriptionManager** - Quản lý theo dõi
**Mục đích**: Quản lý danh sách cổ phiếu theo dõi

**Các tools được phép dùng**:
```
Subscriptions:
- create_subscription (5 calls max)
- get_user_subscriptions (3 calls max)
- delete_subscription (5 calls max)
```

**Giới hạn**: $0.05/truy vấn

**Ví dụ lệnh**:
- "Theo dõi HPG"
- "Danh sách theo dõi của tôi"
- "Bỏ theo dõi VNM"

---

### 7. **MarketContextSpecialist** - Cảnh báo thị trường
**Mục đích**: Cung cấp cảnh báo thị trường chung (VN-Index, ngành, breadth)

**Các tools được phép dùng**:
```
Market Data:
- get_market_overview (1 call max)
- get_sector_performance (2 calls max)
- get_market_top_movers (1 call max)
- screen_stocks (3 calls max)
```

**Giới hạn**: $0.15/truy vấn

**Ví dụ lệnh**:
- "Cảnh báo thị trường"
- "Hiệu suất ngành hôm nay"
- "Top gainers, losers"

---

### 8. **ComparisonSpecialist** - So sánh cổ phiếu
**Mục đích**: So sánh cổ phiếu, phân tích peer

**Các tools được phép dùng**:
```
Comparison:
- compare_stocks (5 calls max)
- get_peer_stocks (3 calls max)
- get_stock_details_from_tcbs (10 calls max)
- get_financial_ratios (5 calls max)
```

**Giới hạn**: $0.25/truy vấn

**Ví dụ lệnh**:
- "So sánh VCB vs HPG"
- "Peer stocks của FPT"

---

## III. 25+ MCP TOOLS - CHI TIẾT

### A. STOCK DATA TOOLS (4 tools)

#### 1️⃣ **get_stock_data**
```yaml
Mô tả: Lấy dữ liệu giá cổ phiếu lịch sử + indicators
Input:
  - symbol: "VCB" (string)
  - start_date: "2025-01-01" (optional)
  - end_date: "2025-01-14" (optional)
  - interval: "1m", "5m", "15m", "1h", "1d" (default)
  
Output:
  - price: OHLCV (Open, High, Low, Close, Volume)
  - technical_indicators: MA20, MA50, RSI, MACD, Bollinger Bands
  - timestamp: Ngày giờ

Chi phí: $0.01/call
Thời gian: ~1 giây
Max calls: 5/truy vấn
Ví dụ: "Lấy giá VCB từ 2025-01-01 đến 2025-01-14"
```

#### 2️⃣ **get_stock_price_prediction**
```yaml
Mô tả: Dự đoán giá cổ phiếu bằng AI Ensemble
Input:
  - symbol: "FPT" (string)
  - table_type: "3d" (3 ngày) hoặc "48d" (48 ngày)
  
Output:
  - predictions: [Ngày, Giá dự đoán, Confidence]
  - model: "LSTM + ARIMA + XGBoost"
  - accuracy: R² score

Chi phí: $0.02/call
Thời gian: ~1.5 giây
Max calls: 3/truy vấn
Ví dụ: "Dự đoán giá FPT 7 ngày"
```

#### 3️⃣ **generate_chart_from_data**
```yaml
Mô tả: Tạo biểu đồ nến (candlestick) interactive
Input:
  - symbol: "HPG" (string)
  - data: Historical OHLCV
  - indicators: ["MA20", "RSI", "MACD"] (optional)
  
Output:
  - chart_html: Interactive Plotly chart
  - saved_path: ~/Downloads/HPG_2025-01-14.html
  - status: "success"

Chi phí: $0.05/call
Thời gian: ~2 giây
Max calls: 3/truy vấn
Ví dụ: "Vẽ biểu đồ VCB 30 ngày"
```

#### 4️⃣ **get_stock_details_from_tcbs**
```yaml
Mô tả: Lấy chi tiết cổ phiếu từ TCBS (70+ fields)
Input:
  - symbols: ["VCB", "HPG"] (list)
  
Output:
  - Thông tin cơ bản: Tên, ngành, giá, P/E, P/B, Dividend
  - Chỉ báo kỹ thuật: RSI, MACD, Bollinger Bands
  - Tin tức, xu hướng
  - Bảng xếp hạng, rating

Chi phí: $0.01/call
Thời gian: ~0.5 giây
Max calls: 10/truy vấn
Ví dụ: "Chi tiết VCB, FPT, HPG"
```

---

### B. FINANCIAL DATA TOOLS (6 tools)

#### 5️⃣ **get_financial_data**
```yaml
Mô tả: Lấy báo cáo tài chính (BCTC, KQKD, LCCT)
Input:
  - symbol: "VCB" (string)
  - report_type: "balance_sheet", "income", "cash_flow"
  - period: "Q3/2025", "9M/2025", "FY/2024"
  
Output:
  - balance_sheet: Tài sản, nợ, vốn chủ
  - income_statement: Doanh thu, lợi nhuận
  - cash_flow: Lưu chuyển tiền

Chi phí: $0.02/call
Thời gian: ~1.5 giây
Max calls: 3/truy vấn
Ví dụ: "Báo cáo tài chính VCB Q3/2025"
```

#### 6️⃣ **get_financial_ratios**
```yaml
Mô tả: Tính toán tỷ lệ tài chính (ROE, ROA, EPS, etc)
Input:
  - symbol: "FPT" (string)
  
Output:
  - Profitability: ROE, ROA, Net Margin
  - Liquidity: Current Ratio, Quick Ratio
  - Valuation: P/E, P/B, EV/EBITDA
  - Efficiency: Asset Turnover, Debt/Equity

Chi phí: $0.01/call
Thời gian: ~0.5 giây
Max calls: 5/truy vấn
Ví dụ: "Tỷ lệ tài chính FPT"
```

#### 7️⃣ **get_income_statement**
```yaml
Mô tả: Bảng KQKD chi tiết
Input:
  - symbol: "HPG" (string)
  - periods: 4 (Q1, Q2, Q3, Q4 gần nhất)
  
Output:
  - Revenue, Cost of Goods Sold, Gross Profit
  - Operating Expenses, Operating Income
  - Net Income, EPS

Chi phí: $0.02/call
Max calls: 3/truy vấn
Ví dụ: "KQKD HPG 4 quý gần nhất"
```

#### 8️⃣ **get_cash_flow**
```yaml
Mô tả: Bảng LCCT chi tiết
Input:
  - symbol: "VCB" (string)
  
Output:
  - Operating Cash Flow
  - Investing Cash Flow
  - Financing Cash Flow
  - Free Cash Flow

Chi phí: $0.02/call
Max calls: 3/truy vấn
Ví dụ: "Lưu chuyển tiền VCB"
```

#### 9️⃣ **get_ratio**
```yaml
Mô tả: Lấy tỷ lệ cụ thể (P/E, P/B, Dividend)
Input:
  - symbol: "FPT" (string)
  - ratio_type: "PE", "PB", "DIVIDEND", "EPS"
  
Output:
  - Giá trị tỷ lệ hiện tại
  - So sánh với ngành, thị trường
  - Xu hướng lịch sử (1Y, 3Y, 5Y)

Chi phí: $0.01/call
Max calls: 5/truy vấn
```

#### 🔟 **get_price**
```yaml
Mô tả: Lấy giá cổ phiếu real-time
Input:
  - symbols: ["VCB", "HPG", "FPT"] (list)
  
Output:
  - Current Price
  - Change %
  - Bid/Ask
  - Volume
  - Updated: timestamp

Chi phí: $0.01/call
Max calls: 10/truy vấn
Ví dụ: "Giá VCB hiện tại"
```

---

### C. ALERT MANAGEMENT TOOLS (3 tools)

#### 1️⃣1️⃣ **create_alert**
```yaml
Mô tả: Tạo cảnh báo giá/chỉ báo
Input:
  - user_id: "user123" (string)
  - symbol: "VCB" (string)
  - alert_type: "price", "technical" (enum)
  - condition: ">" hoặc "<" (enum)
  - value: 90000 (number)
  - indicator: "RSI", "MACD", "MA20" (for technical)
  
Output:
  - alert_id: "alert_xyz123"
  - status: "active"
  - created_at: timestamp

Chi phí: $0.01/call
Max calls: 5/truy vấn
Ví dụ: "Cảnh báo khi VCB > 90000"
```

#### 1️⃣2️⃣ **get_user_alerts**
```yaml
Mô tả: Lấy danh sách cảnh báo của user
Input:
  - user_id: "user123" (string)
  - symbol: "VCB" (optional) (string)
  
Output:
  - alerts: [
      {alert_id, symbol, condition, value, status, created_at}
    ]
  - count: số cảnh báo

Chi phí: $0.01/call
Max calls: 3/truy vấn
Ví dụ: "Xem cảnh báo của tôi"
```

#### 1️⃣3️⃣ **delete_alert**
```yaml
Mô tả: Xóa cảnh báo
Input:
  - alert_id: "alert_xyz123" (string)
  - user_id: "user123" (string)
  
Output:
  - status: "deleted"
  - alert_id: "alert_xyz123"

Chi phí: $0.01/call
Max calls: 5/truy vấn
Ví dụ: "Xóa cảnh báo VCB"
```

---

### D. SUBSCRIPTION TOOLS (3 tools)

#### 1️⃣4️⃣ **create_subscription**
```yaml
Mô tả: Theo dõi cổ phiếu (watchlist)
Input:
  - user_id: "user123" (string)
  - symbol: "HPG" (string)
  - notes: "Watch for earnings" (optional)
  
Output:
  - sub_id: "sub_abc123"
  - symbol: "HPG"
  - status: "active"
  - created_at: timestamp

Chi phí: $0.01/call
Max calls: 5/truy vấn
Ví dụ: "Theo dõi HPG"
```

#### 1️⃣5️⃣ **get_user_subscriptions**
```yaml
Mô tả: Lấy danh sách cổ phiếu đang theo dõi
Input:
  - user_id: "user123" (string)
  
Output:
  - subscriptions: [
      {symbol, notes, created_at, current_price}
    ]
  - count: số cổ phiếu theo dõi

Chi phí: $0.01/call
Max calls: 3/truy vấn
Ví dụ: "Danh sách theo dõi"
```

#### 1️⃣6️⃣ **delete_subscription**
```yaml
Mô tả: Bỏ theo dõi cổ phiếu
Input:
  - sub_id: "sub_abc123" (string)
  - user_id: "user123" (string)
  
Output:
  - status: "deleted"
  - symbol: "HPG"

Chi phí: $0.01/call
Max calls: 5/truy vấn
Ví dụ: "Bỏ theo dõi VNM"
```

---

### E. AI ANALYSIS TOOLS (3 tools) - EXPENSIVE

#### 1️⃣7️⃣ **gemini_summarize**
```yaml
Mô tả: Tóm tắt dữ liệu bằng Gemini AI
Input:
  - data: {text hoặc dữ liệu cụ thể}
  - context: "technical" / "fundamental" / "news"
  - length: "short" (100 từ) / "medium" (300 từ) / "long" (500 từ)
  
Output:
  - summary: Tóm tắt chuyên sâu
  - key_points: [Điểm chính]
  - sentiment: "bullish" / "neutral" / "bearish"

Chi phí: $0.10/call ⚠️ ĐẮT
Max calls: 3/truy vấn
Thời gian: ~2 giây
Ví dụ: "Tóm tắt báo cáo FPT"
```

#### 1️⃣8️⃣ **gemini_search_and_summarize**
```yaml
Mô tả: Tìm kiếm web + tóm tắt bằng Gemini
Input:
  - query: "VCB earnings q4 2024" (string)
  - num_results: 5-10 (int)
  
Output:
  - sources: [URLs]
  - summary: Tóm tắt từ nhiều nguồn
  - sentiment: Cảm nhận thị trường

Chi phí: $0.15/call ⚠️ RẤT ĐẮT
Max calls: 2/truy vấn
Thời gian: ~3 giây
Ví dụ: "Tìm tin về VCB Q4 2024"
```

#### 1️⃣9️⃣ **batch_summarize**
```yaml
Mô tả: Tóm tắt hàng loạt symbols
Input:
  - symbols: ["VCB", "HPG", "FPT"] (list)
  - context: "comparison"
  
Output:
  - summaries: {symbol: tóm tắt}
  - comparison: So sánh

Chi phí: $0.20/call ⚠️ RẤT RẤT ĐẮT
Max calls: 1/truy vấn
Ví dụ: "So sánh VCB vs HPG vs FPT"
```

---

### F. SCREENING TOOLS (4 tools)

#### 2️⃣0️⃣ **screen_stocks**
```yaml
Mô tả: Lọc cổ phiếu theo 80+ tiêu chí
Input:
  - criteria: {
      "PE": "< 15",
      "PB": "< 1.5",
      "Dividend": "> 3%",
      "ROE": "> 15%"
    }
  - sector: "Banking" (optional)
  - limit: 20 (max results)
  
Output:
  - stocks: [
      {symbol, company, PE, PB, Dividend, score}
    ]
  - count: số cổ phiếu tìm được

Chi phí: $0.05/call
Max calls: 3/truy vấn
Ví dụ: "Lọc cổ phiếu P/E < 15"
```

#### 2️⃣1️⃣ **get_screener_columns**
```yaml
Mô tả: Lấy danh sách columns có sẵn để lọc
Output:
  - columns: [
      {name: "PE", type: "number", operators: ["<", ">", "="]},
      {name: "PB", type: "number", operators: ...},
      {name: "Dividend", type: "number", operators: ...},
      {name: "Sector", type: "string", operators: ["=", "!="]},
      ... 80+ columns
    ]

Chi phí: $0.0/call (FREE)
Max calls: 1/truy vấn
Ví dụ: "Xem tùy chọn lọc"
```

#### 2️⃣2️⃣ **filter_stocks_by_criteria**
```yaml
Mô tả: Lọc cổ phiếu chi tiết hơn
Input:
  - criteria: {...}  (like screen_stocks)
  - order_by: "PE", "Dividend", "Score"
  
Output:
  - stocks: [Danh sách lọc]

Chi phí: $0.03/call
Max calls: 5/truy vấn
```

#### 2️⃣3️⃣ **rank_stocks_by_score**
```yaml
Mô tả: Xếp hạng cổ phiếu theo điểm composite
Input:
  - symbols: ["VCB", "HPG", ...] (list)
  - criteria: {...} (weighting)
  
Output:
  - ranking: [
      {symbol, score, rank, reason}
    ]

Chi phí: $0.02/call
Max calls: 3/truy vấn
Ví dụ: "Xếp hạng cổ phiếu theo điểm"
```

---

### G. INVESTMENT PLANNING TOOLS (5 tools)

#### 2️⃣4️⃣ **gather_investment_profile**
```yaml
Mô tả: Thu thập hồ sơ đầu tư của người dùng
Input:
  - user_id: "user123" (string)
  - capital: 100000000 (VNĐ)
  - risk_level: "low" / "medium" / "high"
  - time_horizon: "short" / "medium" / "long"
  
Output:
  - profile: {Hồ sơ chi tiết}
  - recommendations: [Khuyến nghị đầu tư]

Chi phí: $0.05/call
Max calls: 1/truy vấn
```

#### 2️⃣5️⃣ **calculate_portfolio_allocation**
```yaml
Mô tả: Tính phân bổ danh mục theo profile
Input:
  - profile: {...}
  - symbols: ["VCB", "HPG", "FPT"] (optional)
  
Output:
  - allocation: {
      "VCB": "30%",
      "HPG": "25%",
      "FPT": "20%",
      "Cash": "25%"
    }
  - expected_return: "12-15%"
  - risk: "Moderate"

Chi phí: $0.05/call
Max calls: 1/truy vấn
```

#### 2️⃣6️⃣ **generate_entry_strategy**
```yaml
Mô tả: Chiến lược vào lệnh
Input:
  - symbol: "VCB" (string)
  - amount: 10000000 (VNĐ)
  
Output:
  - strategy: {
      "entry_price": 88500,
      "entry_volumes": ["50% ngay", "50% nếu giá giảm 5%"],
      "target_price": [92000, 95000],
      "stop_loss": 85000
    }
  - reasoning: Lý do

Chi phí: $0.05/call
Max calls: 1/truy vấn
```

#### 2️⃣7️⃣ **generate_risk_management_plan**
```yaml
Mô tả: Kế hoạch quản lý rủi ro
Input:
  - portfolio: {...}
  
Output:
  - plan: {
      "position_sizing": "Kích thước vị thế tối đa",
      "stop_loss": "Mức cắt lỗ",
      "profit_taking": "Lấy lợi nhuận",
      "hedging": "Bảo vệ danh mục"
    }

Chi phí: $0.05/call
Max calls: 1/truy vấn
```

#### 2️⃣8️⃣ **generate_monitoring_plan**
```yaml
Mô tả: Kế hoạch giám sát danh mục
Input:
  - portfolio: {...}
  
Output:
  - plan: {
      "check_frequency": "Hàng ngày",
      "key_metrics": ["PE", "RSI", "MA20"],
      "alerts": ["Giảm 5%", "RSI > 70"],
      "rebalancing": "Quý một lần"
    }

Chi phí: $0.05/call
Max calls: 1/truy vấn
```

---

### H. DISCOVERY TOOLS (4 tools)

#### 2️⃣9️⃣ **discover_stocks_by_profile**
```yaml
Mô tả: Khám phá cổ phiếu dựa trên profile
Input:
  - profile: {...} (from gather_investment_profile)
  - num_stocks: 10
  
Output:
  - stocks: [
      {symbol, company, reason, score, risk}
    ]

Chi phí: $0.08/call
Max calls: 2/truy vấn
```

#### 3️⃣0️⃣ **search_potential_stocks**
```yaml
Mô tả: Tìm kiếm cổ phiếu tiềm năng
Input:
  - criteria: "growth" / "value" / "momentum" / "quality"
  - sector: "Banking" (optional)
  - limit: 15
  
Output:
  - stocks: [Danh sách tìm được]
  - explanation: Lý do tìm

Chi phí: $0.06/call
Max calls: 3/truy vấn
```

#### 3️⃣1️⃣ **get_stock_details_from_tcbs** (reused)
```
(Xem phần Stock Data Tools)
Chi phí: $0.01/call
Max calls: 10/truy vấn
```

#### 3️⃣2️⃣ **gemini_search_and_summarize** (reused)
```
(Xem phần AI Analysis Tools)
Chi phí: $0.15/call
Max calls: 3/truy vấn (trong Discovery)
```

---

### I. MARKET DATA TOOLS (3 tools)

#### 3️⃣3️⃣ **get_market_overview**
```yaml
Mô tả: Cảnh báo thị trường chung
Output:
  - VN-Index: Điểm số, thay đổi %
  - HNX-Index: Điểm số, thay đổi %
  - UPCOM: Điểm số, thay đổi %
  - Market Breadth: Tăng/Giảm/Dừng
  - Total Volume, Value

Chi phí: $0.01/call
Max calls: 1/truy vấn
```

#### 3️⃣4️⃣ **get_sector_performance**
```yaml
Mô tả: Hiệu suất ngành
Input:
  - sector: "Banking" (optional, lấy all nếu không)
  
Output:
  - sectors: [
      {name: "Banking", change: "+2.5%", leaders: [...]}
    ]

Chi phí: $0.02/call
Max calls: 2/truy vấn
```

#### 3️⃣5️⃣ **get_market_top_movers**
```yaml
Mô tả: Top gainers, losers, volume leaders
Output:
  - gainers: [{symbol, change, price}]
  - losers: [{symbol, change, price}]
  - volume_leaders: [{symbol, volume}]

Chi phí: $0.01/call
Max calls: 1/truy vấn
```

---

## IV. TOOL ALLOCATION MATRIX

| Agent | Tools Allowed | Max Cost | Tools Count |
|-------|---------------|----------|-------------|
| **AnalysisSpecialist** | Stock Data + Financial + AI | $0.50 | 12 |
| **ScreenerSpecialist** | Screening + Support | $0.20 | 6 |
| **InvestmentPlanner** | Planning + Support | $0.30 | 7 |
| **DiscoverySpecialist** | Discovery + Support + AI | $0.40 | 8 |
| **AlertManager** | Alerts only | $0.05 | 3 |
| **SubscriptionManager** | Subscriptions only | $0.05 | 3 |
| **MarketContextSpecialist** | Market Data + Screening | $0.15 | 4 |
| **ComparisonSpecialist** | Comparison + Support | $0.25 | 5 |
| **DirectExecutor** | Simple fast tools | $0.10 | 9 |

---

## V. FLOW DIAGRAM - CÁC TOOLS ĐƯỢC GỌI LIÊN TIẾP

### Ví dụ 1: "Phân tích VCB"
```
AnalysisSpecialist (selected)
  ├─> get_stock_data (VCB)
  │   └─> Returns: OHLCV + MA, RSI, MACD
  ├─> get_stock_details_from_tcbs (VCB)
  │   └─> Returns: 70 fields
  ├─> get_financial_data (VCB)
  │   └─> Returns: BS, IS, CF
  ├─> get_financial_ratios (VCB)
  │   └─> Returns: ROE, ROA, P/E, etc
  └─> gemini_summarize (all data)
      └─> Returns: AI summary + sentiment
```

### Ví dụ 2: "Lọc cổ phiếu P/E < 15"
```
ScreenerSpecialist (selected)
  ├─> get_screener_columns ()
  │   └─> Returns: Available columns
  └─> screen_stocks (PE < 15)
      └─> Returns: List of stocks
      └─> get_stock_details_from_tcbs (results)
          └─> Returns: Details for each stock
```

### Ví dụ 3: "Lập kế hoạch đầu tư 100 triệu"
```
InvestmentPlanner (selected)
  ├─> gather_investment_profile (user data)
  │   └─> Returns: Profile
  ├─> calculate_portfolio_allocation (profile)
  │   └─> Returns: Phân bổ
  ├─> generate_entry_strategy (symbols)
  │   └─> Returns: Chiến lược vào lệnh
  ├─> generate_risk_management_plan (portfolio)
  │   └─> Returns: Kế hoạch rủi ro
  └─> generate_monitoring_plan (portfolio)
      └─> Returns: Kế hoạch giám sát
```

---

## VI. RESOURCE MONITORING & CONTROL

### Least Privilege Principle
- Mỗi agent chỉ được dùng tools cần thiết
- Không có agent nào dùng all 25+ tools
- Giới hạn gọi tool: 1-10/truy vấn tùy agent

### Cost Control
```python
AGENT_COST_LIMITS = {
    "AnalysisSpecialist": 0.50,      # $0.50/truy vấn
    "ScreenerSpecialist": 0.20,
    "InvestmentPlanner": 0.30,
    "DiscoverySpecialist": 0.40,
    "AlertManager": 0.05,
    "SubscriptionManager": 0.05,
    "MarketContextSpecialist": 0.15,
    "ComparisonSpecialist": 0.25,
}
```

### Quota Management
```python
# Ví dụ AnalysisSpecialist:
"get_stock_data": max 5 calls
"get_stock_price_prediction": max 3 calls
"gemini_summarize": max 3 calls (EXPENSIVE!)
```

---

## VII. ERROR HANDLING & FALLBACK

### Nếu Tool Thất Bại
```
Tool Error
  ├─> Log error
  ├─> Retry (max 2 times)
  ├─> If still fails:
  │   └─> Return partial data / cached data
  └─> Agent continues với thông tin có sẵn
```

### Nếu Agent Hết Chi Phí
```
Cost Limit Exceeded
  └─> Agent stops
  └─> Return partial result
  └─> Suggest: "Quá nhiều analysis, vui lòng thử lại sau"
```

---

## VIII. SUMMARY TABLE - CHI TIẾT TẤT CẢ 25+ TOOLS

| # | Tool Name | Category | Cost | Max Calls | Thời Gian |
|---|-----------|----------|------|-----------|-----------|
| 1 | get_stock_data | Stock Data | $0.01 | 5 | 1s |
| 2 | get_stock_price_prediction | Stock Data | $0.02 | 3 | 1.5s |
| 3 | generate_chart_from_data | Stock Data | $0.05 | 3 | 2s |
| 4 | get_stock_details_from_tcbs | Stock Data | $0.01 | 10 | 0.5s |
| 5 | get_financial_data | Financial | $0.02 | 3 | 1.5s |
| 6 | get_financial_ratios | Financial | $0.01 | 5 | 0.5s |
| 7 | get_income_statement | Financial | $0.02 | 3 | 1s |
| 8 | get_cash_flow | Financial | $0.02 | 3 | 1s |
| 9 | get_ratio | Financial | $0.01 | 5 | 0.3s |
| 10 | get_latest_price | Financial | $0.01 | 10 | 0.3s |
| 11 | create_alert | Alerts | $0.01 | 5 | 0.3s |
| 12 | get_user_alerts | Alerts | $0.01 | 3 | 0.2s |
| 13 | delete_alert | Alerts | $0.01 | 5 | 0.3s |
| 14 | create_subscription | Subscriptions | $0.01 | 5 | 0.3s |
| 15 | get_user_subscriptions | Subscriptions | $0.01 | 3 | 0.2s |
| 16 | delete_subscription | Subscriptions | $0.01 | 5 | 0.3s |
| 17 | gemini_summarize | AI Analysis | $0.10 | 3 | 2s |
| 18 | gemini_search_and_summarize | AI Analysis | $0.15 | 2-3 | 3s |
| 19 | batch_summarize | AI Analysis | $0.20 | 1 | 4s |
| 20 | screen_stocks | Screening | $0.05 | 3 | 2s |
| 21 | get_screener_columns | Screening | $0.00 | 1 | 0.1s |
| 22 | filter_stocks_by_criteria | Screening | $0.03 | 5 | 1s |
| 23 | rank_stocks_by_score | Screening | $0.02 | 3 | 0.8s |
| 24 | gather_investment_profile | Investment | $0.05 | 1 | 1s |
| 25 | calculate_portfolio_allocation | Investment | $0.05 | 1 | 1s |
| 26 | generate_entry_strategy | Investment | $0.05 | 1 | 1s |
| 27 | generate_risk_management_plan | Investment | $0.05 | 1 | 1s |
| 28 | generate_monitoring_plan | Investment | $0.05 | 1 | 1s |
| 29 | discover_stocks_by_profile | Discovery | $0.08 | 2 | 2.5s |
| 30 | search_potential_stocks | Discovery | $0.06 | 3 | 2s |
| 31 | get_market_overview | Market Data | $0.01 | 1 | 0.5s |
| 32 | get_sector_performance | Market Data | $0.02 | 2 | 1s |
| 33 | get_market_top_movers | Market Data | $0.01 | 1 | 0.5s |

---

## IX. CÓ THÊM KHÔNG?

Hệ thống có thể mở rộng với tools thêm:
- 📊 **Technical Analysis Tools**: Fibonacci, Support/Resistance
- 📈 **Portfolio Tools**: Optimization, Backtesting
- 🔔 **Notification Tools**: Email, SMS alerts
- 💬 **Community Tools**: Sentiment from forums
- 🏆 **Recommendation Tools**: Model-based suggestions

---

*Tài liệu cập nhật: 14/01/2025*
