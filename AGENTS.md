# UNIVERSAL AI AGENT INSTRUCTION & WORKFLOW STANDARD

> **Dự án:** Sheet Converter (Chuyển đổi Sheet nhạc PDF/Ảnh thành MusicXML chuẩn)  
> **Phiên bản:** 1.0.0  
> **Nguyên tắc cốt lõi:** Kỷ luật quy trình (Superpowers) + Ngôn ngữ thiết kế chuẩn (Google Labs DESIGN.md) + Bản đồ tri thức (GitNexus) + Kiến trúc MVC/OOP sạch.

---

## 1. NGUYÊN TẮC BẮT BUỘC DÀNH CHO MỌI AI MODEL (Gemini, Claude, GPT, DeepSeek,...)

Bất kỳ AI Agent nào khi làm việc trong repository này **BẮT BUỘC** phải tuân thủ nghiêm ngặt các nguyên tắc sau:

1. **Không code tắt, không bỏ qua kiểm thử (TDD First)**: Mọi tính năng nghiệp vụ (Parser, Exporter, Patcher, Validator) đều phải có Test Case trước hoặc kiểm định với file chuẩn [`001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml`](file:///d:/xampp/htdocs/SheetTools/001%20H%E1%BB%A0I%20TH%C3%81NH%20V%C6%AF%C6%A0NG,%20K%C3%8DP%20NG%E1%BB%B0%20LAI.xml).
2. **Luôn tra cứu [NEXUS.md](file:///d:/xampp/htdocs/SheetTools/NEXUS.md) trước khi tạo/sửa file**: Nắm rõ vai trò, vị trí lớp, quan hệ phụ thuộc và luồng dữ liệu (Data Flow) để tránh trùng lặp hoặc đặt sai vị trí kiến trúc.
3. **Tuyệt đối tuân thủ giao ước [DESIGN.md](file:///d:/xampp/htdocs/SheetTools/DESIGN.md)**: Không tự ý sáng tạo mã màu, khoảng cách (spacing), font chữ hay giao diện tùy tiện ngoài các Design Tokens đã quy định.
4. **Chuẩn mực OOP & Clean Code**: 
   - Không viết "God Controller" hay nhồi nhét logic vào View.
   - Phân tách rõ: Controller $\rightarrow$ Service $\rightarrow$ Repository / Adapter / Worker $\rightarrow$ DTOs.
   - Áp dụng các Design Pattern phù hợp: Strategy/Adapter cho OMR Engine, Pipeline cho tiền xử lý ảnh, Patch Pattern cho XML.
   - Sử dụng Strong Typing (PHP 8.3 `declare(strict_types=1);`, TypeScript strict mode, Python Type Hints).
5. **Tuân thủ đúng Lộ trình 7 Phase**: Không nhảy cóc tính năng khi Phase trước chưa hoàn thành và kiểm thử thành công.

---

## 2. QUY TRÌNH LÀM VIỆC SUPERPOWERS (7 BƯỚC)

```text
1. CLARIFY (Làm rõ yêu cầu & Phạm vi)
   ↓
2. NEXUS LOOKUP (Tra cứu bản đồ kiến trúc & quan hệ phụ thuộc tại NEXUS.md)
   ↓
3. DESIGN COMPLIANCE (Kiểm tra token thiết kế tại DESIGN.md nếu làm UI)
   ↓
4. PLAN & TDD (Lập kế hoạch & Viết Test trước)
   ↓
5. OOP IMPLEMENTATION (Viết code sạch, phân tầng MVC, xử lý lỗi chặt chẽ)
   ↓
6. VALIDATION & GOLDEN TEST (Chạy test tự động & đối chiếu Golden Reference)
   ↓
7. NEXUS SYNC & REPORT (Cập nhật NEXUS.md nếu có file/class mới & Báo cáo)
```

---

## 3. CÁC TÀI LIỆU QUY CHUẨN TRỌNG YẾU

- [**NEXUS.md**](file:///d:/xampp/htdocs/SheetTools/NEXUS.md): Bản đồ tri thức mã nguồn, Danh mục Class/Module, Call Graph và Luồng dữ liệu.
- [**DESIGN.md**](file:///d:/xampp/htdocs/SheetTools/DESIGN.md): Bản giao ước ngôn ngữ thiết kế (YAML Tokens + Prose) chống AI Slop.
- [**SHEET_CONVERTER_ANTIGRAVITY_SPEC.md**](file:///d:/xampp/htdocs/SheetTools/SHEET_CONVERTER_ANTIGRAVITY_SPEC.md): Đặc tả tính năng và yêu cầu nghiệp vụ chi tiết của phần mềm.
- [**.agents/rules/superpowers-workflow.md**](file:///d:/xampp/htdocs/SheetTools/.agents/rules/superpowers-workflow.md): Hướng dẫn chi tiết quy trình phát triển và checklist rà soát code.
- [**.agents/rules/architecture-standards.md**](file:///d:/xampp/htdocs/SheetTools/.agents/rules/architecture-standards.md): Chuẩn mực lập trình hướng đối tượng (OOP), SOLID và cấu trúc MVC.

---

## 4. QUẢN LÝ DỮ LIỆU & BẢN QUYỀN TRẠNG THÁI (Source of Truth)

- `SOURCE FILE` (PDF/Ảnh gốc): **Immutable (Bất biến)**.
- `RAW MUSICXML` (Xuất từ Audiveris): **Immutable (Bất biến)**.
- `CURRENT MUSICXML` (Bản đang chỉnh sửa lời/hợp âm/nốt): **Mutable (Có thể sửa qua patch)**.
- `FINAL MUSICXML` (Bản xuất hoàn chỉnh tương thích OSMD/SheetApp): **Generated (Tạo mới khi export)**.
- `source.omr`: **Tuyệt đối không xóa**, lưu trữ cùng dự án để debug và tái xử lý.

---

## 5. LỆNH VÀ KIỂM TRA MÔI TRƯỜNG NHANH

```bash
# Kiểm tra phiên bản PHP
php -v

# Kiểm tra Node & NPM
node -v && npm -v

# Kiểm tra Java (yêu cầu cho Audiveris)
java -version

# Kiểm tra Tesseract OCR & ngôn ngữ vie
tesseract --list-langs

# Kiểm tra Python & thư viện
python --version
python -c "import cv2, lxml, music21; print('Python OMR libs OK')"
```
