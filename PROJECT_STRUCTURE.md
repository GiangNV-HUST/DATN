# 📂 Cấu Trúc Dự Án

Tài liệu này mô tả cấu trúc tổ chức của dự án sau khi đã được dọn dẹp và tổ chức lại.

---

## 🎯 Nguyên Tắc Tổ Chức

Dự án được chia thành **2 nhóm chính**:

1. **CODE HỆ THỐNG CHÍNH** - Các file cần thiết để chạy hệ thống
2. **FILES ARCHIVED** - Các file không ảnh hưởng đến việc chạy (có thể xóa)

---

## 📦 NHÓM 1: CODE HỆ THỐNG CHÍNH

### 📁 `src/` - Mã nguồn chính (~15,000+ dòng code)

```
src/
├── ai_agent_hybrid/                    # 🤖 Multi-Agent System
│   ├── hybrid_system/
│   │   ├── agents/                     # 8 Specialized Agents
│   │   │   ├── orchestrator_agent.py   # Root Orchestrator
│   │   │   ├── specialized_agents.py   # 8 agents: Alert, Subscription, etc.
│   │   │   └── mcp_tool_wrapper.py     # MCP tool wrapper
│   │   │
│   │   ├── orchestrator/               # Orchestration Layer
│   │   │   ├── main_orchestrator.py    # Main orchestrator
│   │   │   └── ai_router.py            # AI Router (OpenAI GPT-4o-mini)
│   │   │
│   │   ├── core/                       # Core Components
│   │   │   ├── evaluation.py           # Performance evaluation
│   │   │   └── metrics.py              # Metrics tracking
│   │   │
│   │   ├── database/                   # Database Operations
│   │   │   └── db_operations.py        # CRUD operations
│   │   │
│   │   └── executors/                  # Execution Engines
│   │       └── direct_executor.py      # Direct execution
│   │
│   └── mcp_client/                     # MCP Client
│       └── enhanced_client.py          # Enhanced MCP client
│
├── mcp_server/                         # 🔧 MCP Server (22 Tools)
│   ├── server.py                       # Main MCP server
│   └── tools/                          # Tool Implementations
│       ├── stock_tools.py              # Stock data tools (6)
│       ├── finance_tools.py            # Financial tools (3)
│       ├── screener_tools.py           # Screener tools (2)
│       ├── alert_tools.py              # Alert tools (3)
│       ├── subscription_tools.py       # Subscription tools (3)
│       ├── investment_tools.py         # Investment tools (2)
│       └── discovery_tools.py          # Discovery tools (3)
│
├── streamlit_ui/                       # 🎨 Streamlit Web UI
│   ├── app_openai.py                   # Main Streamlit app (OpenAI version)
│   ├── requirements.txt                # Streamlit dependencies
│   ├── pages/                          # Multi-page components
│   │   ├── 1_Dashboard.py
│   │   ├── 2_Chat.py
│   │   ├── 3_Analysis.py
│   │   ├── 4_Prediction.py
│   │   └── 5_Portfolio.py
│   └── components/                     # Reusable UI components
│       ├── charts.py
│       ├── sidebar.py
│       └── utils.py
│
├── predictions_ensemble/               # 🔮 ML Prediction System
│   ├── ensemble_predictor.py           # Main ensemble predictor
│   ├── models/                         # Trained Models
│   │   ├── patchtst/                   # PatchTST model
│   │   ├── lstm_attention/             # LSTM + Attention
│   │   └── ensemble/                   # Ensemble weights
│   └── scenario_handlers/              # Scenario Handlers
│       ├── market_crash_handler.py
│       ├── bull_run_handler.py
│       └── earnings_surprise_handler.py
│
├── data_collector/                     # 📊 Data Collection
│   ├── vnstock_client.py               # VnStock API wrapper
│   ├── collectors.py                   # Data collectors
│   └── schedulers.py                   # Scheduled jobs
│
├── database/                           # 🗄️ Database Management
│   ├── db_manager.py                   # Connection manager
│   ├── data_saver.py                   # Data persistence
│   └── queries.py                      # SQL queries
│
├── kafka_producer/                     # 📤 Kafka Producer
│   └── stock_producer.py               # Stock data producer
│
├── kafka_consumer/                     # 📥 Kafka Consumer
│   └── stock_consumer.py               # Stock data consumer
│
└── config.py                           # ⚙️ Configuration
```

---

### 📁 `diagrams/` - Sơ đồ hệ thống (PNG exported)

```
diagrams/
├── agent_diagrams/                     # Agent Architecture Diagrams
│   ├── agent_system_architecture_with_prediction.png
│   ├── ensemble_prediction_detail.png
│   ├── prediction_agent_multi_model.png
│   ├── retraining_workflow.png
│   └── scenario_response_flow.png
│
├── usecase_diagrams/                   # Use Case Diagrams
│   └── usecase_diagram_with_prediction.png
│
└── sequence_diagrams/                  # Sequence Diagrams
    └── sequence_uc10_prediction.png
```

**Lưu ý:** Đây là file PNG đã export, dùng trực tiếp trong tài liệu/báo cáo.

---

### 📁 `database/` - Database Scripts

```
database/
└── create_public_schema_compatibility.sql  # SQL schema creation
```

---

### 📁 `docs/` - Use Case Documentation

```
docs/
└── UC10_DU_DOAN_GIA_CO_PHIEU.md       # Use case: Stock prediction
```

---

### 📄 Root Files - Core Configuration & Scripts

```
Final/
├── .env.example                        # Template environment variables
├── requirements.txt                    # Python dependencies (main)
├── README.md                           # Main documentation (1,263 lines)
│
├── init_database.py                    # Database initialization script
├── docker-compose.yml                  # Docker services configuration
│
├── run_streamlit_ui.bat               # Run Streamlit UI (Windows)
├── run_streamlit_ui.sh                # Run Streamlit UI (Linux/Mac)
├── run_orchestrator_mcp.bat           # Run MCP server (Windows)
├── run_orchestrator_mcp.sh            # Run MCP server (Linux/Mac)
├── run_full_agent_ui.bat              # Run full agent (Windows)
└── run_full_agent_ui.sh               # Run full agent (Linux/Mac)
```

---

### 📄 Documentation Files (Root)

```
Final/
├── BAO_CAO_HE_THONG_DA_TAC_NHAN.md   # Báo cáo hệ thống đa tác nhân (37KB)
├── CLAUDE_DESKTOP_SETUP.md            # Hướng dẫn tích hợp Claude Desktop (18KB)
└── DEPLOYMENT_GUIDE.md                # Hướng dẫn deployment production (19KB)
```

**Mục đích:** Tài liệu chính thức về hệ thống, cần thiết cho người sử dụng.

---

## 📦 NHÓM 2: FILES ARCHIVED (Có thể xóa)

### 📁 `_archived_files/` - File không ảnh hưởng hệ thống

```
_archived_files/
├── README.md                           # Giải thích thư mục archived
│
├── docs/                               # Tài liệu phát triển cũ (10 files)
│   ├── CLEANUP_REPORT.md
│   ├── DIAGRAM_SUMMARY.md
│   ├── DOCUMENT_UPDATE_MCP.md
│   ├── ENHANCEMENT_REPORT.md
│   ├── ENSEMBLE_COMPARISON_SUMMARY.md
│   ├── ENSEMBLE_MODEL_DOCUMENTATION.md (108KB - chi tiết nhất)
│   ├── ENSEMBLE_PREDICTION_DEMO.md
│   ├── ENSEMBLE_PREDICTION_IMPLEMENTATION.md
│   ├── MULTI_MODEL_IMPLEMENTATION_SUMMARY.md
│   └── SCENARIO_HANDLERS_DETAILED.md
│
├── scripts/                            # Scripts không dùng (2 files)
│   ├── monitor_bot.bat                 # Monitor Discord bot
│   └── run_discord_bot.bat             # Discord bot launcher
│
└── diagrams_source/                    # PlantUML source files (32 files)
    ├── agent_diagrams/*.puml           # Agent diagram sources
    ├── usecase_diagrams/*.puml         # Usecase diagram sources
    └── sequence_diagrams/*.puml        # Sequence diagram sources
```

**⚠️ QUAN TRỌNG:**
- Thư mục này **KHÔNG CẦN THIẾT** để chạy hệ thống
- Có thể **XÓA TOÀN BỘ** để giảm kích thước source code
- **NÊN GIỮ** nếu cần viết báo cáo/thesis về quá trình phát triển

---

## 📊 Thống Kê Dự Án

### Code Hệ Thống Chính

| Component | Files | Lines of Code | Description |
|-----------|-------|---------------|-------------|
| Multi-Agent System | ~20 | ~5,000 | 8 specialized agents + orchestrator |
| MCP Server | ~10 | ~3,000 | 22 tools implementation |
| Streamlit UI | ~15 | ~2,500 | Web interface |
| Prediction Models | ~10 | ~2,000 | 3 ML models + scenarios |
| Data Pipeline | ~10 | ~1,500 | Collectors, Kafka, DB |
| Utilities | ~10 | ~1,000 | Config, helpers |
| **TOTAL** | **~75** | **~15,000** | Production code |

### Files Archived

| Type | Files | Size | Can Delete? |
|------|-------|------|-------------|
| Documentation | 10 | ~350KB | ✅ Yes |
| Scripts | 2 | ~1KB | ✅ Yes |
| Diagram Sources | 32 | ~50KB | ⚠️ Keep if need to edit diagrams |
| **TOTAL** | **44** | **~400KB** | ✅ Yes (mostly) |

---

## 🎯 Hướng Dẫn Sử Dụng

### 1. Chạy Hệ Thống (Không cần file archived)

```bash
# Clone về
git clone <repo>
cd Final

# Cài đặt
pip install -r requirements.txt
pip install -r src/streamlit_ui/requirements.txt

# Config
cp .env.example .env
# Edit .env với OPENAI_API_KEY

# Khởi động database
docker-compose up -d timescaledb
python init_database.py

# Chạy UI
./run_streamlit_ui.sh
```

→ Không cần động vào `_archived_files/`

---

### 2. Viết Báo Cáo/Thesis (Cần file archived)

```bash
# Đọc tài liệu quá trình phát triển
cat _archived_files/docs/ENSEMBLE_MODEL_DOCUMENTATION.md

# Chỉnh sửa diagrams
cd _archived_files/diagrams_source/
# Edit .puml files
java -jar plantuml.jar agent_diagrams/xxx.puml
```

→ Sử dụng các file trong `_archived_files/docs/` để viết báo cáo

---

### 3. Đóng Gói Source Code

**Option A: Đầy đủ (bao gồm archived)**
```bash
# Giữ toàn bộ, kể cả _archived_files/
zip -r project_full.zip Final/
```

**Option B: Chỉ code (không có archived)**
```bash
# Xóa _archived_files/ trước khi đóng gói
rm -rf _archived_files/
zip -r project_code_only.zip Final/
```

**Option C: Code + Documentation chính**
```bash
# Giữ code + 3 docs chính, xóa _archived_files/
rm -rf _archived_files/
zip -r project_production.zip Final/
```

---

## 💡 Khuyến Nghị

### Cho Người Sử Dụng
- **Chỉ cần clone về và chạy** → Không cần quan tâm `_archived_files/`
- Đọc `README.md` để biết cách cài đặt

### Cho Người Phát Triển
- **Giữ lại `_archived_files/`** để tham khảo quá trình phát triển
- Các tài liệu trong `_archived_files/docs/` rất chi tiết về implementation

### Cho Sinh Viên Viết Báo Cáo
- **BẮT BUỘC giữ `_archived_files/`**
- File `ENSEMBLE_MODEL_DOCUMENTATION.md` (108KB) là tài liệu quý nhất
- PlantUML sources để chỉnh sửa diagrams cho báo cáo

### Cho Production Deployment
- **Có thể xóa `_archived_files/`** để giảm kích thước
- Chỉ cần code trong `src/` và config files

---

## 📞 Support

- README chính: [README.md](README.md)
- Archived files: [_archived_files/README.md](_archived_files/README.md)
- Issues: GitHub Issues

---

**Version:** 2.0.0
**Last Updated:** 2026-01-09
**Status:** ✅ Production Ready
