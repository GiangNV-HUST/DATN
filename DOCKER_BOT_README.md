# 🤖 Discord Bot - Docker Setup

## 📚 Tổng quan

Discord Bot được dockerize để:
- Chạy tự động 24/7
- Tự động restart khi crash
- Dễ dàng deploy
- Quản lý dependencies nhất quán

## 🎯 Quick Start

### Bước 1: Chuẩn bị

```bash
# Đảm bảo Docker Desktop đang chạy
docker --version

# Kiểm tra .env file có đầy đủ:
# - DISCORD_BOT_TOKEN
# - GEMINI_API_KEY
# - DB_HOST=timescaledb (quan trọng!)
```

### Bước 2: Khởi động

**Cách nhanh nhất:**
```bash
docker-bot-start.bat
```

**Hoặc thủ công:**
```bash
docker-compose up -d discord-bot timescaledb
```

### Bước 3: Kiểm tra

```bash
# Xem logs
docker-bot-logs.bat

# Hoặc
docker logs -f stock-discord-bot
```

### Bước 4: Test trên Discord

Gửi message trong Discord:
```
@Stock Bot VCB như thế nào?
```

Hoặc dùng command:
```
!ask VCB có đáng mua không?
```

## 📁 Files Đã Tạo

```
├── Dockerfile.bot              # Docker image cho bot
├── docker-compose.yml          # Đã thêm discord-bot service
├── .dockerignore              # Loại trừ files không cần
├── docker-bot-start.bat       # Script khởi động bot
├── docker-bot-stop.bat        # Script dừng bot
├── docker-bot-logs.bat        # Script xem logs
├── HUONG_DAN_DOCKER_BOT.md    # Hướng dẫn chi tiết
└── DOCKER_BOT_README.md       # File này
```

## 🔧 Docker Compose Config

Bot service đã được thêm vào `docker-compose.yml`:

```yaml
discord-bot:
  build:
    context: .
    dockerfile: Dockerfile.bot
  container_name: stock-discord-bot
  depends_on:
    timescaledb:
      condition: service_healthy
  environment:
    DB_HOST: timescaledb
    DB_PORT: 5432
    DB_NAME: stock
    DB_USER: postgres
    DB_PASSWORD: postgres123
    DISCORD_BOT_TOKEN: ${DISCORD_BOT_TOKEN}
    GEMINI_API_KEY: ${GEMINI_API_KEY}
  restart: unless-stopped
  networks:
    - stock-network
```

## 🚀 Commands

### Quản lý bot:

```bash
# Start
docker-bot-start.bat

# Stop
docker-bot-stop.bat

# Logs
docker-bot-logs.bat

# Restart
docker-compose restart discord-bot

# Remove & recreate
docker-compose rm -f discord-bot
docker-compose up -d discord-bot
```

### Debug:

```bash
# Check status
docker ps | findstr discord-bot

# View health
docker inspect stock-discord-bot | findstr Health

# Enter container
docker exec -it stock-discord-bot /bin/bash

# Test inside container
docker exec stock-discord-bot python -c "from src.config import Config; print('Bot Token:', 'OK' if Config.DISCORD_BOT_TOKEN else 'MISSING')"
```

## 💡 Tính năng Auto-Restart

Bot được cấu hình với `restart: unless-stopped`, nghĩa là:
- ✅ Auto restart nếu bot crash
- ✅ Auto start khi Docker daemon restart
- ✅ Auto start sau khi server reboot
- ❌ Không restart nếu bạn stop thủ công

## 🔍 Monitoring

### Xem resource usage:
```bash
docker stats stock-discord-bot
```

### Xem logs với filter:
```bash
# Only errors
docker logs stock-discord-bot 2>&1 | findstr ERROR

# Only INFO
docker logs stock-discord-bot 2>&1 | findstr INFO

# Last 50 lines
docker logs --tail 50 stock-discord-bot
```

## 📋 Checklist

Đảm bảo trước khi chạy:

**Environment:**
- [ ] Docker Desktop installed & running
- [ ] File `.env` exists
- [ ] `DISCORD_BOT_TOKEN` in .env
- [ ] `GEMINI_API_KEY` in .env
- [ ] `DB_HOST=timescaledb` (not localhost!)

**Dependencies:**
- [ ] TimescaleDB container running
- [ ] Network `stock-network` exists
- [ ] Port 5432 available

**After start:**
- [ ] Container status = `Up`
- [ ] No errors in logs
- [ ] Bot online in Discord
- [ ] Bot responds to test message

## 🆘 Troubleshooting

### Bot không start:

1. **Check logs:**
   ```bash
   docker logs stock-discord-bot
   ```

2. **Verify environment:**
   ```bash
   docker exec stock-discord-bot env | findstr DISCORD
   ```

3. **Rebuild:**
   ```bash
   docker-compose build --no-cache discord-bot
   docker-compose up -d discord-bot
   ```

### Bot không phản hồi:

1. **Check bot is online in Discord**

2. **Test connection:**
   ```bash
   docker exec stock-discord-bot python -c "from src.AI_agent.stock_agent import StockAnalysisAgent; agent = StockAnalysisAgent(); print('Agent OK')"
   ```

3. **Check database:**
   ```bash
   docker exec stock-discord-bot python -c "from src.AI_agent.database_tools import DatabaseTools; db = DatabaseTools(); print(db.get_latest_price('VCB'))"
   ```

### Gemini API quota exceeded:

Bot sẽ tự động báo lỗi trên Discord:
```
⚠️ API đã vượt quota. Vui lòng thử lại sau hoặc liên hệ admin.
```

Giải pháp: Đợi quota reset hoặc update API key.

## 📖 Tài liệu chi tiết

Xem file [HUONG_DAN_DOCKER_BOT.md](HUONG_DAN_DOCKER_BOT.md) để biết:
- Hướng dẫn chi tiết từng bước
- Troubleshooting đầy đủ
- Best practices
- Deploy lên server
- Monitoring & maintenance

## 🎯 So sánh: Docker vs Chạy thủ công

| Tiêu chí | Docker | Thủ công |
|----------|---------|----------|
| Auto-restart | ✅ Có | ❌ Không |
| Run 24/7 | ✅ Có | ❌ Phải giữ terminal |
| Dependencies | ✅ Tự động | ⚠️ Phải cài thủ công |
| Môi trường | ✅ Nhất quán | ⚠️ Khác nhau mỗi máy |
| Deploy | ✅ Dễ | ⚠️ Phức tạp |
| Logs | ✅ Tập trung | ⚠️ Rải rác |

**Khuyến nghị: Dùng Docker cho production!**

## 🚢 Next Steps

Sau khi bot chạy ổn định:

1. **Setup monitoring:**
   - Cài Portainer để quản lý GUI
   - Setup alerts khi bot down

2. **Backup:**
   - Backup `.env` file
   - Export logs định kỳ

3. **Deploy to server:**
   - Push code lên Git
   - Clone trên server
   - Run `docker-compose up -d`

4. **Scale:**
   - Thêm load balancer nếu cần
   - Multiple bot instances

## 📞 Support

Nếu gặp vấn đề:
1. Check logs: `docker-bot-logs.bat`
2. Xem [HUONG_DAN_DOCKER_BOT.md](HUONG_DAN_DOCKER_BOT.md)
3. Rebuild: `docker-compose build --no-cache discord-bot`

---

**Được tạo tự động bởi Claude Code** 🤖
**Version: 1.0**
**Date: 2025-12-17**
