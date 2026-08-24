# ARCHITECTURAL STANDARDS & OOP PATTERNS

Tài liệu này quy định các tiêu chuẩn kiến trúc phần mềm, lập trình hướng đối tượng (OOP), các mẫu thiết kế (Design Patterns) và phân tầng MVC trong dự án **Sheet Converter**.

---

## 1. NGUYÊN TẮC CỐT LÕI (SOLID & CLEAN CODE)

1. **Single Responsibility (SRP)**: Mỗi class chỉ đảm nhận một trách nhiệm duy nhất (ví dụ: `AudiverisService` chỉ chịu trách nhiệm điều phối OMR, `MusicXmlPatcher` chỉ chịu trách nhiệm can thiệp XML).
2. **Open/Closed (OCP)**: Kiến trúc OMR mở rộng qua Interface `OmrEngineInterface`. Nếu sau này thêm engine khác, chỉ cần tạo class mới implement interface mà không sửa code cũ.
3. **Liskov Substitution (LSP)**: Mọi implementation của `OmrEngineInterface` đều phải thay thế được cho nhau.
4. **Interface Segregation (ISP)**: Tách các interface nhỏ gọn, tập trung (`MusicXmlReaderInterface`, `MusicXmlWriterInterface`, `MusicXmlValidatorInterface`).
5. **Dependency Inversion (DIP)**: Controller và Service phụ thuộc vào Interface/Abstractions, không phụ thuộc trực tiếp vào concrete class.

---

## 2. PHÂN TẦNG KIẾN TRÚC MVC + CLEAN ARCHITECTURE

### 2.1. Layer 1: HTTP & Controller Layer (`app/Http/Controllers/`)
- **Nhiệm vụ**: Tiếp nhận Request, xác thực bằng FormRequest, gọi Domain Services, trả về Response / DTO / Inertia View.
- **Quy tắc cấm**: Tuyệt đối không viết trực tiếp logic xử lý XML, gọi subprocess OMR hay can thiệp CSDL phức tạp trong Controller.

### 2.2. Layer 2: Domain Services & Use Cases (`app/Services/`)
- `ConversionService`: Điều phối vòng đời chuyển đổi (Upload $\rightarrow$ Preprocess $\rightarrow$ OMR $\rightarrow$ Parse $\rightarrow$ Versioning).
- `AudiverisService`: Quản lý thực thi tiến trình Audiveris CLI, bắt lỗi và đọc file đầu ra `.omr` / `.mxl`.
- `MusicXmlService`: Đọc, parse, trích xuất cấu trúc parts, measures, voices, lyrics, harmonies.
- `LyricService`: Nghiệp vụ cập nhật lời đơn, bulk lyrics, chuyển âm tiết note trước/sau.
- `HarmonyService`: Nghiệp vụ thêm, sửa, xóa hợp âm, parse slash chord (`G/B`), định dạng `<harmony>`.
- `NoteService`: Nghiệp vụ sửa nốt cơ bản (pitch, octave, accidental, duration, dot, voice).
- `ExportService`: Đóng gói MusicXML 3.1 / 4.0 và nén MXL (zip).

### 2.3. Layer 3: Contracts & Adapters (`app/Contracts/`, `app/Adapters/`)
- **Strategy / Adapter Pattern cho OMR**:
  ```php
  namespace App\Contracts;
  
  interface OmrEngineInterface
  {
      public function transcribe(OmrInput $input): OmrResult;
  }
  ```

### 2.4. Layer 4: Data Transfer Objects (`app/DTOs/`)
- Thay vì truyền mảng thô (`array $data`), sử dụng DTOs có kiểu dữ liệu tường minh (Typed properties):
  - `LyricDto`: `part`, `staff`, `measure`, `voice`, `noteId`, `verse`, `text`, `syllabic`, `confidence`.
  - `HarmonyDto`: `part`, `measure`, `beatOffset`, `root`, `accidental`, `kind`, `bass`, `display`.
  - `NoteEditDto`: `noteId`, `pitch`, `octave`, `accidental`, `duration`, `isRest`, `dot`, `voice`.

### 2.5. Layer 5: Worker & Python Subsystem (`workers/`)
- `workers/preprocessing/`: Xử lý ảnh OpenCV (Deskew, Grayscale, Denoise, Binarize).
- `workers/xml_tools/`: Patch MusicXML bằng `lxml` để đảm bảo tốc độ cao và bảo toàn cấu trúc DOM.
- `workers/xml_tools/validator.py`: Dùng `music21` để kiểm tra toàn vẹn thời lượng ô nhịp và cú pháp nhạc lý.

---

## 3. QUY CHUẨN XỬ LÝ LỖI & PHÒNG THỦ (Defensive Programming)

1. **Khử nhiễm lệnh hệ thống (Shell Sanitization)**:
   - Mọi đường dẫn file và tham số truyền cho CLI (Audiveris, Tesseract, Python) phải được kiểm tra hợp lệ, không chứa ký tự nguy hiểm (`escapeshellarg()` trong PHP).
2. **Giới hạn tài nguyên & Timeout**:
   - Mọi tiến trình chạy worker phải có giới hạn thời gian (Timeout 180s) và giới hạn bộ nhớ để tránh treo server.
3. **Phản hồi lỗi thân thiện (Human-friendly Error UI)**:
   - Backend log chi tiết stack trace vào `storage/projects/{uuid}/logs/`.
   - Trả về UI thông điệp dễ hiểu kèm gợi ý khắc phục (ví dụ: *"Ảnh quá mờ hoặc nghiêng, hãy chụp thẳng góc và đủ sáng"*).
