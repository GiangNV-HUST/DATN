# 🐳 HƯỚNG DẪN CHẠY DISCORD BOT VỚI DOCKER

## ✨ LỢI ÍCH CỦA DOCKER

### Tại sao nên dùng Docker?
- ✅ **Tự động khởi động lại** khi bot crash
- ✅ **Chạy trong background** không cần giữ terminal mở
- ✅ **Dễ dàng deploy** lên server
- ✅ **Môi trường nhất quán** trên mọi máy
- ✅ **Quản lý dependencies** tự động
- ✅ **Logs tập trung** dễ debug

## 📋 YÊU CẦU

### 1. Cài đặt Docker Desktop
- Download: https://www.docker.com/products/docker-desktop/
- Cài đặt và khởi động Docker Desktop
- Kiểm tra: `docker --version`

### 2. File .env đầy đủ
File `.env` phải chứa:
```env
# Database
DB_HOST=timescaledb
DB_PORT=5432
DB_NAME=stock
DB_USER=postgres
DB_PASSWORD=postgres123

# Discord
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_WEBHOOK_URL=your_webhook_url_here

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here
```

**LƯU Ý**: `DB_HOST` phải là `timescaledb` (tên service trong Docker)

## 🚀 CÁCH SỬ DỤNG

### Phương án 1: Dùng Scripts (KHUYẾN NGHỊ)

#### Khởi động bot:
```bash
docker-bot-start.bat
```

Script sẽ:
1. Kiểm tra Docker có chạy không
2. Kiểm tra .env file
3. Build Docker image
4. Khởi động bot container
5. Hiển thị hướng dẫn xem logs

#### Xem logs:
```bash
docker-bot-logs.bat
```

Hiển thị logs real-time. Press Ctrl+C để thoát.

#### Dừng bot:
```bash
docker-bot-stop.bat
```

### Phương án 2: Dùng Docker Commands

#### Chỉ chạy bot (không chạy các services khác):
```bash
# Build image
docker-compose build discord-bot

# Start bot + database
docker-compose up -d discord-bot timescaledb

# View logs
docker logs -f stock-discord-bot

# Stop bot
docker-compose stop discord-bot

# Restart bot
docker-compose restart discord-bot
```

#### Chạy toàn bộ hệ thống:
```bash
# Start everything
docker-compose up -d

# View all logs
docker-compose logs -f

# Stop everything
docker-compose down
```

## 🔍 KIỂM TRA TRẠNG THÁI

### Xem bot có đang chạy không:
```bash
docker ps | findstr discord-bot
```

Nếu thấy `stock-discord-bot` với status `Up` → Bot đang chạy

### Xem logs chi tiết:
```bash
docker logs stock-discord-bot

# Hoặc theo dõi real-time:
docker logs -f stock-discord-bot
```

### Kiểm tra health status:
```bash
docker inspect stock-discord-bot | findstr Health
```

### Vào trong container (debug):
```bash
docker exec -it stock-discord-bot /bin/bash
```

## 🔧 TROUBLESHOOTING

### Bot không khởi động:

**1. Kiểm tra logs:**
```bash
docker logs stock-discord-bot
```

**2. Kiểm tra environment variables:**
```bash
docker exec stock-discord-bot env | findstr DISCORD
docker exec stock-discord-bot env | findstr GEMINI
```

**3. Rebuild image:**
```bash
docker-compose build --no-cache discord-bot
docker-compose up -d discord-bot
```

### Bot bị crash liên tục:

**1. Xem lỗi trong logs:**
```bash
docker logs stock-discord-bot --tail 50
```

**2. Kiểm tra API keys:**
```bash
docker exec stock-discord-bot python -c "from src.config import Config; print('Token:', len(Config.DISCORD_BOT_TOKEN) if Config.DISCORD_BOT_TOKEN else 'MISSING'); print('Gemini:', len(Config.GEMINI_API_KEY) if Config.GEMINI_API_KEY else 'MISSING')"
```

**3. Test kết nối database:**
```bash
docker exec stock-discord-bot python -c "from src.AI_agent.database_tools import DatabaseTools; db = DatabaseTools(); print(db.get_latest_price('VCB')); db.close()"
```

### Lỗi "port already in use":

Dừng container cũ:
```bash
docker-compose stop discord-bot
docker rm stock-discord-bot
docker-compose up -d discord-bot
```

### Muốn update code:

**Cách 1: Sử dụng volume (nhanh):**
Code được mount vào container, chỉ cần restart:
```bash
docker-compose restart discord-bot
```

**Cách 2: Rebuild image (chậm hơn):**
```bash
docker-compose build discord-bot
docker-compose up -d discord-bot
```

## 📊 MONITORING

### Xem resource usage:
```bash
docker stats stock-discord-bot
```

Hiển thị:
- CPU usage
- Memory usage
- Network I/O
- Disk I/O

### Xem restart count:
```bash
docker inspect stock-discord-bot | findstr RestartCount
```

## 🎯 BEST PRACTICES

### 1. Luôn kiểm tra logs sau khi start:
```bash
docker-bot-start.bat
docker-bot-logs.bat
```

### 2. Đặt restart policy:
Đã được cấu hình trong docker-compose.yml:
```yaml
restart: unless-stopped
```

Bot sẽ tự động restart nếu:
- Container crash
- Docker daemon restart
- Server reboot

### 3. Backup .env file:
```bash
copy .env .env.backup
```

### 4. Monitor định kỳ:
Chạy command này mỗi ngày:
```bash
docker ps | findstr discord-bot
docker logs stock-discord-bot --tail 20
```

## 🚢 DEPLOY LÊN SERVER

### Trên server Linux/Cloud:

```bash
# 1. Clone repository
git clone <your-repo-url>
cd Final

# 2. Tạo .env file
nano .env
# (paste your environment variables)

# 3. Start bot
docker-compose up -d discord-bot timescaledb

# 4. Verify
docker logs -f stock-discord-bot
```

### Trên Windows Server:

Giống như trên máy local, dùng:
```bash
docker-bot-start.bat
```

## 📝 COMMANDS THAM KHẢO

### Quản lý container:
```bash
# Start
docker-compose up -d discord-bot

# Stop
docker-compose stop discord-bot

# Restart
docker-compose restart discord-bot

# Remove
docker-compose rm -f discord-bot

# Rebuild
docker-compose build discord-bot
```

### Logs & Debug:
```bash
# View logs
docker logs stock-discord-bot

# Follow logs
docker logs -f stock-discord-bot

# Last 100 lines
docker logs --tail 100 stock-discord-bot

# With timestamps
docker logs -t stock-discord-bot
```

### Health check:
```bash
# Container status
docker ps -a | findstr discord-bot

# Health status
docker inspect --format='{{.State.Health.Status}}' stock-discord-bot

# Full health logs
docker inspect stock-discord-bot | findstr Health -A 10
```

## 🎉 CHECKLIST

Trước khi chạy bot, đảm bảo:

- [ ] Docker Desktop đang chạy
- [ ] File `.env` tồn tại và có đủ variables
- [ ] `DISCORD_BOT_TOKEN` đúng
- [ ] `GEMINI_API_KEY` đúng
- [ ] Database (timescaledb) đang chạy
- [ ] Port 5432 không bị chiếm

Sau khi start bot, kiểm tra:

- [ ] Container status = `Up`
- [ ] Logs không có lỗi
- [ ] Bot online trên Discord
- [ ] Bot phản hồi test message

## 💡 TIPS

1. **Auto-start khi Windows boot:**
   - Thêm `docker-bot-start.bat` vào Startup folder
   - Đường dẫn: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

2. **Monitor với Portainer:**
   ```bash
   docker run -d -p 9000:9000 --name portainer \
     -v /var/run/docker.sock:/var/run/docker.sock \
     portainer/portainer-ce
   ```
   Truy cập: http://localhost:9000

3. **Backup logs:**
   ```bash
   docker logs stock-discord-bot > bot-logs-backup.txt
   ```

## 🆘 HỖ TRỢ

Nếu gặp vấn đề:

1. Kiểm tra logs: `docker logs stock-discord-bot`
2. Kiểm tra container status: `docker ps -a`
3. Test thủ công trong container: `docker exec -it stock-discord-bot /bin/bash`
4. Rebuild image: `docker-compose build --no-cache discord-bot`

---

**Tài liệu được tạo tự động bởi Claude Code** 🤖
