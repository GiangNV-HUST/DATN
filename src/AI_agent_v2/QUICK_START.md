# ⚡ QUICK START - Agent V2 Function Calling

## 🚀 Cách sử dụng nhanh

### 1️⃣ Chạy Discord Bot V2

```bash
# Cách 1: Chạy trực tiếp
python src/AI_agent_v2/discord_bot_v2.py

# Cách 2: Dùng batch script
cd src/AI_agent_v2
run_bot_v2.bat
```

---

### 2️⃣ Sử dụng Agent trong Code

```python
from src.AI_agent_v2.stock_agent_v2 import StockAnalysisAgentV2

# Khởi tạo
agent = StockAnalysisAgentV2()

# Hỏi đáp tự nhiên - AI tự gọi tools
response = agent.answer_question("VCB giá bao nhiêu?")
print(response)

# Phân tích cổ phiếu
analysis = agent.analyze_stock("VCB")
print(analysis)

# Tìm kiếm cơ hội
opportunities = agent.find_opportunities("Tìm cổ phiếu RSI dưới 30")
print(opportunities)
```

---

### 3️⃣ Test & So sánh V1 vs V2

```bash
# Chạy test comparison
python src/AI_agent_v2/test_comparison.py
```

---

## 📚 Tài liệu chi tiết

| File | Nội dung |
|------|----------|
| [README.md](README.md) | So sánh V1 vs V2, tổng quan |
| [FUNCTION_CALLING_EXPLAINED.md](FUNCTION_CALLING_EXPLAINED.md) | Giải thích chi tiết `chat_with_tools` |
| [EXAMPLES.md](EXAMPLES.md) | Ví dụ thực tế, use cases |

---

## 🎯 Điểm khác biệt V2

### V1 - Direct API:
```python
# Developer code logic
if ticker:
    data = db_tools.get_latest_price(ticker)  # Hard-coded
else:
    data = None
```

### V2 - Function Calling:
```python
# AI tự quyết định
response = agent.answer_question("VCB thế nào?")
# → AI tự gọi get_latest_price("VCB")
```

---

## 💬 Ví dụ Discord Bot Commands

### V2 Bot Commands:

```
!help
→ Xem hướng dẫn V2

!analysis VCB
→ AI tự động lấy data và phân tích

!ask So sánh VCB và TCB về RSI
→ AI tự gọi get_latest_price cho cả 2

!find cổ phiếu RSI dưới 30
→ AI tự parse và gọi search_stocks

!compare VCB TCB
→ AI tự lấy data cả 2 và so sánh

@Bot VCB có nên mua không?
→ AI tự quyết định tools: get_latest_price + get_predictions
```

---

## ⚙️ Cấu hình

### Thay đổi model:
```python
# File: stock_agent_v2.py, line 24
self.model = genai.GenerativeModel(
    "gemini-2.5-flash-lite",  # Hoặc "gemini-pro"
    tools=self.tools
)
```

### Giới hạn iterations:
```python
# Tránh infinite loop
response = agent.chat_with_tools(message, max_iterations=5)
```

### Thêm tools mới:
```python
# File: stock_agent_v2.py, method _define_tools()
tools.append({
    "name": "get_news",
    "description": "Lấy tin tức cổ phiếu",
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string"}
        }
    }
})

# Thêm execution logic
def _execute_function(self, function_name, args):
    # ...
    elif function_name == "get_news":
        return self.news_service.get_news(args["ticker"])
```

---

## 🐛 Troubleshooting

### Lỗi: "quota exceeded"
```python
# Đã vượt quota Gemini API
# → Đợi 1 phút hoặc đổi API key
```

### Lỗi: "max_iterations reached"
```python
# AI gọi tools quá 5 lần
# → Tăng max_iterations hoặc kiểm tra logic
response = agent.chat_with_tools(message, max_iterations=10)
```

### Bot không phản hồi:
```bash
# Kiểm tra logs
python src/AI_agent_v2/discord_bot_v2.py

# Xem lỗi trong console
```

---

## 📊 Performance Tips

### Giảm API calls:
```python
# Câu hỏi càng rõ ràng, AI gọi ít tools hơn

# ✅ Tốt (1-2 calls)
"VCB giá bao nhiêu?"

# ⚠️ Tốn (3-4 calls)
"VCB thế nào? Có nên mua không?"
```

### Cache responses:
```python
# Implement caching cho frequent queries
from functools import lru_cache

@lru_cache(maxsize=100)
def answer_question(self, question):
    # ...
```

---

## 🎉 Kết luận

**Agent V2 giúp bạn:**
- ✅ Hỏi đáp tự nhiên hơn
- ✅ Không cần code logic phức tạp
- ✅ AI tự động orchestrate tools
- ✅ Dễ mở rộng tính năng mới

**Bắt đầu ngay:**
```bash
python src/AI_agent_v2/discord_bot_v2.py
```

Enjoy! 🚀
