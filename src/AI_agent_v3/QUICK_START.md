# ⚡ QUICK START - Agent V3 with MCP

## 🚀 3 Bước để chạy Agent V3

### Bước 1: Cài đặt dependencies

```bash
pip install anthropic aiohttp
```

### Bước 2: Start MCP Server

```bash
# Terminal 1: Start MCP Server
cd src/AI_agent_v3/mcp_server
python stock_mcp_server.py

# Hoặc dùng batch script (Windows)
src\AI_agent_v3\mcp_server\run_server.bat
```

**Output mong đợi:**
```
============================================================
🚀 Stock MCP Server Started!
============================================================
📍 URL: http://0.0.0.0:5000
🔧 Tools available: 4

📚 Endpoints:
   GET  /health         - Health check
   GET  /tools          - List all tools
   GET  /tools/schema   - Get tool schemas
   POST /tools/call     - Execute a tool
============================================================
```

### Bước 3: Run Agent hoặc Bot

#### Option A: Test Agent trực tiếp

```bash
# Terminal 2: Test Agent
python src/AI_agent_v3/stock_agent_v3.py
```

#### Option B: Run Discord Bot

```bash
# Terminal 2: Run Bot V3
python src/AI_agent_v3/discord_bot_v3.py

# Hoặc với custom MCP URL
python src/AI_agent_v3/discord_bot_v3.py --mcp-url http://localhost:5000
```

---

## 🧪 TESTING

### Test 1: Check MCP Server

```bash
# Health check
curl http://localhost:5000/health

# List tools
curl http://localhost:5000/tools

# Get tool schemas
curl http://localhost:5000/tools/schema
```

### Test 2: Call Tool Directly

```bash
# Test get_latest_price
curl -X POST http://localhost:5000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_latest_price",
    "arguments": {"ticker": "VCB"}
  }'
```

### Test 3: Test Agent

```python
from src.AI_agent_v3.stock_agent_v3 import StockAgentV3
import asyncio

async def test():
    agent = StockAgentV3(mcp_server_url="http://localhost:5000")
    await agent.discover_tools()

    response = await agent.chat_with_tools("VCB giá bao nhiêu?")
    print(response)

asyncio.run(test())
```

---

## 📝 USAGE EXAMPLES

### Example 1: Simple Query

```python
agent = StockAgentV3()
await agent.discover_tools()

# AI tự động gọi MCP tool get_latest_price("VCB")
response = await agent.chat_with_tools("VCB giá bao nhiêu?")
```

### Example 2: Complex Query

```python
# AI tự động gọi nhiều tools:
# - get_latest_price("VCB")
# - get_latest_price("TCB")
# - So sánh kết quả
response = await agent.chat_with_tools("So sánh VCB và TCB về RSI")
```

### Example 3: Search Query

```python
# AI tự động gọi search_stocks với criteria
response = await agent.chat_with_tools("Tìm cổ phiếu RSI dưới 30")
```

---

## 🔧 CONFIGURATION

### Environment Variables

Tạo file `.env`:
```bash
# Discord Bot
DISCORD_BOT_TOKEN=your_discord_token

# Anthropic API (cho Agent V3)
ANTHROPIC_API_KEY=sk-ant-...

# MCP Server (optional, default: http://localhost:5000)
MCP_SERVER_URL=http://localhost:5000
```

### MCP Server Configuration

Trong `stock_mcp_server.py`:
```python
# Thay đổi host/port
server = StockMCPServer(
    host="0.0.0.0",  # Cho phép external connections
    port=5000         # Thay đổi port nếu cần
)
```

---

## 🐛 TROUBLESHOOTING

### Issue 1: MCP Server không start được

**Error:**
```
OSError: [WinError 10048] Only one usage of each socket address...
```

**Solution:**
```bash
# Port 5000 đã được dùng, đổi port khác:
python stock_mcp_server.py --port 5001
```

### Issue 2: Agent không discover được tools

**Error:**
```
❌ No tools discovered
```

**Solution:**
1. Check MCP server đang chạy:
   ```bash
   curl http://localhost:5000/health
   ```

2. Check firewall không block port 5000

3. Dùng đúng MCP URL:
   ```python
   agent = StockAgentV3(mcp_server_url="http://localhost:5000")
   ```

### Issue 3: Discord Bot không phản hồi

**Checklist:**
- [ ] MCP Server đang chạy
- [ ] Bot đã discover tools (`✅ Discovered N tools` in logs)
- [ ] `DISCORD_BOT_TOKEN` đúng trong `.env`
- [ ] `ANTHROPIC_API_KEY` đúng trong `.env`

**Debug:**
```python
# Thêm debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Issue 4: Import errors

**Error:**
```
ModuleNotFoundError: No module named 'stock_tools'
```

**Solution:**
```bash
# Chạy từ đúng directory
cd src/AI_agent_v3/mcp_server
python stock_mcp_server.py

# Hoặc fix import path
export PYTHONPATH="${PYTHONPATH}:/path/to/project"
```

---

## 📊 ARCHITECTURE OVERVIEW

```
┌─────────────────┐
│  Discord User   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│   Discord Bot V3        │
│  (discord_bot_v3.py)    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   Stock Agent V3        │
│  (stock_agent_v3.py)    │
│  - Anthropic Claude     │
│  - Tool Use enabled     │
└────────┬────────────────┘
         │ HTTP/JSON
         ▼
┌─────────────────────────┐
│    MCP Server           │
│  (stock_mcp_server.py)  │
│  - Port 5000            │
│  - REST API             │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   Stock Tools           │
│  (stock_tools.py)       │
│  - DatabaseTools        │
│  - 4 tools available    │
└─────────────────────────┘
```

---

## 🎯 NEXT STEPS

1. **Customize Tools** - Thêm tools mới vào `stock_tools.py`
2. **Add Caching** - Implement Redis caching cho MCP server
3. **Deploy** - Deploy MCP server lên cloud (AWS, GCP, Azure)
4. **Monitor** - Thêm monitoring và metrics
5. **Scale** - Setup multiple MCP servers cho different tools

---

## 📚 DOCS

- [README.md](README.md) - Overview và architecture
- [Stock Agent V3 Code](stock_agent_v3.py) - Agent implementation
- [MCP Server Code](mcp_server/stock_mcp_server.py) - Server implementation
- [Discord Bot V3](discord_bot_v3.py) - Bot implementation

---

**Enjoy Agent V3! 🚀**

*Questions? Check logs or create an issue!*
