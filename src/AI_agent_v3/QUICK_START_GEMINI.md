# 🚀 Quick Start: Gemini Version

## Bước 1: Kiểm tra API Key

Mở file `.env` và đảm bảo có:

```bash
GEMINI_API_KEY=your_api_key_here
```

Lấy key tại: https://aistudio.google.com/apikey

---

## Bước 2: Start MCP Server (Terminal 1)

```bash
cd src\AI_agent_v3\mcp_server
python stock_mcp_server.py
```

✅ Chờ thấy: `🚀 Stock MCP Server Started!`

---

## Bước 3: Test Gemini Agent (Terminal 2)

### Option A: Test standalone

```bash
cd src\AI_agent_v3
python test_gemini.py
```

### Option B: Test Discord Bot

```bash
cd src\AI_agent_v3
python discord_bot_gemini.py
```

✅ Chờ thấy: `✅ Bot (Gemini) ready!`

---

## Bước 4: So sánh Gemini vs Claude

```bash
cd src\AI_agent_v3
python compare_models.py
```

Sẽ chạy cùng 1 query trên cả 2 models và so sánh:
- ⏱️ Speed
- ✅ Success rate
- 📊 Quality

---

## Các models Gemini có thể dùng

Edit trong file `stock_agent_gemini.py`:

```python
# Line 35-36
model_name="gemini-2.0-flash-exp"  # ← Đổi ở đây
```

**Các options:**
- `gemini-2.0-flash-exp` - Mới nhất, nhanh, miễn phí (RECOMMENDED)
- `gemini-1.5-pro` - Mạnh nhất, chậm hơn, có phí
- `gemini-1.5-flash` - Cân bằng speed/quality

---

## Troubleshooting

### ❌ ModuleNotFoundError: google.generativeai

```bash
pip install google-generativeai
```

### ❌ No tools discovered

Kiểm tra MCP server đang chạy:

```bash
curl http://localhost:5000/health
```

### ❌ API key invalid

Kiểm tra lại key tại: https://aistudio.google.com/apikey

---

## Files đã tạo

1. ✅ `stock_agent_gemini.py` - Agent với Gemini
2. ✅ `discord_bot_gemini.py` - Discord bot
3. ✅ `test_gemini.py` - Test script
4. ✅ `compare_models.py` - So sánh Claude vs Gemini
5. ✅ `README_GEMINI.md` - Docs chi tiết
6. ✅ `QUICK_START_GEMINI.md` - Guide này

---

## Test ngay!

```bash
# Terminal 1
python src\AI_agent_v3\mcp_server\stock_mcp_server.py

# Terminal 2
python src\AI_agent_v3\test_gemini.py
```

Enjoy! 🎉
