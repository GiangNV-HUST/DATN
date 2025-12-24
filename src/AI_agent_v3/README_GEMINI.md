# Stock Agent V3 - Gemini Version

Phiên bản Stock Agent sử dụng **Google Gemini** thay vì Claude Anthropic.

## Kiến trúc

```
┌─────────────────────────────────┐
│     Discord User                │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│     Discord Bot (Gemini)        │
│     - discord_bot_gemini.py     │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│     Gemini Stock Agent          │
│     - stock_agent_gemini.py     │
│     - Model: gemini-2.0-flash   │
└───────────────┬─────────────────┘
                │
                │ HTTP REST API
                ▼
┌─────────────────────────────────┐
│     MCP Server                  │
│     - stock_mcp_server.py       │
│     - 4 tools available         │
└─────────────────────────────────┘
```

## Files mới

1. **stock_agent_gemini.py** - Agent sử dụng Gemini
2. **discord_bot_gemini.py** - Discord bot với Gemini
3. **test_gemini.py** - Script test standalone

## Cách sử dụng

### 1. Đảm bảo có GEMINI_API_KEY

Kiểm tra file `.env`:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

Lấy API key tại: https://aistudio.google.com/apikey

### 2. Khởi động MCP Server (Terminal 1)

```bash
cd src/AI_agent_v3/mcp_server
python stock_mcp_server.py
```

Đợi thấy:
```
🚀 Stock MCP Server Started!
📍 URL: http://0.0.0.0:5000
🔧 Tools available: 4
```

### 3. Test Gemini Agent standalone (Terminal 2)

```bash
cd src/AI_agent_v3
python test_gemini.py
```

Kết quả mong đợi:
```
✅ Agent initialized
📡 Discovering tools from MCP server...
✅ Discovered 4 tools:
   - get_latest_price
   - get_price_history
   - get_predictions
   - search_stocks

TEST 1/2: Test get_latest_price tool
❓ User: VCB giá bao nhiêu?

🤖 Gemini Response:
[Phân tích chi tiết từ Gemini...]
```

### 4. Chạy Discord Bot với Gemini (Terminal 2)

```bash
cd src/AI_agent_v3
python discord_bot_gemini.py
```

Đợi thấy:
```
✅ Bot (Gemini) ready! Name: Stock Bot
🤖 Model: gemini-2.0-flash-exp
🔗 MCP Server: http://localhost:5000
✅ Discovered 4 tools
```

### 5. Test trên Discord

Mention bot và hỏi:
```
@Stock Bot VCB giá bao nhiêu?
```

## So sánh Gemini vs Claude

| Feature | Claude (Anthropic) | Gemini (Google) |
|---------|-------------------|-----------------|
| **File** | stock_agent_v3.py | stock_agent_gemini.py |
| **Model** | claude-sonnet-4-5 | gemini-2.0-flash-exp |
| **Speed** | Nhanh | Rất nhanh |
| **Cost** | Trung bình | Rẻ hơn |
| **Function calling** | Native support | Native support |
| **Context window** | 200K tokens | 1M tokens |
| **Free tier** | $5 credit | Miễn phí (có giới hạn) |

## Models Gemini có sẵn

Bạn có thể đổi model trong code:

```python
agent = GeminiStockAgent(
    model_name="gemini-2.0-flash-exp"  # Nhanh, miễn phí
    # model_name="gemini-1.5-pro"      # Mạnh hơn
    # model_name="gemini-1.5-flash"    # Cân bằng
)
```

## Troubleshooting

### ❌ "No tools discovered"
- Kiểm tra MCP server đang chạy: `curl http://localhost:5000/health`
- Kiểm tra port 5000 không bị chiếm

### ❌ "GEMINI_API_KEY not found"
- Kiểm tra file `.env` có `GEMINI_API_KEY=...`
- Restart terminal sau khi sửa .env

### ❌ "google.generativeai not found"
```bash
pip install google-generativeai
```

### ❌ Gemini response chậm
- Đổi sang model nhanh hơn: `gemini-2.0-flash-exp`
- Kiểm tra kết nối internet

## Test A/B: Gemini vs Claude

Chạy song song 2 bots để so sánh:

**Terminal 1:** MCP Server
```bash
python src/AI_agent_v3/mcp_server/stock_mcp_server.py
```

**Terminal 2:** Claude Bot
```bash
python src/AI_agent_v3/discord_bot_v3.py
```

**Terminal 3:** Gemini Bot
```bash
python src/AI_agent_v3/discord_bot_gemini.py
```

Hỏi cùng 1 câu cho cả 2 bots và so sánh!

## Lưu ý

- ✅ **MCP Server** là model-agnostic (không phụ thuộc vào LLM nào)
- ✅ Có thể chạy nhiều clients (Claude, Gemini, GPT) cùng lúc
- ✅ Tools chỉ cần define 1 lần ở MCP server
- ⚠️ Gemini miễn phí có rate limit (15 requests/min)

## Next steps

1. Test performance: Gemini vs Claude
2. Implement model routing (tự động chọn model theo query)
3. Add cost tracking
4. Compare response quality
