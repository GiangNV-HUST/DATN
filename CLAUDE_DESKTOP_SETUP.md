# Hướng Dẫn Tích Hợp Claude Desktop với Hệ Thống Multi-Agent

## Tổng Quan

Tài liệu này hướng dẫn cách kết nối Claude Desktop với hệ thống multi-agent orchestrator của bạn thông qua MCP (Model Context Protocol).

### Kiến Trúc

```
Claude Desktop
    ↓ (MCP Protocol)
Orchestrator MCP Server (orchestrator_server.py)
    ↓
MultiAgentOrchestrator (multi_agent_orchestrator.py)
    ↓
SpecialistRouter (AI-powered routing với GPT-4o-mini)
    ↓
┌─────────────────────────────────────────────────┐
│  8 SPECIALIZED AGENTS                           │
│  ├─ AnalysisSpecialist     (Phân tích cổ phiếu) │
│  ├─ ScreenerSpecialist     (Lọc cổ phiếu)       │
│  ├─ AlertManager           (Quản lý cảnh báo)   │
│  ├─ InvestmentPlanner      (Tư vấn đầu tư)      │
│  ├─ DiscoverySpecialist    (Khám phá cổ phiếu)  │
│  ├─ SubscriptionManager    (Quản lý watchlist)  │
│  ├─ MarketContextSpecialist(Tổng quan thị trường)│
│  └─ ComparisonSpecialist   (So sánh cổ phiếu)   │
└─────────────────────────────────────────────────┘
    ↓
31 MCP Tools (stock data, predictions, alerts, etc.)
```

## Cài Đặt

### Bước 1: Kiểm Tra Dependencies

Đảm bảo bạn đã cài đặt các dependencies cần thiết:

```bash
pip install -r requirements.txt
```

Kiểm tra các packages quan trọng:
- `mcp` - Model Context Protocol
- `anthropic` - Anthropic SDK
- `openai` - OpenAI SDK (nếu dùng OpenAI version)
- `google-generativeai` - Google Gemini API

### Bước 2: Cấu Hình Biến Môi Trường

Tạo file `.env` (nếu chưa có) với các biến sau:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/stock_db

# API Keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key  # Nếu dùng OpenAI

# MCP Server Settings
PYTHONPATH=c:\Users\GIANG\OneDrive - Hanoi University of Science and Technology\Documents\DATN\Final
PYTHONIOENCODING=utf-8
```

### Bước 3: Cấu Hình Claude Desktop

#### Windows

1. Mở thư mục cấu hình Claude Desktop:
   ```
   %APPDATA%\Claude\
   ```

2. Tạo hoặc chỉnh sửa file `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "stock-market-orchestrator": {
      "command": "python",
      "args": [
        "-m",
        "src.mcp_server.orchestrator_server"
      ],
      "cwd": "c:\\Users\\GIANG\\OneDrive - Hanoi University of Science and Technology\\Documents\\DATN\\Final",
      "env": {
        "PYTHONPATH": "c:\\Users\\GIANG\\OneDrive - Hanoi University of Science and Technology\\Documents\\DATN\\Final",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

**Lưu ý:** Thay đổi đường dẫn `cwd` và `PYTHONPATH` theo vị trí thực tế của dự án.

#### macOS/Linux

1. Mở thư mục cấu hình:
   ```bash
   ~/.config/Claude/
   ```

2. Tạo hoặc chỉnh sửa file `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "stock-market-orchestrator": {
      "command": "python3",
      "args": [
        "-m",
        "src.mcp_server.orchestrator_server"
      ],
      "cwd": "/path/to/your/project/Final",
      "env": {
        "PYTHONPATH": "/path/to/your/project/Final",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

### Bước 4: Khởi Động MCP Server (Standalone Testing)

Để test MCP server độc lập (không qua Claude Desktop):

**Windows:**
```bash
run_orchestrator_mcp.bat
```

**macOS/Linux:**
```bash
chmod +x run_orchestrator_mcp.sh
./run_orchestrator_mcp.sh
```

### Bước 5: Khởi Động Claude Desktop

1. Đóng hoàn toàn Claude Desktop nếu đang chạy
2. Khởi động lại Claude Desktop
3. MCP server sẽ tự động được khởi động khi Claude Desktop mở

## Sử Dụng

### Available Tools

Khi kết nối thành công, Claude Desktop sẽ có access đến các tools sau:

#### 1. `process_query` - Tool Chính (Recommended)

Tool này cung cấp access đến toàn bộ hệ thống multi-agent.

**Parameters:**
- `user_query` (string, required): Câu hỏi hoặc yêu cầu của user
- `user_id` (string, optional): User ID để quản lý session (default: "claude_desktop_user")
- `mode` (string, optional): Chế độ thực thi
  - `"auto"` (default): AI tự động quyết định
  - `"agent"`: Bắt buộc dùng AGENT mode (phức tạp, có reasoning)
  - `"direct"`: Bắt buộc dùng DIRECT mode (nhanh, pattern matching)
- `session_id` (string, optional): Session ID để duy trì ngữ cảnh hội thoại

**Ví dụ:**

```javascript
// Câu hỏi đơn giản (sẽ route sang DIRECT mode)
{
  "user_query": "Giá cổ phiếu VCB hiện tại là bao nhiêu?",
  "mode": "auto"
}

// Câu hỏi phức tạp (sẽ route sang AGENT mode)
{
  "user_query": "Tư vấn đầu tư 100 triệu vào ngành ngân hàng với rủi ro trung bình",
  "mode": "auto"
}

// Bắt buộc AGENT mode
{
  "user_query": "Phân tích cổ phiếu FPT",
  "mode": "agent"
}
```

**Response Format:**
```json
{
  "response": "Kết quả phân tích...",
  "session_id": "session_claude_desktop_user",
  "routing": {
    "mode": "agent",
    "reason": "Complex analysis requires multi-step reasoning",
    "confidence": 0.85,
    "complexity": 0.7
  }
}
```

#### 2. `get_session_state` - Xem Trạng Thái Session

Lấy thông tin về session hiện tại.

**Parameters:**
- `session_id` (string, required): Session ID cần xem

**Ví dụ:**
```javascript
{
  "session_id": "session_claude_desktop_user"
}
```

**Response:**
```json
{
  "session_id": "session_claude_desktop_user",
  "execution_state": {
    "iterations": 3,
    "tool_calls": 5,
    "errors": 0,
    "total_cost": 0.05,
    "elapsed_time": 2.3
  },
  "conversation_turns": 4,
  "shared_state_keys": ["stock_data_VCB", "analysis_result"],
  "user_context": {
    "user_id": "claude_desktop_user",
    "watchlist_size": 0,
    "alerts_count": 0,
    "subscriptions_count": 0
  }
}
```

#### 3. `clear_session` - Xóa Session

Xóa session để bắt đầu mới.

**Parameters:**
- `session_id` (string, required): Session ID cần xóa

#### 4. `get_system_status` - Kiểm Tra Trạng Thái Hệ Thống

Xem trạng thái tổng quan của hệ thống.

**Parameters:**
- `include_metrics` (boolean, optional): Có bao gồm metrics không (default: true)

### Ví Dụ Cách Sử Dụng

#### Ví Dụ 1: Phân Tích Cổ Phiếu (AGENT Mode)

**User trong Claude Desktop:**
> Phân tích cổ phiếu VCB cho tôi

**Claude Desktop sẽ gọi:**
```javascript
process_query({
  "user_query": "Phân tích cổ phiếu VCB cho tôi",
  "mode": "auto"
})
```

**Hệ thống xử lý:**
1. SpecialistRouter phân tích query → Route đến **AnalysisSpecialist**
2. AnalysisSpecialist thực hiện:
   - Lấy dữ liệu giá: `get_stock_data(symbols=["VCB"])`
   - Lấy chi tiết từ TCBS: `get_stock_details_from_tcbs(symbols=["VCB"])`
   - Lấy dữ liệu tài chính: `get_financial_data(tickers=["VCB"])`
   - Tạo biểu đồ: `generate_chart_from_data(symbols=["VCB"])`
   - Tóm tắt bằng AI: `gemini_summarize(...)`
3. Trả về kết quả phân tích đầy đủ

#### Ví Dụ 2: Truy Vấn Giá (DIRECT Mode)

**User:**
> Giá VCB hiện tại

**Claude Desktop gọi:**
```javascript
process_query({
  "user_query": "Giá VCB hiện tại",
  "mode": "auto"
})
```

**Hệ thống xử lý:**
1. SpecialistRouter → Route đến **AnalysisSpecialist** (simple price query)
2. AnalysisSpecialist gọi: `get_stock_data(symbols=["VCB"])`
3. Trả về kết quả nhanh

#### Ví Dụ 3: Tư Vấn Đầu Tư (Multi-Step Workflow)

**User:**
> Tư vấn đầu tư 50 triệu vào ngành ngân hàng, tôi chấp nhận rủi ro trung bình

**Claude Desktop gọi:**
```javascript
process_query({
  "user_query": "Tư vấn đầu tư 50 triệu vào ngành ngân hàng, tôi chấp nhận rủi ro trung bình",
  "mode": "auto"
})
```

**Hệ thống xử lý:**
1. SpecialistRouter → Route đến **InvestmentPlanner**
2. InvestmentPlanner thực hiện workflow đầy đủ:
   - Xác định: capital=50M, risk=moderate, sector=banking
   - Lọc cổ phiếu ngành ngân hàng phù hợp
   - Phân bổ vốn theo risk profile
   - Tạo chiến lược đầu tư

**Response:** Báo cáo đầu tư đầy đủ với phân bổ vốn, chiến lược, quản lý rủi ro.

### Routing Logic

SpecialistRouter sử dụng GPT-4o-mini để route query đến agent phù hợp:

| Query Type | Agent | Ví Dụ |
|------------|-------|-------|
| Giá, phân tích | AnalysisSpecialist | "Giá VCB", "Phân tích VCB" |
| Lọc cổ phiếu | ScreenerSpecialist | "Tìm cổ phiếu ROE > 15%" |
| Tư vấn đầu tư | InvestmentPlanner | "Tư vấn đầu tư 50 triệu" |
| Khám phá | DiscoverySpecialist | "Cổ phiếu tiềm năng ngành công nghệ" |
| Cảnh báo | AlertManager | "Tạo cảnh báo VCB > 90" |
| Watchlist | SubscriptionManager | "Theo dõi HPG" |
| Thị trường | MarketContextSpecialist | "Tình hình thị trường hôm nay" |
| So sánh | ComparisonSpecialist | "So sánh VCB với TCB" |

## Troubleshooting

### 1. MCP Server Không Khởi Động

**Triệu chứng:** Claude Desktop không thấy tools

**Giải pháp:**
1. Kiểm tra đường dẫn trong `claude_desktop_config.json` đúng chưa
2. Kiểm tra Python environment có đủ dependencies:
   ```bash
   pip list | grep mcp
   ```
3. Test standalone:
   ```bash
   python -m src.mcp_server.orchestrator_server
   ```
4. Xem logs của Claude Desktop:
   - Windows: `%APPDATA%\Claude\logs\`
   - macOS: `~/Library/Logs/Claude/`

### 2. Import Error

**Triệu chứng:** `ModuleNotFoundError: No module named 'src.ai_agent_hybrid'`

**Giải pháp:**
1. Kiểm tra `PYTHONPATH` trong config
2. Đảm bảo cấu trúc thư mục đúng:
   ```
   Final/
   ├── src/
   │   ├── ai_agent_hybrid/
   │   │   └── hybrid_system/
   │   └── mcp_server/
   │       └── orchestrator_server.py
   ```

### 3. Database Connection Error

**Triệu chứng:** `psycopg2.OperationalError: could not connect to server`

**Giải pháp:**
1. Kiểm tra PostgreSQL đang chạy
2. Kiểm tra `DATABASE_URL` trong `.env`
3. Test connection:
   ```bash
   python test_database.py
   ```

### 4. API Key Error

**Triệu chứng:** `google.api_core.exceptions.Unauthenticated: 401`

**Giải pháp:**
1. Kiểm tra `GEMINI_API_KEY` trong `.env`
2. Đảm bảo API key còn valid và có quota

### 5. Slow Response

**Triệu chứng:** Tool calls mất >30 giây

**Giải pháp:**
1. Sử dụng `"mode": "direct"` cho queries đơn giản
2. Kiểm tra database indexes:
   ```sql
   SELECT * FROM pg_indexes WHERE tablename = 'stock_data';
   ```
3. Kiểm tra MCP client cache:
   ```python
   # Cache TTL mặc định: 5 phút
   # Xem trong enhanced_client.py
   ```

## Kiến Trúc Chi Tiết

### Flow Diagram

```
┌─────────────────┐
│ Claude Desktop  │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────────────────────┐
│  Orchestrator MCP Server        │
│  (orchestrator_server.py)       │
│                                 │
│  Tools:                         │
│  - process_query ───────────┐   │
│  - get_session_state        │   │
│  - clear_session            │   │
│  - get_system_status        │   │
└─────────────────────────────┼───┘
                              │
                              ▼
         ┌────────────────────────────────┐
         │   MultiAgentOrchestrator       │
         │   (multi_agent_orchestrator.py)│
         └───────────┬────────────────────┘
                     │
         ┌───────────▼───────────┐
         │   SpecialistRouter    │
         │ (specialist_router.py)│
         │                       │
         │ AI-powered routing    │
         │ using GPT-4o-mini     │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌──────────┐  ┌──────────┐  ┌──────────────────┐
│Analysis  │  │Screener  │  │ Market Context   │
│Specialist│  │Specialist│  │ Specialist       │
└──────────┘  └──────────┘  └──────────────────┘
    │                │                │
    ▼                ▼                ▼
┌──────────┐  ┌──────────┐  ┌──────────────────┐
│Investment│  │Discovery │  │  Comparison      │
│ Planner  │  │Specialist│  │  Specialist      │
└──────────┘  └──────────┘  └──────────────────┘
    │                │                │
    ▼                ▼                ▼
┌──────────┐  ┌──────────────────────────────┐
│  Alert   │  │    Subscription Manager      │
│ Manager  │  └──────────────────────────────┘
└──────────┘
         │
         ▼
┌──────────────────┐
│   31 MCP Tools   │
│                  │
│ Stock Data       │
│ Predictions      │
│ Charts           │
│ Alerts           │
│ Subscriptions    │
│ AI Summaries     │
│ Screening        │
│ etc.             │
└──────────────────┘
```

### State Management

```
┌──────────────────────────────────┐
│       StateManager               │
├──────────────────────────────────┤
│  Per Session:                    │
│  ┌────────────────────────────┐  │
│  │ ExecutionState             │  │
│  │ - iterations               │  │
│  │ - tool_calls               │  │
│  │ - errors                   │  │
│  │ - cost                     │  │
│  │ - elapsed_time             │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ SharedState (dict)         │  │
│  │ - Thread-safe              │  │
│  │ - Cross-agent data         │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ ConversationMemory         │  │
│  │ - Max 20 turns             │  │
│  │ - Auto pruning             │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │ UserContext                │  │
│  │ - watchlist                │  │
│  │ - alerts                   │  │
│  │ - subscriptions            │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
```

## Best Practices

### 1. Session Management

- Mỗi user nên có `session_id` riêng
- Clear session khi bắt đầu chủ đề mới
- Session tự động timeout sau 1 giờ không hoạt động

### 2. Mode Selection

- Dùng `"auto"` cho hầu hết trường hợp (recommended)
- Dùng `"direct"` khi cần tốc độ và query đơn giản
- Dùng `"agent"` khi cần phân tích sâu

### 3. Error Handling

- Luôn kiểm tra response có `"error"` key không
- Retry với exponential backoff nếu gặp lỗi tạm thời
- Log errors để debug

### 4. Performance

- DIRECT mode: <1s response
- AGENT mode: 2-15s tùy độ phức tạp
- Sử dụng cache khi có thể

## Liên Hệ & Hỗ Trợ

Nếu gặp vấn đề, kiểm tra:
1. Logs: `%APPDATA%\Claude\logs\` (Windows) hoặc `~/Library/Logs/Claude/` (macOS)
2. Database: `python test_database.py`
3. MCP Server: `python -m src.mcp_server.orchestrator_server`
4. Dependencies: `pip list`

## Changelog

- **v2.0** (2026-01-13): Upgraded to Multi-Agent Architecture
  - 8 Specialized Agents (thêm MarketContextSpecialist, ComparisonSpecialist)
  - SpecialistRouter với GPT-4o-mini (97.3% routing accuracy)
  - Removed DIRECT mode, all queries go through specialized agents
  - 31 MCP tools
  - Simplified architecture

- **v1.0** (2026-01-09): Initial release với orchestrator MCP wrapper
  - Support cho full multi-agent system
  - AUTO/AGENT/DIRECT mode routing
  - Session management
  - 4 MCP tools
