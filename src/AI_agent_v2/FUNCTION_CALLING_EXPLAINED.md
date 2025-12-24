# 🎓 GIẢI THÍCH CHI TIẾT HÀM `chat_with_tools`

## 📋 MỤC LỤC
1. [Tổng quan](#tổng-quan)
2. [Flow hoạt động](#flow-hoạt-động)
3. [Phân tích từng dòng code](#phân-tích-từng-dòng-code)
4. [Ví dụ thực tế](#ví-dụ-thực-tế)
5. [Vấn đề thường gặp](#vấn-đề-thường-gặp)

---

## 🎯 TỔNG QUAN

### Hàm làm gì?

```python
def chat_with_tools(self, message: str, max_iterations: int = 5) -> str:
```

**Mục đích:**
- Nhận tin nhắn từ user
- Để AI tự động quyết định gọi tools nào cần thiết
- Xử lý vòng lặp Function Calling
- Trả về câu trả lời cuối cùng

**Khác với V1:**
- V1: Developer code logic gọi tools
- V2: AI tự quyết định và gọi tools

---

## 🔄 FLOW HOẠT ĐỘNG

```
┌──────────────────────────────────────────────────────────┐
│ 1. User gửi message: "VCB giá bao nhiêu?"                │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 2. Khởi tạo chat session với Gemini                      │
│    self.chat = self.model.start_chat(...)                │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 3. Gửi message tới Gemini                                │
│    response = self.chat.send_message(message)            │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 4. Gemini phân tích và quyết định                        │
│    "Cần gọi tool: get_latest_price(ticker='VCB')"        │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 5. Kiểm tra response có function_call không?             │
│    if part.function_call: → YES                          │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 6. Extract thông tin function call                       │
│    function_name = "get_latest_price"                    │
│    function_args = {"ticker": "VCB"}                     │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 7. Execute function                                       │
│    result = self._execute_function(name, args)           │
│    result = {"close": 95000, "rsi": 45.5, ...}          │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 8. Gửi kết quả về cho Gemini                             │
│    response = self.chat.send_message(                    │
│        FunctionResponse(result)                          │
│    )                                                      │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 9. Gemini nhận data và phân tích                         │
│    "VCB hiện tại 95,000đ, RSI 45.5 (trung lập)..."      │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 10. Kiểm tra lại: Còn function call nữa không?          │
│     if part.function_call: → NO (đã có đủ data)         │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 11. Break khỏi loop, trả về response.text               │
│     return "VCB hiện tại 95,000đ..."                    │
└──────────────────────────────────────────────────────────┘
```

---

## 🔍 PHÂN TÍCH TỪNG DÒNG CODE

### **BƯỚC 1: Khởi tạo Chat Session**

```python
# Line 187
self.chat = self.model.start_chat(enable_automatic_function_calling=False)
```

**Giải thích:**
- `start_chat()`: Tạo conversation mới với Gemini
- `enable_automatic_function_calling=False`: **QUAN TRỌNG!**
  - `False` = Gemini KHÔNG tự động gọi function
  - Gemini chỉ **trả về function_call object**
  - **TA** sẽ tự execute function và gửi kết quả về

**Tại sao dùng False?**
- Để kiểm soát việc execute functions
- Có thể log, validate, error handling
- Có thể limit số lần gọi (tránh infinite loop)

**Nếu dùng True:**
```python
# Gemini tự động gọi function → TA KHÔNG kiểm soát
self.chat = self.model.start_chat(enable_automatic_function_calling=True)
response = self.chat.send_message(message)
# → Gemini tự gọi get_latest_price, ta không biết gì!
```

---

### **BƯỚC 2: Gửi Message Đầu Tiên**

```python
# Line 190
response = self.chat.send_message(message)
```

**Giải thích:**
- Gửi tin nhắn user tới Gemini
- `message` = "VCB giá bao nhiêu?"

**Response structure:**
```python
response = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "function_call": {
                            "name": "get_latest_price",
                            "args": {"ticker": "VCB"}
                        }
                    }
                ]
            }
        }
    ]
}
```

---

### **BƯỚC 3: Vòng Lặp Function Calling**

```python
# Line 192-193
iteration = 0
while iteration < max_iterations:
```

**Giải thích:**
- `max_iterations = 5`: Giới hạn tối đa 5 lần gọi tools
- Tránh **infinite loop** nếu AI cứ gọi tools mãi

**Ví dụ khi cần nhiều iterations:**

```
User: "So sánh VCB và TCB về RSI"

Iteration 1: AI gọi get_latest_price("VCB")
Iteration 2: AI gọi get_latest_price("TCB")
Iteration 3: AI phân tích và trả lời (DONE)

→ Tổng: 2 iterations
```

---

### **BƯỚC 4: Kiểm Tra Response Có Parts Không**

```python
# Line 195-196
if not response.candidates[0].content.parts:
    break
```

**Giải thích:**
- `response.candidates[0]`: Lấy candidate đầu tiên (Gemini trả về danh sách)
- `.content.parts`: Danh sách các phần trong response
- Nếu **không có parts** → response rỗng → break

**Khi nào không có parts?**
- Gemini từ chối trả lời (safety filter)
- Response bị block
- Lỗi hệ thống

---

### **BƯỚC 5: Lấy Part Đầu Tiên**

```python
# Line 199
part = response.candidates[0].content.parts[0]
```

**Giải thích:**
- `parts[0]`: Lấy phần đầu tiên
- Part có thể là:
  - **Text response**: `part.text = "VCB hiện tại..."`
  - **Function call**: `part.function_call = {...}`

**Structure của part:**
```python
# Case 1: Text response
part = {
    "text": "VCB hiện tại 95,000đ..."
}

# Case 2: Function call
part = {
    "function_call": {
        "name": "get_latest_price",
        "args": {"ticker": "VCB"}
    }
}
```

---

### **BƯỚC 6: Kiểm Tra Function Call**

```python
# Line 202-203
if not hasattr(part, 'function_call') or not part.function_call:
    break
```

**Giải thích:**
- `hasattr(part, 'function_call')`: Kiểm tra part có attribute `function_call` không?
- `not part.function_call`: Kiểm tra function_call có giá trị không (không phải None/empty)

**Nếu KHÔNG có function_call:**
- → Part là text response
- → AI đã trả lời xong
- → Break khỏi loop

**Nếu CÓ function_call:**
- → AI muốn gọi tool
- → Tiếp tục xử lý

---

### **BƯỚC 7: Extract Function Information**

```python
# Line 206-208
function_call = part.function_call
function_name = function_call.name
function_args = dict(function_call.args)
```

**Giải thích:**
- `function_call.name`: Tên function AI muốn gọi
- `function_call.args`: Arguments dưới dạng dict-like object
- `dict(...)`: Convert sang Python dict thường

**Ví dụ:**
```python
# AI quyết định:
function_name = "get_latest_price"
function_args = {"ticker": "VCB"}

# Log ra:
logger.info(f"🔧 AI calls: get_latest_price({'ticker': 'VCB'})")
```

---

### **BƯỚC 8: Execute Function**

```python
# Line 213
function_result = self._execute_function(function_name, function_args)
```

**Giải thích:**
- Gọi method `_execute_function` để thực thi
- Method này routing tới đúng tool:

```python
def _execute_function(self, function_name, args):
    if function_name == "get_latest_price":
        return self.db_tools.get_latest_price(args["ticker"])
    elif function_name == "get_price_history":
        return self.db_tools.get_price_history(...)
    # ...
```

**Kết quả:**
```python
function_result = {
    "ticker": "VCB",
    "close": 95000,
    "open": 94500,
    "rsi": 45.5,
    "ma5": 94800,
    "ma20": 93200,
    # ...
}
```

---

### **BƯỚC 9: Gửi Kết Quả Về Cho AI**

```python
# Line 218-226
response = self.chat.send_message(
    genai.protos.Content(
        parts=[
            genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=function_name,
                    response={"result": function_result}
                )
            )
        ]
    )
)
```

**Giải thích - ĐÂY LÀ PHẦN KHÁC NHẤT:**

#### 9.1. Tại sao không gửi text thường?
```python
# ❌ KHÔNG thể làm thế này:
response = self.chat.send_message(str(function_result))
```

**Lý do:**
- Gemini cần biết đây là **kết quả của function call**
- Không phải message mới từ user
- Phải dùng đúng protocol: `FunctionResponse`

#### 9.2. Cấu trúc `genai.protos.Content`

```python
Content(
    parts=[...]  # Danh sách các Part
)
```

- `Content`: Đại diện cho 1 message trong conversation
- `parts`: Các phần của message (có thể nhiều parts)

#### 9.3. Cấu trúc `genai.protos.Part`

```python
Part(
    function_response=FunctionResponse(...)
)
```

- `Part`: 1 phần của message
- `function_response`: Đánh dấu đây là kết quả function

#### 9.4. Cấu trúc `FunctionResponse`

```python
FunctionResponse(
    name=function_name,           # Tên function đã gọi
    response={"result": result}   # Kết quả
)
```

- `name`: "get_latest_price" - để Gemini biết kết quả từ function nào
- `response`: Dict chứa kết quả, **phải có key "result"**

**Ví dụ message gửi đi:**
```python
{
    "parts": [
        {
            "function_response": {
                "name": "get_latest_price",
                "response": {
                    "result": {
                        "ticker": "VCB",
                        "close": 95000,
                        "rsi": 45.5
                    }
                }
            }
        }
    ]
}
```

---

### **BƯỚC 10: Lặp Lại Hoặc Kết Thúc**

```python
# Line 228
iteration += 1
```

**Sau khi gửi function result:**
- Loop quay lại đầu
- Kiểm tra response mới
- Nếu AI còn muốn gọi tool khác → tiếp tục
- Nếu AI trả text → break và return

---

### **BƯỚC 11: Trả Về Kết Quả**

```python
# Line 232-236
if response.text:
    return response.text
else:
    return "❌ Không thể tạo response. Vui lòng thử lại."
```

**Giải thích:**
- `response.text`: Text response cuối cùng từ AI
- Nếu không có text → lỗi → trả về message mặc định

---

## 🎬 VÍ DỤ THỰC TÊ

### **Ví dụ 1: Simple Query - 1 Tool Call**

```python
message = "VCB giá bao nhiêu?"
```

**Timeline:**

```
T0: User → "VCB giá bao nhiêu?"
    ↓
T1: Agent gửi tới Gemini
    ↓
T2: Gemini → function_call: get_latest_price(ticker="VCB")
    ↓
T3: Agent execute → result = {close: 95000, rsi: 45.5, ...}
    ↓
T4: Agent gửi result về Gemini
    ↓
T5: Gemini → text: "VCB hiện tại 95,000đ, RSI 45.5..."
    ↓
T6: Agent return text
```

**Iterations: 1**

---

### **Ví dụ 2: Complex Query - Multiple Tool Calls**

```python
message = "So sánh VCB và TCB về RSI"
```

**Timeline:**

```
T0: User → "So sánh VCB và TCB về RSI"
    ↓
T1: Gemini → function_call: get_latest_price(ticker="VCB")
    ↓
T2: Agent execute → {ticker: VCB, rsi: 45.5, ...}
    ↓
T3: Gemini → function_call: get_latest_price(ticker="TCB")
    ↓
T4: Agent execute → {ticker: TCB, rsi: 52.3, ...}
    ↓
T5: Gemini → text: "VCB RSI=45.5 < TCB RSI=52.3. VCB đang oversold hơn..."
    ↓
T6: Agent return text
```

**Iterations: 2**

---

### **Ví dụ 3: Screener Query**

```python
message = "Tìm cổ phiếu RSI dưới 30"
```

**Timeline:**

```
T0: User → "Tìm cổ phiếu RSI dưới 30"
    ↓
T1: Gemini phân tích → Cần search_stocks với rsi_below=30
    ↓
T2: Gemini → function_call: search_stocks(rsi_below=30)
    ↓
T3: Agent execute → [{ticker: AAA, rsi: 28}, {ticker: BBB, rsi: 25}, ...]
    ↓
T4: Gemini → text: "Tìm thấy 5 cổ phiếu: AAA (RSI=28), BBB (RSI=25)..."
    ↓
T5: Agent return text
```

**Iterations: 1**

---

## ⚠️ VẤN ĐỀ THƯỜNG GẶP

### **1. Infinite Loop**

**Vấn đề:**
```python
# AI cứ gọi tools mãi không dừng
while True:  # ❌ Nguy hiểm!
    if function_call:
        execute()
```

**Giải pháp:**
```python
# Giới hạn iterations
while iteration < max_iterations:  # ✅
    iteration += 1
```

---

### **2. Sai Cấu Trúc FunctionResponse**

**Lỗi:**
```python
# ❌ SAI - Thiếu key "result"
response = {"data": function_result}

# ❌ SAI - Gửi string
response = str(function_result)

# ✅ ĐÚNG
response = {"result": function_result}
```

---

### **3. Không Kiểm Tra function_call**

**Lỗi:**
```python
# ❌ Assume luôn có function_call
function_name = part.function_call.name  # → AttributeError!
```

**Đúng:**
```python
# ✅ Kiểm tra trước
if hasattr(part, 'function_call') and part.function_call:
    function_name = part.function_call.name
```

---

### **4. Không Xử Lý Lỗi Execute Function**

**Lỗi:**
```python
# ❌ Không handle error
result = self._execute_function(name, args)
# → Nếu function bị lỗi → crash!
```

**Đúng:**
```python
# ✅ Wrap trong try-except
try:
    result = self._execute_function(name, args)
except Exception as e:
    result = {"error": str(e)}
```

---

## 📊 PERFORMANCE

### Số API Calls

**Simple query:**
- Request 1: User message → Function call
- Request 2: Function result → Text response
- **Total: 2 API calls**

**Complex query (2 tools):**
- Request 1: User message → Function call #1
- Request 2: Function result #1 → Function call #2
- Request 3: Function result #2 → Text response
- **Total: 3 API calls**

**Formula:**
```
API calls = 1 (initial) + N (tools) + 1 (final response)
           = N + 2
```

---

## 🎯 KẾT LUẬN

Hàm `chat_with_tools` là **trái tim** của Function Calling Agent:

1. **Khởi tạo chat** với Gemini
2. **Gửi message** từ user
3. **Loop** để xử lý function calls:
   - Kiểm tra response có function_call?
   - Extract function name & args
   - Execute function
   - Gửi result về Gemini
   - Lặp lại nếu còn function calls
4. **Return** text response cuối cùng

**Key Points:**
- ✅ `enable_automatic_function_calling=False` để kiểm soát
- ✅ `max_iterations` để tránh infinite loop
- ✅ Dùng `FunctionResponse` để gửi kết quả
- ✅ Kiểm tra `function_call` attribute trước khi access
- ✅ Handle errors trong `_execute_function`

---

**Tài liệu này giải thích:** Cách Gemini Function Calling hoạt động trong Agent V2! 🎉
