# CẬP NHẬT DIAGRAMS SAU KHI THÊM PREDICTION SYSTEM

> **Ngày cập nhật**: 2026-01-08
> **Mục đích**: Tích hợp Ensemble Prediction System vào các diagram của hệ thống

---

## 📊 TÓM TẮT CẬP NHẬT

### ✅ Diagrams Mới (4 files)

1. **usecase_diagram_with_prediction.puml** - Use case diagram với UC10
2. **agent_system_architecture_with_prediction.puml** - Agent architecture với prediction_agent
3. **prediction_agent_multi_model.puml** - Chi tiết prediction agent với multi-model
4. **sequence_uc10_prediction.puml** - Sequence diagram cho UC10

### 🔄 Diagrams Cũ (Vẫn giữ nguyên)

- ✅ **usecase_diagram_with_mcp.puml** - Use case gốc (UC1-UC9)
- ✅ **agent_system_architecture.puml** - Agent architecture gốc (7 agents)
- ✅ **sequence_uc1_xac_thuc.puml** - UC1: Xác thực
- ✅ **sequence_uc2_dang_ky_canh_bao.puml** - UC2: Cảnh báo
- ✅ **sequence_uc3_subscription.puml** - UC3: Subscription
- ✅ **sequence_uc4_loc_co_phieu.puml** - UC4: Lọc cổ phiếu
- ✅ **sequence_uc5_truy_van.puml** - UC5: Truy vấn
- ✅ **sequence_uc6_phan_tich.puml** - UC6: Phân tích
- ✅ **sequence_uc7_chart.puml** - UC7: Biểu đồ
- ✅ **sequence_uc8_tu_van_dau_tu.puml** - UC8: Tư vấn đầu tư
- ✅ **sequence_uc9_discovery.puml** - UC9: Discovery
- ✅ Tất cả multi-model diagrams của các agent khác

---

## 📋 CHI TIẾT CẬP NHẬT

### 1. Use Case Diagram

**File mới**: `usecase_diagrams/usecase_diagram_with_prediction.puml`

**Thay đổi**:
- ➕ **UC10: Dự đoán giá cổ phiếu** (màu hồng)
- ➕ **Ensemble Prediction System** component
- 🔄 MCP Server: 25 tools → **28 tools** (thêm 3 prediction tools)

**3 Prediction MCP Tools**:
1. `predict_stock_price` - Dự đoán giá đơn lẻ
2. `batch_predict_stocks` - Dự đoán batch nhiều mã
3. `get_prediction_confidence` - Lấy độ tin cậy

**Ensemble Prediction System**:
- 5 base models: PatchTST, LSTM, LightGBM, Prophet, XGBoost
- Meta-model: MLPRegressor
- 5 scenario handlers: News Shock, Market Crash, Foreign Flow, VN30 Adjustment, Margin Call

---

### 2. Agent System Architecture

**File mới**: `agent_diagrams/agent_system_architecture_with_prediction.puml`

**Thay đổi**:
- ➕ **prediction_agent** (màu hồng)
- Root agent routes "Dự đoán giá cổ phiếu" queries đến prediction_agent

**Prediction Agent Features**:
- Ensemble 5-model prediction
- Scenario handling (5 handlers)
- Time horizons: 3 days, 48 days
- MAPE: 1.99% (3d), 14.58% (48d)

---

### 3. Prediction Agent Multi-Model Diagram

**File mới**: `agent_diagrams/prediction_agent_multi_model.puml`

**Mô tả**:
- Chi tiết luồng xử lý của prediction_agent
- Task classifier phân loại:
  - **PREDICTION** → Claude Sonnet 4.5 (dự đoán chính)
  - **DATA_QUERY** → Gemini 2.0 Flash (dữ liệu lịch sử)

**Components**:
1. **MCP Tools** (3 tools)
2. **Ensemble Stacking** (5 base models + meta-model)
3. **Scenario Handlers** (5 handlers)

**Flow**:
```
User Query
  → Root Agent
    → Prediction Agent
      → Task Classifier
        → Claude Sonnet 4.5 (PREDICTION)
          → MCP Server
            → predict_stock_price
              → Ensemble Stacking
                → 5 Base Models → Meta-Model
                  → Scenario Handlers
                    → Output
```

---

### 4. Sequence Diagram UC10

**File mới**: `sequence_diagrams/sequence_uc10_prediction.puml`

**Mô tả**: Sequence diagram chi tiết cho UC10 - Dự đoán giá cổ phiếu

**Luồng chính**:

1. **Khởi tạo**: User → Root Agent → Prediction Agent → Claude Sonnet 4.5
2. **Gọi MCP Tool**: predict_stock_price(ticker="VCB", horizon="3day")
3. **Lấy dữ liệu**: Query PostgreSQL (1000 trading days + 60+ indicators)
4. **Feature Engineering**: RSI, MACD, Bollinger Bands, Volume indicators
5. **Ensemble Prediction**:
   - Run 5 base models parallel
   - Get 5 predictions: [102300, 101800, 102500, 101200, 102100]
6. **Meta-Learning**: Combine với weights (28.5%, 24.1%, 22.3%, 14.3%, 10.8%)
   - Base prediction: 102,300 VND
7. **Scenario Handling**:
   - Detect Foreign Flow trigger (room 97.3% > 95%)
   - Apply -3% adjustment
   - Adjusted prediction: 99,231 VND
8. **Tính Confidence**: 78% (model agreement + MAPE + scenario impact)
9. **Kết quả**: Return JSON với prediction details

**Example Output**:
```json
{
  "ticker": "VCB",
  "current_price": 98500,
  "predicted_price": 99231,
  "change_percent": 0.74,
  "confidence": 0.78,
  "recommendation": "HOLD",
  "scenario_adjustments": {
    "foreign_flow": -3.0
  }
}
```

---

## 🎯 SO SÁNH TRƯỚC VÀ SAU

### Trước khi thêm Prediction System:

| Thành phần | Số lượng |
|-----------|----------|
| Use Cases | 9 (UC1-UC9) |
| Agents | 7 agents |
| MCP Tools | 25 tools |
| Sequence Diagrams | 9 diagrams |

### Sau khi thêm Prediction System:

| Thành phần | Số lượng | Thay đổi |
|-----------|----------|----------|
| Use Cases | **10** (UC1-UC10) | +1 ✅ |
| Agents | **8** agents | +1 (prediction_agent) ✅ |
| MCP Tools | **28** tools | +3 (prediction tools) ✅ |
| Sequence Diagrams | **10** diagrams | +1 (UC10) ✅ |
| Total Diagrams | **35** files | +4 new versions ✅ |

---

## 📁 CẤU TRÚC THỨ MỤC

```
diagrams/
├── usecase_diagrams/
│   ├── usecase_diagram_with_mcp.puml (cũ - 9 UCs)
│   └── usecase_diagram_with_prediction.puml (mới - 10 UCs) ⭐
│
├── agent_diagrams/
│   ├── agent_system_architecture.puml (cũ - 7 agents)
│   ├── agent_system_architecture_with_prediction.puml (mới - 8 agents) ⭐
│   ├── prediction_agent_multi_model.puml (mới) ⭐
│   ├── ensemble_prediction_detail.puml (đã có)
│   ├── retraining_workflow.puml (đã có)
│   ├── scenario_response_flow.puml (đã có)
│   ├── [7 agent detail diagrams cũ]
│   └── [7 multi-model diagrams cũ]
│
└── sequence_diagrams/
    ├── sequence_uc1_xac_thuc.puml
    ├── sequence_uc2_dang_ky_canh_bao.puml
    ├── sequence_uc3_subscription.puml
    ├── sequence_uc4_loc_co_phieu.puml
    ├── sequence_uc5_truy_van.puml
    ├── sequence_uc6_phan_tich.puml
    ├── sequence_uc7_chart.puml
    ├── sequence_uc8_tu_van_dau_tu.puml
    ├── sequence_uc9_discovery.puml
    └── sequence_uc10_prediction.puml (mới) ⭐
```

---

## 🔍 KHUYẾN NGHỊ SỬ DỤNG

### Cho Báo cáo Đồ án:

**Chương 3: Phân tích Hệ thống**
- ✅ Sử dụng `usecase_diagram_with_prediction.puml` (10 use cases)
- ✅ Sử dụng `agent_system_architecture_with_prediction.puml` (8 agents)

**Chương 4: Thiết kế Hệ thống**
- ✅ Sử dụng `prediction_agent_multi_model.puml` (chi tiết prediction agent)
- ✅ Sử dụng `sequence_uc10_prediction.puml` (luồng dự đoán)
- ✅ Sử dụng `ensemble_prediction_detail.puml` (chi tiết ensemble)

**Chương 5: Triển khai**
- ✅ Sử dụng `retraining_workflow.puml` (quy trình retrain)
- ✅ Sử dụng `scenario_response_flow.puml` (scenario handling)

### Nếu cần tập trung vào AI Agents (không nhấn mạnh Prediction):

- ✅ Sử dụng diagrams cũ (UC1-UC9, 7 agents)
- ℹ️ Đề cập Prediction như một extension/future work

---

## 🎨 RENDER DIAGRAMS

### Online (PlantUML Server):
```
https://www.plantuml.com/plantuml/uml/[encoded_diagram]
```

### Local (VS Code):
- Install extension: "PlantUML" by jebbs
- Open `.puml` file → Right click → "Preview Current Diagram"

### Export PNG/SVG:
```bash
# Install PlantUML
npm install -g node-plantuml

# Generate PNG
puml generate usecase_diagram_with_prediction.puml -o output.png

# Generate SVG
puml generate usecase_diagram_with_prediction.puml -o output.svg
```

---

## ✅ CHECKLIST HOÀN THÀNH

- [x] Use case diagram với UC10
- [x] Agent architecture với prediction_agent
- [x] Prediction agent multi-model diagram
- [x] Sequence diagram UC10
- [x] Cập nhật số lượng MCP tools (25 → 28)
- [x] Thêm note về performance metrics
- [x] Tài liệu DIAGRAM_UPDATES.md

---

## 📚 TÀI LIỆU LIÊN QUAN

- **ENSEMBLE_MODEL_DOCUMENTATION.md** - Tài liệu chi tiết prediction system (2948 dòng)
- **ENSEMBLE_COMPARISON_SUMMARY.md** - So sánh performance
- **src/prediction/** - Source code prediction system
- **scripts/generate_ensemble_comparison.py** - Script tạo comparison data

---

**Tác giả**: AI Assistant (Claude Sonnet 4.5)
**Ngày**: 2026-01-08
**Phiên bản**: 1.0
