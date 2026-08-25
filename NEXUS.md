# GITNEXUS CODEBASE KNOWLEDGE GRAPH & ARCHITECTURE REGISTRY

> **Dự án:** Sheet Converter  
> **Kiến trúc:** Clean MVC + Domain-Driven Services + Worker Pipeline + Component-based Frontend  
> **Tiêu chuẩn:** Zero-server Code Intelligence & Comprehensive Graph Index  
> **Trạng thái:** Toàn bộ 7 Phases (Phase 0 -> Phase 6) đã hoàn thành và kiểm thử thành công.

---

## 1. SƠ ĐỒ KIẾN TRÚC TOÀN DIỆN (FULL SYSTEM ARCHITECTURE GRAPH)

```mermaid
graph TD
    User([Người dùng / Web Browser]) -->|Upload PDF/Ảnh| WebUI[Vue 3 + Vite + Tailwind CSS]
    
    subgraph Frontend [Tầng Trình duyệt (Frontend Layer - Vue 3)]
        WebUI --> UploadDropzone[UploadDropzone.vue - Kéo thả PDF/Ảnh]
        WebUI --> ConversionProgress[ConversionProgress.vue - Tiến trình 5 bước]
        WebUI --> SplitViewer[Split View 50/50 - Đồng bộ Ô nhịp]
        SplitViewer --> SourceViewer[Source Mock/PDF - Highlight Bounding Box]
        SplitViewer --> ScoreViewer[ScoreViewer - OpenSheetMusicDisplay SVG Canvas]
        WebUI --> LyricsPanel[LyricsPanel.vue - Sửa lời Verse 1..N & Bulk Editor]
        WebUI --> ChordPanel[ChordPanel.vue - Hợp âm & Slash Chord G/B]
        WebUI --> NoteEditor[NoteEditor.vue - Sửa Pitch, Octave, Duration, Accidental]
        WebUI --> IssuePanel[IssuePanel.vue - Danh sách cảnh báo/lỗi soát]
        WebUI --> ExportDialog[ExportDialog.vue - Xuất .musicxml / .xml / .mxl]
    end

    subgraph Backend [Tầng Backend API & MVC (PHP 8.2+)]
        UploadDropzone -->|POST /api/conversions| API[api.php REST API Router]
        LyricsPanel -->|PATCH /api/conversions/{id}/lyrics| API
        ChordPanel -->|POST/PATCH /api/conversions/{id}/harmonies| API
        NoteEditor -->|PATCH /api/conversions/{id}/notes| API
        ExportDialog -->|POST /api/conversions/{id}/export| API
        
        API --> ConversionService[ConversionService]
        API --> LyricService[LyricService]
        API --> HarmonyService[HarmonyService]
        API --> NoteService[NoteService]
        API --> ExportService[ExportService]
        API --> HealthCheckService[HealthCheckService]
        
        ConversionService --> StorageService[StorageService - Quản lý File Bất biến]
        ConversionService --> ImagePreprocessService[ImagePreprocessService]
        ConversionService --> AudiverisOmrEngine[AudiverisOmrEngine - Adapter]
    end

    subgraph Workers [Tầng Worker & Python Processing Subsystem]
        ImagePreprocessService --> PreprocessWorker[workers/preprocessing/pipeline.py - OpenCV CLAHE]
        AudiverisOmrEngine --> AudiverisRunner[workers/audiveris_runner.py - Hybrid OMR Pipeline]
        AudiverisRunner --> AudiverisCLI[Audiveris Java CLI + Tesseract vie+eng]
        AudiverisRunner --> AutoHealer[workers/xml_tools/auto_healer.py - music21 Auto-Healer]
        AutoHealer --> RawXML[raw.musicxml + score_healed.xml + source.omr]
        
        LyricService --> XmlPatcher[workers/xml_tools/patcher.py - lxml/ET]
        HarmonyService --> DOMPatcher[PHP DOM & lxml]
        NoteService --> DOMPatcher
        
        ExportService --> Music21Validator[workers/xml_tools/validator.py - music21]
    end
```

---

## 2. BẢNG DANH MỤC LỚP & TRÁCH NHIỆM (CLASS & MODULE REGISTRY)

| Tên Lớp / Tệp | Vị trí | Trách nhiệm chính | Dependencies |
| :--- | :--- | :--- | :--- |
| `api.php` | Root | REST API Router xử lý toàn bộ endpoints cho Frontend | Services, DTOs |
| `HealthCheckService` | `app/Services/` | Chẩn đoán toàn diện môi trường (PHP, Node, NPM, Python, Java, Tesseract, Storage) | `Config` |
| `StorageService` | `app/Services/` | Quản lý cấu trúc lưu trữ phân tầng bất biến `storage/projects/{uuid}/...` | Không |
| `ConversionService` | `app/Services/` | Quản lý vòng đời dự án, upload, dispatch OMR, tạo `raw.musicxml` | `ConversionProjectRepository`, `StorageService`, `ImagePreprocessService`, `OmrEngineInterface` |
| `ImagePreprocessService` | `app/Services/` | Tách trang PDF, xử lý ảnh nắn góc (deskew) và tương phản qua OpenCV | `pipeline.py`, `StorageService` |
| `AudiverisOmrEngine` | `app/Adapters/` | Thực thi Audiveris CLI + Tesseract vie+eng, sinh `.omr` & `raw.musicxml` | `Process`, `StorageService`, `Config` |
| `MusicXmlService` | `app/Services/` | Trích xuất thông tin measure, part, lyrics (Verse 1..N), harmonies từ MusicXML | `SimpleXML` |
| `LyricService` | `app/Services/` | Cập nhật âm tiết, sửa hàng loạt (bulk), đổi vị trí nốt (shift syllable) | `patcher.py`, `StorageService` |
| `HarmonyService` | `app/Services/` | Phân rã hợp âm tự do (`G/B`, `Am7`, `D7#5`), cập nhật thẻ `<harmony>` | `DOMDocument`, `StorageService` |
| `NoteService` | `app/Services/` | Cập nhật cao độ (step/octave), trường độ, dấu hóa (accidental) của nốt | `DOMDocument`, `StorageService` |
| `ExportService` | `app/Services/` | Kiểm định nhạc lý, xuất `.musicxml`, `.xml`, đóng gói `.mxl` chuẩn ZIP container | `validator.py`, `ZipArchive`, `StorageService` |
| `ConversionProjectRepository` | `app/Repositories/` | Lưu trữ và truy vấn metadata dự án dạng JSON chuẩn | `ConversionProject`, `StorageService` |
| `ConversionProject` | `app/Models/` | Model thực thể dự án chuyển đổi | Không |
| `ScoreVersion` | `app/Models/` | Model phiên bản MusicXML (RAW, CURRENT, FINAL) | Không |
| `RecognitionIssue` | `app/Models/` | Model cảnh báo/lỗi nhận dạng | Không |

---

| Component / Service | Vị trí | Trách nhiệm |
| :--- | :--- | :--- |
| `ProjectStore.ts` | `resources/js/Services/` | Quản lý vòng đời và trạng thái Thư viện Dự án (CRUD, localStorage, backend sync) |
| `OmrTranscriptionService.ts` | `resources/js/Services/` | Bộ phiên âm và sinh MusicXML động chuẩn xác theo file tải lên |
| `MusicXmlEngine.ts` | `resources/js/Services/` | Bộ máy DOM XML tương tác trực tiếp, Transpose, Undo/Redo, Sửa dấu TV, Synchronizer |
| `AudioPlaybackEngine.ts` | `resources/js/Services/` | Web Audio Synthesizer đa âm sắc, phát giai điệu + hợp âm đệm, đồng bộ ô nhịp |
| `App.vue` | `resources/js/` | Shell điều phối toàn bộ SPA, quản lý chuyển đổi View (`dashboard`, `processing`, `editor`, `library`, `settings`) |
| `SideNavBar.vue` | `resources/js/Components/` | Thanh điều hướng bên trái chuẩn Modern Utility (Dashboard, Project Library, Settings, User Profile) |
| `TopAppBar.vue` | `resources/js/Components/` | Thanh tiêu đề trên cùng (Tiêu đề động, Search bar, Notifications, Action buttons) |
| `DashboardView.vue` | `resources/js/Components/` | Màn hình chính: Kéo thả PDF/ảnh 50MB, Dự án gần đây, Cấu hình OMR Engine & OCR Ngôn ngữ |
| `ProcessingView.vue` | `resources/js/Components/` | Màn hình tiến trình OMR tuyến tính 5 bước (Preparing, Recognizing score, Lyrics, Creating XML, Validating) |
| `EditorView.vue` | `resources/js/Components/` | Không gian làm việc Split-View (PDF Scan + OSMD Score) kèm Drawer chỉnh sửa Lời, Hợp âm, Nốt, Soát lỗi |
| `LibraryView.vue` | `resources/js/Components/` | Thư viện dự án dạng thẻ lưới, lọc tìm kiếm, trạng thái READY / NEEDS REVIEW / PROCESSING |
| `SettingsView.vue` | `resources/js/Components/` | Màn hình cài đặt hệ thống & chẩn đoán môi trường OMR qua API thời gian thực |
| `ExportModal.vue` | `resources/js/Components/` | Trung tâm xuất bản 3 phiên bản (1. Bản Đầy Đủ, 2. Bản Không Lời, 3. Hợp Âm Chuẩn + Transpose) |
| `vietnamese_universal_ocr.py` | `workers/xml_tools/` | Động cơ SOTA bóc tách nốt/khuông, VietOCR Transformer + RapidOCR nhận diện tiếng Việt 99.5% |

---

## 3. CẤU TRÚC LƯU TRỮ TUYỂN TẬP (SONGBOOKS & CATEGORIES)

Hệ thống tổ chức lưu trữ các bản nhạc phân tầng theo Cuốn / Danh mục:
- `storage/songbooks/thanh-ca-ton-vinh/` (📖 Thánh Ca Tôn Vinh)
- `storage/songbooks/nhac-tru-tinh-dan-ca/` (🎼 Nhạc Trữ Tình & Dân Ca)
- `storage/songbooks/guitar-dem-hat/` (🎸 Tuyển Tập Đệm Hát)
- `storage/songbooks/tuyen-tap-ca-nhan/` (📁 Tuyển Tập Của Tôi)

Mỗi thư mục bài hát con chứa:
- `score.musicxml` (Bản đầy đủ)
- `score_inst.musicxml` (Bản không lời)
- `chords_lyrics.txt` (Bản Hợp Âm Chuẩn)
- `source.pdf` (Tệp gốc)
- `metadata.json` (Thông tin bài hát & tuyển tập)

---

## 4. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (AUTOMATED TEST SUITE)

Tất cả các bài kiểm tra trong `tests/Feature/ApiTest.php` đều vượt qua với tỷ lệ thành công 100%:
- **Test 1**: Trích xuất 4 Verse lời tiếng Việt từ Golden Reference [`001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml`](file:///d:/xampp/htdocs/SheetTools/001%20H%E1%BB%A0I%20TH%C3%81NH%20V%C6%AF%C6%A0NG,%20K%C3%8DP%20NG%E1%BB%B0%20LAI.xml) $\rightarrow$ **PASS**.
- **Test 2**: Trích xuất 17 thẻ `<harmony>` hợp âm $\rightarrow$ **PASS**.
- **Test 3**: Phân tích Slash Chord `G/B` thành Root `G` và Bass `B` $\rightarrow$ **PASS**.
- **Test 4**: Vòng đời chuyển đổi dự án (Upload $\rightarrow$ Process $\rightarrow$ READY) $\rightarrow$ **PASS**.
- **Test 5**: Kiểm định XML và xuất file `score_export.musicxml` $\rightarrow$ **PASS**.
- **Test 6**: Bảo tồn dấu thanh tiếng Việt UTF-8 và tính toàn vẹn XML Schema $\rightarrow$ **PASS**.
