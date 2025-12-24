# 📚 VÍ DỤ SỬ DỤNG AGENT V2

## 🎯 Các ví dụ thực tế về Function Calling

---

## VÍ DỤ 1: SIMPLE QUERY - 1 Function Call

### Input:
```python
agent = StockAnalysisAgentV2()
response = agent.answer_question("VCB giá bao nhiêu?")
```

### Execution Flow:

```
┌─────────────────────────────────────────────────┐
│ Iteration 0: Gửi message                       │
├─────────────────────────────────────────────────┤
│ → chat.send_message("VCB giá bao nhiêu?")      │
│ ← Gemini response:                             │
│   {                                             │
│     function_call: {                            │
│       name: "get_latest_price",                 │
│       args: {ticker: "VCB"}                     │
│     }                                            │
│   }                                             │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Execute Function                                │
├─────────────────────────────────────────────────┤
│ function_name = "get_latest_price"              │
│ function_args = {ticker: "VCB"}                 │
│                                                  │
│ → db_tools.get_latest_price("VCB")             │
│ ← result = {                                    │
│     ticker: "VCB",                              │
│     close: 95000,                               │
│     open: 94500,                                │
│     rsi: 45.5,                                  │
│     ma5: 94800,                                 │
│     ma20: 93200                                 │
│   }                                             │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Iteration 1: Gửi function result                │
├─────────────────────────────────────────────────┤
│ → chat.send_message(FunctionResponse(...))     │
│ ← Gemini response:                             │
│   {                                             │
│     text: "💰 VCB hiện tại đang ở mức           │
│            95,000đ. RSI 45.5 cho thấy           │
│            cổ phiếu đang ở vùng trung lập..."  │
│   }                                             │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Return Final Response                           │
├─────────────────────────────────────────────────┤
│ response.text → "💰 VCB hiện tại..."           │
└─────────────────────────────────────────────────┘
```

### Logs:
```
🔧 AI calls: get_latest_price({'ticker': 'VCB'})
✅ Function result: {"ticker": "VCB", "close": 95000, ...}
```

### Output:
```
💰 VCB hiện tại đang ở mức 95,000đ
📊 Các chỉ số kỹ thuật:
   - RSI: 45.5 (trung lập)
   - MA5: 94,800đ
   - MA20: 93,200đ

📈 Nhận xét: Cổ phiếu đang trong xu hướng tăng nhẹ,
RSI ở vùng trung lập cho thấy chưa có dấu hiệu quá mua.
```

**Total iterations: 1**
**Total API calls: 2**

---

## VÍ DỤ 2: COMPARISON - 2 Function Calls

### Input:
```python
response = agent.answer_question("So sánh VCB và TCB về RSI")
```

### Execution Flow:

```
┌─────────────────────────────────────────────────┐
│ Iteration 0                                     │
├─────────────────────────────────────────────────┤
│ → "So sánh VCB và TCB về RSI"                   │
│ ← function_call: get_latest_price("VCB")        │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Execute: get_latest_price("VCB")                │
│ result = {ticker: "VCB", rsi: 45.5, ...}        │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Iteration 1                                     │
├─────────────────────────────────────────────────┤
│ → Send VCB result                               │
│ ← function_call: get_latest_price("TCB")        │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Execute: get_latest_price("TCB")                │
│ result = {ticker: "TCB", rsi: 52.3, ...}        │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Iteration 2                                     │
├─────────────────────────────────────────────────┤
│ → Send TCB result                               │
│ ← text: "So sánh VCB và TCB..."                │
└─────────────────────────────────────────────────┘
```

### Logs:
```
🔧 AI calls: get_latest_price({'ticker': 'VCB'})
✅ Function result: {"ticker": "VCB", "rsi": 45.5, ...}
🔧 AI calls: get_latest_price({'ticker': 'TCB'})
✅ Function result: {"ticker": "TCB", "rsi": 52.3, ...}
```

### Output:
```
⚖️ SO SÁNH VCB vs TCB

📊 VCB (Vietcombank):
   - RSI: 45.5 (trung lập)
   - Giá: 95,000đ

📊 TCB (Techcombank):
   - RSI: 52.3 (trung lập - cao hơn)
   - Giá: 28,500đ

🔍 Phân tích:
   - TCB có RSI cao hơn (52.3 vs 45.5), cho thấy
     momentum tăng mạnh hơn
   - VCB đang ở vùng oversold hơn, có thể có
     cơ hội mua vào tốt hơn
   - Cả 2 đều trong vùng trung lập, chưa quá mua/bán

💡 Khuyến nghị: VCB có tiềm năng tăng tốt hơn
                do RSI thấp hơn
```

**Total iterations: 2**
**Total API calls: 3**

---

## VÍ DỤ 3: COMPLEX QUERY - 3 Function Calls

### Input:
```python
response = agent.answer_question(
    "VCB có nên mua không? Dự đoán và xu hướng thế nào?"
)
```

### Execution Flow:

```
Iteration 0: get_latest_price("VCB")
    ↓
Iteration 1: get_predictions("VCB")
    ↓
Iteration 2: get_price_history("VCB", days=5)
    ↓
Iteration 3: Generate analysis
```

### Logs:
```
🔧 AI calls: get_latest_price({'ticker': 'VCB'})
✅ Function result: {"close": 95000, "rsi": 45.5, ...}
🔧 AI calls: get_predictions({'ticker': 'VCB'})
✅ Function result: {"day1": 96.5, "day2": 97.2, "day3": 98.0}
🔧 AI calls: get_price_history({'ticker': 'VCB', 'days': 5})
✅ Function result: [{"date": "2025-12-17", "close": 95000}, ...]
```

### Output:
```
📊 PHÂN TÍCH VCB - NÊN MUA KHÔNG?

💰 Giá hiện tại: 95,000đ
📈 RSI: 45.5 (trung lập)

🔮 Dự đoán 3 ngày tới:
   - Ngày 1: 96,500đ (+1.6%)
   - Ngày 2: 97,200đ (+2.3%)
   - Ngày 3: 98,000đ (+3.2%)

📉 Xu hướng 5 ngày qua:
   - Tăng đều từ 92,000đ → 95,000đ
   - Momentum tích cực

✅ KHUYẾN NGHỊ: NÊN MUA

Lý do:
1. RSI 45.5 chưa quá mua, còn dư địa tăng
2. Dự đoán cho thấy xu hướng tăng tiếp
3. 5 ngày qua tăng đều, momentum tốt
4. Giá có thể chạm 98,000đ trong 3 ngày

⚠️ Lưu ý: Nên đặt stop-loss ở 92,000đ
```

**Total iterations: 3**
**Total API calls: 4**

---

## VÍ DỤ 4: SCREENER - Search Function

### Input:
```python
response = agent.answer_question("Tìm cổ phiếu RSI dưới 30")
```

### Execution Flow:

```
┌─────────────────────────────────────────────────┐
│ Iteration 0                                     │
├─────────────────────────────────────────────────┤
│ → "Tìm cổ phiếu RSI dưới 30"                    │
│                                                  │
│ Gemini phân tích:                               │
│   - Cần tìm kiếm cổ phiếu                       │
│   - Tiêu chí: RSI < 30                          │
│   - Tool: search_stocks                         │
│                                                  │
│ ← function_call: {                              │
│     name: "search_stocks",                      │
│     args: {rsi_below: 30}                       │
│   }                                             │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Execute: search_stocks({rsi_below: 30})         │
├─────────────────────────────────────────────────┤
│ → db_tools.search_stocks_by_criteria(...)      │
│ ← result = [                                    │
│     {ticker: "AAA", close: 15000, rsi: 28.5},  │
│     {ticker: "BBB", close: 22000, rsi: 25.3},  │
│     {ticker: "CCC", close: 18000, rsi: 29.1}   │
│   ]                                             │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│ Iteration 1                                     │
├─────────────────────────────────────────────────┤
│ → Send search result                            │
│ ← text: "Tìm thấy 3 cổ phiếu..."              │
└─────────────────────────────────────────────────┘
```

### Output:
```
🔍 TÌM THẤY 3 CỔ PHIẾU RSI DƯỚI 30 (QUÁ BÁN)

1. 📉 BBB - 22,000đ
   - RSI: 25.3 (quá bán mạnh)
   - 💡 Cơ hội tốt cho entry

2. 📉 AAA - 15,000đ
   - RSI: 28.5 (quá bán)
   - 💡 Tiềm năng rebound

3. 📉 CCC - 18,000đ
   - RSI: 29.1 (gần oversold)
   - 💡 Theo dõi thêm

⚠️ Lưu ý:
- RSI < 30 cho thấy áp lực bán lớn
- Có thể là cơ hội mua vào khi đáy
- Nên chờ tín hiệu đảo chiều trước khi vào
```

**Total iterations: 1**
**Total API calls: 2**

---

## VÍ DỤ 5: NATURAL LANGUAGE PARSING

### Input:
```python
# User dùng ngôn ngữ tự nhiên, không cần format chuẩn
questions = [
    "VietComBank thế nào?",           # AI hiểu → VCB
    "So sánh Vietcombank và TCB",     # AI hiểu → VCB vs TCB
    "Tìm cổ phiếu quá bán",           # AI hiểu → RSI < 30
    "Cổ phiếu nào RSI cao",           # AI hiểu → RSI > 70
]
```

### AI Processing:

```python
# Question 1: "VietComBank thế nào?"
AI reasoning:
  - "VietComBank" = VCB ticker
  - User muốn biết thông tin hiện tại
  - → get_latest_price("VCB")

# Question 2: "So sánh Vietcombank và TCB"
AI reasoning:
  - "Vietcombank" = VCB
  - "TCB" = TCB
  - "So sánh" = cần data cả 2
  - → get_latest_price("VCB")
  - → get_latest_price("TCB")

# Question 3: "Tìm cổ phiếu quá bán"
AI reasoning:
  - "quá bán" = oversold = RSI < 30
  - "Tìm" = search
  - → search_stocks(rsi_below=30)

# Question 4: "Cổ phiếu nào RSI cao"
AI reasoning:
  - "RSI cao" = overbought = RSI > 70
  - → search_stocks(rsi_above=70)
```

---

## 🎯 SO SÁNH V1 vs V2

### Cùng 1 câu hỏi:

```python
question = "So sánh VCB và TCB"
```

### V1 (Hard-coded):
```python
def answer_question(self, question):
    # ❌ Không hỗ trợ comparison
    # Chỉ extract được 1 ticker
    ticker = extract_ticker(question)  # → "VCB" (thiếu TCB!)

    if ticker:
        data = get_latest_price(ticker)
        # Chỉ phân tích VCB, bỏ qua TCB
```

**Result:** ❌ Không trả lời đúng

### V2 (Function Calling):
```python
def answer_question(self, question):
    # ✅ AI tự hiểu cần 2 tickers
    # Iteration 1: get_latest_price("VCB")
    # Iteration 2: get_latest_price("TCB")
    # Iteration 3: So sánh và trả lời
```

**Result:** ✅ So sánh đầy đủ cả 2

---

## 💡 TIPS SỬ DỤNG

### 1. Hỏi tự nhiên
```python
# ✅ Tốt - Tự nhiên
"VCB có nên mua không?"
"So sánh VCB và TCB"
"Tìm cổ phiếu giá rẻ RSI thấp"

# ❌ Không cần - Quá cụ thể
"Hãy gọi get_latest_price cho VCB"
"Execute function search_stocks với rsi_below=30"
```

### 2. Cung cấp ngữ cảnh
```python
# ✅ Tốt
"VCB có nên mua không? Tôi muốn hold 3 tháng"

# ⚠️ Thiếu context
"VCB thế nào?"  # AI không biết bạn quan tâm gì
```

### 3. Kết hợp nhiều tiêu chí
```python
# ✅ AI tự parse và gọi đúng
"Tìm cổ phiếu RSI dưới 30 VÀ giá dưới 50k"
# → search_stocks(rsi_below=30, price_below=50000)
```

---

## 🧪 TEST CASES

### Test Function Calling:

```python
# File: test_agent_v2.py
from src.AI_agent_v2.stock_agent_v2 import StockAnalysisAgentV2

agent = StockAnalysisAgentV2()

# Test 1: Simple
print(agent.answer_question("VCB giá bao nhiêu?"))

# Test 2: Comparison
print(agent.answer_question("So sánh VCB và TCB"))

# Test 3: Screener
print(agent.answer_question("Tìm cổ phiếu RSI dưới 30"))

# Test 4: Natural language
print(agent.answer_question("Vietcombank có đáng mua không?"))

# Test 5: Complex
print(agent.answer_question("VCB xu hướng 5 ngày qua và dự đoán thế nào?"))
```

---

**Kết luận:** Agent V2 linh hoạt và thông minh hơn V1 rất nhiều! 🚀
