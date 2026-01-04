# 📖 Hướng Dẫn Cài Đặt & Chạy Hybrid System

## 🎯 Yêu Cầu Hệ Thống

- Python 3.9+
- PostgreSQL 14+ (đã có từ ai_agent_mcp)
- Git
- Google API Key (Gemini AI)

## 📦 Cài Đặt

### Bước 1: Clone/Chuẩn bị Code

Bạn đã có cấu trúc:
```
upload/
├── ai_agent_mcp/     # Hệ thống MCP (NEW)
└── ai_agent_hybrid/  # Hệ thống Hybrid (mới tạo)
```

### Bước 2: Cài đặt Dependencies

```bash
cd ai_agent_hybrid
pip install -r requirements.txt
```

**Lưu ý:** Nếu gặp lỗi với `google-adk`, cài thủ công:
```bash
pip install google-generativeai google-adk --upgrade
```

### Bước 3: Cấu hình Environment

```bash
# Copy file mẫu
cp .env.example .env

# Chỉnh sửa .env
nano .env  # hoặc notepad .env trên Windows
```

Điền các thông tin:
```env
# Google API Key - BẮT BUỘC
GOOGLE_API_KEY=your_google_api_key_here

# Database - Dùng chung với ai_agent_mcp
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_db
DB_USER=postgres
DB_PASSWORD=your_password

# MCP Server Path
MCP_SERVER_SCRIPT=../ai_agent_mcp/mcp_server/server.py
```

**Lấy Google API Key:**
1. Truy cập: https://makersuite.google.com/app/apikey
2. Tạo API key mới
3. Copy và paste vào .env

### Bước 4: Kiểm tra MCP Server

```bash
# Kiểm tra MCP server có chạy được không
cd ../ai_agent_mcp
python -m mcp_server.server
```

Nếu thấy output:
```
Stock Market MCP Server starting...
```

→ ✅ OK! Nhấn Ctrl+C để dừng

## 🚀 Chạy Hệ Thống

### Option 1: Chạy Example (Khuyến nghị cho lần đầu)

```bash
cd ai_agent_hybrid

# Chạy basic example
python examples/example_basic.py
```

**Kết quả mong đợi:**
```
============================================================
🚀 HYBRID SYSTEM - Basic Example
============================================================

📡 Initializing Hybrid Orchestrator...
✅ Enhanced MCP Client connected. 25 tools available.
✅ Orchestrator ready!

============================================================
📝 Query: Giá VCB?
💡 Expected: Simple price query - should use DIRECT mode
============================================================

🧠 AI Router đang phân tích query...

🧠 AI Router Decision:
   Mode Selected: DIRECT
   Confidence: 0.98
   Complexity: 0.10
   Reasoning: Query đơn giản chỉ hỏi giá, 1 tool call là đủ
   Estimated Time: 1.0s
   Suggested Tools: get_stock_data

📍 ⚡ Direct Mode: Thực thi nhanh...

[... results ...]

✅ Completed in 0.85s
```

### Option 2: Chạy trong Code của Bạn

```python
import asyncio
from hybrid_system.orchestrator import HybridOrchestrator

async def main():
    orchestrator = HybridOrchestrator()
    await orchestrator.initialize()

    # Auto mode
    async for event in orchestrator.process_query(
        "Phân tích VCB",
        user_id="user123"
    ):
        if event["type"] == "chunk":
            print(event["data"])

    await orchestrator.cleanup()

asyncio.run(main())
```

### Option 3: Interactive CLI

```bash
python -m applications.cli.cli
```

(Nếu file CLI đã được tạo)

## 🔧 Troubleshooting

### Lỗi 1: "ModuleNotFoundError: No module named 'mcp'"

**Giải pháp:**
```bash
pip install mcp --upgrade
```

### Lỗi 2: "No module named 'google.genai'"

**Giải pháp:**
```bash
pip install google-generativeai --upgrade
```

### Lỗi 3: "Failed to connect to MCP server"

**Nguyên nhân:** MCP server chưa chạy hoặc path sai

**Giải pháp:**
```bash
# Kiểm tra MCP server có thể chạy được
cd ../ai_agent_mcp
python -m mcp_server.server

# Nếu OK, sửa path trong .env:
MCP_SERVER_SCRIPT=../ai_agent_mcp/mcp_server/server.py
```

### Lỗi 4: "GOOGLE_API_KEY not found"

**Giải pháp:**
1. Kiểm tra file `.env` có tồn tại không
2. Kiểm tra `GOOGLE_API_KEY=...` có được điền chưa
3. Restart terminal sau khi sửa .env

### Lỗi 5: "AI Router parsing error"

**Nguyên nhân:** Gemini API response không đúng format

**Giải pháp:** System sẽ tự fallback về mode an toàn, nhưng nếu gặp liên tục:
```python
# Xóa cache routing
orchestrator.ai_router.clear_cache()
```

### Lỗi 6: Database connection error

**Giải pháp:**
```bash
# Kiểm tra PostgreSQL đang chạy
# Windows:
services.msc  # Tìm PostgreSQL service

# Linux/Mac:
sudo service postgresql status

# Kiểm tra thông tin kết nối trong .env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_db
DB_USER=postgres
DB_PASSWORD=your_actual_password
```

## 📊 Kiểm Tra Hoạt Động

### Test 1: AI Router

```python
from hybrid_system.orchestrator import AIRouter
import asyncio

async def test_router():
    router = AIRouter()

    # Test simple query
    decision = await router.analyze("Giá VCB?")
    print(f"Mode: {decision.mode}")  # Expect: "direct"
    print(f"Confidence: {decision.confidence}")

    # Test complex query
    decision = await router.analyze("Phân tích VCB")
    print(f"Mode: {decision.mode}")  # Expect: "agent"

asyncio.run(test_router())
```

### Test 2: Enhanced MCP Client

```python
from mcp_client import EnhancedMCPClient
import asyncio

async def test_client():
    client = EnhancedMCPClient("../ai_agent_mcp/mcp_server/server.py")
    await client.connect()

    # Test with caching
    result1 = await client.get_stock_data(["VCB"], lookback_days=1)
    result2 = await client.get_stock_data(["VCB"], lookback_days=1)

    metrics = client.get_metrics()
    print(f"Cache hits: {metrics['cache_hits']}")  # Expect: 1

    await client.disconnect()

asyncio.run(test_client())
```

### Test 3: Full System

```bash
python examples/example_basic.py
```

Nếu chạy OK và thấy output như mong đợi → ✅ Hệ thống hoạt động!

## 🎯 Next Steps

Sau khi cài đặt thành công:

1. **Đọc API Documentation:**
   - [API_REFERENCE.md](docs/API_REFERENCE.md)

2. **Xem các Examples:**
   - `examples/example_basic.py` - Basic usage
   - `examples/example_agent_mode.py` - Agent mode
   - `examples/example_direct_mode.py` - Direct mode

3. **Tích hợp vào Discord Bot:**
   - Xem `applications/discord_bot/`

4. **Tích hợp vào Web API:**
   - Xem `applications/web_api/`

## 🆘 Hỗ Trợ

Nếu gặp vấn đề:

1. Kiểm tra logs
2. Xem [Troubleshooting](#troubleshooting)
3. Kiểm tra version dependencies
4. Create issue với đầy đủ thông tin lỗi

## 🎉 Done!

Bây giờ bạn đã sẵn sàng sử dụng Hybrid System! 🚀
