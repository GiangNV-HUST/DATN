# 🔄 Hướng dẫn Setup Auto-Start cho Discord Bot

## ✅ ĐÃ CẤU HÌNH

Discord bot đã được cấu hình với `restart: always` trong docker-compose.yml.

## 🚀 Cách hoạt động

### Sau khi start lần đầu:

```bash
docker-bot-start.bat
```

Bot sẽ **TỰ ĐỘNG** start trong các trường hợp:
- ✅ Bot crash hoặc lỗi
- ✅ Docker Desktop restart
- ✅ Máy tính restart/reboot
- ✅ Windows khởi động lại

### Restart Policy = `always`

```yaml
restart: always
```

Có nghĩa là:
- Container sẽ luôn được restart bất kể lý do gì
- Kể cả khi bạn stop thủ công, nó vẫn start lại khi Docker daemon khởi động

## 📋 SETUP CHI TIẾT

### Bước 1: Start bot lần đầu

```bash
docker-bot-start.bat
```

Hoặc:
```bash
docker-compose up -d discord-bot timescaledb
```

### Bước 2: Verify auto-start

**Test 1: Restart Docker Desktop**
1. Stop Docker Desktop
2. Start Docker Desktop lại
3. Đợi 30 giây
4. Check: `docker ps | findstr discord-bot`
5. ✅ Bot phải tự động chạy

**Test 2: Restart máy tính**
1. Restart Windows
2. Đợi Docker Desktop khởi động
3. Check: `docker ps | findstr discord-bot`
4. ✅ Bot phải tự động chạy

### Bước 3: (Tùy chọn) Auto-start Docker Desktop

Để Docker Desktop tự động khởi động khi Windows boot:

**Windows Settings:**
1. Mở Docker Desktop
2. Settings (⚙️) → General
3. ✅ Check "Start Docker Desktop when you log in"
4. Click "Apply & Restart"

**Hoặc thủ công:**
1. Press `Win + R`
2. Nhập: `shell:startup`
3. Tạo shortcut của Docker Desktop vào folder này

## 🎯 Flow Hoàn Chỉnh

```
Windows Boot
    ↓
Docker Desktop Auto-Start (nếu đã setup)
    ↓
Docker Daemon khởi động
    ↓
Tìm containers với restart: always
    ↓
Auto-start: timescaledb
    ↓
Wait for timescaledb healthy
    ↓
Auto-start: discord-bot
    ↓
✅ Bot online trên Discord!
```

## 🔍 Kiểm tra trạng thái

### Check restart policy:
```bash
docker inspect stock-discord-bot | findstr RestartPolicy -A 2
```

Output:
```json
"RestartPolicy": {
    "Name": "always",
    "MaximumRetryCount": 0
}
```

### Check restart count:
```bash
docker inspect stock-discord-bot | findstr RestartCount
```

### Check uptime:
```bash
docker ps | findstr discord-bot
```

Column `STATUS` sẽ hiển thị uptime (vd: "Up 2 hours")

## 🛑 Dừng Auto-Start

Nếu bạn KHÔNG muốn bot tự động start:

### Cách 1: Stop và remove container
```bash
docker-compose stop discord-bot
docker-compose rm -f discord-bot
```

### Cách 2: Disable restart policy
```bash
docker update --restart=no stock-discord-bot
```

### Cách 3: Sửa docker-compose.yml
Đổi lại thành:
```yaml
restart: unless-stopped
```

Sau đó:
```bash
docker-compose up -d discord-bot
```

## 📊 Monitoring Auto-Start

### View logs sau khi auto-start:
```bash
docker logs stock-discord-bot --since 10m
```

### Check nếu bot start thành công:
```bash
docker logs stock-discord-bot | findstr "Bot đã sẵn sàng"
```

Hoặc:
```bash
docker logs stock-discord-bot | findstr "connected to Gateway"
```

## ⚠️ LƯU Ý QUAN TRỌNG

### 1. .env file phải tồn tại
Bot sẽ KHÔNG start nếu không tìm thấy `.env` hoặc thiếu variables:
- `DISCORD_BOT_TOKEN`
- `GEMINI_API_KEY`

### 2. Database phải healthy
Bot chờ database healthy trước khi start:
```yaml
depends_on:
  timescaledb:
    condition: service_healthy
```

### 3. Resource limits
Nếu máy yếu, có thể set resource limits:
```yaml
discord-bot:
  # ... other configs ...
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
```

## 🔧 Troubleshooting

### Bot không auto-start sau reboot:

**1. Check Docker Desktop có start không:**
```bash
docker info
```

**2. Check restart policy:**
```bash
docker inspect stock-discord-bot | findstr RestartPolicy
```

**3. Check logs:**
```bash
docker logs stock-discord-bot --tail 50
```

**4. Manually start để test:**
```bash
docker-compose up -d discord-bot
```

### Bot start nhưng crash ngay:

**Check logs:**
```bash
docker logs stock-discord-bot
```

**Common issues:**
- Missing .env file
- Invalid API keys
- Database not ready
- Network issues

## 🎉 Verification Checklist

Sau khi setup, verify:

- [ ] Bot đã start lần đầu thành công
- [ ] `docker inspect` shows `"RestartPolicy": "always"`
- [ ] Restart Docker Desktop → Bot tự động start
- [ ] (Optional) Docker Desktop auto-start khi Windows boot
- [ ] Bot online trong Discord server
- [ ] Logs không có error
- [ ] Bot responds to test message

## 💡 Tips

### 1. Monitor boot time:
Thêm vào startup script để log boot time:
```bash
echo %date% %time% Bot started >> bot-startup-log.txt
```

### 2. Email notification khi bot start:
Có thể thêm webhook hoặc email script vào bot startup.

### 3. Healthcheck alerts:
Setup monitoring tool (Portainer, Grafana) để alert khi bot down.

## 📞 Support

Nếu auto-start không hoạt động:

1. Check Docker Desktop settings
2. Verify restart policy: `docker inspect stock-discord-bot`
3. Check logs: `docker logs stock-discord-bot`
4. Manual test: `docker-compose up -d discord-bot`

---

**Tài liệu tự động - Claude Code** 🤖
