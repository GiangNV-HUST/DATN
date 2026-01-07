# Hybrid Multi-Model Stock Trading System - Architecture Diagrams

Tài liệu này mô tả 4 diagrams kiến trúc chính của hệ thống **ai_agent_hybrid**.

---

## 📊 Danh sách Diagrams

### 1. **hybrid_system_architecture.puml/png** (205.8 KB)
**Kiến trúc tổng thể hệ thống**

Diagram này cho thấy toàn bộ kiến trúc từ Discord Bot đến Database:

**Các layers:**
- **Discord Layer**: Natural language interface, conversation memory
- **Orchestration Layer**: HybridOrchestrator điều phối 6 specialized agents
- **Specialized Agents Layer**:
  - AnalysisSpecialist
  - ScreenerSpecialist
  - AlertManager
  - InvestmentPlanner
  - DiscoverySpecialist
  - SubscriptionManager
- **Multi-Model AI Layer**:
  - TaskClassifier (phân loại task)
  - ModelClients (Gemini/Claude/GPT-4o)
  - UsageTracker (track cost & performance)
- **MCP Integration Layer**:
  - Enhanced MCP Client (caching, retry, circuit breaker)
  - MCP Server (25 tools)
- **Database Layer**: PostgreSQL + TimescaleDB
  - 14 existing tables
  - 5 new hybrid tables (sessions, user_preferences, ai_usage_logs, portfolios, query_cache)
- **Core Infrastructure**: State Management, Message Protocol, Termination Guards, Resource Monitor, Evaluation

---

### 2. **hybrid_multi_model_flow.puml/png** (145.2 KB)
**Luồng phân loại task và chọn AI model**

Diagram này chi tiết hóa cách hệ thống chọn AI model phù hợp cho từng loại query:

**Task Classification:**
- DATA_QUERY (simple lookup)
- SCREENING (filter stocks)
- ANALYSIS (technical/fundamental)
- ADVISORY (investment advice)
- DISCOVERY (search/explore)
- CRUD (create/update/delete)
- CONVERSATION (general chat)

**Model Selection Strategy:**
- DATA_QUERY → Gemini Flash ($0.000075/1M input) - Fast & cheap
- SCREENING → Gemini Pro ($0.00035/1M input) - Medium complexity
- ANALYSIS → Claude Sonnet ($0.003/1M input) - Complex reasoning
- ADVISORY → GPT-4o ($0.0025/1M input) - Creative planning
- DISCOVERY → Claude Sonnet - NL understanding
- CRUD → Gemini Flash - Simple operations
- CONVERSATION → Gemini Flash - General chat

**Classification Examples:**
- "Giá VCB?" → DATA_QUERY → Gemini Flash
- "Tìm cổ phiếu ROE > 15%" → SCREENING → Gemini Pro
- "Phân tích kỹ thuật HPG" → ANALYSIS → Claude Sonnet
- "Với 100 triệu nên đầu tư gì?" → ADVISORY → GPT-4o

**Components:**
- TaskClassifier: Phân loại query dựa vào keywords và context
- Task-Based Model Selector: Map task type → model name
- 3 Model Clients: GeminiClient, ClaudeClient, GPTClient
- UsageTracker: Log input/output tokens, cost, execution time → ai_usage_logs table

---

### 3. **hybrid_specialist_agents.puml/png** (83.4 KB)
**Chi tiết 6 Specialized Agents**

Diagram này mô tả từng agent chuyên biệt và MCP tools mà agent sử dụng:

**1. AnalysisSpecialist**
- **Handles**: Stock price analysis, technical analysis, fundamental analysis, news & sentiment, comparative analysis
- **MCP Tools**: get_stock_price, get_technical_indicators, get_financial_reports, search_stock_news
- **AI Model**: Claude Sonnet (complex reasoning)

**2. ScreenerSpecialist**
- **Handles**: Filter stocks by criteria, technical screening (RSI, MACD, MA), fundamental screening (PE, ROE, EPS)
- **MCP Tools**: vnstock_screener (81 criteria), filter_by_technical, filter_by_fundamental
- **AI Model**: Gemini Pro (structured data processing)

**3. AlertManager**
- **Handles**: Create price alerts, view user alerts, delete alerts, check alert triggers
- **MCP Tools**: create_alert, get_user_alerts, delete_alert, check_alert_status
- **AI Model**: Gemini Flash (simple CRUD)

**4. InvestmentPlanner**
- **Handles**: Investment advisory, portfolio planning, asset allocation, risk assessment
- **Uses**: GPT-4o (strategic planning), user_preferences table, portfolios table, Stock discovery agent
- **AI Model**: GPT-4o (creative portfolio strategies)

**5. DiscoverySpecialist**
- **Handles**: Discover potential stocks, sector-based exploration, growth opportunities, market trends
- **MCP Tools**: search_stocks_by_criteria, get_sector_leaders, get_trending_stocks, vnstock_screener
- **AI Model**: Claude Sonnet (NL understanding & ranking)

**6. SubscriptionManager**
- **Handles**: User subscriptions, follow/unfollow stocks, view subscribed stocks
- **MCP Tools**: create_subscription, get_user_subscriptions, delete_subscription
- **AI Model**: Gemini Flash (simple CRUD)

**Routing Logic:**
HybridOrchestrator phân tích user query → xác định intent → route đến agent phù hợp

**Query Examples:**
- "Phân tích VCB" → AnalysisSpecialist
- "Tìm cổ phiếu ROE > 15%" → ScreenerSpecialist
- "Tạo cảnh báo VCB > 100k" → AlertManager
- "Với 100 triệu đầu tư gì?" → InvestmentPlanner
- "Cổ phiếu công nghệ tiềm năng" → DiscoverySpecialist
- "Theo dõi HPG" → SubscriptionManager

---

### 4. **hybrid_mcp_simple.puml/png** (48.3 KB)
**Enhanced MCP Client với Caching & Resilience**

Diagram này mô tả các cải tiến ở client-side của MCP integration:

**5 Client-Side Enhancements:**

1. **In-Memory Caching**
   - TTL-based expiration
   - Hash-based keys
   - 60-80% hit rate
   - Cache TTL by type:
     - price_query: 60s
     - screening: 600s (10 min)
     - chart_data: 120s
     - session: 300s

2. **Request Deduplication**
   - Prevent duplicate concurrent requests
   - Same query → single MCP call
   - Reduce server load

3. **Circuit Breaker**
   - Max failures: 5
   - Circuit timeout: 30s
   - Fail fast when service is down
   - Auto-recovery when service is back

4. **Retry Logic**
   - Exponential backoff
   - Initial delay: 1s
   - Max retries: 3
   - Backoff multiplier: 2x

5. **Metrics Tracking**
   - Total requests
   - Cache hit/miss ratio
   - Response times
   - Failure rate

**Persistent Cache:**
- query_cache table in PostgreSQL
- Syncs with in-memory cache
- Survives restarts
- Auto cleanup of expired entries

**Performance Benefits:**
- 60-80% reduction in database queries
- 10x faster for repeated queries
- Circuit breaker prevents cascading failures
- Request deduplication saves resources
- Automatic retry improves reliability

**Flow:**
1. Specialized Agent calls MCP tool
2. Enhanced Client checks in-memory cache
3. If cache miss → deduplicate request
4. Circuit breaker checks if service is available
5. Retry logic handles transient failures
6. Call MCP Server via MCP protocol
7. Server performs database operations
8. Response cached for future use
9. Metrics tracked for monitoring

---

## 🎯 Điểm khác biệt so với hệ thống cũ

### Hệ thống cũ (Old Agent System):
- ❌ Single AI model (Gemini API only)
- ❌ 5 agents (Alert, Subscription, Screener, General, Analysis)
- ❌ No cost optimization
- ❌ No caching layer
- ❌ No user personalization
- ❌ No performance tracking

### Hệ thống mới (Hybrid Multi-Model):
- ✅ **Multi-model AI**: 3 models (Gemini/Claude/GPT-4o) with task-based routing
- ✅ **6 specialized agents**: Added InvestmentPlanner & DiscoverySpecialist
- ✅ **Cost optimization**: TaskClassifier selects cheapest model for each task
- ✅ **Enhanced MCP Client**: Caching (60-80% query reduction), retry, circuit breaker
- ✅ **User personalization**: user_preferences, portfolios tables
- ✅ **Performance tracking**: ai_usage_logs, query_cache tables
- ✅ **Core infrastructure**: State management, message protocol, termination guards
- ✅ **Evaluation layer**: Critic agent, arbitration agent for quality control

---

## 📈 Performance Metrics

**Cost Reduction:**
- Simple queries (70%): Gemini Flash → $0.000075/1M tokens
- Medium queries (20%): Gemini Pro/Claude Sonnet → $0.00035-0.003/1M
- Complex queries (10%): Claude Sonnet/GPT-4o → $0.0025-0.003/1M

**Query Performance:**
- Cache hit rate: 60-80%
- 10x faster for cached queries
- Circuit breaker prevents cascading failures

**Database Optimization:**
- 60-80% reduction in DB queries via query_cache
- Hypertables for time-series data (stock_prices_1m, stock_prices_1d)
- Materialized views for aggregations

---

## 🔧 Sử dụng Diagrams trong Báo cáo

Tất cả 4 diagrams đã được export sang PNG với resolution cao, sẵn sàng để in A4:

1. **hybrid_system_architecture.png** - Cho chương "Kiến trúc tổng thể hệ thống"
2. **hybrid_multi_model_flow.png** - Cho chương "Multi-Model AI Strategy"
3. **hybrid_specialist_agents.png** - Cho chương "Specialized Agents"
4. **hybrid_mcp_simple.png** - Cho chương "MCP Integration & Performance"

Các file `.puml` có thể chỉnh sửa nếu cần thay đổi.
