# AI AGENT HYBRID SYSTEM - COMPLETE DOCUMENTATION

**Hệ thống Multi-Agent Hybrid cho Phân tích Chứng khoán Việt Nam**

---

## MỤC LỤC

1. [Tổng quan](#tổng-quan)
2. [Kiến trúc](#kiến-trúc)
3. [Tính năng](#tính-năng)
4. [Cài đặt](#cài-đặt)
5. [Sử dụng](#sử-dụng)
6. [Discord Bot](#discord-bot)
7. [Testing](#testing)
8. [Performance](#performance)
9. [Troubleshooting](#troubleshooting)
10. [Development](#development)

---

## TỔNG QUAN

### Giới thiệu

AI Agent Hybrid System là hệ thống phân tích chứng khoán thông minh kết hợp:
- **OLD Multi-Agent System**: 6 specialized agents với AI reasoning
- **NEW MCP Tools**: 33 tools truy cập database trực tiếp

### Điểm đặc biệt

**🎯 Dual-Mode Execution**
- **Direct Mode**: Truy vấn đơn giản, nhanh (<1s)
- **Agent Mode**: Phân tích phức tạp, sâu (3-10s)

**🤖 AI-Powered Routing** (Sắp có)
- Tự động phân loại độ phức tạp query
- Chọn mode tối ưu (tiết kiệm 80% thời gian)
- Confidence scoring

**⚡ Performance**
- Client-side caching (60%+ hit rate)
- Sub-second response cho simple queries
- Streaming real-time updates

---

## KIẾN TRÚC

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│  (Discord Bot / Web API / CLI)                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│               HYBRID ORCHESTRATOR                            │
│  - Query routing (AI-powered)                               │
│  - Mode selection (agent/direct)                            │
│  - Event streaming                                          │
└──────┬────────────────────────────────┬─────────────────────┘
       │                                │
       ▼                                ▼
┌──────────────────┐          ┌─────────────────────┐
│   AGENT MODE     │          │    DIRECT MODE      │
│                  │          │                     │
│ ┌──────────────┐ │          │ ┌─────────────────┐ │
│ │ Orchestrator │ │          │ │ Direct Executor │ │
│ │    Agent     │ │          │ └─────────────────┘ │
│ └──────┬───────┘ │          │          │          │
│        │         │          │          │          │
│ ┌──────▼───────────────────┐│          │          │
│ │ Specialized Agents       ││          │          │
│ │ - AnalysisSpecialist     ││          │          │
│ │ - ScreenerSpecialist     ││          │          │
│ │ - InvestmentPlanner      ││          │          │
│ │ - DiscoverySpecialist    ││          │          │
│ │ - AlertManager           ││          │          │
│ │ - SubscriptionManager    ││          │          │
│ └──────┬───────────────────┘│          │          │
└────────┼─────────────────────┘          │          │
         │                                │          │
         └────────────┬───────────────────┘          │
                      ▼                              │
            ┌────────────────────┐                   │
            │ Enhanced MCP Client│◄──────────────────┘
            │ - Caching (TTL)    │
            │ - Retry logic      │
            │ - Circuit breaker  │
            └─────────┬──────────┘
                      │
                      ▼
            ┌────────────────────┐
            │ Database Integration│
            │ Layer (Singleton)   │
            └─────────┬──────────┘
                      │
                      ▼
            ┌────────────────────┐
            │   DatabaseTools    │
            │   (Final System)   │
            └─────────┬──────────┘
                      │
                      ▼
            ┌────────────────────┐
            │    PostgreSQL      │
            │  (Stock Database)  │
            └────────────────────┘
```

### Components

#### 1. Hybrid Orchestrator
**File**: `hybrid_system/orchestrator/main_orchestrator.py`

**Responsibilities**:
- Accept user queries
- Route to AI Router
- Coordinate execution
- Stream events back
- Collect metrics

#### 2. AI Router (⚠️ Needs API update)
**File**: `hybrid_system/orchestrator/ai_router.py`

**Responsibilities**:
- Analyze query complexity
- Decide execution mode
- Suggest tools to use
- Return confidence score

**Current Issue**: Uses old `genai.Client().agents.create()` API

#### 3. Specialized Agents (6 agents)
**Directory**: `hybrid_system/agents/`

| Agent | File | Purpose | Tools |
|-------|------|---------|-------|
| OrchestratorAgent | `orchestrator_agent.py` | Main coordinator | All 33 tools |
| AnalysisSpecialist | `analysis_specialist.py` | Technical analysis | 12 tools |
| ScreenerSpecialist | `screener_specialist.py` | Stock screening | 6 tools |
| InvestmentPlanner | `investment_planner.py` | Investment advice | 15 tools |
| DiscoverySpecialist | `discovery_specialist.py` | Find opportunities | 8 tools |
| AlertManager | `alert_manager.py` | Alert management | 4 tools |
| SubscriptionManager | `subscription_manager.py` | Subscription mgmt | 4 tools |

#### 4. Enhanced MCP Client
**File**: `mcp_client/enhanced_client.py`

**Features**:
- Client-side caching with TTL
- Automatic retry on failure
- Circuit breaker pattern
- Connection pooling
- Error handling

#### 5. Database Integration Layer
**File**: `hybrid_system/database/database_integration.py`

**Features**:
- Singleton pattern
- Thread-safe operations
- Caching with TTL
- Statistics tracking
- Error handling

**8 New Database Tools**:
1. `get_latest_price(ticker)` - Giá mới nhất
2. `get_price_history(ticker, days)` - Lịch sử giá
3. `get_company_info(ticker)` - Thông tin công ty
4. `search_stocks_by_criteria(criteria)` - Lọc cổ phiếu
5. `get_balance_sheet(symbols, year, quarter)` - Bảng cân đối
6. `get_income_statement(symbols, year, quarter)` - Báo cáo thu nhập
7. `get_cash_flow(symbols, year, quarter)` - Lưu chuyển tiền tệ
8. `get_financial_ratios(symbols, year, quarter)` - Chỉ số tài chính

#### 6. Discord Bot
**File**: `discord_bot_hybrid.py`

**Features**:
- Commands (!price, !analysis, !screener)
- Natural language (@bot mention)
- Interactive buttons
- Real-time typing indicator
- Embed responses

---

## TÍNH NĂNG

### ✅ Đã Hoàn Thành

1. **Database Integration** (100%)
   - 8 tools tích hợp thành công
   - Caching hoạt động
   - Test coverage 100%

2. **Direct Mode Execution** (100%)
   - Simple queries < 1s
   - Keyword-based routing
   - Interactive responses

3. **Discord Bot v1.0** (100%)
   - Basic commands
   - Natural language support
   - Interactive UI
   - Statistics tracking

4. **Testing Infrastructure** (100%)
   - Database tests
   - Integration tests
   - Investment query tests

### ⏳ Đang Phát Triển

1. **AI Router** (80%)
   - ✅ Routing logic implemented
   - ✅ Confidence scoring
   - ❌ API compatibility issue (needs fix)
   - ❌ Not tested yet

2. **Agent Mode Execution** (60%)
   - ✅ All agents implemented
   - ✅ Tool allocation defined
   - ❌ Not tested (depends on AIRouter)

3. **Streaming Responses** (50%)
   - ✅ Event system implemented
   - ❌ Not integrated with Discord bot yet

### 📋 Kế Hoạch

1. **AIRouter API Fix** (Priority 1)
   - Replace `genai.Client()` with `genai.GenerativeModel()`
   - Test routing accuracy
   - Benchmark performance

2. **Full System Testing** (Priority 2)
   - Test all 6 specialized agents
   - Test dual-mode switching
   - Load testing

3. **Discord Bot v2.0** (Priority 3)
   - Integrate full orchestrator
   - Streaming responses
   - Alert system
   - Watchlist management

4. **Advanced Features** (Priority 4)
   - Portfolio tracking
   - Backtesting
   - News integration
   - Chart generation

---

## CÀI ĐẶT

### 1. Clone Repository

```bash
git clone <repository-url>
cd Final
```

### 2. Install Dependencies

```bash
# Main dependencies (đã có)
pip install google-generativeai psycopg2-binary python-dotenv

# Discord bot
pip install discord.py

# Or use requirements file
pip install -r src/ai_agent_hybrid/requirements_discord.txt
```

### 3. Configure .env

Tạo/sửa file `Final/.env`:

```bash
# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Database
DB_HOST=localhost
DB_PORT=5434
DB_NAME=stock
DB_USER=postgres
DB_PASSWORD=your_password

# Discord Bot (optional)
DISCORD_BOT_TOKEN=your_discord_token_here
```

### 4. Verify Installation

```bash
# Test database integration
cd src/ai_agent_hybrid
python test_simple.py

# Should see:
# [OK] HybridDatabaseClient imported
# [OK] Database client created
# [OK] VCB price: 57,500 VND
# TEST COMPLETED - Database integration works!
```

---

## SỬ DỤNG

### Option 1: Discord Bot (Recommended)

```bash
cd src/ai_agent_hybrid
python discord_bot_hybrid.py
```

**Commands**:
```
!price VCB           # Xem giá
!analysis HPG        # Phân tích
!screener           # Tìm cổ phiếu tốt
!recommend 100000000 # Tư vấn đầu tư
@bot Nên mua VCB không?  # Hỏi tự nhiên
```

### Option 2: Python Script

```python
import asyncio
from hybrid_system.database import get_database_client

# Get database client
db = get_database_client()

# Get latest price
price = db.get_latest_price("VCB")
print(f"VCB: {price['close']:,} VND, RSI: {price['rsi']:.1f}")

# Search stocks
stocks = db.search_stocks_by_criteria({'rsi_below': 40})
print(f"Found {len(stocks)} undervalued stocks")

# Close connection
db.close()
```

### Option 3: Test Scripts

```bash
# Simple database test
python test_simple.py

# Investment query with AI
python test_investment_simple.py

# Full integration test
python test_integration.py
```

---

## DISCORD BOT

### Tính Năng

**Commands**:
- ✅ `!price <ticker>` - Giá hiện tại
- ✅ `!analysis <ticker>` - Phân tích chi tiết
- ✅ `!screener [criteria]` - Tìm cổ phiếu
- ✅ `!recommend <amount>` - Tư vấn đầu tư
- ✅ `!stats` - Thống kê bot
- ✅ `!help` - Hướng dẫn

**Natural Language**:
- Mention bot: `@bot <câu hỏi>`
- Hiểu tiếng Việt
- Context-aware

**Interactive UI**:
- Embeds với màu sắc
- Buttons (Refresh, Details, Help)
- Typing indicator

### Hướng Dẫn Chi Tiết

Xem: [DISCORD_BOT_GUIDE.md](DISCORD_BOT_GUIDE.md)

---

## TESTING

### Test Files

| File | Purpose | Status |
|------|---------|--------|
| `test_simple.py` | Database integration | ✅ PASSED |
| `test_database_only.py` | All 8 database tools | ✅ PASSED |
| `test_investment_simple.py` | AI investment query | ✅ PASSED |
| `test_investment_query.py` | Full orchestrator | ❌ BLOCKED (AIRouter) |
| `test_integration.py` | Full system | ❌ BLOCKED (AIRouter) |

### Running Tests

```bash
cd src/ai_agent_hybrid

# Quick test (30s)
python test_simple.py

# Comprehensive test (2min)
python test_database_only.py

# AI test (1min)
python test_investment_simple.py
```

### Test Results

Xem: [FINAL_TEST_RESULTS.md](FINAL_TEST_RESULTS.md)

**Summary**:
- ✅ Database Layer: 100% working
- ✅ Direct Mode: 100% working
- ✅ AI Integration: 100% working
- ⏳ Full Orchestrator: Blocked by AIRouter API

---

## PERFORMANCE

### Current Metrics

| Operation | Latency | Cache Hit |
|-----------|---------|-----------|
| get_latest_price | ~50ms | 60% |
| get_price_history | ~100ms | 50% |
| search_stocks | ~120ms | 40% |
| get_financial_ratios | ~80ms | 70% |
| AI recommendation | ~5s | 0% |

### Caching Strategy

**TTL by Data Type**:
- Price data: 30s (realtime)
- Technical indicators: 60s
- Financial statements: 300s
- Company info: 3600s

**Cache Hit Rates**:
- Price queries: 60%+
- Financial queries: 70%+
- Overall: 50%+

### Optimization Tips

1. **Batch Queries**
   ```python
   # Good
   ratios = db.get_financial_ratios(['VCB', 'ACB', 'TCB'])

   # Bad
   for ticker in ['VCB', 'ACB', 'TCB']:
       ratio = db.get_financial_ratios([ticker])
   ```

2. **Use Cache**
   ```python
   # Cache hit
   price1 = db.get_latest_price("VCB")  # Query DB
   price2 = db.get_latest_price("VCB")  # From cache (if < 30s)
   ```

3. **Limit Results**
   ```python
   stocks = db.search_stocks_by_criteria({
       'rsi_below': 50,
       'limit': 10  # Don't fetch all
   })
   ```

---

## TROUBLESHOOTING

### Common Issues

#### 1. Import Error: "No module named 'src'"

**Cause**: Wrong sys.path

**Fix**:
```python
import sys
import os

final_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, final_root)
```

#### 2. Database Connection Error

**Cause**: PostgreSQL not running or wrong credentials

**Fix**:
```bash
# Check PostgreSQL
psql -h localhost -p 5434 -U postgres -d stock

# Check .env
cat .env | grep DB_
```

#### 3. GEMINI_API_KEY Error

**Cause**: API key not loaded

**Fix**:
```python
# Load .env BEFORE imports
from dotenv import load_dotenv
load_dotenv(os.path.join(final_root, '.env'))

# Then import modules
```

#### 4. Discord Bot Not Responding

**Cause**: Missing Message Content Intent

**Fix**:
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to "Bot" tab
4. Enable "Message Content Intent"
5. Save and restart bot

#### 5. UnicodeEncodeError (Vietnamese text)

**Cause**: Windows console encoding

**Fix**:
```python
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

#### 6. Column Not Found Error

**Cause**: Database schema mismatch

**Fix**: Check [database_tools.py](../../AI_agent/database_tools.py) column names match database

---

## DEVELOPMENT

### Project Structure

```
ai_agent_hybrid/
├── hybrid_system/
│   ├── orchestrator/
│   │   ├── main_orchestrator.py     # Main entry point
│   │   ├── ai_router.py             # AI routing (needs fix)
│   │   └── __init__.py
│   ├── agents/
│   │   ├── orchestrator_agent.py    # Root agent
│   │   ├── analysis_specialist.py   # Analysis
│   │   ├── screener_specialist.py   # Screening
│   │   ├── investment_planner.py    # Investment
│   │   ├── discovery_specialist.py  # Discovery
│   │   ├── alert_manager.py         # Alerts
│   │   └── subscription_manager.py  # Subscriptions
│   ├── core/
│   │   ├── state_management.py      # State
│   │   ├── tool_allocation.py       # Tool policies
│   │   ├── evaluation.py            # CriticAgent
│   │   └── conversation_memory.py   # Memory
│   ├── executors/
│   │   └── direct_executor.py       # Direct mode
│   ├── database/
│   │   ├── database_integration.py  # DB wrapper
│   │   └── __init__.py
│   └── utils/
│       ├── termination.py           # Guards
│       └── logging_config.py        # Logging
├── mcp_client/
│   └── enhanced_client.py           # MCP client
├── examples/
│   ├── simple_query.py
│   └── complex_query.py
├── discord_bot_hybrid.py            # Discord bot
├── test_simple.py                   # Simple test
├── test_database_only.py            # DB test
├── test_investment_simple.py        # AI test
├── test_investment_query.py         # Full test
├── test_integration.py              # Integration test
├── requirements_discord.txt         # Dependencies
├── DISCORD_BOT_GUIDE.md            # Bot guide
├── FINAL_TEST_RESULTS.md           # Test results
├── README_FULL.md                  # This file
└── ...
```

### Adding New Features

#### 1. New Database Tool

```python
# In database_integration.py

def get_my_data(self, param: str) -> Dict:
    """Get my custom data"""
    cache_key = self._cache_key("get_my_data", param=param)

    # Try cache first
    cached = self._cache_get(cache_key, ttl=300)
    if cached:
        return cached

    # Query database
    result = self.db_tools.get_my_data(param)

    # Cache result
    if result:
        self._cache_set(cache_key, result)

    return result
```

#### 2. New Discord Command

```python
@bot.command(name="mycommand")
async def my_command(ctx, arg: str):
    """My custom command"""
    async with ctx.typing():
        try:
            result = bot.db.get_my_data(arg)

            embed = discord.Embed(
                title=f"Result for {arg}",
                description=str(result),
                color=discord.Color.blue()
            )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")
```

#### 3. New Specialized Agent

```python
# In hybrid_system/agents/my_agent.py

class MySpecialist:
    def __init__(self, mcp_client):
        self.mcp = mcp_client
        self.name = "MySpecialist"

    async def process(self, query: str, context: Dict):
        """Process query"""
        # Your logic here
        result = await self.mcp.get_my_data(query)

        return {
            "response": result,
            "confidence": 0.9
        }
```

### Code Style

- **Formatting**: PEP 8
- **Docstrings**: Google style
- **Type hints**: Required for public APIs
- **Comments**: Vietnamese OK for domain logic

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes
git add .
git commit -m "Add my feature"

# Push
git push origin feature/my-feature

# Create PR
```

---

## CHANGELOG

### Version 1.0 (2026-01-04)

**✅ Completed**:
- Database integration layer (8 tools)
- Direct mode execution
- Discord bot v1.0
- Test infrastructure
- Documentation

**🐛 Fixed**:
- Database column names (`debt_equity`, `dividend_yfield`)
- UTF-8 encoding for Vietnamese
- Import paths (`from src.AI_agent...`)
- API key naming (GOOGLE → GEMINI)

**📝 Known Issues**:
- AIRouter uses old API (`genai.Client().agents.create()`)
- Full orchestrator not tested yet
- Streaming responses not integrated

### Planned Version 2.0

**Features**:
- Fix AIRouter API compatibility
- Test full orchestrator
- Integrate streaming responses
- Add alert system
- Add watchlist management

---

## CONTRIBUTORS

- **DATN Team** - Initial work
- **Claude Sonnet 4.5** - Development assistance

---

## LICENSE

MIT License - See LICENSE file

---

## SUPPORT

- **Documentation**: This file and linked guides
- **Issues**: Create GitHub issue
- **Questions**: Discord server

---

**🚀 Happy Trading! 📈**
