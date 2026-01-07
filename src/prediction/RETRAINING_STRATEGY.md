# Retraining Strategy: Giữ Model Luôn Cập Nhật

> **Vấn đề**: Hệ thống thu thập data mới mỗi ngày, làm sao để model luôn chính xác?
> **Giải pháp**: Chiến lược retraining tự động với 3 kịch bản

---

## 🎯 TL;DR: Khuyến nghị

**Retrain mỗi tuần (Weekly)** - Cân bằng tốt giữa accuracy và compute cost

```bash
# Chạy tự động mỗi thứ 2 lúc 2h sáng
Schedule: 0 2 * * 1
```

---

## 📊 3 Kịch bản Retraining

### Kịch bản 1: **Time-Based** (Dựa trên thời gian) ⭐ KHUYẾN NGHỊ

**Nguyên tắc**: Retrain model định kỳ (hàng tuần/tháng)

```
Ngày 1:  Train model với 1000 ngày
         ↓ (Sử dụng model này)
Ngày 2:  Thu thập data mới
Ngày 3:  Thu thập data mới
Ngày 4:  Thu thập data mới
Ngày 5:  Thu thập data mới
Ngày 6:  Thu thập data mới
Ngày 7:  Thu thập data mới
         ↓
Ngày 8:  RETRAIN với 1007 ngày (cũ + 7 mới)
         ↓ (Deploy model mới nếu tốt hơn)
Ngày 9:  Sử dụng model mới
         ...
Lặp lại mỗi 7 ngày
```

**Ưu điểm**:
- ✅ Đơn giản, dễ implement
- ✅ Chi phí compute thấp (chỉ retrain 1 lần/tuần)
- ✅ Model luôn cập nhật với data mới
- ✅ Không cần tracking prediction accuracy

**Nhược điểm**:
- ⚠️ Không phản ứng ngay với thay đổi đột ngột của thị trường
- ⚠️ Có thể retrain khi không cần thiết (market ổn định)

**Khi nào dùng**: **Mặc định** - Phù hợp hầu hết trường hợp

**Tần suất khuyến nghị**:

| Horizon | Tần suất | Lý do |
|---------|----------|-------|
| 3-day | **Hàng tuần** (7 ngày) | Cập nhật patterns ngắn hạn |
| 48-day | **2 tuần 1 lần** (14 ngày) | Patterns dài hạn ổn định hơn |

**Implementation**:

```python
# Manual check
python scripts/retrain_scheduler.py --mode check --strategy time --interval 7

# Auto retrain if needed
python scripts/retrain_scheduler.py --mode auto --strategy time --interval 7 --tickers VCB,VHM,HPG
```

**Airflow DAG** (Tự động):
```python
# dags/retrain_ensemble_models.py
schedule_interval='0 2 * * 1'  # Mỗi thứ 2 lúc 2h sáng
```

---

### Kịch bản 2: **Performance-Based** (Dựa trên độ chính xác)

**Nguyên tắc**: Retrain khi model accuracy giảm xuống dưới threshold

```
Ngày 1-7:  Model MAPE = 0.9% ✅ OK
Ngày 8-10: Model MAPE = 1.1% ⚠️ Tăng nhẹ
Ngày 11:   Model MAPE = 1.8% ❌ QUÁ THRESHOLD (1.5%)
           → RETRAIN NGAY!
```

**Ưu điểm**:
- ✅ Phản ứng nhanh với market changes
- ✅ Chỉ retrain khi thực sự cần
- ✅ Tiết kiệm compute (không retrain nếu model vẫn tốt)

**Nhược điểm**:
- ⚠️ Cần infrastructure để track predictions
- ⚠️ Cần store predictions + actual prices
- ⚠️ Phức tạp hơn để implement

**Khi nào dùng**: Khi bạn muốn **tối ưu chi phí compute** và có infrastructure tracking

**Implementation**:

```python
# 1. Store predictions vào database
# prediction_log table:
# - prediction_id
# - ticker
# - horizon
# - prediction_date
# - target_date
# - predicted_price
# - actual_price (NULL until target_date)
# - mape

# 2. Daily job: Calculate recent MAPE
SELECT
    ticker,
    horizon,
    AVG(ABS((predicted_price - actual_price) / actual_price)) * 100 as mape_7d
FROM prediction_log
WHERE prediction_date >= NOW() - INTERVAL '7 days'
    AND actual_price IS NOT NULL
GROUP BY ticker, horizon

# 3. Retrain if MAPE > threshold
python scripts/retrain_scheduler.py --mode auto --strategy performance
```

**Threshold recommendations**:

| Horizon | Normal MAPE | Threshold | Action |
|---------|-------------|-----------|--------|
| 3-day | 0.8-1.2% | **1.5%** | Retrain if MAPE > 1.5% |
| 48-day | 2.5-3.5% | **4.0%** | Retrain if MAPE > 4.0% |

---

### Kịch bản 3: **Data-Based** (Dựa trên % data mới)

**Nguyên tắc**: Retrain khi tích lũy đủ N% data mới

```
Train lần 1: 1000 ngày
             ↓
Sau 50 ngày: 1050 ngày (5% data mới)
             → RETRAIN (threshold = 5%)
             ↓
Train lần 2: 1050 ngày
             ↓
Sau 52 ngày: 1102 ngày (5% data mới so với 1050)
             → RETRAIN
```

**Ưu điểm**:
- ✅ Đảm bảo model luôn có data mới
- ✅ Scale với data size (ít data = retrain thường hơn)
- ✅ Không phụ thuộc calendar

**Nhược điểm**:
- ⚠️ Không xét đến model performance
- ⚠️ Có thể retrain quá thường (với threshold thấp)

**Khi nào dùng**: Khi bạn có **data size không đồng đều** giữa các stocks

**Implementation**:

```python
python scripts/retrain_scheduler.py --mode auto --strategy data --new-data-threshold 0.05
```

**Threshold recommendations**:

| Training Data Size | New Data Threshold | Days to Retrain |
|--------------------|-------------------|-----------------|
| 500 days | 5% | ~25 days |
| 1000 days | 5% | ~50 days |
| 1500 days | 5% | ~75 days |

---

## 🏗️ Workflow Chi Tiết

### 1. Check if Retraining Needed

```python
from scripts.retrain_scheduler import RetrainingScheduler

scheduler = RetrainingScheduler()

# Check VCB 3-day model
should_retrain, reason = scheduler.should_retrain(
    ticker='VCB',
    horizon='3day',
    strategy='time',
    retrain_interval_days=7
)

if should_retrain:
    print(f"🔄 Need to retrain: {reason}")
else:
    print(f"✅ Model is fresh: {reason}")
```

### 2. Retrain Model

```python
import pandas as pd

# Load latest data
from database.connection import get_connection
conn = get_connection()

query = """
SELECT time, open, high, low, close, volume
FROM stock_prices
WHERE ticker = 'VCB'
ORDER BY time DESC
LIMIT 1500
"""
df = pd.read_sql(query, conn)
df = df.sort_values('time')
df.set_index('time', inplace=True)

# Retrain
result = scheduler.retrain_model(
    ticker='VCB',
    horizon='3day',
    data=df,
    compare_with_old=True
)

# Check result
if result['status'] == 'deployed':
    print(f"✅ New model deployed")
    print(f"   Old MAPE: {result['old_mape']:.3f}%")
    print(f"   New MAPE: {result['new_mape']:.3f}%")
    print(f"   Improvement: {result['improvement_pct']:+.1f}%")
else:
    print(f"⚠️ New model not deployed: {result['decision']}")
```

### 3. Automated Retraining (Airflow)

**Setup Airflow DAG**:

```bash
# 1. Copy DAG to Airflow
cp dags/retrain_ensemble_models.py /opt/airflow/dags/

# 2. DAG sẽ chạy tự động mỗi thứ 2 lúc 2h sáng

# 3. Monitor trong Airflow UI
http://localhost:8080/admin/airflow/graph?dag_id=retrain_ensemble_models
```

**DAG Workflow**:
```
1. check_retraining_needed
   → Kiểm tra models nào cần retrain (theo time-based)
   ↓
2. fetch_training_data
   → Lấy 1500 ngày data mới nhất từ database
   ↓
3. retrain_models
   → Retrain từng model
   → So sánh với model cũ
   → Deploy nếu tốt hơn
   ↓
4. send_notification
   → Gửi report về Discord/Email
```

---

## 📊 Comparison: Chọn Strategy Nào?

| Tiêu chí | Time-Based | Performance-Based | Data-Based |
|----------|------------|-------------------|------------|
| **Độ phức tạp** | ⭐ Đơn giản | ⭐⭐⭐ Phức tạp | ⭐⭐ Trung bình |
| **Compute cost** | ⭐⭐ Cố định | ⭐⭐⭐ Tối ưu | ⭐⭐ Trung bình |
| **Phản ứng nhanh** | ⭐⭐ Chậm (7 ngày) | ⭐⭐⭐ Nhanh (1 ngày) | ⭐⭐ Trung bình |
| **Infrastructure** | ✅ Không cần gì | ❌ Cần tracking DB | ✅ Chỉ cần model metadata |
| **Accuracy** | ⭐⭐ Tốt | ⭐⭐⭐ Rất tốt | ⭐⭐ Tốt |
| **Khuyến nghị** | ✅ **Mặc định** | ⚠️ Advanced | ⚠️ Special cases |

---

## 🎯 Khuyến Nghị Cuối Cùng

### Phase 1: Starting Out (1-3 tháng đầu)

**Strategy**: Time-Based Weekly
```bash
# Retrain mỗi tuần
python scripts/retrain_scheduler.py --mode auto --strategy time --interval 7
```

**Lý do**:
- Đơn giản, dễ implement
- Không cần infrastructure phức tạp
- Đủ để model cập nhật

### Phase 2: Optimization (3-6 tháng)

**Strategy**: Time-Based + Manual Performance Check
```bash
# Auto retrain weekly
Airflow DAG: schedule='0 2 * * 1'

# + Manual check accuracy hàng ngày
python scripts/evaluate_predictions.py --last-7-days
```

**Lý do**:
- Tự động hóa retraining
- Theo dõi performance để điều chỉnh
- Phát hiện vấn đề sớm

### Phase 3: Production (> 6 tháng)

**Strategy**: Hybrid (Time-Based + Performance-Based)
```python
# 1. Auto retrain weekly (scheduled)
# 2. Emergency retrain nếu MAPE > threshold (triggered)
# 3. Alert nếu accuracy giảm liên tục
```

**Infrastructure**:
- ✅ Airflow DAG cho scheduled retraining
- ✅ Database tracking predictions
- ✅ Dashboard monitoring model performance
- ✅ Alert system (Discord/Email)

---

## 🔧 Best Practices

### 1. **Always Compare Before Deploy**
```python
# ĐÚNG: So sánh new vs old
result = scheduler.retrain_model(
    ticker='VCB',
    horizon='3day',
    data=df,
    compare_with_old=True  # ✅
)

# SAI: Deploy trực tiếp không kiểm tra
ensemble.save('model.pkl')  # ❌ Không so sánh
```

### 2. **Backup Old Models**
```python
# Old model được backup tự động
# src/prediction/trained_models/
# ├── VCB_3day_ensemble.pkl                (current)
# ├── VCB_3day_ensemble_backup_20260107.pkl (backup)
# └── VCB_3day_ensemble_candidate_20260106.pkl (không deploy)
```

### 3. **Monitor Retraining Results**
```python
# Store retraining history
retraining_log = {
    'date': '2026-01-07',
    'ticker': 'VCB',
    'horizon': '3day',
    'old_mape': 0.95,
    'new_mape': 0.87,
    'improvement': 0.08,
    'deployed': True
}
# Save to database or log file
```

### 4. **Set Realistic Thresholds**
```python
# Deploy new model nếu:
# 1. Better than old (MAPE thấp hơn)
# 2. Within 5% of old (MAPE ~ old * 1.05)

if new_mape < old_mape * 1.05:
    deploy()
else:
    save_as_candidate()
```

---

## 📚 Files Created

1. **[scripts/retrain_scheduler.py](../../scripts/retrain_scheduler.py)** - Retraining scheduler
   - Check if retraining needed
   - Retrain and compare models
   - Auto-deploy if better

2. **[dags/retrain_ensemble_models.py](../../dags/retrain_ensemble_models.py)** - Airflow DAG
   - Scheduled weekly retraining
   - Automatic for all VN30 stocks
   - Send notifications

3. **[scripts/check_data_availability.py](../../scripts/check_data_availability.py)** - Data checker
   - Check data availability
   - Recommendations based on data size

---

## 🚀 Quick Start

### Manual Retraining

```bash
# 1. Check which models need retraining
python scripts/retrain_scheduler.py --mode check --strategy time --interval 7

# 2. Retrain specific stocks
python scripts/retrain_scheduler.py --mode retrain --tickers VCB,VHM --horizons 3day

# 3. Auto retrain all that need it
python scripts/retrain_scheduler.py --mode auto --strategy time --interval 7
```

### Automated (Airflow)

```bash
# 1. Enable DAG in Airflow
airflow dags unpause retrain_ensemble_models

# 2. Trigger manually (test)
airflow dags trigger retrain_ensemble_models

# 3. Check logs
airflow tasks logs retrain_ensemble_models retrain_models <date>
```

---

## ❓ FAQ

**Q: Có nên retrain mỗi ngày không?**

A: **Không khuyến nghị**. Lý do:
- Mỗi ngày chỉ thêm 0.1% data → không đủ để model học được gì mới
- Tốn compute (~30 phút/stock)
- Model có thể overfit với data mới nhất
- **Khuyến nghị**: Mỗi tuần (3-day) hoặc 2 tuần (48-day)

**Q: Model mới tệ hơn model cũ thì sao?**

A: Scheduler tự động xử lý:
1. So sánh new vs old MAPE
2. Nếu worse → **Không deploy**, save as candidate
3. Keep old model cho production
4. Alert để investigate

**Q: Làm sao biết khi nào cần retrain khẩn cấp?**

A: Monitor indicators:
- MAPE tăng đột ngột (> 2x normal)
- Prediction direction sai liên tục
- Market có event lớn (khủng hoảng, policy change)
- → Trigger manual retrain ngay

**Q: Retraining mất bao lâu?**

A:
- 1 model (3-day): ~20-30 phút
- 1 model (48-day): ~30-40 phút
- All VN30 (60 models): ~30-40 giờ
- → Nên chạy parallel (10 models cùng lúc) = ~3-4 giờ

---

**Tóm lại**: Bắt đầu với **Time-Based Weekly** retraining, sau đó nâng cấp lên Performance-Based khi có infrastructure 🚀
