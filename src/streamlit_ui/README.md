# Streamlit UI for Stock Advisor AI Agent System

Giao diện người dùng web-based cho hệ thống Multi-Agent tư vấn chứng khoán.

## 🎯 Tính năng

### 💬 Chat Interface
- Chat với AI Agent thông minh
- Real-time streaming responses
- Conversation history với metadata
- Suggested questions

### 📊 Portfolio Management
- Xem tổng quan danh mục đầu tư
- Quản lý alerts (tạo, xem, xóa)
- Theo dõi subscriptions
- Quick actions

### 📈 Visualization
- Biểu đồ giá cổ phiếu (candlestick, line, OHLC)
- Biểu đồ dự đoán với confidence intervals
- So sánh nhiều cổ phiếu
- Portfolio allocation pie chart

### ⚙️ Settings
- Toggle real-time streaming
- Show/hide metrics
- Session management

### 📊 System Metrics
- Mode distribution (Agent vs Direct)
- Cache performance
- Response times
- Success rates

## 🏗️ Kiến Trúc

```
Streamlit UI (Browser)
    ↓ Direct Python calls
AgentBridge (utils/agent_bridge.py)
    ↓ Preserves ALL logic
HybridOrchestrator (YOUR EXISTING SYSTEM)
    ↓ MCP Protocol
EnhancedMCPClient (25 tools)
```

**Key Design Principles:**
- ✅ **Zero changes to agent system** - AgentBridge chỉ là interface layer
- ✅ **All logic preserved** - HybridOrchestrator, AIRouter, agents unchanged
- ✅ **Clean separation** - UI layer hoàn toàn độc lập

## 📁 Cấu Trúc

```
streamlit_ui/
├── app.py                      # Main entry point
├── config.py                   # Configuration
├── requirements.txt            # Dependencies
├── README.md                   # This file
│
├── components/                 # UI Components
│   ├── chat_interface.py      # Chat UI
│   ├── sidebar.py             # Sidebar với portfolio, settings
│   ├── metrics_dashboard.py   # System metrics
│   └── visualization.py       # Charts & graphs
│
└── utils/                      # Utilities
    ├── agent_bridge.py        # Bridge to HybridOrchestrator ⭐
    ├── session_manager.py     # Session state management
    └── formatters.py          # Response formatters
```

## 🚀 Cài Đặt & Chạy

### 1. Install Dependencies

```bash
# Navigate to project root
cd "c:\Users\GIANG\OneDrive - Hanoi University of Science and Technology\Documents\DATN\Final"

# Install Streamlit UI requirements
pip install -r src/streamlit_ui/requirements.txt
```

### 2. Set Environment Variables

Tạo file `.env` ở project root:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

### 3. Run Streamlit App

```bash
streamlit run src/streamlit_ui/app.py
```

App sẽ mở tại: `http://localhost:8501`

### 4. (Optional) Custom Port

```bash
streamlit run src/streamlit_ui/app.py --server.port 8502
```

## 💡 Cách Sử Dụng

### Chat với Agent

1. Mở app trong browser
2. Nhập câu hỏi vào chat input
3. Agent sẽ xử lý và trả lời

**Ví dụ câu hỏi:**
- "Phân tích cổ phiếu VCB"
- "Tư vấn đầu tư 100 triệu vào ngành ngân hàng"
- "So sánh VCB với TCB"
- "Tạo cảnh báo khi VCB vượt 100k"
- "Dự đoán giá VCB 3 ngày tới"

### Quản Lý Portfolio

1. Click "Refresh Portfolio" trong sidebar
2. Xem tổng số alerts và subscriptions
3. Click vào expander để xem chi tiết

### Tạo Alert

1. Mở "Alerts Management" page (sidebar)
2. Click "➕ Tạo cảnh báo mới"
3. Điền thông tin:
   - Mã cổ phiếu (VD: VCB)
   - Điều kiện (Trên, Dưới, Vượt lên, Vượt xuống)
   - Giá mục tiêu
   - Loại alert
4. Click "Tạo cảnh báo"

### Xem Metrics

1. Enable "Hiển thị metrics" trong sidebar settings
2. Click vào expander "📊 System Metrics" ở cuối chat
3. Xem chi tiết về:
   - Mode distribution
   - Cache performance
   - Response times
   - Success rates

## 🎨 Customization

### Thay Đổi Theme

Edit [config.py](config.py):

```python
PRIMARY_COLOR = "#1f77b4"
BACKGROUND_COLOR = "#ffffff"
```

### Thay Đổi Page Title/Icon

```python
PAGE_TITLE = "Your Custom Title"
PAGE_ICON = "🚀"
```

### Disable Features

```python
ENABLE_PORTFOLIO_PAGE = False
ENABLE_METRICS_DASHBOARD = False
```

## 🔧 Troubleshooting

### Lỗi: "Cannot import HybridOrchestrator"

**Nguyên nhân:** Python path chưa đúng

**Giải pháp:**
```python
# Đã xử lý trong agent_bridge.py
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
```

### Lỗi: "Event loop is already running"

**Nguyên nhân:** Streamlit chạy trong async context

**Giải pháp:** Đã xử lý bằng `asyncio.run()` trong app.py

### Chat không hiển thị response

**Kiểm tra:**
1. GOOGLE_API_KEY có được set chưa?
2. Agent system có chạy được không? (test bằng cách import trực tiếp)
3. Xem logs trong terminal

### Metrics không hiển thị

**Nguyên nhân:** Chưa có dữ liệu hoặc tắt trong settings

**Giải pháp:**
1. Chat với agent ít nhất 1 lần
2. Enable "Hiển thị metrics" trong sidebar

## 📊 Performance

### Khuyến Nghị

- **Streamlit caching**: Sử dụng `@st.cache_data` cho operations nặng
- **Session state**: Minimize state updates để tránh re-renders
- **Lazy loading**: Agent system chỉ initialize khi cần

### Benchmarks

| Operation | Time |
|-----------|------|
| App startup | ~2-3s |
| Agent initialization | ~1-2s |
| Simple query (Direct mode) | <1s |
| Complex query (Agent mode) | 3-5s |
| Chart rendering | <0.5s |

## 🔐 Security Notes

- ⚠️ **Không deploy public** mà không có authentication
- 🔒 API keys phải được quản lý qua environment variables
- 🚫 Không commit `.env` file lên git
- ✅ Sử dụng Streamlit Cloud secrets cho production

## 🎯 Roadmap

### Version 1.1
- [ ] Multi-user authentication
- [ ] Real-time push notifications
- [ ] Advanced charting (technical indicators)
- [ ] Export conversation history
- [ ] Dark mode support

### Version 1.2
- [ ] Mobile responsive design
- [ ] Voice input support
- [ ] PDF report generation
- [ ] Webhook integration

## 📝 License

Same as parent project.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📧 Support

Issues? Questions? Create an issue on GitHub or contact the maintainers.

---

**Built with ❤️ using Streamlit and Claude AI**
