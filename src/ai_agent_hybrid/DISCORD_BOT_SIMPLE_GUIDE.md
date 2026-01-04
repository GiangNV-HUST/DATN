# HƯỚNG DẪN SỬ DỤNG DISCORD BOT SIMPLE

**Bot Phân Tích Chứng Khoán - Siêu Đơn Giản**

---

## ✨ ĐIỂM ĐẶC BIỆT

### Chỉ cần MENTION là xong!

**KHÔNG CẦN NHỚ LỆNH PHỨC TẠP**

Thay vì phải nhớ:
- ❌ `!price VCB`
- ❌ `!analysis HPG`
- ❌ `!screener RSI < 40`
- ❌ `!recommend 100000000`

**Chỉ cần:**
- ✅ `@stock_bot giá VCB`
- ✅ `@stock_bot phân tích HPG`
- ✅ `@stock_bot tìm cổ phiếu tốt`
- ✅ `@stock_bot với 100 triệu nên đầu tư gì`

### Bot tự động hiểu ý bạn!

Bot sử dụng AI để:
- 🤖 Phát hiện ý định (price, analysis, screener, investment...)
- 🎯 Tự động route đến handler phù hợp
- 💬 Trả lời bằng ngôn ngữ tự nhiên
- 🧠 Nhớ ngữ cảnh hội thoại

---

## CÀI ĐẶT

### 1. Yêu cầu

```bash
pip install discord.py google-generativeai python-dotenv
```

### 2. Cấu hình .env

Thêm vào file `Final/.env`:

```bash
# Discord Bot Token
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Gemini AI (để bot thông minh hơn)
GEMINI_API_KEY=your_gemini_api_key

# Database (đã có)
DB_HOST=localhost
DB_PORT=5434
DB_NAME=stock
DB_USER=postgres
DB_PASSWORD=your_password
```

### 3. Tạo Discord Bot

1. Vào [Discord Developer Portal](https://discord.com/developers/applications)
2. Tạo "New Application"
3. Vào tab "Bot" → "Add Bot"
4. Copy **Token** (đây là DISCORD_BOT_TOKEN)
5. Bật **Message Content Intent**
6. Vào tab "OAuth2" → "URL Generator"
7. Chọn:
   - Scopes: `bot`
   - Permissions: Send Messages, Read Message History, Embed Links
8. Copy URL và mở trong browser để invite bot vào server

### 4. Chạy Bot

```bash
cd src/ai_agent_hybrid
python discord_bot_simple.py
```

**Output:**
```
============================================================
🤖 SIMPLE STOCK BOT
============================================================
✨ Chỉ cần mention @stock_bot <câu hỏi> để sử dụng!
📝 Ví dụ: @stock_bot giá VCB
============================================================

Bot ready! Logged in as stock_bot#1234
📡 Serving 1 servers
```

---

## CÁCH SỬ DỤNG

### ✨ CÔNG THỨC DUY NHẤT

```
@stock_bot <câu hỏi bất kỳ>
```

**Đó là tất cả!** Bot sẽ tự hiểu và trả lời.

---

## VÍ DỤ CỤ THỂ

### 1. Xem Giá Cổ Phiếu

```
@stock_bot giá VCB
@stock_bot VCB giá bao nhiêu
@stock_bot cho tôi xem giá HPG
@stock_bot price FPT
```

**Bot trả về:**
```
📊 VCB - GIÁ HIỆN TẠI

💰 Giá đóng cửa: 57,500 VND
📈 Khối lượng: 2,450,000
🟢 Thay đổi: +1.50%

Chỉ báo kỹ thuật:
• RSI: 46.6 (Trung bình)
• MA20: 55,200 VND (Tăng 📈)
• MACD: 0.25

Cập nhật: 2026-01-04
```

---

### 2. Phân Tích Kỹ Thuật

```
@stock_bot phân tích HPG
@stock_bot đánh giá ACB
@stock_bot analyze VNM
@stock_bot HPG có nên mua không
```

**Bot trả về:**
```
📊 PHÂN TÍCH HPG

💰 Giá hiện tại: 25,300 VND

📈 CHỈ BÁO KỸ THUẬT:
• RSI: 32.5 💡 QUÁ BÁN - Có thể là cơ hội mua
• MA20: 26,100 VND 📉 Giá dưới MA20 (tiêu cực)
• MACD: -0.15 🔴 Tiêu cực

📊 XU HƯỚNG GIÁ:
• 5 ngày gần đây: Giảm 3.2% 📉

💡 GỢI Ý:
• RSI thấp - có thể xem xét mua khi có tín hiệu tích cực khác

Dữ liệu cập nhật: 2026-01-04
```

---

### 3. Tìm Cổ Phiếu Tốt

```
@stock_bot tìm cổ phiếu tốt
@stock_bot tìm cổ phiếu RSI thấp
@stock_bot cổ phiếu nào đáng mua
@stock_bot screener PE thấp
```

**Bot trả về:**
```
🔍 TÌM THẤY 10 CỔ PHIẾU

1. HPG: 25,300 VND | RSI: 32.5 💡
2. VNM: 68,500 VND | RSI: 35.2 💡
3. FPT: 112,000 VND | RSI: 38.7
4. ACB: 23,800 VND | RSI: 41.2
5. TCB: 24,500 VND | RSI: 43.1
...

💡 Gợi ý: Dùng @stock_bot phân tích <mã> để xem chi tiết
```

---

### 4. Tư Vấn Đầu Tư

```
@stock_bot với 100 triệu nên đầu tư gì
@stock_bot 50 triệu nên mua cổ phiếu nào
@stock_bot tư vấn đầu tư cho tôi
@stock_bot tôi có 200 triệu muốn đầu tư
```

**Bot trả về (với AI):**
```
💰 TƯ VẤN ĐẦU TƯ CHO 100 TRIỆU VND

Với số vốn 100 triệu VND, tôi đề xuất phân bổ vào 3 cổ phiếu sau:

1. HPG (40% - 40 triệu):
   - Ngành thép, vị thế số 1
   - RSI thấp (32.5) - đang oversold
   - Tiềm năng phục hồi tốt

2. VNM (35% - 35 triệu):
   - Blue chip, ổn định
   - Cổ tức ổn định
   - Phù hợp nắm giữ dài hạn

3. FPT (25% - 25 triệu):
   - Công nghệ, tăng trưởng tốt
   - Đa dạng hóa danh mục

Rủi ro:
- Thị trường biến động
- Chỉ đầu tư khi đã nghiên cứu kỹ

⚠️ Đây chỉ là gợi ý, không phải lời khuyên tài chính.
```

---

### 5. So Sánh Cổ Phiếu

```
@stock_bot so sánh VCB và ACB
@stock_bot VCB vs TCB
@stock_bot HPG hay FPT tốt hơn
```

**Bot trả về:**
```
⚖️ SO SÁNH VCB vs ACB

💰 Giá:
• VCB: 57,500 VND
• ACB: 23,800 VND

📊 RSI:
• VCB: 46.6
• ACB: 41.2 (Tốt hơn 💡)

📈 Thay đổi:
• VCB: +1.50%
• ACB: +0.80%

💡 Dùng @stock_bot phân tích <mã> để xem chi tiết
```

---

### 6. Câu Hỏi Chung (AI)

```
@stock_bot nên đầu tư vào ngành gì năm 2026
@stock_bot PE là gì
@stock_bot RSI thấp hơn 30 nghĩa là gì
@stock_bot cách đọc biểu đồ nến
```

**Bot sử dụng AI để trả lời các câu hỏi chung về chứng khoán**

---

## BOT TỰ ĐỘNG HIỂU

Bot có **6 loại xử lý tự động**:

### 1. Price Queries (Giá)
**Keywords**: giá, gia, price, bao nhiêu

**Ví dụ:**
- giá VCB
- VCB giá bao nhiêu
- price HPG

**→ Hiển thị giá + chỉ báo kỹ thuật**

---

### 2. Analysis Queries (Phân tích)
**Keywords**: phân tích, phan tich, analyze, analysis, đánh giá, nhận xét

**Ví dụ:**
- phân tích VCB
- đánh giá HPG
- analyze FPT

**→ Phân tích kỹ thuật chi tiết**

---

### 3. Screener Queries (Tìm kiếm)
**Keywords**: tìm, tim, find, search, screener, lọc, loc, danh sách

**Ví dụ:**
- tìm cổ phiếu tốt
- tìm cổ phiếu RSI thấp
- screener PE < 15

**→ Danh sách cổ phiếu phù hợp**

---

### 4. Investment Queries (Đầu tư)
**Keywords**: đầu tư, dau tu, invest, mua, buy, nên, nen, khuyến nghị

**Ví dụ:**
- với 100 triệu nên đầu tư gì
- nên mua cổ phiếu nào
- tư vấn đầu tư

**→ Gợi ý phân bổ vốn (dùng AI)**

---

### 5. Compare Queries (So sánh)
**Keywords**: so sánh, so sanh, compare, vs, hay, tốt hơn

**Ví dụ:**
- so sánh VCB và ACB
- VCB vs TCB
- HPG hay FPT tốt hơn

**→ So sánh 2 cổ phiếu**

---

### 6. General Queries (Câu hỏi chung)
**Tất cả các câu hỏi khác**

**Ví dụ:**
- PE là gì
- cách đọc biểu đồ
- nên đầu tư vào ngành gì

**→ AI trả lời (nếu có GEMINI_API_KEY)**

---

## TÍNH NĂNG

### ✅ Đã Có

1. **Tự động phát hiện ý định**
   - 6 loại query được detect tự động
   - Không cần nhớ cú pháp lệnh

2. **Natural language**
   - Hiểu tiếng Việt tự nhiên
   - Linh hoạt với nhiều cách hỏi

3. **AI-powered responses**
   - Sử dụng Gemini AI cho câu hỏi phức tạp
   - Tư vấn đầu tư thông minh

4. **Conversation memory**
   - Nhớ 5 tin nhắn gần nhất
   - Context-aware responses

5. **Rich formatting**
   - Emoji để dễ đọc
   - Phân loại thông tin rõ ràng

6. **Performance**
   - Database caching
   - Async processing
   - Response < 2s

### 🔜 Sắp Có

1. **Watchlist**
   - Theo dõi danh sách cổ phiếu
   - Nhận thông báo tự động

2. **Alerts**
   - Cảnh báo khi giá đạt ngưỡng
   - DM tự động

3. **Portfolio tracking**
   - Quản lý danh mục đầu tư
   - Tính P/L realtime

4. **Charts**
   - Tạo biểu đồ giá
   - Technical analysis charts

---

## COMMANDS DỰ PHÒNG

Vẫn có thể dùng commands (nhưng không cần thiết):

```bash
!help      # Hiển thị hướng dẫn
!stats     # Thống kê bot
```

**Nhưng thực tế chỉ cần mention bot!**

---

## TROUBLESHOOTING

### Bot không reply

**1. Check permissions:**
- Bot có permission "Send Messages"?
- Bot có permission "Read Message History"?
- Channel có restrict bot không?

**2. Check bot status:**
- Bot có online không?
- Logs có lỗi gì không?

**3. Check mention:**
- Đã mention đúng bot chưa? `@stock_bot`
- Có content sau mention không?

### Bot reply chậm

**Nguyên nhân:**
- Database query chậm
- AI generation mất thời gian
- Network latency

**Bình thường:**
- Simple queries: < 1s
- AI queries: 2-5s
- Investment advice: 3-10s

### Bot reply "Lỗi"

**Check:**
1. Database có chạy không?
2. GEMINI_API_KEY có đúng không?
3. Logs có chi tiết gì?

**Fix:**
```bash
# Test database
cd src/ai_agent_hybrid
python test_simple.py

# Check logs
python discord_bot_simple.py
# Xem output để biết lỗi gì
```

---

## STATISTICS

### Tracking

Bot tự động track:
- Tổng queries
- Queries theo loại (price, analysis, screener, investment, general)
- Errors
- Success rate
- Uptime
- Database cache stats

### Xem stats

```
!stats
```

**Output:**
```
📊 Thống kê Bot

📈 Truy vấn:
Tổng: 150
Giá: 50
Phân tích: 30
Tìm kiếm: 25
Đầu tư: 20
Khác: 25

⚡ Hiệu suất:
Lỗi: 5
Thành công: 145
Success rate: 96.7%

⏱️ Uptime:
2d 5h 30m

💾 Database:
Calls: 200
Cache hits: 120
Hit rate: 60%
```

---

## SO SÁNH VERSIONS

### Bot Cũ (discord_bot_hybrid.py)

**Cần nhớ nhiều lệnh:**
```
!price VCB
!analysis HPG
!screener
!recommend 100000000
!compare VCB ACB
!watchlist add VCB
!alert VCB 60000
```

**Khó nhớ, dễ nhầm**

### Bot Mới (discord_bot_simple.py) ✨

**Chỉ cần mention:**
```
@stock_bot giá VCB
@stock_bot phân tích HPG
@stock_bot tìm cổ phiếu tốt
@stock_bot với 100 triệu nên đầu tư gì
@stock_bot so sánh VCB và ACB
```

**Tự nhiên, dễ dùng**

---

## BEST PRACTICES

### 1. Hỏi rõ ràng

✅ **Good:**
```
@stock_bot giá VCB
@stock_bot phân tích HPG
@stock_bot tìm cổ phiếu RSI thấp
```

❌ **Bad:**
```
@stock_bot VCB
@stock_bot HPG
@stock_bot cổ phiếu
```

### 2. Một câu hỏi mỗi lần

✅ **Good:**
```
@stock_bot giá VCB
(đợi bot reply)
@stock_bot phân tích VCB
```

❌ **Bad:**
```
@stock_bot giá VCB, HPG, FPT, và phân tích ACB, TCB
```

### 3. Dùng mã chính xác

✅ **Good:**
```
@stock_bot giá VCB
@stock_bot phân tích HPG
```

❌ **Bad:**
```
@stock_bot giá vcb (lowercase - may not work)
@stock_bot giá Vietcombank (tên công ty không work)
```

---

## PERFORMANCE TIPS

### 1. Tận dụng cache

**Hỏi lại trong vòng 30s = instant response**

```
@stock_bot giá VCB  (Query DB - 500ms)
@stock_bot giá VCB  (From cache - 10ms) ✨
```

### 2. Batch queries

**Thay vì:**
```
@stock_bot giá VCB
@stock_bot giá ACB
@stock_bot giá TCB
```

**Dùng:**
```
@stock_bot so sánh VCB và ACB và TCB
```

### 3. Câu hỏi cụ thể

**Câu hỏi càng cụ thể, bot trả lời càng nhanh:**

✅ Fast: `@stock_bot giá VCB`
⚡ Medium: `@stock_bot phân tích VCB`
🐌 Slow: `@stock_bot với 100 triệu nên đầu tư gì` (dùng AI)

---

## FAQ

### Q: Bot có hiểu tiếng Anh không?

A: Có! Bot hiểu cả tiếng Việt và tiếng Anh.
```
@stock_bot price VCB
@stock_bot analyze HPG
```

### Q: Bot có nhớ hội thoại trước không?

A: Có! Bot nhớ 5 tin nhắn gần nhất của mỗi user.

### Q: Tôi có thể hỏi nhiều cổ phiếu cùng lúc không?

A: Tốt nhất là hỏi từng cổ phiếu hoặc dùng "so sánh" cho 2 mã.

### Q: Bot reply chậm là do sao?

A:
- Simple queries (giá, phân tích): < 1s
- AI queries (tư vấn đầu tư): 3-5s
- Nếu chậm hơn → check network/database

### Q: Bot có miễn phí không?

A: Có! Hoàn toàn miễn phí. Chỉ cần có:
- DISCORD_BOT_TOKEN (free từ Discord)
- GEMINI_API_KEY (free tier từ Google)
- Database (local PostgreSQL)

### Q: Tôi có thể deploy bot lên server không?

A: Có! Xem phần Deployment trong README_FULL.md

---

## DEPLOYMENT

### Local (Windows/Mac/Linux)

```bash
cd src/ai_agent_hybrid
python discord_bot_simple.py
```

### Server (Linux)

```bash
# Install dependencies
pip install discord.py google-generativeai python-dotenv

# Run with nohup
nohup python discord_bot_simple.py > bot.log 2>&1 &

# Or use systemd
sudo systemctl start discord-bot
```

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements_discord.txt .
RUN pip install -r requirements_discord.txt
COPY . .
CMD ["python", "discord_bot_simple.py"]
```

```bash
docker build -t stock-bot .
docker run -d --name stock-bot --env-file .env stock-bot
```

---

## SUPPORT

### Logs

```bash
# Run bot với logs
python discord_bot_simple.py

# Xem chi tiết errors
# Logs sẽ hiện trong terminal
```

### Test

```bash
# Test database connection
python test_simple.py

# Test AI integration
python test_investment_simple.py
```

### Issues

Nếu gặp vấn đề:
1. Check logs
2. Test database connection
3. Verify .env configuration
4. Check Discord permissions

---

## SUMMARY

### 🎯 Core Concept

**1 công thức duy nhất:**
```
@stock_bot <câu hỏi>
```

### ✨ Features

- ✅ Auto intent detection
- ✅ Natural language
- ✅ AI-powered
- ✅ Conversation memory
- ✅ Rich formatting
- ✅ Fast & reliable

### 🚀 Getting Started

```bash
# 1. Install
pip install discord.py google-generativeai

# 2. Configure .env
DISCORD_BOT_TOKEN=...
GEMINI_API_KEY=...

# 3. Run
python discord_bot_simple.py

# 4. Use
@stock_bot giá VCB
```

---

**That's it! Enjoy your simple stock bot! 🎉**
