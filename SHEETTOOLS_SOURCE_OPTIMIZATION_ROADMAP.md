# SHEETTOOLS — SOURCE AUDIT, OPTIMIZATION & UPGRADE ROADMAP

**Repository:** https://github.com/haiyenpa25/sheettools  
**Branch reviewed:** `main`  
**Review date:** 24/08/2026  
**Purpose:** Nâng source hiện tại từ mức demo/prototype thành công cụ PDF/PNG/JPG → MusicXML đáng tin cậy, có Review Studio để sửa lời, hợp âm và nốt cơ bản trực tiếp.

---

# 1. KẾT LUẬN ĐIỀU HÀNH

Source hiện tại đã có hướng kiến trúc đúng:

```text
app/
├── Adapters
├── Contracts
├── DTOs
├── Models
├── Repositories
└── Services

workers/
├── preprocessing
└── xml_tools
```

Frontend đã có hướng:

```text
Vue
+
OpenSheetMusicDisplay
```

Backend đã chia:

```text
ConversionService
MusicXmlService
LyricService
HarmonyService
NoteService
ExportService
StorageService
ImagePreprocessService
AudiverisOmrEngine
```

Đây là nền tốt và **không cần đập đi viết lại**.

Tuy nhiên source hiện tại có một số đoạn `demo fallback` khiến hệ thống có thể:

> báo `READY` và trả Golden Reference XML ngay cả khi file người dùng chưa được Audiveris convert thật.

Do đó ưu tiên số 1 không phải thêm tính năng mới mà là:

```text
TRUTHFUL CONVERSION PIPELINE
```

Tức là:

```text
SUCCESS = Audiveris thực sự tạo artifact hợp lệ
FAIL    = báo FAIL thật
```

---

# 2. ĐÁNH GIÁ HIỆN TRẠNG

| Hạng mục | Đánh giá |
|---|---:|
| Cấu trúc thư mục / separation | 8/10 |
| Ý tưởng Adapter/Service/DTO | 8/10 |
| Frontend foundation | 7.5/10 |
| MusicXML reading | 7/10 |
| Conversion runtime reliability | 4/10 |
| Multi-page PDF | 2/10 |
| Lyrics editing correctness | 5/10 |
| Chord editing completeness | 5/10 |
| Note editing correctness | 3/10 |
| Export/validation | 5.5/10 |
| Automated tests | 4/10 |
| Production readiness | 4/10 |

Sau khi hoàn thành P0 + P1:

```text
mục tiêu reliability ≈ 8/10
```

Sau P2 + P3:

```text
mục tiêu production utility ≈ 9/10
```

---

# 3. NGUYÊN TẮC NÂNG CẤP

Antigravity phải tuân thủ:

1. Không viết lại toàn repo.
2. Không thay stack nếu không cần.
3. Không thêm tính năng trước khi conversion thật đáng tin.
4. Không dùng Golden Reference trong runtime.
5. Golden Reference chỉ thuộc test fixtures.
6. Không cho project `READY` nếu artifact thật không tồn tại.
7. Raw artifact là immutable.
8. User edits phải tác động lên `current.musicxml`.
9. Export chỉ từ file đã validate.
10. Mỗi entity âm nhạc phải có stable locator.
11. Không xác định note/lyric bằng pixel.
12. Không xác định note đơn giản bằng `item(0)`.
13. Không hard-code P1, staff 1, voice 1 nếu API đã truyền thông tin.
14. PDF nhiều trang phải giữ đầy đủ tất cả trang.
15. Long-running OMR không chạy trong HTTP request.
16. Mọi error phải fail loudly, không silently fallback.
17. Sau mỗi phase: test → report → commit → stop.

---

# 4. P0 — FIX DATA INTEGRITY / REMOVE FAKE SUCCESS

**Priority:** CRITICAL

Không làm tính năng mới trước khi P0 pass.

## P0.1 — XÓA GOLDEN REFERENCE FALLBACK KHỎI RUNTIME

### Hiện trạng

`app/Services/ConversionService.php`:

```text
Nếu raw MusicXML không tồn tại
→ lấy file:
001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml
→ save thành raw XML
→ project READY
```

`api.php` cũng có các fallback tương tự:

```text
project không tồn tại
→ tạo mock READY project

MusicXML không tồn tại
→ trả Golden Reference

Lyrics không có current XML
→ đọc Golden Reference

Harmonies không có current XML
→ đọc Golden Reference
```

### Nguy cơ

User upload:

```text
abc.pdf
```

Audiveris thất bại nhưng UI có thể hiện:

```text
HỠI THÁNH VƯƠNG, KÍP NGỰ LAI
```

và user hiểu nhầm convert thành công.

### Bắt buộc sửa

Các file:

```text
app/Services/ConversionService.php
api.php
tests/Feature/ApiTest.php
```

Runtime:

```text
artifact missing
→ throw ConversionArtifactMissingException
→ project status FAILED
```

API project không tồn tại:

```http
404 PROJECT_NOT_FOUND
```

MusicXML chưa tồn tại:

```http
409 MUSICXML_NOT_READY
```

Không được trả fixture.

### Golden file mới

Move:

```text
001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml
```

sang:

```text
tests/fixtures/golden_hymn.musicxml
```

### Acceptance

- [ ] Upload invalid PDF không thể status READY.
- [ ] UUID không tồn tại trả 404.
- [ ] Project chưa có XML trả 409/404 phù hợp.
- [ ] Golden XML không được tham chiếu từ runtime.
- [ ] Search source runtime không còn string tên Golden file.

---

## P0.2 — AUDIVERIS RESULT PHẢI KIỂM TRA ARTIFACT THẬT

### Hiện trạng

`app/Adapters/AudiverisOmrEngine.php` hiện:

```text
exec Audiveris
→ exitCode == 0
→ return success
→ trả rawMusicXmlPath/omrFilePath đã tính trước
```

Nhưng chưa thấy bước bắt buộc:

```text
scan Audiveris output
→ tìm artifact thật
→ kiểm tra file
→ copy/rename canonical
```

### Cần thiết kế

Sau khi Audiveris chạy:

```text
outDir/
  ...
```

phải:

```text
1. Recursively scan output directory.
2. Find *.omr
3. Find *.mxl / *.musicxml / *.xml
4. Xác định đúng score output.
5. Check filesize > minimum.
6. Try parse XML/MXL.
7. Only then mark success.
```

### Canonical artifacts

```text
storage/projects/{uuid}/omr/source.omr
storage/projects/{uuid}/musicxml/raw.musicxml
```

Nếu output là `.mxl`:

```text
unpack
→ extract MusicXML
→ save raw.musicxml
→ retain original .mxl nếu cần
```

### Result contract đề nghị

```php
class OmrResultDto
{
    public bool $success;
    public ?string $musicXmlPath;
    public ?string $omrPath;
    public array $generatedArtifacts;
    public int $exitCode;
    public string $logs;
    public array $warnings;
}
```

### Success condition

Không dùng duy nhất:

```text
exitCode == 0
```

Mà:

```text
exitCode == 0
AND
valid MusicXML exists
```

### Acceptance

- [ ] Audiveris exit 0 nhưng không có XML → FAIL.
- [ ] Audiveris có XML invalid → FAIL/NEEDS_REVIEW.
- [ ] Audiveris có `.omr` → copy canonical.
- [ ] Audiveris có XML valid → raw.musicxml tồn tại.
- [ ] Logs giữ command, exit code, artifact list.

---

## P0.3 — PROCESSPROJECT PHẢI DÙNG `OmrResult`

### Hiện trạng

`ConversionService` gọi:

```php
$result = $this->omrEngine->transcribe($dto);
```

nhưng sau đó logic chưa bắt buộc kiểm tra:

```text
$result success
artifact exists
```

### Sửa

Pseudo flow:

```php
$result = $omrEngine->transcribe($dto);

if (!$result->success) {
    throw new OmrFailedException(...);
}

if (!$result->musicXmlPath || !file_exists(...)) {
    throw new ConversionArtifactMissingException(...);
}

$storage->importRawMusicXml(...);
$storage->importOmr(...);

$validator->assertParseable(rawXml);

create current.musicxml from raw;
status = NEEDS_REVIEW;
```

### Không nên

```text
READY ngay sau OMR
```

Nên:

```text
UPLOADED
PROCESSING
NEEDS_REVIEW
READY
FAILED
```

`READY` chỉ sau user review/validation hoặc khi system policy cho phép.

---

# 5. P0 — TESTS PHẢI NGĂN FALSE POSITIVE

## P0.4 — VIẾT LẠI `ApiTest.php`

### Hiện trạng nguy hiểm

Test hiện:

```text
temp file = "Dummy sheet content"
filename  = test_hymn.pdf
processProject()
assert status == READY
```

Đây không phải integration test.

Nó pass nhờ Golden fallback.

### Tách thành 4 nhóm

```text
tests/
├── Unit/
├── Integration/
├── Golden/
└── Failure/
```

### Unit

Không gọi Audiveris:

```text
MusicXmlServiceTest
HarmonyParserTest
LyricLocatorTest
NoteLocatorTest
MusicXmlValidatorTest
StorageServiceTest
```

### Integration

Dùng PDF/PNG thật:

```text
tests/fixtures/hymn_one_page.png
tests/fixtures/hymn_two_pages.pdf
```

Expected:

```text
real Audiveris
→ real artifact
→ parseable XML
```

Nếu môi trường CI không có Audiveris:

```text
tag/group integration
```

và skip rõ ràng.

### Failure tests

```text
invalid.pdf
blank.png
corrupt.xml
```

Expected:

```text
FAILED
```

### Golden tests

Golden file dùng để:

```text
test parser
test extract lyrics
test harmony
test semantic exporter
```

Không dùng làm runtime conversion fallback.

---

# 6. P1 — MULTI-PAGE PDF THẬT

**Priority:** CRITICAL

## P1.1 — SỬA `extractPdfPages()`

### Hiện trạng

`ImagePreprocessService` hiện Python inline:

```python
doc.load_page(0)
```

=> chỉ trang đầu.

### Phải đổi

Không dùng Python `-c` dài trong PHP.

Tạo:

```text
workers/preprocessing/extract_pdf.py
```

Input:

```text
--input
--output-dir
--dpi
```

Output:

```text
page-001.png
page-002.png
page-003.png
...
```

JSON stdout:

```json
{
  "success": true,
  "pages": [
    ".../page-001.png",
    ".../page-002.png"
  ]
}
```

### Rendering

PyMuPDF:

```python
matrix = fitz.Matrix(scale, scale)
```

Mục tiêu tương đương:

```text
300–400 DPI
```

### Acceptance

- [ ] 1-page PDF → 1 PNG.
- [ ] 5-page PDF → 5 PNG.
- [ ] thứ tự trang đúng.
- [ ] page count được lưu project.
- [ ] không tạo white PNG giả khi extract fail.

### Quan trọng

Hiện code có fallback:

```text
nếu extract fail
→ tạo ảnh trắng
```

Bỏ fallback này.

Nếu extract fail:

```text
throw PdfExtractionException
```

Không feed ảnh trắng vào Audiveris.

---

## P1.2 — KHÔNG CHỈ TRUYỀN `$pages[0]`

Hiện:

```php
sourceFilePath: $pages[0] ?? $sourcePath
```

Phải thay bằng một trong hai cách:

### Option A — tốt nhất

Nếu Audiveris hỗ trợ input PDF trực tiếp ổn:

```text
Original PDF
→ Audiveris book
```

Pages preprocess chỉ dùng preview/quality.

### Option B

Nếu muốn preprocess:

```text
all preprocessed pages
→ build input sequence/book
→ Audiveris
```

`ConversionInputDto` nên hỗ trợ:

```php
public array $pagePaths;
public string $originalSourcePath;
```

Không chỉ:

```text
sourceFilePath
```

---

# 7. P1 — PREPROCESSING THẬT SỰ HỮU ÍCH CHO OMR

## P1.3 — NÂNG `pipeline.py`

Pipeline đề nghị:

```text
LOAD
↓
ORIENTATION
↓
DESKEW
↓
PERSPECTIVE CHECK
↓
GRAYSCALE
↓
LIGHT DENOISE
↓
CLAHE
↓
OPTIONAL BINARIZATION
↓
QUALITY METRICS
↓
SAVE
```

### Deskew

Staff line là tín hiệu mạnh.

Có thể dùng:

```text
Canny
HoughLinesP
median horizontal angle
```

Không deskew nếu confidence thấp.

### Không preprocess quá mức

OMR đôi khi nhận bản original tốt hơn threshold image.

Do đó mỗi page giữ:

```text
original.png
enhanced.png
```

### P1 lựa chọn đơn giản

Cho config:

```text
PREPROCESS_MODE:
off
safe
strong
```

Default:

```text
safe
```

### Acceptance

- [ ] Ảnh thẳng không bị xoay sai.
- [ ] Ảnh nghiêng 2–5° được sửa.
- [ ] Không làm mất staff line.
- [ ] Original luôn được giữ.
- [ ] Worker trả quality metrics.

---

# 8. P1 — JOB ASYNC / KHÔNG BLOCK HTTP

## P1.4 — BỎ `processProject()` KHỎI POST REQUEST

Hiện `api.php`:

```text
POST conversion
→ createProject
→ processProject
→ mới response
```

Audiveris là long-running process.

### Target

```text
POST /api/conversions
      ↓
save project UPLOADED
      ↓
enqueue
      ↓
response 202
```

Response:

```json
{
  "data": {
    "uuid": "...",
    "status": "UPLOADED"
  }
}
```

Worker:

```text
php worker.php
```

hoặc DB queue nhỏ.

Vì app nhỏ, chưa bắt buộc Laravel/Horizon.

### Minimal queue design

SQLite/MySQL:

```text
conversion_jobs
id
project_uuid
status
attempts
available_at
reserved_at
started_at
finished_at
error
```

Worker loop:

```text
reserve
→ process
→ ack/fail
```

### Status polling

Frontend:

```text
GET /api/conversions/{uuid}
```

1–2 giây/lần.

### Acceptance

- [ ] Upload response không chờ Audiveris.
- [ ] Refresh browser không mất job.
- [ ] Worker restart không làm READY giả.
- [ ] Failed job có log.
- [ ] Retry configurable.

---

# 9. P1 — API / PROJECT STATE

## P1.5 — STATE MACHINE CHÍNH THỨC

```text
UPLOADED
  ↓
QUEUED
  ↓
PREPROCESSING
  ↓
OMR_RUNNING
  ↓
NORMALIZING
  ↓
VALIDATING
  ↓
NEEDS_REVIEW
  ↓
READY

bất kỳ step:
  ↓
FAILED
```

### Project fields

```text
status
progress
current_step
error_code
error_message
started_at
finished_at
page_count
```

### Không dùng progress giả

Progress theo stage:

```text
Queued             5
Preprocess         10–25
OMR                25–75
Normalize          75–85
Validate           85–95
Needs Review       100
```

Không giả % bên trong Audiveris nếu engine không cung cấp.

---

# 10. P1 — COMPOSER / AUTOLOAD / CONFIG

## P1.6 — BỎ `require_once` HÀNG LOẠT

Tạo:

```text
composer.json
```

Ví dụ:

```json
{
  "autoload": {
    "psr-4": {
      "App\\": "app/"
    }
  }
}
```

Sau đó:

```php
require __DIR__.'/vendor/autoload.php';
```

### Lợi ích

- sạch dependency;
- dễ unit test;
- Antigravity dễ refactor;
- IDE tốt;
- giảm lỗi require order.

## P1.7 — ENV CONFIG

Tạo `.env.example`:

```text
APP_ENV=local
APP_DEBUG=true

STORAGE_PATH=
PYTHON_BIN=python
JAVA_BIN=java
AUDIVERIS_JAR=
TESSDATA_PREFIX=

MAX_UPLOAD_MB=50
MAX_PAGES=50
OMR_TIMEOUT=300
QUEUE_DRIVER=database
```

---

# 11. P2 — STABLE MUSIC ENTITY LOCATOR

**Priority:** HIGH

## P2.1 — VẤN ĐỀ

MusicXML không có `id` ổn định cho mọi note.

Hiện API gửi:

```text
noteId
```

nhưng `NoteService` vẫn:

```php
$targetNote = $notes->item(0);
```

=> luôn nốt đầu measure.

Lyric cũng chưa map ổn định.

### Phải tạo locator

Internal locator:

```json
{
  "partId": "P1",
  "measure": "5",
  "staff": 1,
  "voice": "1",
  "noteOrdinal": 3,
  "chordOrdinal": 0
}
```

Canonical string:

```text
P1:M5:S1:V1:N3
```

Đối với harmony:

```text
P1:M5:H2
```

Đối với lyric:

```text
P1:M5:S1:V1:N3:L4
```

### MusicXmlIndexService

Tạo:

```text
app/Services/MusicXmlIndexService.php
```

Responsibilities:

```text
parse XML
build index
generate locators
resolve locator → DOMElement
```

Mọi service edit phải dùng chung.

---

# 12. P2 — NOTE EDIT CORRECTNESS

## P2.2 — SỬA `NoteService`

Không:

```text
measure → first note
```

Mà:

```text
locator → exact DOM note
```

### Pitch

Nếu nhập:

```text
F#
```

phải đồng bộ:

```xml
<pitch>
  <step>F</step>
  <alter>1</alter>
  <octave>4</octave>
</pitch>
<accidental>sharp</accidental>
```

### Nếu đổi về natural

Phải remove/update `<alter>`, không chỉ đổi `<accidental>`.

### Duration

MusicXML có:

```text
<duration>
```

và:

```text
<type>
```

Không được chỉ đổi `<type>`.

Cần biết:

```text
<divisions>
```

Ví dụ divisions = 2:

```text
quarter = 2
half = 4
eighth = 1
```

Dotted:

```text
quarter dot = 3
```

### Rhythm integrity

Sau edit:

```text
run MeasureDurationValidator
```

Nếu vượt measure:

```text
reject
```

hoặc warning + explicit force.

---

# 13. P2 — LYRICS MAPPING

## P2.3 — SỬA `LyricService`

### Vấn đề bulkUpdate

Hiện logic:

```text
lyricsList index 0
→ measure 1

index 1
→ measure 2
```

Đây là sai mô hình.

Một measure có nhiều syllables.

### Target

Lấy toàn bộ **lyric-capable note sequence**:

```text
P1:
note 1
note 2
note 3
...
```

theo:

```text
measure order
voice
staff
musical time
```

Bulk lyric map dựa trên sequence này.

### API bulk payload tốt hơn

```json
{
  "partId": "P1",
  "verse": 2,
  "tokens": [
    {
      "locator": "P1:M1:S1:V1:N1",
      "text": "Cúi",
      "syllabic": "single"
    }
  ]
}
```

### Fast bulk paste

Input:

```text
Cúi xin Vua Thánh ngự lai...
```

System:

```text
tokenize
→ suggest alignment
→ preview
→ user Apply
```

Không auto commit nếu count mismatch.

---

# 14. P2 — HARMONY / CHORD ENGINE

## P2.4 — NÂNG `HarmonyService`

Hiện parser đã có:

```text
major
minor
minor-seventh
dominant
major-seventh
diminished
suspended-fourth
slash bass
```

Cần mở rộng.

### Chord grammar

```text
Major
Minor
5
6
m6
7
maj7
m7
mMaj7
dim
dim7
m7b5
aug
sus2
sus4
add9
9
maj9
m9
11
13
```

### Alterations

```text
b5
#5
b9
#9
#11
b13
```

### Refactor

Tạo:

```text
ChordParser
HarmonyXmlWriter
HarmonyService
```

---

# 15. P2 — VALIDATE AFTER EVERY EDIT

Sau lyric edit:

```text
XML parse
```

Sau harmony edit:

```text
XML parse + harmony semantic
```

Sau note edit:

```text
XML parse + measure duration
```

Nếu fail:

```text
do not overwrite current.musicxml
```

### Atomic write

```text
current.tmp
→ validate
→ rename current.musicxml
```

---

# 16. P2 — API CLEANUP

Hiện API nằm trong một file lớn.

Không nhất thiết chuyển Laravel.

Nhưng tách:

```text
public/index.php
app/Http/Router.php
app/Http/Controllers/
```

Controllers:

```text
ConversionController
LyricController
HarmonyController
NoteController
ExportController
```

Controller chỉ:

```text
validate request
call service
return response
```

---

# 17. P2 — API RESPONSE STANDARD

Success:

```json
{
  "ok": true,
  "data": {},
  "meta": {}
}
```

Error:

```json
{
  "ok": false,
  "error": {
    "code": "MUSICXML_NOT_READY",
    "message": "MusicXML has not been generated yet",
    "details": {}
  }
}
```

Status codes:

```text
200 GET success
201 create
202 queued
400 invalid request
404 project/entity not found
409 project state conflict
422 invalid music edit
500 unexpected internal
503 Audiveris unavailable
```

---

# 18. P3 — OMR QUALITY IMPROVEMENTS

Sau P0–P2.

## P3.1 — ORIGINAL VS ENHANCED TRY

Không nhất thiết chạy Audiveris 2 lần mọi file.

Rule:

```text
quality good
→ original

quality poor/rotated
→ enhanced

OMR fails original
→ retry enhanced
```

## P3.2 — OCR LANGUAGE PROFILE

Default:

```text
vie+eng
```

Health check phải báo:

```text
vie installed?
eng installed?
```

---

# 19. P3 — REVIEW STUDIO UX

Layout:

```text
┌─────────────────────┬─────────────────────┐
│ Original PDF/Image  │ OSMD MusicXML       │
└─────────────────────┴─────────────────────┘
```

Side panel:

```text
Lyrics
Chords
Notes
Issues
Metadata
```

Click measure:

```text
score measure 7
→ source page + approximate region
```

Nếu chưa có bounding box exact thì chỉ làm measure-level sync.

---

# 20. P3 — EXPORT GATE

Hiện ExportService copy `.xml`/`.musicxml` trực tiếp.

`export()` phải:

```text
validateProject()
```

Nếu errors:

```text
throw ExportValidationException
```

Không export.

### `.xml` vs `.musicxml`

Đây chỉ là extension nếu content cùng MusicXML version.

Không claim version conversion nếu chưa implement transformer.

### MXL

Kiểm tra `META-INF/container.xml` theo MusicXML compressed container spec trước khi phát hành.

---

# 21. P3 — REVISION / OPTIMISTIC LOCK

Nếu mở 2 tab, cần chống overwrite.

Thêm:

```text
revision integer
```

Mỗi edit gửi revision.

Server mismatch:

```text
409 EDIT_CONFLICT
```

---

# 22. P3 — STORAGE ROBUSTNESS

Project:

```text
source/
pages/
omr/
musicxml/
logs/
export/
```

Internal source path:

```text
source/original.pdf
```

Tên gốc lưu metadata.

Lưu:

```text
SHA-256
```

cho source.

---

# 23. P3 — HEALTH CHECK

Health response nên có:

```json
{
  "php": true,
  "storageWritable": true,
  "python": true,
  "java": true,
  "audiveris": true,
  "tesseract": {
    "available": true,
    "languages": ["vie", "eng"]
  },
  "opencv": true,
  "pymupdf": true,
  "zip": true
}
```

---

# 24. CI/CD

GitHub Actions:

```text
PHP syntax
PHP unit tests
Python tests
npm build
TypeScript check
```

Integration OMR có thể dùng runner riêng/container có Audiveris.

---

# 25. SOURCE STRUCTURE ĐỀ NGHỊ

```text
sheettools/
├── app/
│   ├── Adapters/
│   ├── Contracts/
│   ├── DTOs/
│   ├── Exceptions/
│   ├── Http/
│   │   ├── Controllers/
│   │   └── Router.php
│   ├── Models/
│   ├── Repositories/
│   └── Services/
│       ├── ConversionService.php
│       ├── ImagePreprocessService.php
│       ├── MusicXmlService.php
│       ├── MusicXmlIndexService.php
│       ├── LyricService.php
│       ├── ChordParser.php
│       ├── HarmonyXmlWriter.php
│       ├── HarmonyService.php
│       ├── NoteService.php
│       ├── ExportService.php
│       └── StorageService.php
├── workers/
│   ├── preprocessing/
│   │   ├── extract_pdf.py
│   │   └── pipeline.py
│   └── xml_tools/
├── tests/
│   ├── fixtures/
│   ├── Unit/
│   ├── Integration/
│   ├── Failure/
│   └── Golden/
├── composer.json
├── .env.example
└── public/
    └── index.php
```

---

# 26. CONVERSION PIPELINE TARGET

```text
UPLOAD
 │
 ▼
VALIDATE FILE
 │
 ▼
SAVE IMMUTABLE SOURCE
 │
 ▼
QUEUE
 │
 ▼
PDF PAGE EXTRACTION
 │
 ▼
SAFE PREPROCESS
 │
 ▼
AUDIVERIS
 │
 ▼
DISCOVER REAL ARTIFACTS
 │
 ▼
IMPORT .OMR + RAW MUSICXML
 │
 ▼
XML VALIDATE
 │
 ▼
COPY RAW → CURRENT
 │
 ▼
MUSIC SEMANTIC VALIDATE
 │
 ▼
NEEDS_REVIEW
 │
 ▼
USER EDIT
 │
 ▼
FINAL VALIDATE
 │
 ▼
READY
 │
 ▼
EXPORT
```

---

# 27. EDIT PIPELINE TARGET

```text
USER CLICK
 │
 ▼
ENTITY LOCATOR
 │
 ▼
PATCH REQUEST + REVISION
 │
 ▼
RESOLVE EXACT DOM NODE
 │
 ▼
PATCH TEMP XML
 │
 ▼
VALIDATE
 │
 ├── fail → discard temp
 │
 └── pass
       ↓
  atomic replace
       ↓
 revision + 1
       ↓
 frontend rerender
```

---

# 28. SPECIFIC FILE CHANGE MAP

## `api.php`

Remove:

- Golden fixture fallback.
- mock project creation.
- synchronous OMR.

Add:

- standard errors;
- async create;
- controller/router;
- revision support;
- strict validation.

## `app/Services/ConversionService.php`

Remove:

```text
Golden fallback
READY regardless OMR result
$pages[0] assumption
```

Add:

```text
result verification
real artifact import
state machine
validation
queue-safe behavior
```

## `app/Adapters/AudiverisOmrEngine.php`

Add:

```text
artifact discovery
artifact verification
timeout
structured process result
version logging
```

## `app/Services/ImagePreprocessService.php`

Remove:

```text
page 0 only
blank white image fallback
inline long python command
```

Add:

```text
all pages
worker JSON result
DPI
quality
error handling
```

## `workers/preprocessing/pipeline.py`

Improve:

```text
deskew
orientation
quality metrics
configurable threshold
structured JSON
```

## `app/Services/LyricService.php`

Remove:

```text
bulk lyric index → measure index
```

Add:

```text
stable locator
note sequence
preview alignment
atomic patch
```

## `app/Services/HarmonyService.php`

Refactor:

```text
ChordParser
HarmonyXmlWriter
```

Add full chord grammar.

## `app/Services/NoteService.php`

Remove:

```php
$targetNote = $notes->item(0);
```

Add:

```text
stable locator
duration math
pitch alter handling
dot/rest/voice
measure validation
atomic patch
```

## `app/Services/ExportService.php`

Add:

```text
validation gate
correct MXL package
export metadata
```

## `tests/Feature/ApiTest.php`

Split:

```text
Unit
Integration
Failure
Golden
```

Remove dummy READY false-positive.

---

# 29. P0 ACCEPTANCE GATE

Không sang P1 cho tới khi:

- [ ] Runtime không còn Golden fallback.
- [ ] Invalid PDF → FAILED.
- [ ] Missing artifact → FAILED.
- [ ] API UUID không tồn tại → 404.
- [ ] Audiveris result được verify.
- [ ] Tests không có dummy READY false-positive.

---

# 30. P1 ACCEPTANCE GATE

- [ ] PDF 5 trang → đủ 5 pages.
- [ ] Upload request không block OMR.
- [ ] Audiveris tạo MusicXML thật.
- [ ] `.omr` được lưu.
- [ ] current.musicxml được tạo từ raw.
- [ ] project → NEEDS_REVIEW.
- [ ] OSMD mở được output thực.

---

# 31. P2 ACCEPTANCE GATE

### Lyrics

- [ ] Click đúng lyric → đúng note.
- [ ] Verse 1–4 không lẫn.
- [ ] Bulk lyrics không map theo measure giả.
- [ ] sửa tiếng Việt giữ dấu.

### Chords

- [ ] G/B.
- [ ] F#m7.
- [ ] Bb/D.
- [ ] Cmaj7.
- [ ] Bm7b5.
- [ ] A7b9.
- [ ] D7#5.
- [ ] XML parse được.

### Notes

- [ ] Click nốt thứ 3 → sửa nốt thứ 3.
- [ ] F → F# tạo alter đúng.
- [ ] F# → F natural xóa alter đúng.
- [ ] quarter → half cập nhật duration đúng.
- [ ] invalid rhythm bị reject/warn.

---

# 32. P3 ACCEPTANCE GATE

- [ ] Source/Score split view ổn.
- [ ] measure navigation đúng.
- [ ] edit history/undo.
- [ ] revision conflict protection.
- [ ] export blocked nếu invalid.
- [ ] MXL mở được.
- [ ] OSMD automated render test pass.
- [ ] health check đủ dependencies.

---

# 33. NHỮNG THỨ CHƯA NÊN LÀM

Cho đến khi P0–P2 ổn:

- [ ] AI Vision OMR.
- [ ] LLM tự sửa nốt.
- [ ] PaddleOCR multi-engine.
- [ ] homr fallback.
- [ ] full notation editor.
- [ ] playback DAW.
- [ ] WebSocket.
- [ ] collaboration.
- [ ] user accounts phức tạp.
- [ ] batch hàng trăm file.
- [ ] microservices phức tạp.
- [ ] Redis nếu queue nhỏ chưa cần.

---

# 34. QUICK WINS / COMMIT ORDER

```text
Commit 1  Remove runtime Golden fallback
Commit 2  Verify Audiveris artifacts
Commit 3  Fix project/API failure states
Commit 4  Move golden XML to tests/fixtures
Commit 5  Replace dummy READY test
Commit 6  Extract all PDF pages
Commit 7  Async conversion job
Commit 8  Stable MusicXML locator/index
Commit 9  Fix exact note editing
Commit 10 Fix lyric mapping
Commit 11 Expand chord parser
Commit 12 Validation-gated export
```

---

# 35. DEFINITION OF DONE — CORE APP

App đạt mục tiêu khi:

```text
PDF / PNG / JPG
        ↓
Audiveris thật
        ↓
MusicXML thật
        ↓
OSMD render
        ↓
Sửa lời đúng note
        ↓
Thêm/sửa harmony đúng measure/beat
        ↓
Sửa exact note
        ↓
Validate
        ↓
Export
```

và:

- [ ] Không có false success.
- [ ] Không có Golden runtime fallback.
- [ ] PDF multi-page đầy đủ.
- [ ] Jobs không block HTTP.
- [ ] Lời tiếng Việt giữ đúng Unicode.
- [ ] Multiple verses hoạt động.
- [ ] Chord parser đủ dùng.
- [ ] Note edit không làm hỏng rhythm.
- [ ] Invalid XML không export.
- [ ] SheetApp/OSMD đọc được final output.

---

# 36. MỤC TIÊU CHẤT LƯỢNG

Không đặt mục tiêu:

> OMR chính xác 100%.

Đặt mục tiêu:

> Conversion trung thực + review nhanh + correction chính xác.

```text
OMR làm phần lớn công việc
↓
User chỉ sửa vùng sai
↓
App đảm bảo XML không hỏng
```

---

# 37. MỆNH LỆNH CHO ANTIGRAVITY

Làm theo thứ tự:

```text
P0
DATA INTEGRITY
↓
P1
REAL CONVERSION + MULTI-PAGE + ASYNC
↓
P2
CORRECT MUSIC EDITING
↓
P3
UX + PERFORMANCE + PRODUCTION HARDENING
```

Sau mỗi phase phải báo:

```text
1. Files changed
2. Behavior changed
3. Tests added/changed
4. Test result
5. Known limitations
6. Architecture decisions
```

Sau đó STOP.

---

# 38. P0 TASK PROMPT CHO ANTIGRAVITY

```text
Review SHEETTOOLS_SOURCE_OPTIMIZATION_ROADMAP.md.

Implement P0 only.

Objectives:
1. Remove every runtime Golden Reference/mock fallback.
2. A conversion must be successful only if Audiveris produced a real, valid MusicXML artifact.
3. Missing project must return 404.
4. Missing/unready MusicXML must not return fixture data.
5. Invalid/dummy source must fail, not become READY.
6. Move Golden Reference into tests/fixtures and use only for parser/semantic tests.
7. Improve AudiverisOmrEngine to discover and verify actual generated artifacts.
8. ConversionService must inspect OmrResult and set FAILED correctly.
9. Rewrite false-positive tests.
10. Do not implement P1/P2/P3.

Constraints:
- Preserve existing architecture where reasonable.
- No full rewrite.
- No new unrelated features.
- Maintain clean Adapter/Service/DTO separation.
- Add exceptions/error codes where needed.
- Run tests before declaring P0 complete.

At completion provide:
- files changed;
- exact old vs new behavior;
- tests;
- test results;
- remaining limitations;
then STOP.
```

---

# 39. FINAL ARCHITECTURE GOAL

```text
                  SHEETTOOLS
                      │
        ┌─────────────┴─────────────┐
        │                           │
      IMPORT                      REVIEW
        │                           │
 PDF / Image                  OSMD + Source
        │                           │
        ▼                 ┌─────────┼────────┐
 PREPROCESS               ▼         ▼        ▼
        │               Lyrics    Chords    Notes
        ▼                 │         │        │
   AUDIVERIS              └─────────┼────────┘
        │                           │
        ▼                           ▼
  REAL ARTIFACTS              ATOMIC PATCH
 .omr + raw.xml                    │
        │                           ▼
        ▼                      VALIDATION
   VALIDATION                      │
        │                           ▼
        └───────────────→ current.musicxml
                                    │
                                    ▼
                                  READY
                                    │
                                    ▼
                              XML / MXL EXPORT
```

---

# 40. KẾT LUẬN

Source hiện tại **không cần viết lại**.

Điều quan trọng nhất là chuyển nó từ:

```text
prototype nhìn có vẻ chạy
```

sang:

```text
pipeline trung thực và có thể tin cậy
```

Ưu tiên tuyệt đối:

```text
1. Remove fake success.
2. Get real Audiveris output.
3. Support all PDF pages.
4. Async conversion.
5. Stable entity addressing.
6. Correct lyric/chord/note editing.
7. Validation-gated export.
8. UX optimization afterward.
```

Nếu làm đúng thứ tự này, source hiện tại có thể trở thành công cụ rất thực dụng để:

> **PDF/ảnh bản nhạc → MusicXML → review/sửa lời & hợp âm → xuất thẳng sang SheetApp.**
