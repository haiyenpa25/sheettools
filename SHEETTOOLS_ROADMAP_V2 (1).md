# SHEETTOOLS ROADMAP V2
## PDF/Image → Multi-page Analysis → OMR/OCR → ScoreJSON → MusicXML

> Mục tiêu: xây dựng SheetTools thành một hệ thống chuyển đổi bản nhạc từ PDF/ảnh scan sang MusicXML/MXL với độ chính xác cao, đặc biệt cho các bản thánh ca có:
>
> - nhiều trang;
> - 2 khuông nhạc;
> - 4 bè SATB;
> - lời 1, 2, 3...;
> - điệp khúc;
> - dấu nối âm tiết;
> - repeat / ending;
> - nhiều chữ, watermark, số trang, tên bài, tác giả và các thành phần gây nhiễu.

---

# 1. Mục tiêu tổng thể

Không đi theo hướng:

```text
PDF/Image
   ↓
OCR/OMR một lần
   ↓
MusicXML
```

Mà đi theo kiến trúc nhiều lớp:

```text
PDF / IMAGE / MULTI-PAGE DOCUMENT
                │
                ▼
        DOCUMENT INGESTION
                │
                ▼
        PAGE NORMALIZATION
                │
                ▼
       PAGE SEGMENTATION V2
                │
     ┌──────────┼──────────┐
     │          │          │
     ▼          ▼          ▼
   MUSIC      LYRICS      META
     │          │          │
     ▼          ▼          ▼
    OMR         OCR        OCR
     │          │          │
     └──────┬───┴──────┬───┘
            ▼          ▼
       MUSIC MODEL   TEXT MODEL
            │          │
            └────┬─────┘
                 ▼
         ALIGNMENT ENGINE
                 │
                 ▼
            SCOREJSON
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
    MusicXML    MXL      Preview
        │
        ▼
     MuseScore
```

Nguyên tắc quan trọng:

> MusicXML không phải dữ liệu nguồn chính của SheetTools.

SheetTools nên có một format trung gian riêng:

```text
ScoreJSON
```

Sau đó mới export:

```text
ScoreJSON
   ├── MusicXML
   ├── MXL
   ├── MIDI
   └── OSMD Preview
```

---

# 2. Hai vấn đề cần ưu tiên sửa ngay

Hai phần hiện tại cần được nâng cấp trước:

1. **Thuật toán phân tích/tách vùng trên PDF và ảnh chưa đủ tốt.**
2. **Thiếu pipeline xử lý tài liệu nhiều trang.**

Đây là hai phần nền móng. Nếu Page Segmentation sai thì OCR, OMR, lyrics, 4 voices và MusicXML phía sau đều sai theo.

---

# 3. Document Intake – xử lý PDF và ảnh nhiều trang

## 3.1 Các input cần hỗ trợ

```text
.pdf
.png
.jpg
.jpeg
.webp
.tiff
.tif
```

Tùy chọn sau có thể bổ sung:

```text
.heic
.bmp
```

---

# 4. Tư duy mới: Document khác Page

Không nên coi mỗi file là một ảnh duy nhất.

Data model:

```text
Document
 ├── Page 1
 ├── Page 2
 ├── Page 3
 └── Page N
```

Ví dụ:

```json
{
  "document_id": "DOC_001",
  "source_type": "pdf",
  "page_count": 12,
  "pages": [
    {
      "page_id": "DOC_001_P001",
      "index": 1
    },
    {
      "page_id": "DOC_001_P002",
      "index": 2
    }
  ]
}
```

---

# 5. PDF pipeline

PDF upload:

```text
songbook.pdf
     │
     ▼
PDF Inspector
     │
     ├── PDF text-based?
     │
     └── PDF scanned?
     │
     ▼
Render từng page
     │
     ▼
Page Images
```

Khuyến nghị render:

```text
300 DPI mặc định
400 DPI cho bản khó
```

Không nên thấp hơn 250 DPI nếu cần nhận diện nốt nhạc.

Output:

```text
workspace/
  DOC_001/
    original/
      source.pdf

    pages/
      page_001.png
      page_002.png
      page_003.png
```

---

# 6. Multi-page Job Model

Không xử lý cả file như một request HTTP dài.

Tạo job:

```json
{
  "job_id": "JOB_20261003_001",
  "document_id": "DOC_001",
  "status": "processing",
  "total_pages": 12,
  "processed_pages": 4,
  "failed_pages": [],
  "progress": 33
}
```

Status:

```text
queued
extracting
normalizing
segmenting
recognizing_music
recognizing_text
aligning
assembling
exporting
completed
failed
partial
```

---

# 7. Page-level processing

Mỗi page phải xử lý độc lập trước.

```text
Document
   │
   ├── Page 1 → pipeline
   ├── Page 2 → pipeline
   ├── Page 3 → pipeline
   └── Page N → pipeline
```

Sau đó mới chạy:

```text
Cross-page Assembly
```

Lợi ích:

- page lỗi có thể retry;
- không phải chạy lại toàn bộ PDF;
- chạy parallel;
- dễ cache;
- dễ debug;
- UI hiển thị progress tốt;
- có thể sửa từng trang.

---

# 8. Page Classification

Không phải trang nào trong PDF cũng là bản nhạc.

Một sách thánh ca có thể có:

```text
cover
table of contents
index
blank page
song page
lyrics-only page
intro page
copyright page
```

Page classifier:

```text
PAGE
 │
 ├── music_page
 ├── mixed_music_text
 ├── text_page
 ├── index_page
 ├── cover
 ├── blank
 └── unknown
```

Heuristic ban đầu:

```text
staff_line_density
text_density
connected_component_distribution
horizontal_line_patterns
white_space_ratio
```

Sau này mới nâng lên model classifier.

---

# 9. Song Boundary Detection trong tài liệu nhiều trang

Không phải một PDF chỉ chứa một bài.

Ví dụ:

```text
Page 1 → Bài 101
Page 2 → Bài 101
Page 3 → Bài 102
Page 4 → Bài 102
Page 5 → Bài 103
```

Cần xác định:

```text
Document
 ├── Song A
 │    ├── page 1
 │    └── page 2
 │
 ├── Song B
 │    ├── page 3
 │    └── page 4
 │
 └── Song C
      └── page 5
```

Các tín hiệu:

- song number;
- title;
- composer;
- page header;
- layout break;
- hệ thống nhạc đầu trang;
- số bài;
- metadata OCR.

Score:

```text
new_song_score =
 title_detected
 + song_number_changed
 + composer_detected
 + top_margin_structure_changed
```

Nếu confidence thấp:

```text
requires_review = true
```

---

# 10. Cross-page Continuity

Vấn đề quan trọng:

Page 1 kết thúc giữa bài,
Page 2 tiếp tục hệ thống tiếp theo.

Không được reset toàn bộ state.

Cần giữ:

```json
{
  "song_state": {
    "key_signature": "G",
    "time_signature": "4/4",
    "current_measure": 24,
    "current_verse_count": 3,
    "active_repeat": false
  }
}
```

Page sau có thể kế thừa:

```text
key signature
time signature
measure number
voice mapping
part mapping
verse mapping
```

Nhưng nếu page sau phát hiện clef/key/time mới rõ ràng thì dùng dữ liệu mới.

---

# 11. Repeated Headers / Footers

PDF nhiều trang thường có:

```text
Tên sách
Số trang
Tên chương
Logo
Copyright
```

Không nên OCR lặp lại thành lyrics.

Tạo cơ chế:

```text
repeated_region_detector
```

Nếu cùng vùng:

```text
top 10%
bottom 8%
```

lặp trên nhiều page và nội dung gần giống nhau:

```text
classify = header/footer
ignore_from_music
ignore_from_lyrics
```

---

# 12. PAGE SEGMENTATION V2

Đây là phần cần sửa mạnh nhất.

Không sử dụng một bước đơn giản kiểu:

```text
threshold → contour → crop
```

Vì bản nhạc có:

- staff lines;
- lyrics;
- stems;
- beams;
- slur;
- dấu luyến;
- chord symbols;
- tiêu đề;
- page noise.

Cần pipeline nhiều giai đoạn.

---

# 13. Preprocessing Pipeline

```text
Original Page
    │
    ▼
Orientation detection
    │
    ▼
Deskew
    │
    ▼
Perspective correction
    │
    ▼
Background normalization
    │
    ▼
Contrast enhancement
    │
    ▼
Adaptive threshold
    │
    ▼
Denoise
    │
    ▼
Normalized Page
```

---

# 14. Orientation Detection

Ảnh từ điện thoại có thể:

```text
0°
90°
180°
270°
```

Phải detect trước staff line.

Heuristic:

```text
horizontal line dominance
OCR orientation
page aspect ratio
```

---

# 15. Deskew

Sai 1–2 độ cũng ảnh hưởng lớn tới staff line detection.

Phương pháp:

```text
Hough line transform
horizontal projection profile
```

Output:

```json
{
  "rotation_angle": -1.72,
  "confidence": 0.96
}
```

---

# 16. Perspective Correction

Ảnh chụp điện thoại thường:

```text
trapezoid
curved page
camera perspective
```

Basic:

```text
page contour
4 corner detection
perspective transform
```

Advanced phase:

```text
document dewarping
curved page correction
```

---

# 17. Background normalization

Đối với scan cũ:

```text
yellow paper
gray background
shadow
uneven lighting
```

Nên:

```text
estimate background
subtract background
normalize illumination
```

Không dùng global threshold đơn giản.

---

# 18. Adaptive Threshold

Ưu tiên:

```text
Sauvola
Wolf
Adaptive Gaussian
```

Không chỉ:

```text
threshold(gray, 127)
```

Lý do:

- giấy không đều;
- ảnh chụp điện thoại;
- shadow giữa gáy;
- watermark;
- scan cũ.

---

# 19. Denoise

Noise không chỉ là pixel noise.

Các loại:

```text
scanner dust
page border
shadow
hole punch
stain
watermark
compression artifacts
```

Mỗi loại cần strategy riêng.

---

# 20. Staff-line Detection trước OCR

Đây là thay đổi quan trọng.

Không bắt đầu bằng OCR.

Bắt đầu bằng:

```text
Normalized Page
      ↓
horizontal projection
      ↓
staff-line candidates
      ↓
5-line grouping
      ↓
staff detection
```

Một staff:

```text
line 1
line 2
line 3
line 4
line 5
```

Detect:

```json
{
  "staff_id": "ST_001",
  "lines": [211, 223, 235, 247, 259],
  "spacing": 12,
  "confidence": 0.97
}
```

---

# 21. System Detection

Một system có thể gồm:

```text
Treble staff
Bass staff
```

Cho piano/hymn:

```text
System
 ├── Staff 1 treble
 └── Staff 2 bass
```

Data:

```json
{
  "system_id": "SYS_01",
  "bbox": [104, 186, 1840, 510],
  "staff_ids": [
    "ST_001",
    "ST_002"
  ]
}
```

---

# 22. Staff Grouping

Không chỉ dựa distance.

Cần dùng:

```text
vertical spacing
brace/bracket detection
barline continuity
aligned measures
system width
```

Để tránh nhầm:

```text
staff cuối system 1
```

với:

```text
staff đầu system 2
```

---

# 23. Region Expansion

Sau khi phát hiện staff:

Không crop đúng 5 dòng staff.

Phải mở vùng:

```text
above staff
below staff
```

Vì có:

```text
lyrics
dynamic
chord symbols
tempo
articulation
```

Ví dụ:

```text
music_core_bbox
music_extended_bbox
lyrics_candidate_bbox
```

---

# 24. Layout Analysis

Page segmentation không nên chỉ là contour.

Tạo các region:

```text
page
 ├── title_region
 ├── author_region
 ├── composer_region
 ├── system_1
 │    ├── music_region
 │    └── lyrics_region
 ├── system_2
 │    ├── music_region
 │    └── lyrics_region
 └── footer
```

---

# 25. Connected Components Analysis

Sau threshold:

```text
Connected Components
```

Mỗi component có:

```json
{
  "bbox": [x, y, w, h],
  "area": 921,
  "aspect_ratio": 2.4,
  "density": 0.43
}
```

Dùng để phân biệt:

```text
text
note head
stem
beam
dot
staff line
large title
noise
```

Không cần classify hoàn hảo ở bước này.

Mục tiêu:

```text
lọc candidate
```

---

# 26. Multi-scale Processing

Title và note head khác kích thước rất lớn.

Do đó segmentation nên chạy:

```text
page scale
system scale
staff scale
symbol scale
```

Không dùng duy nhất 1 threshold + 1 kernel.

---

# 27. Music/Text Separation

Không “xóa chữ khỏi ảnh” trực tiếp.

Sinh masks:

```text
music_mask
text_mask
staff_mask
lyrics_mask
metadata_mask
noise_mask
```

Ví dụ:

```text
original_page.png
music_mask.png
lyrics_mask.png
meta_mask.png
noise_mask.png
```

Giữ nguyên:

```text
width
height
coordinate system
```

---

# 28. Coordinate System

Mọi object phải có tọa độ trên ảnh gốc.

Ví dụ:

```json
{
  "coordinate_space": "page_original",
  "page_width": 2480,
  "page_height": 3508
}
```

Bất kỳ crop nào cũng phải lưu transform:

```json
{
  "crop_bbox": [100, 300, 2200, 700],
  "scale_x": 1.0,
  "scale_y": 1.0
}
```

Điều này cực quan trọng cho lyric-note alignment.

---

# 29. Region Classification

Mỗi region:

```text
music
lyrics
title
composer
author
tempo
chord_symbol
page_number
header
footer
copyright
annotation
unknown
```

Data:

```json
{
  "region_id": "REG_041",
  "page_id": "P001",
  "type": "lyrics",
  "bbox": [121, 612, 2100, 160],
  "confidence": 0.91
}
```

---

# 30. Confidence System

Không quyết định cứng.

Mỗi recognition:

```json
{
  "prediction": "lyrics",
  "confidence": 0.74
}
```

Ngưỡng:

```text
>= 0.90  auto accept
0.70–0.89 accept but warning
0.50–0.69 review suggested
< 0.50   fallback / manual
```

---

# 31. Fallback Strategy

Nếu staff detection thất bại:

```text
Fallback A
→ Hough transform

Fallback B
→ projection profile

Fallback C
→ ML detector

Fallback D
→ manual region editor
```

Không cho pipeline fail toàn bộ chỉ vì một module.

---

# 32. Manual Region Editor

UI cần cho user sửa segmentation.

Ví dụ:

```text
[Original Page]

┌─────────────────────────┐
│ Title                   │
├─────────────────────────┤
│ System 1                │
│ [music]                 │
│ [lyrics]                │
├─────────────────────────┤
│ System 2                │
│ [music]                 │
│ [lyrics]                │
└─────────────────────────┘
```

User có thể:

```text
resize region
move region
change type
delete noise
split region
merge regions
```

Sau đó:

```text
Re-run selected region only
```

---

# 33. Music Recognition Pipeline

Sau segmentation:

```text
music_region
     ↓
Audiveris
     ↓
OMR result
```

Không feed nguyên PDF scan nếu có thể.

Nhưng cần benchmark hai chế độ:

```text
Mode A:
whole page → Audiveris

Mode B:
system regions → Audiveris
```

Tùy Audiveris và tài liệu thực tế, có thể chọn một mode làm default và mode kia làm fallback.

---

# 34. OMR Output

Cần lấy:

```text
clef
key
time signature
measure
barline
note
pitch
duration
rest
beam
stem
tie
slur
voice
staff
repeat
ending
dynamic
fermata
```

---

# 35. Hai staff – bốn voice

Không flatten.

Model:

```text
Part
 ├── Staff 1
 │    ├── Voice 1
 │    └── Voice 2
 │
 └── Staff 2
      ├── Voice 3
      └── Voice 4
```

Hymn SATB:

```text
Voice 1 = Soprano
Voice 2 = Alto
Voice 3 = Tenor
Voice 4 = Bass
```

Không assume 100%.

Có thể map bằng:

```text
staff
stem direction
pitch range
voice continuity
```

---

# 36. Voice Continuity

OMR thường dễ nhầm voice khi:

```text
hai nốt cùng stem
cross voice
rest bị mất
whole note
```

Cần post-processing:

```text
duration consistency
measure duration
pitch continuity
stem direction
voice occupancy
```

Ví dụ 4/4:

```text
sum duration voice = 4 quarter
```

Nếu:

```text
3.5 quarter
```

→ warning.

---

# 37. Measure Validation

Mỗi measure:

```json
{
  "measure": 12,
  "expected_duration": 16,
  "voices": {
    "1": 16,
    "2": 16,
    "3": 12,
    "4": 16
  }
}
```

Result:

```text
Voice 3 duration mismatch
```

---

# 38. Lyrics OCR Pipeline

Không trộn với music OCR.

```text
lyrics_region
      ↓
preprocess text
      ↓
OCR Vietnamese
      ↓
line detection
      ↓
verse detection
      ↓
syllable parser
```

---

# 39. OCR Engine

Có thể benchmark:

```text
PaddleOCR
Tesseract
EasyOCR
```

Ưu tiên engine hỗ trợ tiếng Việt tốt.

Không phụ thuộc 1 engine duy nhất.

Có thể dùng:

```text
OCR ensemble
```

---

# 40. OCR Ensemble

Ví dụ:

```text
Engine A:
"Chúa yêu thế gian"

Engine B:
"Chúa yêu thê gian"

Engine C:
"Chúa yêu thế gian"
```

Consensus:

```text
Chúa yêu thế gian
```

---

# 41. Verse Detection

Các pattern:

```text
1.
2.
3.
4.

1)
2)

1 -
2 -

I.
II.
III.
```

Normalize:

```json
{
  "verse_number": 1
}
```

---

# 42. Chorus Detection

Pattern:

```text
ĐK
Đ.K.
DK
D.K.
Điệp khúc
CHORUS
Chorus
Refrain
```

Normalize:

```json
{
  "section_type": "chorus"
}
```

---

# 43. Lyrics Data Model

Không lưu lyrics là một chuỗi.

```json
{
  "lyrics": {
    "sections": [
      {
        "type": "verse",
        "number": 1,
        "lines": []
      },
      {
        "type": "verse",
        "number": 2,
        "lines": []
      },
      {
        "type": "chorus",
        "lines": []
      }
    ]
  }
}
```

---

# 44. Syllable Parsing

Ví dụ:

```text
Giê-xu
```

Parser:

```json
[
  {
    "text": "Giê",
    "syllabic": "begin"
  },
  {
    "text": "xu",
    "syllabic": "end"
  }
]
```

Ví dụ:

```text
Ha-lê-lu-gia
```

→ 4 syllables.

---

# 45. Lyric-note Alignment

Đây là một trong các module khó nhất.

Input:

```text
notes with x positions
lyrics syllables with x positions
```

Dùng:

```text
horizontal alignment
nearest note/chord
measure boundary
word spacing
melisma
hyphen
verse row
```

---

# 46. Alignment Data

```json
{
  "syllable_id": "LYR_0012",
  "text": "Chúa",
  "verse": 1,
  "note_id": "NOTE_0049",
  "confidence": 0.94
}
```

---

# 47. Melisma

Trường hợp:

```text
một âm tiết
→ nhiều nốt
```

Data:

```json
{
  "text": "ơi",
  "start_note_id": "N10",
  "end_note_id": "N13",
  "extend": true
}
```

MusicXML:

```text
<extend/>
```

---

# 48. Chord Symbols

Chord guitar:

```text
C
G/B
Am
F
```

Không classify là lyrics.

Region:

```text
chord_symbol
```

Sau này export:

```xml
<harmony>
```

---

# 49. Metadata OCR

Nhận diện riêng:

```text
song number
title
subtitle
author
composer
arranger
copyright
tempo
key description
```

Example:

```json
{
  "metadata": {
    "song_number": "182",
    "title": "Ơn Chúa Diệu Kỳ",
    "composer": "...",
    "author": "..."
  }
}
```

---

# 50. ScoreJSON – Source of Truth

Đây là format trung tâm.

Không sửa trực tiếp MusicXML trong logic app.

Ví dụ:

```json
{
  "version": "2.0",

  "document_id": "DOC_001",

  "score": {
    "score_id": "SCORE_001",

    "metadata": {
      "title": "Example",
      "song_number": "101"
    },

    "pages": [
      {
        "page_id": "P001",
        "index": 1
      }
    ],

    "parts": [
      {
        "part_id": "P1",

        "staves": [
          {
            "staff": 1,

            "voices": [
              {
                "voice": 1,
                "role": "soprano"
              },
              {
                "voice": 2,
                "role": "alto"
              }
            ]
          },

          {
            "staff": 2,

            "voices": [
              {
                "voice": 3,
                "role": "tenor"
              },
              {
                "voice": 4,
                "role": "bass"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

---

# 51. Page JSON

```json
{
  "page_id": "P001",

  "source": {
    "width": 2480,
    "height": 3508,
    "dpi": 300
  },

  "transform": {
    "rotation": -1.2
  },

  "regions": [],

  "systems": [],

  "warnings": []
}
```

---

# 52. Recognition Versioning

Mỗi page nên lưu:

```json
{
  "recognition_version": 3
}
```

Nếu user sửa:

```text
version 3 → version 4
```

Không ghi đè mất lịch sử ngay.

Sau này có thể support:

```text
undo
compare
rollback
```

---

# 53. MusicXML Export

MusicXML chỉ generate từ ScoreJSON.

```text
ScoreJSON
     ↓
MusicXML Builder
```

Không:

```text
OMR raw
     ↓
MusicXML
     ↓
edit XML trực tiếp
```

---

# 54. MusicXML Mapping

Các object:

```text
ScoreJSON note
→ <note>

voice
→ <voice>

staff
→ <staff>

lyrics
→ <lyric>

measure
→ <measure>

slur
→ <notations>

chord
→ <harmony>

repeat
→ <repeat>
```

---

# 55. MXL

Ngoài `.musicxml`:

```text
score.musicxml
```

support:

```text
score.mxl
```

MXL là compressed MusicXML.

---

# 56. Preview

Frontend:

```text
ScoreJSON
     ↓
MusicXML
     ↓
OpenSheetMusicDisplay
```

Preview trực tiếp trong browser.

---

# 57. Correction UI

Màn hình chính:

```text
┌─────────────────┬───────────────────────┐
│ Original Image  │ Music Preview         │
│                 │                       │
│ Page 3          │ Digital score         │
│                 │                       │
├─────────────────┴───────────────────────┤
│ Warnings                                │
│ Measure 23 voice 3 duration mismatch    │
│ Verse 2 lyric uncertain                 │
└─────────────────────────────────────────┘
```

---

# 58. Editing Modes

## Region mode

```text
edit page regions
```

## Music mode

```text
pitch
duration
voice
staff
rest
beam
measure
```

## Lyrics mode

```text
text
verse
chorus
syllable
alignment
```

---

# 59. Confidence Overlay

UI có thể hiển thị:

```text
green = high confidence
yellow = review
red = low confidence
```

Không cần cố auto-correct mọi thứ.

Mục tiêu:

```text
AI xử lý phần lớn
human sửa phần không chắc
```

---

# 60. API Design

Base:

```text
/api/v2
```

---

# 61. Upload

```http
POST /api/v2/documents
```

Input:

```text
PDF/Image
```

Response:

```json
{
  "document_id": "DOC_001",
  "job_id": "JOB_001"
}
```

---

# 62. Job Status

```http
GET /api/v2/jobs/{job_id}
```

Response:

```json
{
  "status": "segmenting",
  "progress": 42,
  "page": 5,
  "total_pages": 12
}
```

---

# 63. Document Pages

```http
GET /api/v2/documents/{document_id}/pages
```

---

# 64. Page Regions

```http
GET /api/v2/pages/{page_id}/regions
```

---

# 65. Update Region

```http
PATCH /api/v2/pages/{page_id}/regions/{region_id}
```

---

# 66. Retry Page

```http
POST /api/v2/pages/{page_id}/retry
```

Có thể retry:

```text
segmentation
ocr
omr
alignment
```

---

# 67. Export

```http
POST /api/v2/scores/{score_id}/export
```

Input:

```json
{
  "format": "musicxml"
}
```

Options:

```text
musicxml
mxl
midi
json
```

---

# 68. Suggested Project Structure

```text
sheettools/

├── apps/
│   ├── web/
│   └── api/
│
├── services/
│   ├── document/
│   ├── preprocessing/
│   ├── segmentation/
│   ├── omr/
│   ├── ocr/
│   ├── alignment/
│   ├── score/
│   └── exporter/
│
├── workers/
│   ├── document_worker/
│   ├── page_worker/
│   └── export_worker/
│
├── libs/
│   ├── geometry/
│   ├── image/
│   ├── music/
│   ├── lyrics/
│   └── common/
│
├── models/
│   ├── document.py
│   ├── page.py
│   ├── region.py
│   ├── score.py
│   └── lyrics.py
│
├── docker/
│   ├── api/
│   ├── audiveris/
│   ├── ocr/
│   └── worker/
│
└── tests/
```

---

# 69. Docker Architecture

```text
                  ┌──────────────┐
                  │  WEB / UI    │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   API        │
                  │  FastAPI     │
                  └──────┬───────┘
                         │
             ┌───────────┼───────────┐
             │           │           │
             ▼           ▼           ▼
        Redis Queue    Postgres    Storage
             │
             ▼
          Workers
     ┌───────┼───────────┐
     │       │           │
     ▼       ▼           ▼
 preprocess OMR         OCR
           Audiveris   PaddleOCR
     │       │           │
     └───────┼───────────┘
             ▼
          Alignment
             │
             ▼
          ScoreJSON
             │
             ▼
          Exporter
```

---

# 70. Suggested Containers

```text
sheettools-web
sheettools-api
sheettools-worker
sheettools-omr
sheettools-ocr
sheettools-redis
sheettools-postgres
```

Optional:

```text
sheettools-minio
```

---

# 71. Storage Layout

```text
data/
  documents/
    DOC_001/
      source/
      pages/
      normalized/
      masks/
      crops/
      omr/
      ocr/
      score/
      exports/
```

---

# 72. Cache

Cache theo hash:

```text
file_hash
page_hash
region_hash
```

Nếu cùng ảnh:

```text
không OCR lại
không OMR lại
```

---

# 73. Retry Strategy

Nếu page 8 fail:

```text
retry page 8
```

Không chạy:

```text
page 1 → page 12
```

lại từ đầu.

---

# 74. Parallel Processing

Document 20 pages:

```text
Page 1 ─┐
Page 2 ─┤
Page 3 ─┤ Worker pool
Page 4 ─┤
...     │
Page20 ─┘
```

Nhưng cần giới hạn:

```text
Audiveris concurrency
OCR concurrency
RAM usage
```

---

# 75. Progress System

UI:

```text
Uploading         100%
Extract pages     100%
Normalize         100%
Segment           72%
OMR               48%
OCR               60%
Alignment         12%
Export             0%
```

---

# 76. Error Model

Không trả lỗi kiểu:

```text
500 recognition failed
```

Mà:

```json
{
  "code": "OMR_MEASURE_DURATION_MISMATCH",
  "page": 4,
  "system": 2,
  "measure": 17,
  "severity": "warning"
}
```

---

# 77. Warning Categories

```text
PAGE_LOW_RESOLUTION
PAGE_SKEW_HIGH
STAFF_NOT_FOUND
SYSTEM_GROUP_UNCERTAIN
OMR_VOICE_CONFLICT
OMR_DURATION_MISMATCH
OCR_LOW_CONFIDENCE
VERSE_NUMBER_UNCERTAIN
CHORUS_UNCERTAIN
LYRIC_ALIGNMENT_UNCERTAIN
SONG_BOUNDARY_UNCERTAIN
```

---

# 78. Quality Score

Mỗi page:

```json
{
  "quality": {
    "image": 0.92,
    "segmentation": 0.88,
    "omr": 0.81,
    "ocr": 0.94,
    "alignment": 0.76,
    "overall": 0.85
  }
}
```

---

# 79. Acceptance Criteria

## Page preprocessing

Pass khi:

```text
deskew error < 0.5°
```

trên bộ test chuẩn.

## Staff detection

Mục tiêu:

```text
>= 98% staff detected
```

với scan sạch.

## System grouping

```text
>= 97%
```

## Lyrics region

```text
>= 95%
```

## Verse number detection

```text
>= 98%
```

trên dữ liệu thánh ca chuẩn.

## Page ordering

```text
100%
```

với PDF input.

---

# 80. OMR Acceptance

Không nên đo chỉ bằng:

```text
"file export được"
```

Phải đo:

```text
note pitch accuracy
duration accuracy
measure completeness
voice assignment
staff assignment
```

---

# 81. Lyrics Acceptance

Metrics:

```text
Character Error Rate
Word Error Rate
Verse classification accuracy
Chorus classification accuracy
Syllable-note alignment accuracy
```

---

# 82. Test Dataset

Tự tạo dataset dự án.

Folder:

```text
tests/data/

  clean/
  noisy/
  phone_photo/
  skewed/
  old_scan/
  satb/
  multi_verse/
  chorus/
  multi_page/
  mixed_pages/
```

---

# 83. Golden Dataset

Mỗi sample có:

```text
input.pdf
expected_regions.json
expected_score.musicxml
expected_lyrics.json
```

Đây là test quan trọng nhất khi cải tiến thuật toán.

---

# 84. Regression Testing

Mỗi lần chỉnh segmentation:

```text
run 100 samples
```

So sánh:

```text
old accuracy
new accuracy
```

Không để fix sample A nhưng làm hỏng sample B.

---

# 85. Debug Artifacts

Mỗi page nên có debug:

```text
01_original.png
02_gray.png
03_deskew.png
04_threshold.png
05_staff_lines.png
06_systems.png
07_regions.png
08_music_mask.png
09_text_mask.png
```

Nếu pipeline sai sẽ biết sai từ bước nào.

---

# 86. Page Segmentation Debug JSON

```json
{
  "staff_candidates": [],
  "systems": [],
  "regions": [],
  "discarded_components": [],
  "confidence": {}
}
```

---

# 87. Development Roadmap

## PHASE 0 – Baseline

Mục tiêu:

```text
đo hệ thống hiện tại
```

Làm:

- chọn 30–50 ảnh/PDF thực tế;
- lưu output hiện tại;
- đánh dấu lỗi;
- chia lỗi theo category.

Không tối ưu trước khi có baseline.

---

# 88. PHASE 1 – Document Engine

Ưu tiên số 1.

Implement:

```text
PDF upload
multi-page extraction
page numbering
page storage
job system
retry page
progress
```

Done khi:

```text
50-page PDF
```

có thể tách và xử lý từng page độc lập.

---

# 89. PHASE 2 – Preprocessing V2

Implement:

```text
orientation
deskew
perspective correction
illumination normalization
adaptive threshold
denoise
```

Output debug image ở mỗi bước.

---

# 90. PHASE 3 – Staff/System Detection

Implement:

```text
staff-line detector
5-line grouping
staff confidence
system grouping
```

Chưa cần OCR lyrics ở phase này.

---

# 91. PHASE 4 – Layout Segmentation

Implement:

```text
music region
lyrics region
metadata region
header/footer
noise
```

Đây là phần trực tiếp giải quyết vấn đề “tách chưa tốt”.

---

# 92. PHASE 5 – OMR Integration

Implement:

```text
Audiveris service
OMR import
OMR normalization
measure validation
voice validation
```

---

# 93. PHASE 6 – Lyrics Engine

Implement:

```text
Vietnamese OCR
verse detection
chorus detection
syllable parsing
```

---

# 94. PHASE 7 – Lyric Alignment

Implement:

```text
note X
syllable X
measure context
verse rows
melisma
```

---

# 95. PHASE 8 – ScoreJSON

Không làm quá sớm.

Sau khi OMR/OCR structures tương đối ổn:

```text
define ScoreJSON v1
```

Tất cả module convert vào ScoreJSON.

---

# 96. PHASE 9 – MusicXML Exporter

Implement:

```text
notes
measures
voices
staff
lyrics
repeats
ties
slurs
harmony
```

---

# 97. PHASE 10 – Correction UI

Implement:

```text
page view
region editor
score preview
lyrics editor
warning navigator
```

---

# 98. PHASE 11 – Multi-page Score Assembly

Implement:

```text
song boundary
cross-page state
measure continuation
metadata merge
header/footer removal
```

---

# 99. PHASE 12 – Accuracy Improvement

Sau khi hệ thống end-to-end chạy được:

```text
collect failures
cluster errors
improve each module
```

Không train model lung tung trước khi biết lỗi nằm ở đâu.

---

# 100. Thứ tự code đề xuất ngay lúc này

Nếu tiếp tục từ code hiện tại:

```text
1. Document / Page abstraction
2. Multi-page PDF extraction
3. Debug artifact system
4. Preprocessing V2
5. Staff-line detector
6. System grouping
7. Region segmentation
8. Region confidence
9. Manual region editor
10. OMR integration
11. Lyrics OCR
12. Verse / chorus parser
13. 4 voice normalization
14. Alignment engine
15. ScoreJSON
16. MusicXML exporter
17. Multi-page score assembler
18. Correction UI
```

---

# 101. Không nên làm ngay

Không nên ưu tiên:

```text
train LLM riêng
train vision model lớn
auto-correct bằng AI tất cả
```

trước khi:

```text
segmentation
coordinates
staff
system
page model
```

ổn định.

---

# 102. Khi nào dùng AI model

AI/vision model phù hợp làm fallback:

```text
ambiguous region
bad scan
unknown page layout
chorus classification
metadata ambiguity
```

Không dùng AI để thay thế toàn bộ deterministic pipeline.

---

# 103. Hybrid Strategy

Hướng tốt nhất:

```text
Computer Vision
      +
Rules
      +
OMR
      +
OCR
      +
AI fallback
      +
Human correction
```

Không phải:

```text
LLM sees image
→ outputs MusicXML
```

---

# 104. Final Architecture

```text
                        USER
                          │
                          ▼
                  Upload PDF/Image
                          │
                          ▼
                 Document Service
                          │
                          ▼
               Multi-page Extractor
                          │
                          ▼
                     PAGE QUEUE
                          │
             ┌────────────┼────────────┐
             │            │            │
             ▼            ▼            ▼
       Preprocessor   Preprocessor  Preprocessor
             │
             ▼
      Page Segmentation V2
             │
     ┌───────┼───────────────┐
     │       │               │
     ▼       ▼               ▼
   MUSIC   LYRICS          META
     │       │               │
     ▼       ▼               ▼
 Audiveris OCR Engine      OCR
     │       │               │
     └───────┼───────────────┘
             ▼
       Page Recognition
             │
             ▼
       Alignment Engine
             │
             ▼
          ScoreJSON
             │
             ▼
     Cross-page Assembler
             │
             ▼
       Complete ScoreJSON
             │
     ┌───────┼──────────────┐
     ▼       ▼              ▼
 MusicXML   MXL            MIDI
     │
     ▼
 OSMD / MuseScore
```

---

# 105. Definition of Done – V2

V2 nên được xem là đạt khi:

1. Upload được PDF 20–50 trang.
2. Tự render từng page.
3. Có page queue và retry.
4. Detect được staff/system đáng tin cậy.
5. Tách được:
   - music;
   - lyrics;
   - metadata;
   - header/footer;
   - noise.
6. Hỗ trợ:
   - 2 staff;
   - 4 voices;
   - verse 1/2/3;
   - chorus.
7. Có lyrics-note alignment.
8. Có ScoreJSON.
9. Export được MusicXML/MXL.
10. Có warning và confidence.
11. User sửa được page/region/lyrics/note.
12. Chỉ rerun phần bị sửa.
13. Ghép được score qua nhiều page.
14. Có regression dataset.

---

# 106. Ưu tiên kỹ thuật

Nếu phải chọn 5 thứ quan trọng nhất:

```text
#1 Page preprocessing
#2 Staff/System detection
#3 Region segmentation
#4 Multi-page document architecture
#5 ScoreJSON + correction workflow
```

OMR/OCR engine có thể thay đổi sau.

Nhưng nếu 5 nền móng trên sai thì thay engine cũng không cứu được accuracy.

---

# 107. Nguyên tắc cuối cùng

SheetTools nên được thiết kế như:

```text
Document understanding system
```

chứ không chỉ là:

```text
image → MusicXML converter
```

Vì bản nhạc thực tế có:

```text
page structure
music semantics
text semantics
cross-page continuity
lyrics structure
voice structure
human correction
```

Khi những lớp này được tách riêng, hệ thống sẽ:

- dễ debug hơn;
- dễ nâng cấp hơn;
- dễ thay OCR/OMR engine;
- hỗ trợ nhiều trang tốt hơn;
- ít phụ thuộc vào một model;
- tăng accuracy theo từng module;
- phù hợp để phát triển lâu dài.

---

# 108. Next Coding Target

Module nên code ngay sau roadmap này:

```text
DocumentService
    ↓
PageExtractor
    ↓
PagePreprocessorV2
    ↓
StaffDetector
    ↓
SystemDetector
    ↓
RegionSegmenterV2
```

Output đầu tiên cần đạt:

```text
page_001_regions.json
page_002_regions.json
...
```

với overlay debug:

```text
page_001_regions_debug.png
```

Khi segmentation đã tốt, mới tiếp tục nối:

```text
OMR + OCR + Alignment + MusicXML
```

Đây là cách giảm rất nhiều thời gian debug về sau.
