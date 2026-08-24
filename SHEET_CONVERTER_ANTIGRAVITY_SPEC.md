# SHEET CONVERTER — ĐẶC TẢ TÍNH NĂNG PDF/ẢNH → MUSICXML CHO ANTIGRAVITY

**Tên đề xuất:** Sheet Converter  
**Mục tiêu:** Xây dựng một ứng dụng nhỏ, tập trung duy nhất vào việc chuyển PDF/PNG/JPG chứa bản nhạc thành MusicXML, cho phép xem trực tiếp kết quả, theo dõi vị trí lời, sửa lời, thêm/sửa hợp âm và chỉnh một số lỗi ký âm cơ bản trước khi xuất file XML/MXL.

**Golden Reference:**  
`001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml`

---

# 1. PHẠM VI CHÍNH

Ứng dụng chỉ làm tốt quy trình sau:

```text
PDF / PNG / JPG
      ↓
TIỀN XỬ LÝ ẢNH
      ↓
AUDIVERIS OMR
      ↓
MUSICXML THÔ
      ↓
XEM SHEET TRỰC TIẾP
      ↓
SỬA LỜI / HỢP ÂM / NỐT CƠ BẢN
      ↓
VALIDATE
      ↓
XUẤT XML / MUSICXML / MXL
```

Không xây thành DAW.

Không cố thay thế MuseScore.

Không làm Live Sync.

Không làm Playback Studio nâng cao.

Không làm AI đa engine ở bản đầu.

---

# 2. MỤC TIÊU V1

V1 phải hoàn thành được:

- [ ] Upload PDF nhiều trang.
- [ ] Upload PNG/JPG.
- [ ] Chuyển PDF/ảnh thành MusicXML bằng Audiveris.
- [ ] Giữ file `.omr`.
- [ ] Render MusicXML trực tiếp trên web.
- [ ] Hiển thị PDF/ảnh gốc song song với sheet nhận dạng.
- [ ] Click measure/note/lyric để theo dõi vị trí.
- [ ] Sửa lời trực tiếp.
- [ ] Hỗ trợ nhiều câu lời: Verse 1, Verse 2, Verse 3, Verse 4... Verse N.
- [ ] Thêm/sửa/xóa hợp âm.
- [ ] Hỗ trợ slash chord.
- [ ] Sửa pitch/note duration/accidental cơ bản.
- [ ] Validate XML.
- [ ] Xuất `.xml`, `.musicxml`, `.mxl`.
- [ ] File xuất phải tương thích với OSMD/SheetApp.

---

# 3. GOLDEN REFERENCE

File mẫu hiện tại có các đặc điểm:

```text
MusicXML score-partwise
2 parts
16 measures mỗi part
Treble clef
Bass clef
Key: G Major
Time Signature: 3/4
Tempo: 104 BPM
Multiple voices
Chord symbols bằng <harmony>
4 verse lyrics
Lyric gắn trực tiếp vào note
Slurs
Dotted notes
Accidentals
Metadata
```

Antigravity phải dùng file mẫu này làm fixture để test parser/exporter.

Mục tiêu là output mới giữ được các nhóm dữ liệu tương đương.

---

# 4. YÊU CẦU MÁY

## Máy phát triển khuyến nghị

```text
CPU:
Intel Core i5/i7 Gen 10+
hoặc Ryzen 5/7

Cores:
6–8 cores

RAM:
16 GB

Storage:
SSD/NVMe
tối thiểu 50 GB trống

GPU:
Không bắt buộc

OS:
Windows 10/11 64-bit
hoặc Linux 64-bit
```

## Tối thiểu

```text
CPU: 4 cores
RAM: 8 GB
SSD: 20 GB trống
GPU: Không cần
```

## Server khuyến nghị

```text
8 vCPU
16 GB RAM
NVMe SSD
Linux 64-bit
```

Không cần GPU cho V1.

---

# 5. KIẾN TRÚC ĐƠN GIẢN

```text
┌──────────────────────────────┐
│          WEB CLIENT          │
│ Vue 3 + TypeScript           │
│                              │
│ Upload                       │
│ Source Viewer                │
│ OSMD Viewer                  │
│ Lyrics Editor                │
│ Chord Editor                 │
│ Note Quick Edit              │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│        LARAVEL BACKEND       │
│                              │
│ Project                      │
│ Upload                       │
│ Queue                        │
│ Version                      │
│ Export                       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│          OMR WORKER          │
│                              │
│ Audiveris                    │
│ Tesseract vie+eng            │
│ MusicXML Normalize           │
│ MusicXML Validate            │
└──────────────────────────────┘
```

---

# 6. STACK KHUYẾN NGHỊ

## Web

```text
Laravel 12
PHP 8.3+
Vue 3 Composition API
TypeScript
Inertia.js
Tailwind CSS
Vite
MySQL 8+
Laravel Queue
```

## OMR Worker

```text
Java
Audiveris
Tesseract OCR
Vietnamese language pack: vie
English language pack: eng
Python 3.11+
lxml
music21
OpenCV
```

## Frontend Renderer

```text
OpenSheetMusicDisplay (OSMD)
```

---

# 7. OPEN-SOURCE CẦN TẬN DỤNG

## Audiveris

Vai trò chính:

```text
PDF/Image
→ OMR
→ MusicXML
```

Phải tận dụng cho:

- Staff detection.
- Notes.
- Rests.
- Clefs.
- Measures.
- Key signature.
- Time signature.
- Rhythm.
- Text.
- Lyrics.
- Chord names.
- Slurs.
- Voices.

Không tự viết OMR từ đầu.

---

## Tesseract

Cấu hình:

```text
vie+eng
```

Dùng để hỗ trợ:

- lời tiếng Việt;
- tiêu đề;
- tác giả;
- ghi chú;
- chord text;
- metadata.

---

## OSMD

Dùng để:

```text
MusicXML
→ SVG score
→ hiển thị trên browser
```

Không dùng OSMD làm source-of-truth.

---

## music21

Chỉ dùng cho:

- kiểm tra duration;
- phân tích measure;
- kiểm tra pitch/voice;
- validation semantic;
- gợi ý chord optional.

---

## lxml

Dùng để patch MusicXML chính xác.

Không rewrite toàn bộ XML nếu chỉ sửa một lyric/harmony/note.

---

# 8. LUỒNG NGƯỜI DÙNG

```text
1. Người dùng mở app.
2. Kéo PDF hoặc hình vào.
3. Chọn:
   - Nhận dạng lời: ON
   - Ngôn ngữ: Vietnamese + English
   - Nhận dạng hợp âm: ON
4. Bấm Convert.
5. App chạy Audiveris.
6. App tạo MusicXML.
7. App render MusicXML bên phải.
8. PDF/ảnh gốc nằm bên trái.
9. Người dùng kiểm tra:
   - lời;
   - hợp âm;
   - nốt;
   - nhịp.
10. Người dùng sửa trực tiếp.
11. App validate.
12. Người dùng download MusicXML.
```

---

# 9. GIAO DIỆN CHÍNH

```text
┌─────────────────────────┬─────────────────────────┐
│ SOURCE                  │ RECOGNIZED SCORE        │
│                         │                         │
│ PDF / PNG / JPG         │ OSMD                    │
│                         │                         │
│                         │                         │
│                         │                         │
└─────────────────────────┴─────────────────────────┘

┌───────────────────────────────────────────────────┐
│ Lyrics | Chords | Note | Metadata | Issues        │
└───────────────────────────────────────────────────┘
```

Desktop ưu tiên split view 50/50.

Mobile/tablet có thể chuyển tab:

```text
SOURCE
SCORE
EDIT
```

---

# 10. THEO DÕI VỊ TRÍ TRỰC TIẾP

Đây là tính năng bắt buộc.

Khi click một lyric/note ở score:

```text
Score
→ highlight note
→ highlight measure
→ Source Viewer cuộn tới measure tương ứng
```

Khi click một issue:

```text
Issue
→ Score highlight
→ Source highlight vùng tương ứng
```

V1 tối thiểu cần mapping:

```text
page
system
measure
```

Nếu mapping chính xác symbol chưa đủ thì measure-level là bắt buộc.

---

# 11. LYRICS — YÊU CẦU QUAN TRỌNG

File mẫu có 4 verse.

App không được hard-code 4.

Phải hỗ trợ:

```text
Verse 1
Verse 2
Verse 3
Verse 4
...
Verse N
```

---

# 12. LYRIC MODEL

Mỗi lyric phải có:

```text
id
part
staff
measure
voice
note_id
verse
text
syllabic
confidence
```

`syllabic` hỗ trợ:

```text
single
begin
middle
end
```

---

# 13. SỬA LỜI TRỰC TIẾP

Khi click chữ:

```text
Thảnh
```

mở editor:

```text
Verse:   1
Measure: 2
Note:    E4
Text:    [ Thảnh ]
```

Người dùng sửa:

```text
Thánh
```

App patch MusicXML:

```xml
<lyric number="1">
    <syllabic>single</syllabic>
    <text>Thánh</text>
</lyric>
```

Sau đó render lại ngay.

---

# 14. BULK LYRICS EDITOR

Cho phép mở:

```text
VERSE 1
VERSE 2
VERSE 3
VERSE 4
```

và sửa text hàng loạt.

Optional:

```text
Paste Full Lyrics
```

App cố gắng map lại lyric → note.

Không tự commit nếu mapping chưa chắc chắn.

---

# 15. MOVE LYRIC

Phải hỗ trợ:

```text
Move to previous note
Move to next note
```

Cho trường hợp OCR gắn sai âm tiết.

---

# 16. HỢP ÂM

Hợp âm phải lưu đúng trong MusicXML:

```xml
<harmony>
...
</harmony>
```

Không dùng text overlay.

---

# 17. CHORD EDITOR

Khi click trên measure/beat:

```text
[ Add Chord ]
```

Form:

```text
Root:       G
Accidental: #
Quality:    minor
Extension:  7
Bass:       B
Display:    G#m7/B
```

---

# 18. CHORD INPUT

Người dùng được phép nhập nhanh:

```text
G
Am
D7
Em
F#m
Bb
G/B
D/F#
Cmaj7
Cm7
Cm7b5
Cdim
Cdim7
Csus2
Csus4
Cadd9
A7b9
D7#5
```

Parser chuyển thành MusicXML `<harmony>`.

---

# 19. SLASH CHORD

Ví dụ:

```text
G/B
D/F#
C/E
```

phải được lưu với:

```text
root
kind
bass
```

---

# 20. CHORD ANCHOR

Chord không lưu theo pixel.

Phải anchor theo:

```text
part
measure
beatOffset
```

---

# 21. ADD / EDIT / DELETE CHORD

Các thao tác:

```text
Add
Edit
Delete
Move Left
Move Right
```

---

# 22. NOTE QUICK EDIT

Không xây full notation editor.

V1 chỉ cần sửa các lỗi OCR phổ biến.

Khi click note:

```text
Pitch:      G4
Duration:   Quarter
Accidental: Natural
Voice:      1
Dot:        No
```

Có thể sửa:

- Pitch.
- Octave.
- Duration.
- Accidental.
- Rest/Note.
- Dot.
- Voice.

---

# 23. RENDER AFTER EDIT

Quy trình:

```text
Edit
→ Patch MusicXML
→ Validate XML
→ Render OSMD
```

Không reload toàn app.

---

# 24. PROJECT FILES

Mỗi conversion tạo folder:

```text
storage/projects/{uuid}/
```

gồm:

```text
source/
    original.pdf

pages/
    page-001.png

omr/
    source.omr

musicxml/
    raw.musicxml
    current.musicxml
    final.musicxml

logs/
    audiveris.log
    validation.log
```

---

# 25. KHÔNG XÓA `.omr`

Bắt buộc giữ:

```text
source.omr
```

để:

- debug;
- reprocess;
- sửa bằng Audiveris nếu cần;
- cải tiến về sau.

---

# 26. VERSION

Tối thiểu:

```text
RAW
CURRENT
FINAL
```

Không overwrite raw.

---

# 27. DATABASE ĐƠN GIẢN

## conversion_projects

```text
id
uuid
title
status
source_filename
source_type
language
created_at
updated_at
```

## score_versions

```text
id
project_id
type
path
created_at
```

## recognition_issues

```text
id
project_id
part
measure
entity_type
message
severity
status
```

Không cần DB phức tạp hơn trong V1.

---

# 28. STATUS

```text
UPLOADED
PROCESSING
NEEDS_REVIEW
READY
FAILED
```

---

# 29. QUEUE

Audiveris không được chạy trực tiếp trong HTTP request.

Dùng:

```text
ConvertScoreJob
```

Flow:

```text
Upload
→ Save
→ Dispatch Job
→ Worker
→ MusicXML
→ Status update
```

---

# 30. PROCESSING UI

Hiển thị:

```text
Preparing pages      ✓
Recognizing score    65%
Recognizing lyrics   waiting
Creating MusicXML    waiting
Validating           waiting
```

Không chỉ hiển thị spinner.

---

# 31. IMAGE PREPROCESS

Dùng OpenCV.

Hỗ trợ:

- rotate;
- deskew;
- grayscale;
- contrast;
- binarize;
- crop margin;
- denoise;
- basic perspective correction.

---

# 32. SCAN QUALITY

Hiển thị:

```text
GOOD
MEDIUM
POOR
```

Cảnh báo:

```text
Low resolution
Blur
Rotation
Perspective
Shadow
Cut staff
```

---

# 33. VALIDATION

Trước khi export:

```text
XML well-formed
MusicXML parseable
OSMD renderable
```

Kiểm tra thêm:

- measure duration;
- invalid pitch;
- malformed harmony;
- lyric orphan;
- bad voice;
- missing staff.

---

# 34. EXPORT

Nút:

```text
Export MusicXML
```

Options:

```text
.xml
.musicxml
.mxl
```

Output mặc định:

```text
MusicXML 4.0
```

Optional:

```text
MusicXML 3.1 compatibility
```

---

# 35. SHEETAPP COMPATIBILITY

Mọi export phải test:

```text
final.musicxml
→ OSMD
→ SheetApp
```

Nếu OSMD không parse:

```text
không cho đánh dấu READY
```

---

# 36. GOLDEN TEST

Dùng:

```text
001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml
```

Expected:

```text
Title:
HỠI THÁNH VƯƠNG, KÍP NGỰ LAI

Parts:
2

Measures:
16 / part

Key:
G Major

Time:
3/4

Tempo:
104

Lyrics:
4 verses

Harmony:
Present

Clefs:
G + F
```

---

# 37. KHÔNG CẦN FULL ROUND-TRIP PIXEL

Không yêu cầu output giống pixel-by-pixel với Finale.

Yêu cầu:

```text
musical semantics preserved
```

gồm:

```text
Pitch
Duration
Measure
Voice
Lyrics
Harmony
Key
Time
Tempo
```

---

# 38. API CƠ BẢN

## Create

```text
POST /api/conversions
```

## Status

```text
GET /api/conversions/{id}
```

## MusicXML

```text
GET /api/conversions/{id}/musicxml
```

## Update lyric

```text
PATCH /api/conversions/{id}/lyrics/{lyricId}
```

## Update chord

```text
PATCH /api/conversions/{id}/harmonies/{harmonyId}
```

## Update note

```text
PATCH /api/conversions/{id}/notes/{noteId}
```

## Export

```text
POST /api/conversions/{id}/export
```

---

# 39. FRONTEND COMPONENTS

```text
UploadDropzone.vue
ConversionProgress.vue
SourceViewer.vue
ScoreViewer.vue
ScoreToolbar.vue
LyricsPanel.vue
LyricEditor.vue
ChordPanel.vue
ChordEditor.vue
NoteEditor.vue
IssuePanel.vue
ExportDialog.vue
```

---

# 40. BACKEND SERVICES

```text
ConversionService
AudiverisService
ImagePreprocessService
MusicXmlService
MusicXmlValidator
LyricService
HarmonyService
NoteService
ExportService
```

---

# 41. OMR ADAPTER

Tạo interface:

```php
interface OmrEngine
{
    public function transcribe(OmrInput $input): OmrResult;
}
```

Implementation:

```text
AudiverisOmrEngine
```

Không gọi Audiveris trực tiếp từ Controller.

---

# 42. SOURCE OF TRUTH

```text
SOURCE FILE
    immutable

RAW MUSICXML
    immutable

CURRENT MUSICXML
    editable

FINAL MUSICXML
    generated
```

---

# 43. SECURITY

Upload:

- validate MIME;
- validate extension;
- max file size;
- random UUID;
- không dùng filename trực tiếp trong shell;
- escape command arguments;
- timeout worker;
- giới hạn CPU/RAM;
- không cho arbitrary path.

---

# 44. CONFIG

```text
MAX_FILE_SIZE_MB
MAX_PAGES
AUDIVERIS_PATH
TESSDATA_PATH
OMR_TIMEOUT_SECONDS
PROJECT_STORAGE_PATH
```

---

# 45. LOGGING

Ghi:

```text
project_created
file_uploaded
conversion_started
conversion_completed
conversion_failed
lyric_updated
chord_added
chord_updated
note_updated
export_created
```

---

# 46. ERROR UI

Ví dụ:

```text
Không nhận diện được khuông nhạc ở trang 2.

Gợi ý:
- xoay lại trang;
- crop sát bản nhạc;
- dùng ảnh độ phân giải cao hơn;
- tăng contrast.
```

Không hiển thị lỗi kỹ thuật thô cho người dùng.

---

# 47. AUTOSAVE

Sửa lời/hợp âm/nốt:

```text
debounce 1–2 giây
→ save
```

Không save mỗi keystroke.

---

# 48. UNDO / REDO

V1 nên có:

```text
Undo
Redo
```

tối thiểu cho:

- lyric;
- chord;
- note.

---

# 49. KHÔNG LÀM Ở V1

Không làm:

- [ ] WebSocket.
- [ ] Live Band Sync.
- [ ] Roadmap.
- [ ] MIDI.
- [ ] Full notation editor.
- [ ] AI Vision OMR.
- [ ] Batch 100 files.
- [ ] Multi-engine OMR.
- [ ] Training model.
- [ ] User collaboration.
- [ ] DAW.
- [ ] Audio recording.

---

# 50. PHASE 0 — SETUP

Antigravity làm:

- [ ] tạo project;
- [ ] cài dependencies;
- [ ] cấu hình Audiveris;
- [ ] cấu hình Tesseract vie+eng;
- [ ] cấu hình OSMD;
- [ ] health check;
- [ ] storage structure;
- [ ] test golden XML render.

Sau khi pass thì dừng và báo cáo.

---

# 51. PHASE 1 — CONVERSION

Mục tiêu:

```text
PDF/PNG/JPG
→ Audiveris
→ .omr
→ raw.musicxml
```

Checklist:

- [ ] upload;
- [ ] queue;
- [ ] worker;
- [ ] status;
- [ ] logs;
- [ ] raw MusicXML download.

Không làm editor trong phase này.

---

# 52. PHASE 2 — PREVIEW

```text
MusicXML
→ OSMD
→ Browser
```

Checklist:

- [ ] render;
- [ ] zoom;
- [ ] page navigation;
- [ ] measure navigation;
- [ ] original/recognized split view.

---

# 53. PHASE 3 — LYRICS

Checklist:

- [ ] detect lyrics;
- [ ] verse number;
- [ ] Vietnamese;
- [ ] lyric editor;
- [ ] move lyric to note;
- [ ] bulk lyrics editor;
- [ ] render after edit.

Golden test phải giữ được 4 verse.

---

# 54. PHASE 4 — CHORDS

Checklist:

- [ ] parse `<harmony>`;
- [ ] add chord;
- [ ] edit chord;
- [ ] delete chord;
- [ ] slash chord;
- [ ] altered chord;
- [ ] anchor by measure/beat;
- [ ] render after change.

---

# 55. PHASE 5 — NOTE QUICK EDIT

Checklist:

- [ ] pitch;
- [ ] octave;
- [ ] duration;
- [ ] accidental;
- [ ] dot;
- [ ] rest;
- [ ] voice.

Không build full score editor.

---

# 56. PHASE 6 — VALIDATE + EXPORT

Checklist:

- [ ] XML validation;
- [ ] MusicXML validation;
- [ ] OSMD render test;
- [ ] export XML;
- [ ] export MXL;
- [ ] compatibility with SheetApp.

---

# 57. ACCEPTANCE TEST V1

Người dùng phải làm được:

```text
1. Upload một PDF thánh ca.
2. App chuyển thành MusicXML.
3. App hiển thị PDF bên trái.
4. App hiển thị sheet nhận dạng bên phải.
5. Click lyric.
6. Sửa lyric.
7. Click vị trí trên measure.
8. Thêm D7.
9. Click note.
10. Sửa G4 → A4.
11. Validate.
12. Export MusicXML.
13. Mở file đó bằng SheetApp/OSMD thành công.
```

Nếu 13 bước này chạy ổn:

```text
V1 = DONE
```

---

# 58. DEFINITION OF DONE

V1 được xem là hoàn thành khi:

- [ ] PDF/ảnh chuyển thành MusicXML.
- [ ] Có `.omr`.
- [ ] Có raw MusicXML.
- [ ] Sheet render được.
- [ ] Lời nhiều verse sửa được.
- [ ] Hợp âm thêm/sửa được.
- [ ] Nốt cơ bản sửa được.
- [ ] Validate được.
- [ ] Export XML/MXL được.
- [ ] SheetApp đọc được.
- [ ] Golden Reference test pass.

---

# 59. NGUYÊN TẮC QUAN TRỌNG

```text
OMR KHÔNG BAO GIỜ CHÍNH XÁC 100%
```

Do đó sản phẩm phải tối ưu cho:

```text
AUTO CONVERT
+
FAST REVIEW
+
DIRECT CORRECTION
```

không phải:

```text
AUTO CONVERT
+
TRUST EVERYTHING
```

---

# 60. CHỈ THỊ CUỐI CHO ANTIGRAVITY

Bắt đầu đúng thứ tự:

```text
PHASE 0
↓
PHASE 1
↓
PHASE 2
↓
PHASE 3
↓
PHASE 4
↓
PHASE 5
↓
PHASE 6
```

Sau mỗi phase:

```text
CODE
↓
TEST
↓
DOCUMENT
↓
COMMIT
↓
REPORT
↓
STOP
```

Không tự động chuyển sang phase tiếp theo nếu phase hiện tại chưa pass.

---

# 61. KIẾN TRÚC CUỐI CÙNG

```text
             SHEET CONVERTER
                    │
         ┌──────────┴──────────┐
         │                     │
       SOURCE               MUSICXML
     PDF / IMAGE                │
         │                     │
         ▼                     ▼
     AUDIVERIS               OSMD
         │                     │
         └──────────┬──────────┘
                    ▼
               REVIEW UI
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
        LYRICS    CHORDS     NOTES
          │         │         │
          └─────────┼─────────┘
                    ▼
                 VALIDATE
                    │
                    ▼
             XML / MXL EXPORT
                    │
                    ▼
                 SHEETAPP
```

---

# 62. KẾT LUẬN

Không cần xây một hệ thống quá lớn.

Sản phẩm V1 chỉ cần thật mạnh ở một việc:

> **Biến PDF/ảnh bản nhạc thành MusicXML có thể chỉnh sửa nhanh, đặc biệt tối ưu cho lời tiếng Việt và hợp âm, sau đó xuất file chuẩn để SheetApp sử dụng.**

Nếu làm đúng phạm vi này, app đã đủ giá trị thực tế để xử lý số lượng lớn bản Thánh ca mà không cần nhập lại MusicXML bằng tay.
