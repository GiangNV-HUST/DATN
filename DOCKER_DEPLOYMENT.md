# DOCKER DEPLOYMENT GUIDE

**Hướng dẫn deploy toàn bộ hệ thống với Docker**

---

## TỔNG QUAN

Hệ thống bao gồm 11 containers:

1. **timescaledb** - Database chính (TimescaleDB)
2. **postgres-airflow** - Database cho Airflow metadata
3. **zookeeper** - Service cho Kafka
4. **kafka** - Message broker
5. **kafka-ui** - Web UI quản lý Kafka
6. **airflow-webserver** - Airflow Web UI
7. **airflow-scheduler** - Airflow scheduler
8. **airflow-init** - Khởi tạo Airflow (chạy 1 lần)
9. **pgadmin** - Web UI quản lý PostgreSQL
10. **kafka-consumer** - Consumer xử lý dữ liệu từ Kafka
11. **discord-bot** - ⭐ **Discord Bot Simple** (NEW)

---

## YÊU CẦU

### 1. Docker & Docker Compose

```bash
# Check version
docker --version
# Docker version 20.10+ required

docker-compose --version
# Docker Compose version 1.29+ required
```

### 2. System Resources

**Minimum**:
- RAM: 8GB
- CPU: 4 cores
- Disk: 20GB

**Recommended**:
- RAM: 16GB
- CPU: 8 cores
- Disk: 50GB

---

## CÀI ĐẶT

### 1. Clone Repository

```bash
git clone <your-repo>
cd Final
```

### 2. Cấu hình .env

Tạo file `.env` ở root:

```bash
# Discord Bot
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Database (optional - sẽ dùng default từ docker-compose.yml)
DB_HOST=timescaledb
DB_PORT=5432
DB_NAME=stock
DB_USER=postgres
DB_PASSWORD=postgres123

# Kafka (optional)
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC_STOCK_PRICES=stock_prices_daily
```

### 3. Build Images

```bash
# Build tất cả images
docker-compose build

# Hoặc build riêng Discord bot
docker-compose build discord-bot
```

---

## CHẠY HỆ THỐNG

### Option 1: Chạy Toàn Bộ

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Option 2: Chỉ Chạy Discord Bot + Database

```bash
# Start only essential services
docker-compose up -d timescaledb discord-bot

# Check bot logs
docker-compose logs -f discord-bot
```

### Option 3: Chạy Từng Phần

```bash
# 1. Database first
docker-compose up -d timescaledb postgres-airflow

# Wait for DB to be ready
docker-compose ps

# 2. Kafka stack
docker-compose up -d zookeeper kafka kafka-ui

# 3. Airflow
docker-compose up -d airflow-init airflow-webserver airflow-scheduler

# 4. Consumer
docker-compose up -d kafka-consumer

# 5. Discord Bot
docker-compose up -d discord-bot
```

---

## VERIFY DEPLOYMENT

### 1. Check Container Status

```bash
docker-compose ps
```

**Expected output:**
```
NAME                        STATUS         PORTS
stock-airflow-init          exited (0)     -
stock-airflow-scheduler     Up             -
stock-airflow-webserver     Up             0.0.0.0:8081->8080/tcp
stock-discord-bot           Up             -
stock-kafka                 Up             0.0.0.0:9092-9093->9092-9093/tcp
stock-kafka-consumer        Up             -
stock-kafka-ui              Up             0.0.0.0:8080->8080/tcp
stock-pgadmin               Up             0.0.0.0:5050->80/tcp
stock-postgres-airflow      Up             0.0.0.0:5433->5432/tcp
stock-timescaledb           Up             0.0.0.0:5434->5432/tcp
stock-zookeeper             Up             0.0.0.0:2181->2181/tcp
```

### 2. Check Discord Bot

```bash
# Check logs
docker-compose logs discord-bot

# Should see:
# ✅ Database client initialized
# ✅ Gemini AI initialized
# ✅ Simple Stock Bot initialized
# 🤖 Bot ready! Logged in as stock_bot#1234
# 📡 Serving X servers
```

### 3. Test Discord Bot

Trong Discord server:
```
@stock_bot giá VCB
```

Nếu bot reply với thông tin giá → ✅ **SUCCESS!**

### 4. Check Database

```bash
# Connect to database
docker exec -it stock-timescaledb psql -U postgres -d stock

# Check tables
\dt stock.*

# Check data
SELECT COUNT(*) FROM stock.stock_prices_1d;

# Exit
\q
```

### 5. Check Web UIs

**PgAdmin**: http://localhost:5050
- Email: admin@admin.com
- Password: admin

**Kafka UI**: http://localhost:8080

**Airflow**: http://localhost:8081
- Username: admin
- Password: admin

---

## LOGS & MONITORING

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f discord-bot
docker-compose logs -f timescaledb
docker-compose logs -f kafka-consumer

# Last 100 lines
docker-compose logs --tail=100 discord-bot

# Since specific time
docker-compose logs --since 10m discord-bot
```

### Monitor Resources

```bash
# Resource usage
docker stats

# Specific container
docker stats stock-discord-bot
```

### Health Checks

```bash
# Check health status
docker inspect stock-discord-bot | grep Health -A 20

# All unhealthy containers
docker ps --filter health=unhealthy
```

---

## TROUBLESHOOTING

### Discord Bot Not Starting

**1. Check logs:**
```bash
docker-compose logs discord-bot
```

**Common errors:**

**Error: "DISCORD_BOT_TOKEN not found"**
```bash
# Fix: Add to .env
echo "DISCORD_BOT_TOKEN=your_token" >> .env

# Restart bot
docker-compose restart discord-bot
```

**Error: "Database connection failed"**
```bash
# Check if DB is running
docker-compose ps timescaledb

# Check DB logs
docker-compose logs timescaledb

# Restart both
docker-compose restart timescaledb discord-bot
```

**Error: "ModuleNotFoundError"**
```bash
# Rebuild image
docker-compose build discord-bot

# Restart
docker-compose up -d discord-bot
```

### Database Issues

**Connection refused:**
```bash
# Check if DB is healthy
docker-compose ps timescaledb

# Should show: Up (healthy)
# If not, check logs:
docker-compose logs timescaledb

# Restart DB
docker-compose restart timescaledb
```

**No data:**
```bash
# Check if init.sql ran
docker-compose logs timescaledb | grep "init.sql"

# If not, recreate container
docker-compose down
docker volume rm final_timescale-data
docker-compose up -d timescaledb
```

### Kafka Issues

**Kafka not ready:**
```bash
# Check Zookeeper first
docker-compose ps zookeeper

# Then Kafka
docker-compose ps kafka

# Restart in order
docker-compose restart zookeeper
sleep 10
docker-compose restart kafka
```

### Out of Memory

```bash
# Check memory usage
docker stats

# If high memory usage:
# 1. Stop unnecessary services
docker-compose stop airflow-webserver airflow-scheduler

# 2. Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory

# 3. Or run only essentials:
docker-compose up -d timescaledb discord-bot
```

---

## UPDATING & MAINTENANCE

### Update Discord Bot Code

```bash
# 1. Update code
git pull origin main

# 2. Rebuild image
docker-compose build discord-bot

# 3. Restart container
docker-compose up -d discord-bot

# 4. Check logs
docker-compose logs -f discord-bot
```

### Update Environment Variables

```bash
# 1. Edit .env
nano .env

# 2. Restart affected services
docker-compose restart discord-bot

# Or recreate (if ENV changed in docker-compose.yml)
docker-compose up -d --force-recreate discord-bot
```

### Database Backup

```bash
# Backup
docker exec stock-timescaledb pg_dump -U postgres stock > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20260104.sql | docker exec -i stock-timescaledb psql -U postgres -d stock
```

### Clean Up

```bash
# Stop all services
docker-compose down

# Remove volumes (⚠️ DATA WILL BE LOST)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Clean unused resources
docker system prune -a
```

---

## PRODUCTION DEPLOYMENT

### 1. Use Production .env

```bash
# Create production .env
cp .env.example .env.production

# Edit with production values
nano .env.production

# Use it
docker-compose --env-file .env.production up -d
```

### 2. Security Best Practices

**Change default passwords:**
```yaml
# In docker-compose.yml
environment:
  POSTGRES_PASSWORD: <strong-password>
  PGADMIN_DEFAULT_PASSWORD: <strong-password>
```

**Use secrets (Docker Swarm):**
```yaml
secrets:
  discord_token:
    external: true
  gemini_key:
    external: true
```

**Limit exposed ports:**
```yaml
# Only expose what's needed
ports:
  - "127.0.0.1:5434:5432"  # Only localhost
```

### 3. Monitoring & Logging

**Add logging driver:**
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**Add monitoring (Prometheus + Grafana):**
```bash
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus
  # ... config

grafana:
  image: grafana/grafana
  # ... config
```

### 4. Auto-restart on Failure

```yaml
restart: unless-stopped  # Already set for most services
```

### 5. Resource Limits

```yaml
discord-bot:
  # ...
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 1G
      reservations:
        cpus: '0.5'
        memory: 512M
```

---

## SCALING

### Horizontal Scaling (Multiple Bots)

```yaml
discord-bot:
  # ...
  deploy:
    replicas: 3  # Run 3 instances
```

**Note**: Discord bot không scale tốt vì mỗi bot cần unique token.

### Vertical Scaling (More Resources)

```yaml
discord-bot:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

---

## DEVELOPMENT vs PRODUCTION

### Development

```bash
# docker-compose.yml
volumes:
  - ./src:/app/src  # Hot reload

# Run with override
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Production

```bash
# docker-compose.prod.yml
volumes:
  # No bind mounts - use copy

# Run
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## CHEAT SHEET

```bash
# ============== COMMON COMMANDS ==============

# Start all
docker-compose up -d

# Stop all
docker-compose down

# Restart specific service
docker-compose restart discord-bot

# View logs
docker-compose logs -f discord-bot

# Rebuild and restart
docker-compose up -d --build discord-bot

# Check status
docker-compose ps

# Enter container shell
docker-compose exec discord-bot bash

# Remove everything
docker-compose down -v --rmi all

# ============== DISCORD BOT SPECIFIC ==============

# Check bot logs
docker-compose logs -f discord-bot

# Restart bot
docker-compose restart discord-bot

# Rebuild bot
docker-compose build discord-bot && docker-compose up -d discord-bot

# Check bot health
docker inspect stock-discord-bot | grep Health

# Execute command in bot container
docker-compose exec discord-bot python -c "import discord; print(discord.__version__)"

# ============== DATABASE ==============

# Connect to DB
docker exec -it stock-timescaledb psql -U postgres -d stock

# Backup
docker exec stock-timescaledb pg_dump -U postgres stock > backup.sql

# Restore
cat backup.sql | docker exec -i stock-timescaledb psql -U postgres -d stock

# ============== TROUBLESHOOTING ==============

# Check all container health
docker-compose ps

# View all logs
docker-compose logs

# Check resource usage
docker stats

# Clean up
docker system prune -a
```

---

## FAQ

### Q: Bot không online trong Discord?

A:
```bash
# 1. Check logs
docker-compose logs discord-bot

# 2. Check token
cat .env | grep DISCORD_BOT_TOKEN

# 3. Restart bot
docker-compose restart discord-bot
```

### Q: Bot không trả lời?

A:
```bash
# 1. Check if DB is healthy
docker-compose ps timescaledb

# 2. Check bot logs for errors
docker-compose logs --tail=50 discord-bot

# 3. Check bot permissions in Discord
```

### Q: Làm sao update code mới?

A:
```bash
git pull
docker-compose build discord-bot
docker-compose up -d discord-bot
```

### Q: Container bị crash liên tục?

A:
```bash
# Check logs
docker-compose logs discord-bot

# Common fixes:
# - Out of memory → increase Docker memory
# - Missing dependencies → rebuild image
# - Wrong env vars → check .env
```

---

## SUPPORT

### Logs Location

```bash
# Docker logs
docker-compose logs

# Application logs (if configured)
./logs/discord-bot.log

# Database logs
docker-compose logs timescaledb
```

### Debugging

```bash
# Enter container
docker-compose exec discord-bot bash

# Test imports
python -c "from hybrid_system.database import get_database_client"

# Test database connection
python -c "import psycopg2; conn = psycopg2.connect('host=timescaledb dbname=stock user=postgres password=postgres123')"

# Test Discord.py
python -c "import discord; print(discord.__version__)"
```

---

**🚀 Happy Deploying! 📦**
