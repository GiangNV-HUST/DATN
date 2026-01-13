# MCP Server - 25 Tools Documentation

## ✅ Installation Complete

Đã copy thành công 25 tools từ upload sang Final project.

## 📁 Cấu trúc thư mục

```
Final/src/mcp_server/
├── server.py              # MCP server chính (25 tools)
├── __init__.py
├── shared/                # Utilities và constants
│   ├── database.py        # Database connection & utilities
│   ├── constants.py       # VN30 stocks, alert types, validators
│   └── utilities.py       # Helper functions
└── tools/                 # Implementation của 25 tools
    ├── stock_tools.py          # 4 tools: stock data, predictions, charts, TCBS
    ├── alert_tools.py          # 3 tools: create/get/delete alerts
    ├── subscription_tools.py   # 3 tools: create/get/delete subscriptions
    ├── gemini_tools.py         # 3 tools: AI summarization & search
    ├── finance_tools.py        # 1 tool: financial data
    ├── screener_tools.py       # 2 tools: stock screening
    ├── investment_planning_tools.py  # 5 tools: investment planning
    └── stock_discovery_tools.py      # 4 tools: stock discovery
```

## 🔧 Import Paths đã được sửa

Tất cả import paths đã được cập nhật từ:
- `from ...shared.database` → `from ..shared.database`
- Đảm bảo tương thích với cấu trúc Final project

## 📦 Dependencies cần thiết

Các package Python cần cài đặt:
```bash
pip install psycopg2-binary
pip install pandas
pip install matplotlib
pip install mplfinance
pip install vnstock
pip install google-generativeai
pip install python-dotenv
pip install mcp
```

## 🔐 Environment Variables (.env)

```env
# Database
DB_HOST=localhost
DB_NAME=stock_db
DB_USER=your_user
DB_PASSWORD=your_password
DB_PORT=5432

# Gemini AI (for AI tools)
GOOGLE_API_KEY=your_gemini_api_key
```

## 🚀 Cách chạy MCP Server

```bash
cd Final/src/mcp_server
python server.py
```

## 📋 Danh sách 25 Tools

### Stock Data Tools (4)
1. **get_stock_data** - Lấy dữ liệu giá OHLCV + indicators
2. **get_stock_price_prediction** - Dự đoán giá (3d/48d)
3. **generate_chart_from_data** - Tạo biểu đồ nến
4. **get_stock_details_from_tcbs** - 70+ fields từ TCBS

### Alert Tools (3)
5. **create_alert** - Tạo cảnh báo giá/indicators
6. **get_user_alerts** - Lấy danh sách alerts
7. **delete_alert** - Xóa alert

### Subscription Tools (3)
8. **create_subscription** - Đăng ký theo dõi cổ phiếu
9. **get_user_subscriptions** - Lấy danh sách subscriptions
10. **delete_subscription** - Hủy đăng ký

### Gemini AI Tools (3)
11. **gemini_summarize** - Tóm tắt data bằng AI
12. **gemini_search_and_summarize** - Tìm kiếm web + tóm tắt
13. **batch_summarize** - Tóm tắt hàng loạt (parallel)

### Financial Data Tools (2)
14. **get_financial_data** - Báo cáo tài chính (BS/IS/CF/Ratios)
15. **screen_stocks** - Lọc cổ phiếu (80+ tiêu chí)
16. **get_screener_columns** - Danh sách cột screening

### Investment Planning Tools (5)
17. **gather_investment_profile** - Thu thập profile đầu tư
18. **calculate_portfolio_allocation** - Phân bổ danh mục
19. **generate_entry_strategy** - Chiến lược vào lệnh
20. **generate_risk_management_plan** - Quản lý rủi ro
21. **generate_monitoring_plan** - Kế hoạch theo dõi

### Stock Discovery Tools (4)
22. **discover_stocks_by_profile** - Tìm cổ phiếu theo profile
23. **search_potential_stocks** - Tìm kiếm cổ phiếu tiềm năng
24. **filter_stocks_by_criteria** - Lọc theo tiêu chí
25. **rank_stocks_by_score** - Xếp hạng theo điểm

## ⚠️ Lưu ý

1. **Database Schema**: Đảm bảo database có các bảng:
   - `stock.stock_prices_1d` - Dữ liệu giá daily
   - `stock.stock_prices_3d_predict` - Dự đoán 3 ngày
   - `stock.stock_prices_48d_predict` - Dự đoán 48 ngày
   - `stock.alert` - Bảng alerts
   - `stock.subscribe` - Bảng subscriptions
   - `stock.balance_sheet`, `stock.income_statement`, `stock.cash_flow`, `stock.ratio`

2. **TCBS Integration**: Sử dụng vnstock package để fetch data từ TCBS

3. **Gemini API**: Cần API key hợp lệ để sử dụng AI tools

## 🧪 Testing

Sau khi setup, test MCP server bằng cách:
```python
# Test import
from mcp_server.tools.stock_tools import get_stock_data_mcp

# Test MCP server
python server.py
```

## 📞 Support

Nếu gặp lỗi import hoặc dependencies, kiểm tra:
1. Python version >= 3.10
2. Tất cả packages đã cài đầy đủ
3. Database connection string đúng
4. API keys hợp lệ
