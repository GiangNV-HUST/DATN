# 🔬 Models Comparison: Claude vs Gemini

## Tổng quan

Cả 2 phiên bản đều sử dụng **cùng một MCP Server**, chỉ khác **LLM client**:

```
┌────────────────────────────────────────────┐
│           MCP Server (Port 5000)           │
│  - get_latest_price                        │
│  - get_price_history                       │
│  - get_predictions                         │
│  - search_stocks                           │
└──────────────┬─────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌─────────────┐  ┌──────────────┐
│   Claude    │  │    Gemini    │
│  Sonnet 4.5 │  │ 2.0 Flash    │
└─────────────┘  └──────────────┘
```

---

## So sánh chi tiết

| Tiêu chí | Claude Sonnet 4.5 | Gemini 2.0 Flash Exp |
|----------|-------------------|----------------------|
| **Provider** | Anthropic | Google |
| **File agent** | [stock_agent_v3.py](stock_agent_v3.py) | [stock_agent_gemini.py](stock_agent_gemini.py) |
| **Discord bot** | [discord_bot_v3.py](discord_bot_v3.py) | [discord_bot_gemini.py](discord_bot_gemini.py) |
| **Model ID** | `claude-sonnet-4-5-20250929` | `gemini-2.0-flash-exp` |
| **Context window** | 200K tokens | 1M tokens |
| **Function calling** | ✅ Native | ✅ Native |
| **Speed** | Nhanh | Rất nhanh |
| **Cost** | ~$3/1M input tokens | Miễn phí (có limit) |
| **Free tier** | $5 credit | 15 req/min |
| **Quality** | Xuất sắc | Tốt |
| **Best for** | Production, phân tích sâu | Testing, prototype |

---

## Kiến trúc code

### Claude Version

```python
# stock_agent_v3.py
from anthropic import Anthropic

class StockAgentV3:
    def __init__(self):
        self.client = Anthropic(api_key=...)
        self.model = "claude-sonnet-4-5-20250929"

    async def chat_with_tools(self, message):
        response = self.client.messages.create(
            model=self.model,
            tools=self.mcp_tools,  # ← From MCP server
            messages=[...]
        )
```

### Gemini Version

```python
# stock_agent_gemini.py
import google.generativeai as genai

class GeminiStockAgent:
    def __init__(self):
        genai.configure(api_key=...)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    async def chat_with_tools(self, message):
        response = chat.send_message(
            message,
            tools=self.gemini_tools  # ← From MCP server
        )
```

---

## Tool Schema Conversion

### MCP Tool Schema (Standard)

```json
{
  "name": "get_latest_price",
  "description": "Lấy giá và chỉ báo kỹ thuật",
  "input_schema": {
    "type": "object",
    "properties": {
      "ticker": {"type": "string"}
    }
  }
}
```

### Claude Format (trực tiếp sử dụng)

```python
tools = mcp_tools  # Claude API tương thích JSON schema
```

### Gemini Format (cần convert)

```python
# Gemini cần FunctionDeclaration object
function = genai.protos.FunctionDeclaration(
    name="get_latest_price",
    description="Lấy giá và chỉ báo kỹ thuật",
    parameters=genai.protos.Schema(...)
)
tools = [genai.protos.Tool(function_declarations=[function])]
```

---

## Performance Benchmarks

### Test Setup
- Same MCP server
- Same queries
- Same database
- Measured: response time, accuracy

### Expected Results (ước tính)

| Query | Claude (s) | Gemini (s) | Winner |
|-------|-----------|-----------|--------|
| Simple (giá?) | 2-3s | 1-2s | Gemini |
| Analysis (RSI?) | 3-5s | 2-4s | Gemini |
| Complex (so sánh?) | 5-8s | 4-6s | Gemini |

**Tổng kết:** Gemini nhanh hơn ~30-40% nhưng Claude có thể cho câu trả lời chi tiết hơn.

---

## Cost Analysis

### Claude Sonnet 4.5

**Pricing:**
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

**Example:**
- 1 query ≈ 1000 input + 500 output tokens
- Cost: $0.003 + $0.0075 = **$0.0105/query**
- 1000 queries = **$10.50**

### Gemini 2.0 Flash

**Pricing:**
- Free tier: 15 RPM, 1500 RPD
- Paid: Chưa công bố (experimental)

**Example:**
- 1 query = **$0** (trong free tier)
- 1000 queries/day = cần ~11 hours (trong limit)

---

## Use Cases

### Dùng Claude khi:
- ✅ Production app với users thực
- ✅ Cần phân tích sâu, chi tiết
- ✅ Budget cho API costs
- ✅ Cần quality cao nhất

### Dùng Gemini khi:
- ✅ Testing, development
- ✅ Prototype, demo
- ✅ Budget thấp/zero cost
- ✅ Cần speed, volume cao
- ✅ Queries đơn giản

---

## How to Switch

### Switch model trong runtime

```python
# Option 1: Dùng file khác nhau
from stock_agent_v3 import StockAgentV3      # Claude
from stock_agent_gemini import GeminiStockAgent  # Gemini

# Option 2: Environment variable
import os
model_type = os.getenv("MODEL_TYPE", "claude")

if model_type == "gemini":
    agent = GeminiStockAgent()
else:
    agent = StockAgentV3()
```

### A/B Testing

Chạy script so sánh:
```bash
python compare_models.py
```

---

## Limitations

### Claude
- ❌ Rate limits (50 req/min tier 1)
- ❌ Costs money sau free tier
- ❌ Anthropic API key cần account

### Gemini
- ❌ Free tier có strict limits (15 RPM)
- ❌ Model experimental (có thể đổi)
- ❌ Response quality thấp hơn Claude một chút

---

## Recommendations

### Development Phase
```
🏗️ Use Gemini (free, fast, enough quality)
```

### Testing Phase
```
🧪 Use compare_models.py (test both)
```

### Production Phase
```
🚀 Use Claude (higher quality, scalable)
```

### Budget Constrained
```
💰 Use Gemini + caching strategies
```

---

## Files Reference

| Purpose | Claude | Gemini |
|---------|--------|--------|
| Agent | [stock_agent_v3.py](stock_agent_v3.py) | [stock_agent_gemini.py](stock_agent_gemini.py) |
| Discord Bot | [discord_bot_v3.py](discord_bot_v3.py) | [discord_bot_gemini.py](discord_bot_gemini.py) |
| Test | Built-in | [test_gemini.py](test_gemini.py) |
| Compare | - | [compare_models.py](compare_models.py) |

**MCP Server (shared):**
- [mcp_server/stock_mcp_server.py](mcp_server/stock_mcp_server.py)

---

## Next Steps

1. ✅ Test Gemini: `python test_gemini.py`
2. ✅ Compare: `python compare_models.py`
3. 📊 Analyze results
4. 🎯 Choose model for production
5. 🚀 Deploy!
