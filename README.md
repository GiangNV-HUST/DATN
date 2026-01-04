# 🤖 Stock Trading Bot with AI Agents

**Hệ thống Discord Bot tư vấn chứng khoán Việt Nam tích hợp AI**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![OpenAI](https://img.shields.io/badge/AI-OpenAI%20GPT--4o--mini-green.svg)](https://openai.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![TimescaleDB](https://img.shields.io/badge/database-TimescaleDB-orange.svg)](https://www.timescale.com/)

---

## 📋 Tổng Quan

Hệ thống tự động thu thập, phân tích và tư vấn đầu tư chứng khoán Việt Nam thông qua Discord bot, sử dụng:
- **50 mã cổ phiếu** VN30 & VNMidcap
- **AI OpenAI GPT-4o-mini** cho tư vấn thông minh
- **LLM-powered** hiểu ngôn ngữ tự nhiên
- **Real-time data pipeline** với Kafka & TimescaleDB

---

## 🌟 Tính Năng Chính

### 1. Discord Bot AI (LLM-Powered)
- ✅ **Hỏi giá cổ phiếu:** "giá VCB", "cho tôi biết giá HPG"
- ✅ **Phân tích kỹ thuật:** "phân tích VCB" → RSI, MA20, MACD
- ✅ **Tìm kiếm cổ phiếu:** "tìm cổ phiếu tốt", "RSI thấp"
- ✅ **Tư vấn đầu tư AI:** "với 100 triệu nên đầu tư gì"
- ✅ **So sánh cổ phiếu:** "so sánh VCB và ACB"
- ✅ **Q&A chung:** "RSI là gì?", "khi nào nên mua?"
- ✅ **Ghi nhớ hội thoại:** Context-aware responses

### 2. Data Pipeline
- **VnStock** → Crawl dữ liệu từ SSI, VND
- **Kafka** → Stream processing
- **TimescaleDB** → Time-series database
- **Airflow** → Orchestration & scheduling

### 3. 50 Mã Cổ Phiếu
**Ngân hàng (10):** VCB, BID, CTG, VPB, TCB, MBB, ACB, STB, HDB, SSI
**Bất động sản (10):** VHM, VIC, VRE, NVL, PDR, DXG, KDH, HDC, DIG, BCM
**Tiêu dùng (10):** VNM, MSN, MWG, SAB, VHC, FRT, MCH, ASM, DGW, PNJ
**Công nghiệp (10):** HPG, GAS, POW, PLX, PVD, PVS, PVT, GEG, NT2, REE
**Công nghệ (10):** FPT, VGC, GMD, SHB, EVF, VCI, VIX, HCM, CMG, ITD

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key ([Get here](https://platform.openai.com/api-keys))
- Discord Bot Token ([Create bot](https://discord.com/developers/applications))

### 1. Clone & Configure
```bash
git clone <your-repo>
cd Final

# Copy and edit .env
cp .env.example .env
nano .env
```

**Required in `.env`:**
```env
OPENAI_API_KEY=sk-proj-...
DISCORD_BOT_TOKEN=MTQ0Mj...
```

### 2. Start All Services
```bash
# Start database, Kafka, Airflow
docker-compose up -d

# Wait 30 seconds for services to initialize

# Start Discord bot
docker-compose -f docker-compose.bot.yml up -d
```

### 3. Verify Setup
```bash
# Check all containers running
docker ps

# Check Airflow DAGs
open http://localhost:8080
# Login: airflow / airflow

# Check bot logs
docker logs -f stock-discord-bot
```

### 4. Trigger Data Collection
```bash
# Trigger stock data collection (50 stocks)
docker exec stock-airflow-scheduler airflow dags trigger stock_data_collector

# Wait ~2 minutes for completion
# Verify: Should have 5,450 records (50 stocks × 109 days)
```

---

## 📊 Architecture

```
┌─────────────┐     ┌──────────┐     ┌────────────┐     ┌──────────────┐
│   VnStock   │────>│  Airflow │────>│   Kafka    │────>│ TimescaleDB  │
│  Data API   │     │   DAGs   │     │  Streams   │     │  Time-Series │
└─────────────┘     └──────────┘     └────────────┘     └──────────────┘
                                                                 │
                                                                 ▼
┌─────────────┐     ┌──────────┐     ┌────────────┐     ┌──────────────┐
│   Discord   │────>│   Bot    │────>│   OpenAI   │────>│   Response   │
│    User     │     │   LLM    │     │ GPT-4o-mini│     │              │
└─────────────┘     └──────────┘     └────────────┘     └──────────────┘
```

### Components:

**Data Collection:**
- `dags/stock_data_collector.py` - 50 stocks, 5 parallel batches
- `src/data_collector/vnstock_client.py` - VnStock API wrapper
- `src/kafka_producer/producer.py` - Kafka message producer

**Data Storage:**
- `src/kafka_consumer/consumer.py` - Kafka → Database
- `init-db/01-init.sql` - TimescaleDB schema with hypertables

**Discord Bot:**
- `src/ai_agent_hybrid/discord_bot_simple.py` - Main bot (LLM-powered)
- `src/ai_agent_hybrid/hybrid_system/` - AI orchestration system

---

## 💡 Usage Examples

### Discord Bot Commands

**Hỏi giá:**
```
User: giá VCB
Bot: 📊 VCB - GIÁ HIỆN TẠI
     💰 Giá đóng cửa: 58,000 VND
     📈 Khối lượng: 2,530,800
     • RSI: 46.6 (Trung bình)
     • MA20: 57,000 VND (Tăng 📈)
```

**Phân tích kỹ thuật:**
```
User: phân tích HPG
Bot: 📊 PHÂN TÍCH HPG
     💰 Giá hiện tại: 26,000 VND

     📈 CHỈ BÁO KỸ THUẬT:
     • RSI: 46.1 ✅ Ở mức trung bình
     • MA20: 27,000 VND 📉 Tiêu cực
     • MACD: -0.08 🔴 Tiêu cực

     📊 XU HƯỚNG GIÁ:
     • 5 ngày: Tăng 0.6% 📈
```

**Tư vấn đầu tư (AI):**
```
User: với 100 triệu nên đầu tư gì
Bot: 💰 TƯ VẤN ĐẦU TƯ CHO 100 TRIỆU VND

     1. Cổ phiếu chọn:
        • VCB: 40 triệu (688,000 cổ phiếu)
        • VNM: 30 triệu (491,000 cổ phiếu)
        • SAB: 30 triệu (612,000 cổ phiếu)

     2. Lý do đầu tư:
        [AI detailed analysis...]

     3. Rủi ro cần lưu ý:
        [Risk warnings...]
```

---

## 🗂️ Project Structure

```
Final/
├── .env                          # ⚙️ Config
├── docker-compose.yml            # 🐳 Main services
├── docker-compose.bot.yml        # 🤖 Discord bot
├── requirements.txt              # 📦 Dependencies
│
├── dags/                         # 📅 Airflow DAGs
│   ├── stock_data_collector.py   # 50 stocks daily
│   ├── company_info_collector.py # Company info
│   ├── financial_reports_collector.py
│   └── intraday_1m_collector.py  # 1-min data
│
├── src/
│   ├── ai_agent_hybrid/          # 🤖 Discord Bot
│   │   ├── discord_bot_simple.py # Main bot (LLM)
│   │   └── hybrid_system/        # AI orchestration
│   ├── data_collector/           # 📊 Data collection
│   ├── kafka_producer/           # 📤 Kafka producer
│   ├── kafka_consumer/           # 📥 Kafka → DB
│   └── config.py                 # ⚙️ Configuration
│
└── init-db/
    └── 01-init.sql               # 🗄️ Database schema
```

---

## 🔧 Configuration

### Environment Variables (`.env`)

**Required:**
```env
# OpenAI
OPENAI_API_KEY=sk-proj-...        # Get from platform.openai.com

# Discord
DISCORD_BOT_TOKEN=MTQ0Mj...       # From discord.com/developers

# Database (default values work)
DB_HOST=timescaledb
DB_PORT=5432
DB_NAME=stock
DB_USER=postgres
DB_PASSWORD=postgres123

# Kafka (default values work)
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
```

**Optional:**
```env
# Discord Webhook (for alerts)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## 📈 Database Schema

### Main Tables:

**stock.stock_prices_1d** (Hypertable)
- Daily OHLCV + technical indicators
- 5,450 records (50 stocks × 109 days)
- Partitioned by time

**stock.stock_prices_1m** (Hypertable)
- 1-minute intraday data
- Partitioned by time

**stock.information**
- Company information

**stock.income_statement, balance_sheet, cash_flow**
- Financial reports

---

## 🧪 Testing

### Manual Test:
```python
# Test data availability
docker exec stock_timescaledb psql -U postgres -d stock -c "
  SELECT COUNT(*) as total_records,
         COUNT(DISTINCT ticker) as stocks
  FROM stock.stock_prices_1d;
"
# Expected: 5,450 records, 50 stocks

# Test bot (if running)
# Go to Discord, mention @stock_bot
# Try: "giá VCB"
```

### Automated Tests:
See [DISCORD_BOT_TEST_RESULTS_FINAL.md](DISCORD_BOT_TEST_RESULTS_FINAL.md) for full test report.

---

## 📊 Performance

### Bot Response Times:
- Price queries: ~1.5s
- Analysis: ~2.0s
- AI investment advice: ~3.5s
- General AI: ~2.5s

### Data Pipeline:
- 50 stocks collection: ~60 seconds
- Kafka → DB latency: <1 second
- Database query: <100ms

### Costs (OpenAI):
- ~$0.40-0.50 per 1000 queries
- Very affordable for production!

---

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| timescaledb | 5434 | PostgreSQL + TimescaleDB |
| kafka | 9092 | Message broker |
| zookeeper | 2181 | Kafka coordination |
| airflow-webserver | 8080 | Airflow UI |
| pgadmin | 5050 | Database admin |
| kafka-ui | 8090 | Kafka monitoring |
| discord-bot | - | Discord bot |

---

## 🛠️ Maintenance

### Daily Tasks:
- ✅ Automatic (via Airflow schedule)
- DAGs run at 15:30 daily (after market close)

### Weekly Tasks:
```bash
# Check database size
docker exec stock_timescaledb psql -U postgres -d stock -c "
  SELECT pg_size_pretty(pg_database_size('stock'));
"

# Check logs
docker-compose logs --tail=100

# Backup database
docker exec stock_timescaledb pg_dump -U postgres stock > backup.sql
```

### Troubleshooting:
```bash
# Restart bot
docker-compose -f docker-compose.bot.yml restart

# Restart all services
docker-compose restart

# Check service health
docker ps
docker logs <container-name>
```

---

## 📚 Documentation

- [DATABASE_REBUILD_REPORT.md](DATABASE_REBUILD_REPORT.md) - Database setup guide
- [DISCORD_BOT_TEST_RESULTS_FINAL.md](DISCORD_BOT_TEST_RESULTS_FINAL.md) - Test results
- [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) - Deployment guide
- [OPENAI_MIGRATION_REPORT.md](OPENAI_MIGRATION_REPORT.md) - Gemini → OpenAI migration
- [CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md) - Project cleanup details

---

## 🎯 Roadmap

### Current (v1.0):
- ✅ 50 stock tickers
- ✅ OpenAI GPT-4o-mini
- ✅ LLM-powered query understanding
- ✅ Daily data collection
- ✅ Technical analysis
- ✅ AI investment advice

### Future (v2.0):
- [ ] 100+ stocks (full VN30 + VNMidcap)
- [ ] Real-time alerts
- [ ] Portfolio tracking
- [ ] Backtesting system
- [ ] Web dashboard
- [ ] Mobile app

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is for educational purposes.

---

## 👤 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Discord: your#1234

---

## 🙏 Acknowledgments

- [VnStock](https://github.com/thinh-vu/vnstock) - Vietnamese stock data API
- [OpenAI](https://openai.com/) - GPT-4o-mini model
- [TimescaleDB](https://www.timescale.com/) - Time-series database
- [Apache Airflow](https://airflow.apache.org/) - Workflow orchestration
- [Discord.py](https://discordpy.readthedocs.io/) - Discord bot framework

---

## 📞 Support

For issues or questions:
- Open an [Issue](https://github.com/yourusername/yourrepo/issues)
- Check [Documentation](./docs/)
- Discord: [Join our server](https://discord.gg/yourserver)

---

**⭐ If you find this project helpful, please give it a star!**

**Generated:** 2026-01-05
**Version:** 1.0.0
**Status:** ✅ Production Ready
