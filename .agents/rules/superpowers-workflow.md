# SUPERPOWERS WORKFLOW RULES & DEVELOPMENT HABITS

Tài liệu này quy định chi tiết quy trình làm việc chuẩn mực "Superpowers" dành cho AI Agent trong dự án **Sheet Converter**.

---

## 1. NGUYÊN LÝ "SUPERPOWERS"
Superpowers biến quá trình coding của AI từ ngẫu hứng (chaotic/prompt-and-pray) thành một quy trình kỹ thuật phần mềm có kỷ luật, có thể kiểm soát và tái lập (predictable & reproducible).

---

## 2. QUY TRÌNH 7 BƯỚC BẮT BUỘC

### Bước 1: Clarify & Scope Boundary (Làm rõ yêu cầu & Phạm vi)
- Xác định rõ tính năng thuộc Phase nào trong 7 Phases của dự án.
- Kiểm tra danh sách "Không làm ở V1" (Không làm DAW, MIDI synth, multi-engine AI...) để tránh feature creep.
- Xác định các dữ liệu đầu vào (Input), kết quả đầu ra mong đợi (Expected Output) và tác động tiềm ẩn.

### Bước 2: Nexus Knowledge Graph Lookup (Tra cứu bản đồ kiến trúc)
- Mở và đọc [`NEXUS.md`](file:///d:/xampp/htdocs/SheetTools/NEXUS.md).
- Tìm vị trí tương ứng của tính năng: Model nào? Controller nào? Service nào? DTO nào?
- Xác định các Dependency và Data Flow liên quan.

### Bước 3: Design Contract Compliance (Nếu có thành phần UI)
- Mở và đọc [`DESIGN.md`](file:///d:/xampp/htdocs/SheetTools/DESIGN.md).
- Sử dụng chính xác các Design Tokens (mã màu, spacing, typography, component rules).
- Đảm bảo tỷ lệ tương phản đạt chuẩn WCAG AA.

### Bước 4: Test-Driven Development (TDD First)
- Viết Test Case trước khi viết code nghiệp vụ:
  - Unit Test cho Services/Patcher/DTOs/Validators.
  - Feature Test cho API Endpoints.
  - Fixture Test đối chiếu với [`001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml`](file:///d:/xampp/htdocs/SheetTools/001%20H%E1%BB%A0I%20TH%C3%81NH%20V%C6%AF%C6%A0NG,%20K%C3%8DP%20NG%E1%BB%B0%20LAI.xml).
- Chạy test và xác nhận Test Fail đúng kỳ vọng trước khi implement logic.

### Bước 5: Clean OOP / MVC Implementation
- Viết code sạch, áp dụng đúng Design Patterns (Adapter, Pipeline, Patch, DTO, Repository).
- Tuân thủ nguyên tắc SOLID.
- Sử dụng Strong Typing (PHP 8.3, TypeScript, Python Type Annotations).
- Phòng thủ lỗi (Defensive Programming): Validate input MIME, extension, shell argument escaping, timeout handling.

### Bước 6: Run Verification & Golden Reference Check
- Chạy toàn bộ test suite.
- Kiểm tra khả năng render trên OSMD.
- Xác thực XML well-formed và MusicXML 3.1/4.0 schema.

### Bước 7: Nexus Sync & Report
- Nếu có file mới hoặc thay đổi kiến trúc/class: **Cập nhật ngay vào [`NEXUS.md`](file:///d:/xampp/htdocs/SheetTools/NEXUS.md)**.
- Báo cáo kết quả rõ ràng, súc tích kèm bằng chứng kiểm thử (Test results).

---

## 3. CHECKLIST CODE REVIEW DÀNH CHO AI AGENT

Trước khi hoàn thành bất kỳ task nào, AI Agent phải tự rà soát:

- [ ] Code có vi phạm phạm vi V1 không?
- [ ] Logic có bị nhồi nhét vào Controller/View thay vì Service/DTO không?
- [ ] Đã khai báo strict types (`declare(strict_types=1);` trong PHP, `strict: true` trong TS) chưa?
- [ ] Các tham số dòng lệnh (shell command) cho Audiveris/Tesseract đã được escape an toàn chưa?
- [ ] Giao diện có tuân thủ Design Tokens trong `DESIGN.md` không?
- [ ] File `source.omr` và `raw.musicxml` có được giữ nguyên bất biến không?
- [ ] `NEXUS.md` đã được đồng bộ với cấu trúc file mới nhất chưa?
