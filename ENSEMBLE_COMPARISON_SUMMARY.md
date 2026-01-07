# TÓM TẮT SO SÁNH ENSEMBLE MODEL VỚI BASE MODELS

> **Tài liệu này tóm tắt các bảng số liệu chính để đưa vào Báo cáo Đồ án**
>
> **Nguồn**: ENSEMBLE_MODEL_DOCUMENTATION.md - Chương 7.4
> **Ngày tạo**: 2026-01-08

---

## 📊 BẢNG 1: So sánh Tổng quan (3 ngày)

| Model | Avg MAPE | Avg R² | Cải thiện so với Ensemble |
|-------|----------|--------|---------------------------|
| **Ensemble** | **1.99%** | **0.874** | - |
| PatchTST | 2.23% | 0.839 | +10.8% |
| LSTM | 2.42% | 0.778 | +17.8% |
| LightGBM | 2.69% | 0.706 | +26.0% |
| XGBoost | 2.78% | 0.663 | +28.4% |
| Prophet | 3.23% | 0.587 | +38.4% |

**Kết luận**: Ensemble giảm MAPE 10.8% so với PatchTST (model riêng lẻ tốt nhất)

---

## 📊 BẢNG 2: So sánh Tổng quan (48 ngày)

| Model | Avg MAPE | Avg R² | Cải thiện so với Ensemble |
|-------|----------|--------|---------------------------|
| **Ensemble** | **14.58%** | **0.176** | - |
| PatchTST | 16.06% | 0.167 | +9.2% |
| LSTM | 17.57% | 0.157 | +17.0% |
| LightGBM | 19.16% | 0.142 | +23.9% |
| XGBoost | 19.79% | 0.133 | +26.3% |
| Prophet | 23.33% | 0.119 | +37.5% |

**Kết luận**: Ensemble giảm MAPE 9.2% so với PatchTST

---

## 📊 BẢNG 3: Top 5 Stocks dễ dự đoán (3 ngày)

| Ticker | Ensemble MAPE | Ensemble R² | PatchTST MAPE | Cải thiện |
|--------|---------------|-------------|---------------|-----------|
| VCB | 1.68% | 0.960 | 1.83% | 8.2% |
| BID | 1.55% | 0.960 | 1.81% | 14.4% |
| GAS | 1.70% | 0.940 | 1.98% | 14.1% |
| ACB | 1.72% | 0.960 | 1.89% | 9.0% |
| CTG | 1.78% | 0.960 | 1.92% | 7.3% |

**Insight**: Stocks ngân hàng (VCB, BID, CTG, ACB) có MAPE thấp nhất → dễ dự đoán nhất

---

## 📊 BẢNG 4: Top 5 Stocks khó dự đoán (3 ngày)

| Ticker | Ensemble MAPE | Ensemble R² | PatchTST MAPE | Cải thiện |
|--------|---------------|-------------|---------------|-----------|
| VHM | 2.79% | 0.645 | 2.99% | 6.7% |
| VIC | 2.62% | 0.675 | 2.94% | 10.9% |
| VRE | 2.42% | 0.713 | 2.79% | 13.3% |
| MBB | 2.13% | 0.862 | 2.34% | 9.0% |
| HDB | 2.15% | 0.863 | 2.35% | 8.5% |

**Insight**: Stocks bất động sản (VHM, VIC, VRE) có volatility cao hơn → khó dự đoán hơn

---

## 📊 BẢNG 5: Weight Distribution trong Meta-model

### Dự báo 3 ngày:
| Model | Weight | Vai trò |
|-------|--------|---------|
| PatchTST | 28.5% | ⭐ Highest - Transformer architecture |
| LSTM | 24.1% | ⭐ High - Sequential patterns |
| LightGBM | 22.3% | ⭐ High - Stability |
| XGBoost | 14.3% | Medium - Tree-based diversity |
| Prophet | 10.8% | Low - Seasonality specialist |

### Dự báo 48 ngày:
| Model | Weight | Vai trò |
|-------|--------|---------|
| PatchTST | 26.2% | ⭐ Highest |
| LightGBM | 24.5% | ⭐ High |
| LSTM | 22.8% | ⭐ High |
| XGBoost | 14.4% | Medium |
| Prophet | 12.1% | Low |

**Insight**:
- PatchTST được meta-model tin tưởng nhất
- Prophet có weight thấp nhất nhưng vẫn quan trọng cho diversity
- Weight cân bằng (10-28%) → không có model bị bỏ qua

---

## 📊 BẢNG 6: Correlation Analysis (Diversity Score)

| Model Pair | Correlation | Diversity Score | Ý nghĩa |
|------------|-------------|-----------------|---------|
| Prophet - LightGBM | 0.49 | ⭐⭐⭐ Very High | Rất khác biệt → tốt cho ensemble |
| Prophet - PatchTST | 0.54 | ⭐⭐⭐ Very High | Statistical vs Deep Learning |
| LSTM - LightGBM | 0.68 | ⭐⭐ High | Neural vs Tree-based |
| PatchTST - LightGBM | 0.71 | ⭐⭐ High | Transformer vs Boosting |
| PatchTST - LSTM | 0.82 | ⭐ Medium | Cùng deep learning |

**Insight**:
- Prophet đóng góp diversity cao nhất (correlation thấp với các model khác)
- LightGBM và XGBoost khác biệt rõ rệt với neural models
- Diversity cao → ensemble hiệu quả hơn

---

## 📊 BẢNG 7: So sánh với TimeMixer (Benchmark)

| Metric | TimeMixer | Ensemble 5-Model | Improvement |
|--------|-----------|------------------|-------------|
| **3-day MAPE** | 1.42% | 1.99% | +40% worse ⚠️ |
| **48-day MAPE** | 4.64% | 14.58% | +214% worse ⚠️ |
| **48-day negative R²** | 19/31 stocks | 0/28 stocks | ✅ 100% better |
| **Training time** | 2 hours | 3-4 hours | -50% slower |
| **Inference time** | 50ms | 120ms | -140% slower |
| **Scenario handling** | None | 5 handlers | ✅ Major advantage |

**⚠️ LƯU Ý QUAN TRỌNG**:
- Số liệu TimeMixer và Ensemble được đánh giá trên datasets khác nhau
- TimeMixer có MAPE tốt hơn nhưng có nhiều negative R² (19/31 stocks)
- Ensemble có MAPE cao hơn nhưng **không có stock nào negative R²** (robust hơn)
- Ensemble có ưu thế lớn về scenario handling (5 handlers chuyên biệt)

**Recommendation**:
- Sử dụng **Ensemble** nếu cần robustness và scenario handling
- Sử dụng **TimeMixer** nếu chỉ quan tâm MAPE thấp nhất

---

## 📈 BIỂU ĐỒ ĐỀ XUẤT CHO BÁO CÁO

### Biểu đồ 1: MAPE Comparison (Bar Chart)
```
Dự báo 3 ngày:
Ensemble   ████░░░░░░ 1.99%
PatchTST   █████░░░░░ 2.23%
LSTM       █████▌░░░░ 2.42%
LightGBM   ██████░░░░ 2.69%
XGBoost    ██████▌░░░ 2.78%
Prophet    ███████▌░░ 3.23%
```

### Biểu đồ 2: R² Score Comparison (Bar Chart)
```
Dự báo 3 ngày:
Ensemble   ████████▌░ 0.874
PatchTST   ████████░░ 0.839
LSTM       ███████▌░░ 0.778
LightGBM   ███████░░░ 0.706
XGBoost    ██████▌░░░ 0.663
Prophet    █████▌░░░░ 0.587
```

### Biểu đồ 3: Improvement by Stock Type
```
Banking (VCB, BID, ACB, CTG):
  Ensemble MAPE: 1.68%
  Improvement: 8-14%

Tech/Retail (FPT, MSN):
  Ensemble MAPE: 2.02%
  Improvement: 7-12%

Real Estate (VHM, VIC, VRE):
  Ensemble MAPE: 2.61%
  Improvement: 7-13%
```

---

## 🎯 KẾT LUẬN CHO BÁO CÁO

### Ưu điểm của Ensemble Stacking:

1. ✅ **Performance tốt nhất**: Outperform tất cả base models ở cả 2 time horizons
2. ✅ **Robust và Stable**: Không có stock nào có negative R²
3. ✅ **Cải thiện đồng đều**: 6-14% trên tất cả loại stocks (banking, tech, real estate)
4. ✅ **Diversity cao**: Kết hợp 5 models với correlation thấp
5. ✅ **Scenario Handling**: 5 handlers chuyên biệt cho thị trường Việt Nam
6. ✅ **Error Compensation**: Sai số của model này được bù bởi model khác

### Trade-offs cần chấp nhận:

- ❌ **Training Time**: Tăng 3-4 lần (2h → 6-8h) - chấp nhận được với weekly retraining
- ❌ **Inference Time**: 120ms vs 50ms - vẫn real-time cho trading
- ❌ **Model Size**: 500 MB vs 150 MB - không vấn đề với storage hiện đại
- ❌ **Complexity**: 6 models thay vì 1 - cần quản lý phức tạp hơn

### Recommendation:

**Môi trường Production**:
- ✅ Sử dụng **Ensemble** (accuracy và robustness quan trọng nhất)

**Resource-constrained hoặc Low-latency**:
- ✅ Sử dụng **PatchTST** standalone (MAPE 2.23%, inference 30ms)

**Research/Experimentation**:
- ✅ Sử dụng **LSTM** (balance giữa accuracy và simplicity)

---

## 📝 CÂU TRẢ LỜI CHO CÂU HỎI THƯỜNG GẶP

**Q1: Tại sao Ensemble tốt hơn single model?**
> A: Ensemble kết hợp 5 models khác nhau (Transformer, GBM, LSTM, Prophet, XGBoost), mỗi model capture patterns khác nhau. Meta-model học cách weighted combination tối ưu, giảm MAPE 10.8% so với PatchTST.

**Q2: Prophet có MAPE cao nhất (3.23%) nhưng tại sao vẫn cần?**
> A: Prophet có correlation thấp nhất với các models khác (0.49-0.54) → đóng góp diversity cao. Meta-model chỉ gán 10.8% weight cho Prophet nhưng đủ để cải thiện ensemble.

**Q3: Tại sao stocks ngân hàng dễ dự đoán hơn bất động sản?**
> A: Banking stocks có fundamentals ổn định hơn, ít bị impact bởi news/events. Real estate stocks có volatility cao hơn do cycle dài hạn và policy sensitivity.

**Q4: 48-day prediction có MAPE cao (14.58%), có đáng tin không?**
> A: MAPE 14.58% cho 48 ngày vẫn tốt trong stock prediction. R² dương (0.176) chứng tỏ model vẫn better than baseline. Ensemble vẫn tốt hơn PatchTST 9.2%.

**Q5: Khi nào nên retrain models?**
> A: Weekly retraining theo schedule, hoặc emergency retraining khi:
- VN-Index thay đổi >5% trong 3 ngày
- MAPE trên test set tăng >30%
- Scenario handler trigger >3 lần/tuần

---

**Tài liệu đầy đủ**: ENSEMBLE_MODEL_DOCUMENTATION.md (2948 dòng, 8 chương)
**Scripts tạo dữ liệu**: scripts/generate_ensemble_comparison.py
**Dữ liệu chi tiết**: results/ENSEMBLE_VS_BASE_MODELS_20260108_033946.md
