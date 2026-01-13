# ĐẶC TẢ USE CASE: DỰ ĐOÁN GIÁ CỔ PHIẾU

## Bảng 2.11: Đặc tả Use Case: Dự đoán giá cổ phiếu

| Thành phần | Mô tả |
|-----------|-------|
| **Tên Use Case** | Dự đoán giá cổ phiếu |
| **Mục đích** | Cho phép người dùng dự đoán giá cổ phiếu trong tương lai dựa trên mô hình ensemble learning kết hợp 5 mô hình AI và xử lý các kịch bản thị trường đặc biệt. |
| **Tác nhân** | User |
| **Luồng sự kiện chính** | 1. Người dùng gửi yêu cầu dự đoán giá cổ phiếu (VD: "Dự đoán giá VCB 3 ngày tới", "Forecast ACB price for next 48 days").<br><br>2. Hệ thống phân tích yêu cầu và xác định mã cổ phiếu, khung thời gian dự đoán (3 ngày hoặc 48 ngày).<br><br>3. Hệ thống thu thập dữ liệu lịch sử (1000+ phiên giao dịch) và tính toán 60+ chỉ báo kỹ thuật (RSI, MACD, Bollinger Bands, volume indicators, ...).<br><br>4. Hệ thống chạy 5 mô hình base models song song:<br>   - PatchTST (Time Series Transformer)<br>   - LSTM (Long Short-Term Memory)<br>   - LightGBM (Gradient Boosting)<br>   - Prophet (Facebook's forecasting)<br>   - XGBoost (Extreme Gradient Boosting)<br><br>5. Meta-model (MLPRegressor) kết hợp kết quả từ 5 base models với trọng số tối ưu.<br><br>6. Hệ thống phát hiện và xử lý các kịch bản thị trường đặc biệt (nếu có):<br>   - News Shock (tin tức đột biến)<br>   - Market Crash (sụp đổ thị trường)<br>   - Foreign Flow (dòng tiền nước ngoài)<br>   - VN30 Adjustment (điều chỉnh danh mục VN30)<br>   - Margin Call (cảnh báo margin)<br><br>7. Hệ thống tính toán độ tin cậy (confidence score) dựa trên:<br>   - Mức độ đồng thuận giữa các mô hình<br>   - MAPE lịch sử của ensemble<br>   - Tác động của scenario adjustments<br><br>8. Hệ thống trả về kết quả dự đoán với đầy đủ thông tin cho người dùng. |
| **Luồng sự kiện phụ** | 2a. Nếu người dùng không chỉ định khung thời gian, hệ thống mặc định sử dụng 3 ngày.<br><br>3a. Nếu mã cổ phiếu không có đủ dữ liệu lịch sử, hệ thống thông báo lỗi và yêu cầu chọn mã khác.<br><br>6a. Nếu không phát hiện scenario đặc biệt nào, hệ thống sử dụng kết quả từ meta-model trực tiếp.<br><br>7a. Nếu confidence score < 60%, hệ thống cảnh báo người dùng về độ tin cậy thấp. |
| **Điều kiện tiên quyết** | - Người dùng đã xác thực danh tính.<br>- Hệ thống có dữ liệu lịch sử đầy đủ cho mã cổ phiếu được yêu cầu.<br>- Các mô hình AI đã được training và sẵn sàng. |
| **Kết quả** | Người dùng nhận được thông tin dự đoán bao gồm:<br>- Giá hiện tại<br>- Giá dự đoán (predicted_price)<br>- Phần trăm thay đổi (change_percent)<br>- Độ tin cậy (confidence: 0-100%)<br>- Khuyến nghị (BUY/HOLD/SELL)<br>- Danh sách scenario adjustments (nếu có)<br>- Breakdown từng mô hình (tùy chọn)<br>- Visualization dạng biểu đồ (tùy chọn) |

---

## Ví dụ Output

### Ví dụ 1: Dự đoán 3 ngày (không có scenario)

**Input**: "Dự đoán giá VCB 3 ngày tới"

**Output**:
```json
{
  "ticker": "VCB",
  "horizon": "3_days",
  "current_price": 98500,
  "predicted_price": 100234,
  "change_percent": 1.76,
  "confidence": 85.2,
  "recommendation": "BUY",
  "scenario_adjustments": {},
  "model_breakdown": {
    "PatchTST": 100100,
    "LSTM": 99800,
    "LightGBM": 100500,
    "Prophet": 99200,
    "XGBoost": 100300
  },
  "metrics": {
    "ensemble_mape": "1.99%",
    "ensemble_r2": 0.874,
    "prediction_date": "2026-01-11"
  }
}
```

### Ví dụ 2: Dự đoán 3 ngày (có Foreign Flow scenario)

**Input**: "Predict ACB price for next 3 days"

**Output**:
```json
{
  "ticker": "ACB",
  "horizon": "3_days",
  "current_price": 25300,
  "predicted_price": 24541,
  "change_percent": -3.0,
  "confidence": 78.5,
  "recommendation": "HOLD",
  "scenario_adjustments": {
    "foreign_flow": -3.0,
    "reason": "Foreign room 97.3% > 95% threshold, selling pressure detected"
  },
  "base_prediction": 25300,
  "adjusted_prediction": 24541,
  "metrics": {
    "ensemble_mape": "1.72%",
    "ensemble_r2": 0.960,
    "prediction_date": "2026-01-11"
  }
}
```

### Ví dụ 3: Dự đoán 48 ngày

**Input**: "Dự báo giá HPG trong 48 ngày tới"

**Output**:
```json
{
  "ticker": "HPG",
  "horizon": "48_days",
  "current_price": 28700,
  "predicted_price": 31250,
  "change_percent": 8.89,
  "confidence": 62.3,
  "recommendation": "BUY",
  "scenario_adjustments": {},
  "warning": "Long-term prediction (48 days) has lower confidence. Market conditions may change significantly.",
  "metrics": {
    "ensemble_mape": "12.88%",
    "ensemble_r2": 0.177,
    "prediction_date": "2026-02-25"
  },
  "trend": "upward",
  "support_levels": [27500, 26800],
  "resistance_levels": [30000, 32000]
}
```

---

## Performance Metrics

### Dự đoán 3 ngày
- **Average MAPE**: 1.99%
- **Average R²**: 0.874
- **Average MAE**: 0.76
- **Average RMSE**: 1.03

### Dự đoán 48 ngày
- **Average MAPE**: 14.58%
- **Average R²**: 0.176
- **Average MAE**: 5.65
- **Average RMSE**: 7.67

---

## 5 Scenario Handlers

1. **News Shock Handler**
   - Phát hiện: Khối lượng tin tức đột biến > 5x bình thường
   - Điều chỉnh: ±5% tùy sentiment

2. **Market Crash Handler**
   - Phát hiện: VN-Index giảm > 3% trong 1 phiên
   - Điều chỉnh: -8% cho tất cả mã

3. **Foreign Flow Handler**
   - Phát hiện: Room nước ngoài > 95%
   - Điều chỉnh: -3% (áp lực bán)

4. **VN30 Adjustment Handler**
   - Phát hiện: Mã cổ phiếu vào/ra VN30
   - Điều chỉnh: +4% (vào) hoặc -4% (ra)

5. **Margin Call Handler**
   - Phát hiện: Tỷ lệ margin > 80%
   - Điều chỉnh: -6% (rủi ro thanh lý)

---

## Ghi chú
- Use case này được triển khai thông qua **prediction_agent** trong hệ thống AI Agent.
- Sử dụng 3 MCP tools: `predict_stock_price`, `batch_predict_stocks`, `get_prediction_confidence`
- Ensemble model được retrain tự động hàng tuần để đảm bảo độ chính xác.
