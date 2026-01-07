# PlantUML Diagrams - Hệ thống Stock Trading (Có MCP + Multi-Model)

Thư mục này chứa tất cả các diagram được vẽ bằng PlantUML cho hệ thống Stock Trading với MCP integration và Multi-Model AI System.

> **📝 Lưu ý**: Sau khi tích hợp Multi-Model System (2026-01-06), một số diagrams đã được cập nhật để phản ánh kiến trúc mới. Xem [SEQUENCE_DIAGRAM_COMPARISON.md](SEQUENCE_DIAGRAM_COMPARISON.md) để biết chi tiết.

## 📁 Danh sách Files

### 1. Use Case Diagram
- **File**: `usecase_diagram_with_mcp.puml`
- **Mô tả**: Sơ đồ tổng quan 9 use cases với MCP Server
- **Status**: ✅ Valid (chưa cần update cho multi-model)

### 2. Sequence Diagrams (Current)

**✨ Updated**: Tất cả sequence diagrams sử dụng AI đã được cập nhật với Multi-Model Architecture (2026-01-06)

| File | Use Case | Độ phức tạp | Architecture | Models Used |
|------|----------|-------------|--------------|-------------|
| `sequence_uc1_xac_thuc.puml` | UC1: Xác thực danh tính | ⭐ Simple | Basic | None (no AI) |
| `sequence_uc2_dang_ky_canh_bao.puml` | UC2: Đăng ký cảnh báo | ⭐⭐ Medium | Basic | Minimal AI |
| `sequence_uc3_subscription.puml` | UC3: Đăng ký theo dõi | ⭐⭐ Medium | Basic | Minimal AI |
| `sequence_uc4_loc_co_phieu.puml` | UC4: Lọc cổ phiếu | ⭐⭐⭐ Complex | Basic | Simple queries |
| `sequence_uc5_truy_van.puml` | UC5: Truy vấn dữ liệu cơ bản | ⭐ Simple | Basic | None (direct MCP) |
| `sequence_uc6_phan_tich.puml` | UC6: Phân tích KT & TC | ⭐⭐⭐⭐⭐ | **Multi-Model** ✅ | 3 (Flash, Claude, GPT-4o) |
| `sequence_uc7_chart.puml` | UC7: Xem biểu đồ | ⭐⭐ Medium | Basic | None (MCP tool only) |
| `sequence_uc8_tu_van_dau_tu.puml` | UC8: Tư vấn đầu tư | ⭐⭐⭐⭐⭐⭐ | **Multi-Model** ✅ | 4 (Flash, Pro, Claude, GPT-4o) |
| `sequence_uc9_discovery.puml` | UC9: Khám phá cổ phiếu | ⭐⭐⭐⭐ | **Multi-Model** ✅ | 3 (Flash, Pro, Claude) |

**Multi-Model Diagrams** (UC6, UC8, UC9):
- ✅ Multi-Model Layer (Task Classifier + Model Selector)
- ✅ 4 AI Models với specialized tasks
- ✅ Usage Tracker (cost monitoring)
- ✅ Detailed cost breakdown per model
- ✅ Quality improvement metrics (+40-80%)
- ✅ Participants: 11-12 (vs 7-8 trước đây)

### 4. Documentation

| File | Mô tả |
|------|-------|
| `SEQUENCE_DIAGRAM_COMPARISON.md` | **MỚI**: So sánh chi tiết trước/sau Multi-Model |
| `README.md` | File này - Tổng quan tất cả diagrams |
| `DIAGRAM_SUMMARY.md` | Summary ban đầu (có MCP, chưa có multi-model) |

## 🚀 Cách sử dụng

### Option 1: VS Code Extension (Khuyến nghị ✅)

1. Cài extension **PlantUML** trong VS Code
2. Mở file `.puml` bất kỳ
3. Nhấn `Alt+D` để xem preview
4. Nhấn `Ctrl+Shift+P` → "PlantUML: Export Current Diagram" để export PNG/SVG

### Option 2: PlantUML Online

1. Mở https://www.plantuml.com/plantuml/uml/
2. Copy nội dung file `.puml`
3. Paste vào editor
4. Click "Submit" để xem diagram
5. Download PNG/SVG

### Option 3: Command Line

```bash
# Cài PlantUML (requires Java)
# Download plantuml.jar từ https://plantuml.com/download

# Render 1 file
java -jar plantuml.jar usecase_diagram_with_mcp.puml

# Render tất cả
java -jar plantuml.jar *.puml

# Output: file .png cùng thư mục
```

### Option 4: Python Script (Batch Render)

```bash
# Sử dụng script render_all.py
python render_all.py
```

## 📊 Diagram Features

### ✅ Có trong tất cả diagrams:

- **MCP Layer**: Hiển thị đầy đủ MCP Wrapper, MCP Client, MCP Server
- **Participants**: User, Discord Bot, Root Agent, Specialized Agents, MCP components, Database, External APIs
- **Messages**: Rõ ràng, có mô tả tham số
- **Notes**: Giải thích cache strategy, AI features, technical details
- **Activations**: Thể hiện thời gian active của mỗi participant
- **Colors**: Sử dụng theme `plain` với background colors để dễ đọc

### 🎨 Styling

- Theme: `plain` (sáng, dễ đọc)
- Background: `#FEFEFE` (gần trắng)
- Message alignment: `center`
- No shadowing (gọn gàng hơn)

## 🔄 So sánh với Tài liệu cũ

| Aspect | Tài liệu cũ | Diagrams mới (có MCP) |
|--------|-------------|----------------------|
| **Participants** | 4-5 | 7-9 (thêm MCP layer) |
| **MCP Tools** | ❌ Không đề cập | ✅ Hiển thị cụ thể tool nào được dùng |
| **Caching** | ❌ Không hiển thị | ✅ Note về cache TTL |
| **AI Integration** | ❓ Mơ hồ | ✅ Rõ ràng (Gemini AI calls) |
| **External APIs** | ❌ Trực tiếp | ✅ Qua MCP Server (proper architecture) |

## 📝 Cập nhật vào Tài liệu

### Bước 1: Export PNG/SVG

Render tất cả diagrams ra PNG:

```bash
cd diagrams
java -jar plantuml.jar -tpng *.puml
```

Output: 9 files PNG

### Bước 2: Thay thế trong tài liệu Word/PDF

- **Hình 2.5** → `usecase_diagram_with_mcp.png`
- **Hình 2.6** → `sequence_uc2_dang_ky_canh_bao.png`
- **Hình 2.7** → `sequence_uc3_subscription.png`
- **Hình 2.8** → `sequence_uc4_loc_co_phieu.png`
- Thêm các hình mới cho UC1, UC6, UC7, UC8, UC9

### Bước 3: Cập nhật chú thích

Mỗi hình cần có chú thích:

```
Hình X.Y: Sequence Diagram - [Use Case Name] (Có MCP Integration)

Diagram thể hiện luồng xử lý khi [action]. Lưu ý các thành phần MCP:
- MCP Wrapper: Bridge async/sync contexts
- MCP Client: Caching, retry, circuit breaker
- MCP Server: Quản lý 25 tools, kết nối Database/TCBS/Gemini AI
```

## 🛠️ Maintenance

Khi cần chỉnh sửa diagrams:

1. Mở file `.puml` trong VS Code
2. Edit PlantUML code
3. Preview với `Alt+D`
4. Export lại PNG
5. Commit vào Git

## 📚 PlantUML Documentation

- Official docs: https://plantuml.com/
- Sequence diagram syntax: https://plantuml.com/sequence-diagram
- Use case diagram: https://plantuml.com/use-case-diagram
- Styling: https://plantuml.com/skinparam

## 🔄 Multi-Model Integration Updates

### Thay đổi sau khi tích hợp Multi-Model (2026-01-06)

**Files đã cập nhật**:
- ✅ `sequence_uc5_truy_van.puml` - **MỚI**: Basic data query (simple, fast)
- ✅ `sequence_uc6_phan_tich.puml` - Analysis với 3 AI models (Flash, Claude, GPT-4o)
- ✅ `sequence_uc8_tu_van_dau_tu.puml` - Investment advisory với 4 AI models (tất cả)
- ✅ `sequence_uc9_discovery.puml` - Discovery với 3 AI models (Flash, Pro, Claude) - **Fixed lỗi participant**
- ✅ `SEQUENCE_DIAGRAM_COMPARISON.md` - Document so sánh chi tiết

**Thay đổi chính**:
1. ➕ Thêm sequence_uc5_truy_van.puml (thiếu trong bản trước)
2. ➕ Thêm Multi-Model Layer (Task Classifier + Model Selector)
3. ➕ Thêm 4 AI Models (Gemini Flash, Gemini Pro, Claude Sonnet, GPT-4o)
4. ➕ Thêm Usage Tracker participant
5. 📊 Cost breakdown chi tiết cho từng model
6. 📈 Quality improvement metrics (+40-80%)
7. 🐛 Sửa lỗi UC9 (thiếu Gemini Pro participant)
8. ❌ Xóa legacy files (đã được thay thế)

**Lưu ý quan trọng**:
- Files cũ (legacy) đã bị XÓA và được THAY THẾ bằng multi-model versions
- Tên file vẫn giữ nguyên (không có suffix "_multimodel")
- Tất cả diagrams hiện tại đều là phiên bản mới nhất

---

## ✅ Checklist Export

### All Diagrams (Current Architecture)
- [ ] Export usecase_diagram_with_mcp.png
- [ ] Export sequence_uc1_xac_thuc.png (no changes)
- [ ] Export sequence_uc2_dang_ky_canh_bao.png (no changes)
- [ ] Export sequence_uc3_subscription.png (no changes)
- [ ] Export sequence_uc4_loc_co_phieu.png (no changes)
- [ ] Export sequence_uc5_truy_van.png ⭐ **NEW** (Basic query)
- [ ] Export sequence_uc6_phan_tich.png ⭐ **Multi-Model** (UPDATED)
- [ ] Export sequence_uc7_chart.png (no changes)
- [ ] Export sequence_uc8_tu_van_dau_tu.png ⭐ **Multi-Model** (UPDATED)
- [ ] Export sequence_uc9_discovery.png ⭐ **Multi-Model** (UPDATED, FIXED)

### Documentation Updates
- [ ] Thay thế UC6, UC8, UC9 trong tài liệu Word bằng versions mới
- [ ] Thêm section về Multi-Model Architecture
- [ ] Cập nhật chú thích cho UC6, UC8, UC9
- [ ] Thêm cost comparison table
- [ ] Review toàn bộ tài liệu
- [ ] Export PDF final

---

**Created**: 2026-01-06
**Last Updated**: 2026-01-06 (Multi-Model Integration)
**Author**: AI Agent Hybrid System
**Version**: 3.0