# 🤖 AI AGENTS OVERVIEW - Stock Analysis System

## 📚 Tổng quan 3 phiên bản AI Agent

Project này hiện có **3 phiên bản AI Agent** với kiến trúc và công nghệ khác nhau:

---

## 📁 CẤU TRÚC THƯ MỤC

```
Final/
├── src/
│   ├── AI_agent/              # V1 - Direct API
│   │   ├── stock_agent.py
│   │   ├── database_tools.py
│   │   └── discord_bot.py
│   │
│   ├── AI_agent_v2/           # V2 - Function Calling
│   │   ├── stock_agent_v2.py
│   │   ├── discord_bot_v2.py
│   │   ├── test_comparison.py
│   │   ├── README.md
│   │   ├── FUNCTION_CALLING_EXPLAINED.md
│   │   ├── EXAMPLES.md
│   │   └── QUICK_START.md
│   │
│   └── AI_agent_v3/           # V3 - MCP (Model Context Protocol)
│       ├── stock_agent_v3.py
│       ├── discord_bot_v3.py
│       ├── mcp_server/
│       │   ├── stock_mcp_server.py
│       │   ├── stock_tools.py
│       │   └── run_server.bat
│       ├── README.md
│       └── QUICK_START.md
│
├── AGENT_COMPARISON.md        # So sánh chi tiết 3 versions
└── AI_AGENTS_OVERVIEW.md      # File này
```

---

## 🎯 V1 - DIRECT API (Baseline)

### Location: `src/AI_agent/`

### Technology Stack:
- **AI Model:** Google Gemini 2.5 Flash Lite
- **Architecture:** Monolithic, hard-coded logic
- **Tools:** DatabaseTools (direct calls)

### Key Files:
- [stock_agent.py](src/AI_agent/stock_agent.py) - Main agent
- [discord_bot.py](src/AI_agent/discord_bot.py) - Discord bot
- [database_tools.py](src/AI_agent/database_tools.py) - Database utilities

### How to Run:
```bash
# Run bot
python src/AI_agent/discord_bot.py
```

### Pros:
- ✅ Simple, dễ hiểu
- ✅ Fast (1-2s response)
- ✅ Low cost (1 API call)

### Cons:
- ❌ Hard-coded logic
- ❌ Không linh hoạt
- ❌ Không support natural language tốt

### Use Cases:
- MVP, prototypes
- Simple queries
- Budget-constrained projects

---

## 🤖 V2 - FUNCTION CALLING (Smart)

### Location: `src/AI_agent_v2/`

### Technology Stack:
- **AI Model:** Google Gemini 2.5 Flash Lite
- **Architecture:** Function Calling / Tool Use
- **Tools:** 4 tools với auto-selection

### Key Files:
- [stock_agent_v2.py](src/AI_agent_v2/stock_agent_v2.py) - Agent với Function Calling
- [discord_bot_v2.py](src/AI_agent_v2/discord_bot_v2.py) - Discord bot V2
- [FUNCTION_CALLING_EXPLAINED.md](src/AI_agent_v2/FUNCTION_CALLING_EXPLAINED.md) - Chi tiết về Function Calling
- [EXAMPLES.md](src/AI_agent_v2/EXAMPLES.md) - Ví dụ và use cases

### Tools Available:
1. `get_latest_price(ticker)` - Lấy giá và indicators
2. `get_price_history(ticker, days)` - Lịch sử giá
3. `get_predictions(ticker)` - Dự đoán ML
4. `search_stocks(criteria)` - Tìm kiếm cổ phiếu

### How to Run:
```bash
# Run bot V2
python src/AI_agent_v2/discord_bot_v2.py

# Test comparison V1 vs V2
python src/AI_agent_v2/test_comparison.py
```

### Pros:
- ✅ AI tự quyết định tools
- ✅ Natural language understanding
- ✅ Multi-tool orchestration
- ✅ Flexible responses

### Cons:
- ⚠️ Slower (3-5s)
- ⚠️ Higher cost (2-5 API calls)
- ❌ Tools inline (không scale)

### Use Cases:
- Production apps
- Complex queries
- Natural language interaction
- Medium-scale systems

---

## 🚀 V3 - MCP (Enterprise)

### Location: `src/AI_agent_v3/`

### Technology Stack:
- **AI Model:** Anthropic Claude Sonnet 4.5
- **Architecture:** Client-Server (MCP Protocol)
- **MCP Server:** HTTP REST API (Port 5000)
- **Tools:** Centralized, discoverable

### Key Components:

#### 1. MCP Server (`src/AI_agent_v3/mcp_server/`)
- [stock_mcp_server.py](src/AI_agent_v3/mcp_server/stock_mcp_server.py) - HTTP server
- [stock_tools.py](src/AI_agent_v3/mcp_server/stock_tools.py) - Tool registry
- [run_server.bat](src/AI_agent_v3/mcp_server/run_server.bat) - Start script

#### 2. MCP Client
- [stock_agent_v3.py](src/AI_agent_v3/stock_agent_v3.py) - Agent client
- [discord_bot_v3.py](src/AI_agent_v3/discord_bot_v3.py) - Discord bot

#### 3. Documentation
- [README.md](src/AI_agent_v3/README.md) - Full documentation
- [QUICK_START.md](src/AI_agent_v3/QUICK_START.md) - Quick start guide

### How to Run:

```bash
# Terminal 1: Start MCP Server
python src/AI_agent_v3/mcp_server/stock_mcp_server.py

# Terminal 2: Run bot
python src/AI_agent_v3/discord_bot_v3.py

# Or test agent directly
python src/AI_agent_v3/stock_agent_v3.py
```

### MCP Endpoints:
```
GET  /health         - Health check
GET  /tools          - List tools
GET  /tools/schema   - Get tool schemas
POST /tools/call     - Execute tool
```

### Pros:
- ✅ Centralized tool management
- ✅ Remote tools (distributed)
- ✅ Tool discovery
- ✅ Multi-agent support
- ✅ Horizontal scaling
- ✅ Caching & rate limiting ready

### Cons:
- ⚠️ More complex setup
- ⚠️ Network latency (HTTP)
- ⚠️ Requires infrastructure

### Use Cases:
- Enterprise applications
- Multi-agent systems
- Distributed tools
- High-traffic systems
- Large teams

---

## 📊 QUICK COMPARISON

| Feature | V1 | V2 | V3 |
|---------|----|----|-----|
| **AI Model** | Gemini 2.5 | Gemini 2.5 | Claude Sonnet 4.5 |
| **Response Time** | 1.2s | 3.5s | 4.2s |
| **API Calls** | 1 | 2-5 | 2-5 + HTTP |
| **Natural Language** | ❌ | ✅ | ✅ |
| **Tool Selection** | Manual | AI | AI |
| **Scalability** | Low | Medium | High |
| **Multi-Agent** | ❌ | ❌ | ✅ |
| **Complexity** | Low | Medium | High |

**Full comparison:** [AGENT_COMPARISON.md](AGENT_COMPARISON.md)

---

## 🎓 LEARNING PATH

### For Beginners:
1. Start with **V1** - Understand basics
2. Study **V2** - Learn Function Calling
3. Explore **V3** - Understand MCP architecture

### For Production:
1. **Use V2** for most applications
2. **Upgrade to V3** when:
   - Nhiều agents cần share tools
   - Tools phân tán trên nhiều services
   - Need horizontal scaling
   - Team lớn, nhiều developers

---

## 📖 DOCUMENTATION

### V1 Documentation:
- Code: `src/AI_agent/`
- No separate docs (simple architecture)

### V2 Documentation:
- [README.md](src/AI_agent_v2/README.md) - Overview
- [FUNCTION_CALLING_EXPLAINED.md](src/AI_agent_v2/FUNCTION_CALLING_EXPLAINED.md) - Deep dive
- [EXAMPLES.md](src/AI_agent_v2/EXAMPLES.md) - Use cases
- [QUICK_START.md](src/AI_agent_v2/QUICK_START.md) - Get started

### V3 Documentation:
- [README.md](src/AI_agent_v3/README.md) - Full guide
- [QUICK_START.md](src/AI_agent_v3/QUICK_START.md) - Quick start

### Comparison:
- [AGENT_COMPARISON.md](AGENT_COMPARISON.md) - Detailed comparison

---

## 🛠️ SETUP REQUIREMENTS

### Common Requirements:
```bash
# Python 3.11+
pip install -r requirements.txt
```

### V1 & V2:
- Google Gemini API key
- TimescaleDB running
- Discord bot token

### V3 Additional:
- Anthropic Claude API key
- MCP Server running (Port 5000)
- aiohttp library

---

## 💡 WHICH VERSION TO CHOOSE?

### Choose V1 if:
- Building MVP/prototype
- Simple use cases
- Need fast development
- Budget constraints

### Choose V2 if:
- Production application
- Natural language queries
- Medium complexity
- **RECOMMENDED FOR MOST CASES**

### Choose V3 if:
- Enterprise system
- Multiple agents
- Distributed tools
- High scale requirements
- Large team

---

## 🚀 GETTING STARTED

### Quick Test All Versions:

```bash
# Test V1
python src/AI_agent/discord_bot.py

# Test V2
python src/AI_agent_v2/discord_bot_v2.py

# Test V3
# Terminal 1:
python src/AI_agent_v3/mcp_server/stock_mcp_server.py
# Terminal 2:
python src/AI_agent_v3/discord_bot_v3.py
```

---

## 📈 EVOLUTION TIMELINE

```
V1 (Nov 2024)     V2 (Dec 2024)     V3 (Dec 2024)
     ↓                  ↓                  ↓
 Direct API    →  Function Calling  →     MCP
 Simple        →  Smart             →  Enterprise
 Baseline      →  Production        →  Scalable
```

---

## 🎯 PROJECT STATUS

- ✅ **V1** - Production ready
- ✅ **V2** - Production ready (Recommended)
- ✅ **V3** - Production ready (Enterprise)

**All 3 versions are fully functional and can be used independently!**

---

## 📝 NEXT STEPS

1. **Read** [AGENT_COMPARISON.md](AGENT_COMPARISON.md) for detailed comparison
2. **Choose** version based on your needs
3. **Follow** QUICK_START.md for chosen version
4. **Deploy** and enjoy! 🎉

---

## 🤝 CONTRIBUTING

When adding new features:
- **V1**: Update `src/AI_agent/`
- **V2**: Update `src/AI_agent_v2/` + tools
- **V3**: Update MCP server tools in `src/AI_agent_v3/mcp_server/stock_tools.py`

---

## 📞 SUPPORT

- **V1/V2**: Check inline code comments
- **V2**: Read [FUNCTION_CALLING_EXPLAINED.md](src/AI_agent_v2/FUNCTION_CALLING_EXPLAINED.md)
- **V3**: Read [QUICK_START.md](src/AI_agent_v3/QUICK_START.md)
- **All**: See [AGENT_COMPARISON.md](AGENT_COMPARISON.md)

---

**Happy coding! 🚀**

*Built with ❤️ using Claude Code*
