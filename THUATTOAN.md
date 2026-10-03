# THUẬT TOÁN CHUYỂN ĐỔI PDF/JPG → MUSICXML
## Sheet Converter — Algorithm Design Document

> **Phiên bản:** 1.0.0  
> **Dự án:** SheetTools — Sheet Converter  
> **Chuẩn tham chiếu:** Golden Reference `001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml`  
> **3 Chế độ xuất:** (1) Chỉ nốt nhạc · (2) Lời riêng · (3) Đầy đủ (nốt + lời + hợp âm)

---

## MỤC LỤC

1. [Tổng quan Pipeline](#1-tổng-quan-pipeline)
2. [Giai đoạn 0 — Phân tích đầu vào](#2-giai-đoạn-0--phân-tích-đầu-vào)
3. [Giai đoạn 1 — Tiền xử lý ảnh (OpenCV)](#3-giai-đoạn-1--tiền-xử-lý-ảnh-opencv)
4. [Giai đoạn 2 — Phân vùng không gian 3 lớp](#4-giai-đoạn-2--phân-vùng-không-gian-3-lớp)
5. [Giai đoạn 3 — OMR Nhận dạng nốt nhạc (Audiveris)](#5-giai-đoạn-3--omr-nhận-dạng-nốt-nhạc-audiveris)
6. [Giai đoạn 4 — OCR Nhận dạng lời ca tiếng Việt](#6-giai-đoạn-4--ocr-nhận-dạng-lời-ca-tiếng-việt)
7. [Giai đoạn 5 — Căn lời vào nốt (Lyrics Alignment)](#7-giai-đoạn-5--căn-lời-vào-nốt-lyrics-alignment)
8. [Giai đoạn 6 — Xử lý Giọng bè & Đa bè (Multi-Voice / Multi-Part)](#8-giai-đoạn-6--xử-lý-giọng-bè--đa-bè-multi-voice--multi-part)
9. [Giai đoạn 7 — Hợp âm (Harmony / Chord)](#9-giai-đoạn-7--hợp-âm-harmony--chord)
10. [Giai đoạn 8 — Ghép trang PDF nhiều trang](#10-giai-đoạn-8--ghép-trang-pdf-nhiều-trang)
11. [Giai đoạn 9 — Kiểm định (Validation)](#11-giai-đoạn-9--kiểm-định-validation)
12. [Giai đoạn 10 — Xuất 3 chế độ (Export)](#12-giai-đoạn-10--xuất-3-chế-độ-export)
13. [Cấu trúc dữ liệu MusicXML chuẩn](#13-cấu-trúc-dữ-liệu-musicxml-chuẩn)
14. [Sơ đồ luồng dữ liệu tổng thể](#14-sơ-đồ-luồng-dữ-liệu-tổng-thể)
15. [Bảng quyết định 3 chế độ xuất](#15-bảng-quyết-định-3-chế-độ-xuất)
16. [Xử lý lỗi & Fallback](#16-xử-lý-lỗi--fallback)
17. [Điểm kiểm chất lượng (Quality Checkpoints)](#17-điểm-kiểm-chất-lượng-quality-checkpoints)

---

## 1. TỔNG QUAN PIPELINE

```
INPUT (PDF / JPG / PNG)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 0: Phân tích đầu vào                          │
│  - Phát hiện loại file (PDF multi-page / Single image)    │
│  - Phân tích chất lượng scan (GOOD/MEDIUM/POOR)           │
│  - Chọn tham số xử lý tối ưu                             │
└────────────────────┬──────────────────────────────────────┘
                     │ Từng trang ảnh (PNG)
                     ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 1: Tiền xử lý ảnh (OpenCV Pipeline)           │
│  1. Grayscale conversion                                  │
│  2. Shadow removal (ảnh chụp không đều sáng)              │
│  3. Deskew — Hough Line Transform ±10°                    │
│  4. CLAHE Contrast Enhancement (tileGridSize=8×8)         │
│  5. Fast Non-Local Means Denoising                        │
│  6. Sauvola Adaptive Binarization (tùy chọn)             │
└────────────────────┬──────────────────────────────────────┘
                     │ Ảnh đã xử lý (grayscale sạch)
                     ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 2: Phân vùng 3 lớp (3-Zone Decomposition)    │
│  Zone 1: Header (tiêu đề, tác giả, số bài)               │
│  Zone 2: Notation (khuông nhạc + nốt — SẠCH)             │
│  Zone 3: Lyrics Band (lời ca bên dưới từng khuông)        │
└────────┬──────────────────────┬──────────────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐   ┌──────────────────────────────────┐
│ GIAI ĐOẠN 3:    │   │ GIAI ĐOẠN 4:                     │
│ Audiveris OMR   │   │ OCR Tiếng Việt                   │
│                 │   │                                  │
│ - Staff detect  │   │ - RapidOCR (primary)             │
│ - Clef/Key/Time │   │ - Tesseract vie+eng (secondary)  │
│ - Notes/Rests   │   │ - Consensus voting               │
│ - Voices/Parts  │   │ - Vietnamese tone recovery       │
│ - Slurs/Beams   │   │ - Syllable segmentation          │
│ → raw.musicxml  │   │ → lyrics.json (artifact)         │
└────────┬────────┘   └────────────┬─────────────────────┘
         │                         │
         └──────────┬──────────────┘
                    ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 5: Căn lời vào nốt (Lyrics Alignment)         │
│  - Needleman-Wunsch Monotonic DP                          │
│  - Spatial + OCR Confidence scoring                       │
│  - Ngưỡng chấp nhận >= 0.55                              │
│  → notation_with_lyrics.musicxml                          │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 6: Xử lý Giọng bè & Đa bè                    │
│  - Multi-Part (P1 giai điệu, P2 bè trầm)                 │
│  - Multi-Voice (Voice 1, 2, 3, 4 trong cùng khuông)       │
│  - Staff assignment (staff 1 = treble, staff 2 = bass)    │
│  - Lyric binding: chỉ P1/Voice 1 nhận lời chính          │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 7: Hợp âm (Chord / Harmony)                   │
│  - Parse text harmony từ OCR Zone 1 / Notation zone       │
│  - Chord parser: Root + Quality + Extension + Bass        │
│  - Anchor theo measure:beatOffset                         │
│  - Sinh thẻ <harmony> MusicXML chuẩn                     │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 8: Ghép trang (PDF nhiều trang)               │
│  - Merge DOM MusicXML theo part-id                        │
│  - Đánh dấu new-page trên measure đầu mỗi trang          │
│  - Giữ toàn bộ part/voice/staff/lyric                     │
│  - page_checkpoint.json để resume nếu bị gián đoạn       │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 9: Kiểm định (Validation — music21 + lxml)    │
│  - XML well-formed                                        │
│  - MusicXML schema parseable                              │
│  - Measure duration check (underfull / overfull)          │
│  - Voice / pitch / lyric orphan warnings                  │
│  - OSMD render test                                       │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────────┐
│  GIAI ĐOẠN 10: XUẤT 3 CHẾ ĐỘ                            │
│                                                           │
│  [Option A] CHỈ NỐT NHẠC                                 │
│    score_notation_only.musicxml                           │
│    Bỏ: <lyric>, <harmony>, direction, dynamics            │
│    Giữ: notes, rests, ties, slurs, beams, clef, key      │
│                                                           │
│  [Option B] LỜI RIÊNG                                    │
│    lyrics_only.txt / lyrics_only.json                     │
│    Xuất verse 1..N theo thứ tự, có bounding box          │
│                                                           │
│  [Option C] ĐẦY ĐỦ (nốt + lời + hợp âm)                 │
│    score_full.musicxml / .mxl                             │
│    Giữ toàn bộ: notes, lyrics, harmony, dynamics         │
└───────────────────────────────────────────────────────────┘
```

---

## 2. GIAI ĐOẠN 0 — PHÂN TÍCH ĐẦU VÀO

### 2.1 Phát hiện loại file

```
INPUT
 ├─ PDF → Tách trang: poppler / pdf2image (300 DPI)
 │        → Lưu: pages/page-001.png, page-002.png, ...
 │        → page_checkpoint.json (resume nếu crash)
 │
 ├─ JPG / PNG → Single page, đưa thẳng vào pipeline
 │
 └─ Multi-image ZIP → Giải nén, sắp xếp theo tên tự nhiên
```

### 2.2 Phân tích chất lượng scan

```python
# Bốn profile chất lượng:
profile = analyze_image_quality(gray)

# Kết quả:
{
  "profile": "already_binary" | "uneven_lighting" | 
             "low_resolution_or_blurred" | "clean_scan",
  "metrics": {
    "near_binary_ratio":  float,  # Tỷ lệ pixel đã gần trắng/đen
    "contrast_std":       float,  # Độ lệch chuẩn độ tương phản
    "blur_score":         float,  # Laplacian variance (< 35 = mờ)
    "illumination_range": float   # Chênh lệch sáng/tối (>90 = bóng)
  },
  "recommended": {
    "shadow_removal": bool,
    "clahe":          bool,
    "denoise":        bool
  }
}
```

**Ngưỡng cảnh báo hiển thị cho người dùng:**

| Vấn đề | Ngưỡng | Gợi ý |
|--------|--------|--------|
| Phân giải thấp | blur_score < 35 | Dùng ảnh >= 300 DPI |
| Bóng / Ánh sáng không đều | illumination_range > 90 | Chụp lại nơi sáng đều |
| Nghiêng | Góc phát hiện > 5° | Xoay lại ảnh |
| Cắt mất khuông | Staff bị truncate | Crop lại sát bản nhạc |

---

## 3. GIAI ĐOẠN 1 — TIỀN XỬ LÝ ẢNH (OPENCV)

### Thuật toán Pipeline 6 bước

```
Ảnh gốc (BGR)
    │
    ▼ Bước 1: GRAYSCALE
    cv2.cvtColor(img, COLOR_BGR2GRAY)
    │
    ▼ Bước 2: SHADOW REMOVAL (nếu profile = "uneven_lighting")
    │  - Dilate kernel 21×21 → ước lượng nền
    │  - GaussianBlur nền (sigma=21)
    │  - Divide(gray, blurred) × 255 → chuẩn hoá sáng
    │
    ▼ Bước 3: DESKEW — Hough Line Transform
    │  - Canny edge detection (50, 150)
    │  - HoughLinesP với min_line_length = 25% chiều rộng
    │  - Lọc lines gần nằm ngang (|angle| < 15°)
    │  - Góc trung vị (median_angle)
    │  - Xoay nếu: 0.5° < |angle| < 10°
    │  - warpAffine với BORDER_REPLICATE (tránh viền đen)
    │
    ▼ Bước 4: CLAHE — Tăng tương phản cục bộ
    │  createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    │  → Giữ chi tiết nốt nhỏ trong vùng ánh sáng thấp
    │
    ▼ Bước 5: FAST DENOISING
    │  fastNlMeansDenoising(h=5, templateWindowSize=7, searchWindowSize=21)
    │  → Giảm nhiễu JPEG/scan mà không xoá nét nốt nhạc
    │
    ▼ Bước 6: SAUVOLA BINARIZATION (tuỳ chọn)
       threshold_sauvola(window_size=25, k=0.15)
       → Ngưỡng động theo từng vùng 25×25 px
       → Tốt hơn Otsu khi ánh sáng không đều
       → Fallback: Otsu global (cv2.THRESH_OTSU)
```

> **QUY TẮC BẤT BIẾN:** Không vẽ lại dòng khuông nhạc.
> Không xoá pixel nào trong vùng bảo vệ khuông (staff corridor).
> Mọi thao tác chỉ được cải thiện độ tương phản, KHÔNG làm biến dạng ký hiệu.

---

## 4. GIAI ĐOẠN 2 — PHÂN VÙNG KHÔNG GIAN 3 LỚP

### Mục đích: Tách biệt 3 loại thông tin trước khi xử lý riêng

```
┌──────────────────────────────────────────────────┐
│  ZONE 1: HEADER                                  │  y < staff_0_top
│  Tiêu đề bài, Số thứ tự, Tác giả, Nhịp/Giọng   │
└──────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────┐
│  ZONE 2: NOTATION (PURE MUSIC LAYER)             │  y trong vùng staff
│  Khuông nhạc (5 dòng), Khoá nhạc, Nốt, Lặng     │
│  Dấu hóa, Nhịp, Liên kết, Chùm nốt (beam)       │
│  Mask text nằm NGOÀI khuông → ảnh thuần nốt      │
└──────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────┐
│  ZONE 3: LYRICS BANDS                            │  y giữa 2 khuông
│  Verse 1, Verse 2, ..., Verse N                  │
│  Hợp âm (chữ phía trên khuông)                  │
└──────────────────────────────────────────────────┘
```

### Thuật toán phân vùng

```python
# Bước 1: Phát hiện dòng khuông (Staff Line Detection)
# - Phân tích horizontal projection (tổng pixel trắng theo hàng)
# - Tìm 5 dòng cách đều (pattern matching 5-line staff)
# - Gom nhóm 5 dòng thành 1 khuông
# - staff_top[i], staff_bottom[i] cho mỗi khuông i

# Bước 2: Xác định Lyric Band của mỗi khuông
lyric_band_top = staff_bottom[i]
lyric_band_bot = (staff_top[i+1] + staff_bottom[i]) / 2  # trung điểm

# Lưu ý: Chữ nằm gần khuông KẾ (Fine, D.C. al Fine, chỉ dẫn)
# KHÔNG thuộc lyric band của khuông trên

# Bước 3: Phân loại từng OCR bounding box
for box in all_text_boxes:
    if box.y < staff_0_top:
        zone = "header"
    elif is_inside_staff_corridor(box):
        zone = "notation_text"  # Có thể là dynamics/direction
    elif is_in_lyric_band(box):
        zone = "lyric"
        verse_number = detect_verse_number(box)  # 1, 2, 3, 4...
    elif box.y_position == "above_staff":
        zone = "chord_symbol"  # Hợp âm ở trên khuông
```

---

## 5. GIAI ĐOẠN 3 — OMR NHẬN DẠNG NỐT NHẠC (AUDIVERIS)

### 5.1 Chuẩn bị ảnh Notation Layer

```python
# Chỉ đưa ảnh Zone 2 (notation-only) vào Audiveris
# Mask tất cả text nằm ngoài staff corridors:
for box in ocr_boxes:
    if not overlaps_staff_corridor(box):
        image[box.y1:box.y2, box.x1:box.x2] = 255  # trắng hoá
    # NHƯNG: box chạm vào staff → KHÔNG xoá (tránh giả nốt mất)
```

### 5.2 Thực thi Audiveris CLI

```bash
audiveris -batch -export -output {out_dir} \
          -option org.audiveris.omr.sheet.Book.printSheetNumber=false \
          -- {input_page.png}
```

**Audiveris nhận dạng các ký hiệu:**

| Ký hiệu nhạc | MusicXML output |
|---|---|
| Khoá Sol (G clef) | `<clef sign="G" line="2"/>` |
| Khoá Fa (F clef) | `<clef sign="F" line="4"/>` |
| Giọng (Key sig.) | `<key><fifths>1</fifths></key>` (G major = 1 dấu thăng) |
| Nhịp | `<time><beats>3</beats><beat-type>4</beat-type></time>` |
| Nốt nhạc | `<note><pitch><step>G</step><octave>4</octave></pitch>...</note>` |
| Nốt lặng (Rest) | `<note><rest/><duration>...</duration></note>` |
| Dấu nối (Tie) | `<tie type="start"/>` / `<tie type="stop"/>` |
| Slur | `<notations><slur type="start" number="1"/></notations>` |
| Chùm nốt (Beam) | `<beam number="1">begin</beam>` |
| Nốt chấm | `<dot/>` |
| Dấu hóa | `<accidental>sharp</accidental>` |
| Giọng (Voice) | `<voice>1</voice>` |
| Khuông (Staff) | `<staff>1</staff>` |

### 5.3 Kết quả: raw.musicxml

```
raw.musicxml  ← BẤT BIẾN (không bao giờ sửa)
source.omr    ← BẤT BIẾN (giữ để debug & reprocess)
```

### 5.4 Auto-Healer (music21)

Sau khi Audiveris sinh raw.musicxml, bộ Auto-Healer:
- Phát hiện và báo cáo lỗi nhạc lý cơ bản
- KHÔNG tự sửa nốt — chỉ ghi issues vào `recognition_report.json`
- Ví dụ: measure duration mismatch, missing clef, etc.

---

## 6. GIAI ĐOẠN 4 — OCR NHẬN DẠNG LỜI CA TIẾNG VIỆT

### 6.1 Kiến trúc OCR Ensemble

```
Zone 3 (Lyric Bands)
        │
        ├──► RapidOCR (Primary)
        │    - Nhanh, độ chính xác cao cho chữ in rõ
        │    - Confidence score: 0.0 → 1.0
        │
        ├──► Tesseract (lang=vie+eng) (Secondary)
        │    - Model vie được upscale crop giữ dấu
        │    - Chạy trên crop 2x để bảo toàn dấu thanh
        │
        └──► Consensus Voting
             - So sánh kết quả 2 engine
             - Normalize: bỏ dấu để so chuỗi cơ sở
             - Nếu chuỗi bỏ dấu giống nhau (similarity >= 0.86):
               → Ưu tiên candidate có dấu tiếng Việt
               → Confidence gốc giữ nguyên (không inflate)
             - Nếu khác nhau: giữ confidence gốc, đánh dấu needs_review
```

### 6.2 Phục hồi dấu thanh tiếng Việt (Vietnamese Context)

```python
# vietnamese_context.py — Vietnamese Tonal Context Recovery

# Nguyên tắc: KHÔNG đoán từ đơn mơ hồ, chỉ phục hồi theo cụm ngữ cảnh
# Ví dụ đúng:
"NGOI CA" → "NGỢI CA"                              # 2-word phrase
"hat khen ngoi Chua tren troi" → "hát khen ngợi Chúa trên trời"

# Ví dụ sai (không làm):
"ca" → ???                                          # Từ đơn mơ hồ

# Context tracking:
context_changes = [
  {"token": "NGOI", "from": "NGOI", "to": "NGỢI", "source": "hymn_phrase_db"}
]
```

### 6.3 Schema Artifact lyrics.json

```json
{
  "schema_version": 1,
  "artifact_type": "lyrics_ocr",
  "alignment_status": "unreviewed",
  "word_count": 87,
  "words": [
    {
      "id": "p1-w1",
      "page": 1,
      "staff_index": 0,
      "verse_number": 1,
      "sequence": 1,
      "text": "Hỡi",
      "x": 142.5,
      "y": 380.2,
      "box": [135, 372, 168, 395],
      "confidence": 0.94,
      "ocr_engine": "rapidocr",
      "raw_ocr": "Hỡi",
      "context_changes": [],
      "alignment": null
    }
  ],
  "verses": {
    "1": ["..."],
    "2": ["..."],
    "3": ["..."],
    "4": ["..."]
  }
}
```

> **QUY TẮC BẤT BIẾN:** `lyrics.json` là artifact độc lập.
> MusicXML nốt KHÔNG phụ thuộc artifact này.
> `notation_with_lyrics.musicxml` chỉ là dẫn xuất — có thể tái tạo bất kỳ lúc nào.

---

## 7. GIAI ĐOẠN 5 — CĂN LỜI VÀO NỐT (LYRICS ALIGNMENT)

### 7.1 Thuật toán Needleman-Wunsch Monotonic DP

```
Bài toán: Ghép W words (OCR) → N notes (MusicXML) tối ưu theo không gian
Ràng buộc: Monotonic (không đảo thứ tự nốt/lời)

Ma trận DP: dp[i][j] = cost tốt nhất để ghép i words với j notes

Transitions:
  MATCH    : dp[i-1][j-1] + spatial_cost + ocr_penalty
  SKIP_NOTE: dp[i][j-1]   + 0.34   (nốt không có lời: melisma, tied)
  SKIP_WORD: dp[i-1][j]   + 1.15   (lời OCR sai: penalty cao hơn)

Trong đó:
  spatial_cost = |normalized_x_word - normalized_x_note|
  ocr_penalty  = (1.0 - ocr_confidence) × 0.35
```

### 7.2 Normalized Position Mapping

```python
# Chuẩn hoá toạ độ X về [0, 1] trong từng hàng (staff-row)
# Nhằm so sánh vị trí OCR words và MusicXML notes cùng thang đo

note_x_norm = (note.default_x - min_x) / (max_x - min_x)
word_x_norm = (word.x - min_x) / (max_x - min_x)

# Trường hợp đặc biệt: 1 word, nhiều notes
# → Tìm note gần nhất theo x
```

### 7.3 Ngưỡng chấp nhận và Syllabic

```python
# Điểm kết hợp:
ocr_confidence  = word['confidence']                # từ OCR engine
spatial_conf    = exp(-2.4 × spatial_error)         # giảm nhanh khi xa
combined_score  = ocr_confidence × spatial_conf

# Quyết định:
if combined_score >= 0.55:
    status = "accepted"  # Ghi vào MusicXML
else:
    status = "review"    # Giữ trong lyrics.json, đánh dấu needs_review

# Phân loại âm tiết (syllabic):
"-Thánh" → syllabic="end"
"Thánh-" → syllabic="begin"
"-Thánh-" → syllabic="middle"
"Thánh"  → syllabic="single"
```

### 7.4 Note Eligibility (Nốt được nhận lời)

```python
# Nốt ĐƯỢC nhận lời:
eligible(note) = True khi:
  - Không phải <rest/>
  - Không phải <chord/> (chord continuation note)
  - Không phải <grace/> (grace note)
  - Không phải tied-continuation (tie stop, không có tie start)

# Nốt KHÔNG nhận lời:
  - Nốt lặng → bỏ qua (SKIP_NOTE cost=0.34)
  - Nốt nối (tied) → bỏ qua
  - Nốt melisma (phụ âm dài kéo nhiều nốt) → SKIP_NOTE
```

---

## 8. GIAI ĐOẠN 6 — XỬ LÝ GIỌNG BÈ & ĐA BÈ (MULTI-VOICE / MULTI-PART)

### 8.1 Mô hình bè trong MusicXML

```xml
<!-- Ví dụ bản nhạc SATB (4 giọng) hoặc đàn Piano -->

<part id="P1">  <!-- Giai điệu chính / Soprano -->
  <measure number="1">
    <note>
      <voice>1</voice>    <!-- Voice 1: soprano (đầu nốt hướng lên) -->
      <staff>1</staff>    <!-- Khuông treble -->
      ...
    </note>
    <note>
      <voice>2</voice>    <!-- Voice 2: alto (đầu nốt hướng xuống) -->
      <staff>1</staff>
      ...
    </note>
  </measure>
</part>

<part id="P2">  <!-- Bè trầm / Bass -->
  <measure number="1">
    <note>
      <voice>1</voice>    <!-- Voice 1 trong P2: tenor -->
      <staff>2</staff>    <!-- Khuông bass -->
      ...
    </note>
    <note>
      <voice>2</voice>    <!-- Voice 2 trong P2: bass -->
      <staff>2</staff>
      ...
    </note>
  </measure>
</part>
```

### 8.2 Quy tắc gán lời cho giọng bè

```
NGUYÊN TẮC: Lời chính gắn vào P1 (Giai điệu / Soprano)

Lý do:
  - Bản thánh ca Việt: lời chủ yếu hát theo giai điệu P1
  - Audiveris nhận dạng lời và tự động gắn vào giai điệu chính
  - lyrics_aligner.py: chỉ xử lý parts[0] = P1

Trường hợp đặc biệt:
  - Nếu bản nhạc có lời riêng cho từng bè → Verse number khác nhau
    * P1/Voice 1: verse="1" (Soprano lyrics)
    * P1/Voice 2: verse="2" (Alto lyrics, nếu có)
    * P2: không có lyric (nhạc đệm)
  - Nếu dò thấy text bands riêng biệt cho từng bè → tạo verse số tương ứng
```

### 8.3 Phát hiện số bè tự động

```python
def detect_voice_structure(musicxml_path):
    parts = []
    for part in root.iter('part'):
        voices = set()
        staves = set()
        for note in part.iter('note'):
            voice = note.find('voice')
            staff = note.find('staff')
            if voice is not None: voices.add(voice.text)
            if staff is not None: staves.add(staff.text)
        parts.append({
            'part_id': part.get('id'),
            'voice_count': len(voices),
            'staff_count': len(staves)
        })
    return parts

# Ví dụ Golden Reference:
# P1: voice_count=2, staff_count=1 (treble, soprano+alto)
# P2: voice_count=2, staff_count=1 (bass, tenor+bass)
```

### 8.4 Chiến lược lyric cho từng loại bè

| Cấu trúc | P1 | P2 | Verse Mapping |
|---|---|---|---|
| Đơn ca (1 part, 1 voice) | lời đầy đủ | — | verse 1..N |
| Thánh ca (2 parts, 2 voices each) | verse 1 (soprano) | không có lời | verse 1..N chỉ P1 |
| SATB chép đơn (4 parts) | P1=S, P2=A | P3=T, P4=B | verse 1 cho tất cả, hoặc riêng |
| Đàn đệm (voice melody + chord) | lời đầy đủ | không có lời | verse 1..N |

---

## 9. GIAI ĐOẠN 7 — HỢP ÂM (HARMONY / CHORD)

### 9.1 OCR hợp âm từ ảnh

```
Chord symbols thường nằm:
  - Phía TRÊN khuông (trên staff top)
  - Trong header zone
  - Đôi khi xen kẽ với notation (Audiveris nhận dạng trực tiếp)

Pipeline nhận dạng hợp âm:
1. Tesseract / RapidOCR trên vùng trên khuông
2. Regex match chord pattern:
   [A-G][#b]?(m|M|maj|min|dim|aug|sus|add)?[0-9]*(/[A-G][#b]?)?
3. Chord parser → phân rã thành Root, Kind, Extension, Bass
```

### 9.2 Chord Parser Algorithm

```
Input: "D7#5/F#"

Bước 1: Tách slash chord
  root_part = "D7#5"
  bass_part = "F#"

Bước 2: Parse root
  step = "D",  alter = 0 (không có # hay b)

Bước 3: Parse quality
  "m"    → kind = "minor"
  "maj"  → kind = "major"
  "dim"  → kind = "diminished"
  "aug"  → kind = "augmented"
  "sus2" → kind = "suspended-second"
  "sus4" → kind = "suspended-fourth"
  ""     → kind = "major" (default)

Bước 4: Parse extensions
  "7"   → <degree>7, add</degree>
  "maj7"→ <degree>7, major</degree>
  "#5"  → <degree>5, sharp alter</degree>
  "b9"  → <degree>9, flat</degree>
  "add9"→ <degree>9, add</degree>

Bước 5: Parse bass (slash chord)
  bass-step = "F",  bass-alter = 1 (sharp)

Output MusicXML:
<harmony>
  <root>
    <root-step>D</root-step>
    <root-alter>0</root-alter>
  </root>
  <kind>dominant</kind>
  <degree>
    <degree-value>5</degree-value>
    <degree-alter>1</degree-alter>
    <degree-type>alter</degree-type>
  </degree>
  <bass>
    <bass-step>F</bass-step>
    <bass-alter>1</bass-alter>
  </bass>
</harmony>
```

### 9.3 Chord Anchor (gắn vị trí hợp âm)

```python
# Hợp âm KHÔNG lưu theo pixel
# Phải anchor theo measure:beat_offset

# Cách xác định beat_offset từ x-position:
beat_offset = (chord_x - measure_start_x) / measure_width * beats_per_measure

# Ví dụ: nhịp 3/4, hợp âm ở giữa nhịp
beat_offset = 1.5  # Phách thứ 2

# MusicXML:
<harmony default-x="145.2">
  <root>...</root>
  <kind>major</kind>
  <offset>1.5</offset>
</harmony>
```

---

## 10. GIAI ĐOẠN 8 — GHÉP TRANG PDF NHIỀU TRANG

### 10.1 Page Checkpoint (Resume an toàn)

```json
{
  "total_pages": 4,
  "completed": [1, 2, 3],
  "pending": [4],
  "failed": [],
  "pages": {
    "1": {
      "status": "done",
      "raw_musicxml": "pages/page-1/raw.musicxml",
      "lyrics_artifact": "pages/page-1/lyrics.json"
    }
  }
}
```

Nếu crash ở trang 4: chỉ xử lý lại trang 4, không tái nhận diện trang 1-3.

### 10.2 DOM Merge Algorithm

```
Input: [page1.musicxml, page2.musicxml, page3.musicxml, ...]
Output: merged.musicxml

Thuật toán:
1. Parse từng file thành DOM tree (lxml — không round-trip qua music21)
2. Lấy page1 làm base (deep copy)
3. Với mỗi page tiếp theo (page_k):
   a. Đọc tất cả <part> theo part_id
   b. Với mỗi part_id tìm thấy trong merged:
      - Lấy tất cả <measure> từ page_k
      - Đánh lại số measure (tiếp theo số cuối của merged)
      - Thêm <print new-page="yes"/> vào measure đầu tiên
      - Append vào merged part tương ứng
   c. Nếu page_k có part_id mới:
      - Thêm vào <part-list> và append part mới
4. Ghi ra merged.musicxml

Đảm bảo:
  ✓ Giữ toàn bộ voices (1, 2, 3, 4...)
  ✓ Giữ toàn bộ staves (staff 1, 2...)
  ✓ Giữ toàn bộ lyrics (tất cả verse)
  ✓ Giữ page boundary (new-page marker)
  ✗ KHÔNG round-trip qua music21 (tránh mất dữ liệu)
  ✗ KHÔNG fallback về trang 1 khi merge thất bại
```

---

## 11. GIAI ĐOẠN 9 — KIỂM ĐỊNH (VALIDATION)

### 11.1 Các lớp kiểm định

```
Lớp 1: XML Well-Formed
  - lxml etree.parse() không exception
  - UTF-8 encoding hợp lệ
  - Dấu thanh tiếng Việt được preserve

Lớp 2: MusicXML Schema
  - Kiểm tra thẻ bắt buộc: <score-partwise>, <part-list>, <part>, <measure>
  - Kiểm tra attributes: measure@number, part@id

Lớp 3: Music Theory Semantics (music21)
  - Measure duration: sum(note.duration) == time_sig.beats
  - Cảnh báo underfull: thiếu nốt/lặng trong ô nhịp
  - Cảnh báo overfull: quá nhiều nốt trong ô nhịp
  - Pitch range: C0 <= pitch <= C9
  - Voice: không trùng lặp onset trong cùng voice

Lớp 4: Lyric Consistency
  - Lyric orphan: <lyric> gắn vào note không tồn tại
  - Missing verse: verse 2 tồn tại nhưng verse 1 rỗng
  - Syllabic chain: begin → middle* → end phải liên tục

Lớp 5: Harmony
  - <harmony> có <root> hợp lệ
  - <kind> là giá trị hợp lệ trong MusicXML spec
  - Slash chord: <bass> hợp lệ nếu có

Lớp 6: OSMD Render Test
  - Load MusicXML vào OpenSheetMusicDisplay
  - Kiểm tra không exception khi parse
  - Nếu OSMD không render → không đánh dấu READY
```

### 11.2 Severity Levels

| Severity | Mô tả | Hành động |
|---|---|---|
| `ERROR` | Lỗi ngăn export | Block export, hiển thị đỏ |
| `WARNING` | Vấn đề nhạc lý | Hiển thị vàng, cho phép export |
| `INFO` | Thông tin tham khảo | Hiển thị xanh nhạt |

---

## 12. GIAI ĐOẠN 10 — XUẤT 3 CHẾ ĐỘ (EXPORT)

### Chế độ A: CHỈ NỐT NHẠC (Notation Only)

```
Trigger: detect_lyrics=false hoặc export option "Chỉ nốt nhạc"

Thuật toán (write_notation_only):
  Input: current.musicxml
  Output: score_notation_only.musicxml

  Xoá khỏi DOM:
    <lyric>           → XÓA (tất cả verse)
    <lyric-font>      → XÓA
    <lyric-language>  → XÓA
    <harmony>         → XÓA (chord symbols)
    <direction>       → XÓA (dynamics, tempo text)
    <figured-bass>    → XÓA
    <ornaments>       → XÓA (nhưng giữ tie/slur/beam)
    <articulations>   → XÓA
    <technical>       → XÓA
    <fermata>         → XÓA

  Giữ nguyên:
    <note>     ← GIỮ (tất cả nốt, pitch, duration)
    <rest>     ← GIỮ (nốt lặng)
    <tie>      ← GIỮ (nối nốt)
    <slur>     ← GIỮ (legato)
    <beam>     ← GIỮ (chùm nốt)
    <clef>     ← GIỮ (khoá nhạc)
    <key>      ← GIỮ (giọng nhạc)
    <time>     ← GIỮ (nhịp)
    <voice>    ← GIỮ (giọng bè)
    <staff>    ← GIỮ (khuông nhạc)
    <part>     ← GIỮ (tất cả parts / bè)
    <measure>  ← GIỮ (tất cả ô nhịp)

  Dọn dẹp: Xoá thẻ <notations/> rỗng sau khi strip biểu cảm

  Lưu ý đặc biệt về GIỌNG BÈ:
    → Giữ toàn bộ P1, P2, ..., Pn
    → Giữ toàn bộ voice 1, 2, 3, 4 trong mỗi part
    → Bản instrumentalist vẫn đọc được đầy đủ
```

### Chế độ B: LỜI RIÊNG (Lyrics Only)

```
Trigger: Export option "Lời riêng"

Output 1: lyrics_only.txt
─────────────────────────────────────────────
[Verse 1]
Hỡi Thánh Vương kíp ngự lai
Đến thăm viếng trần ai...

[Verse 2]
Ngôi lời nhập thể trần gian
Xuống thăm chốn lưu đày...
─────────────────────────────────────────────

Output 2: lyrics_only.json (structured)
{
  "title": "HỠI THÁNH VƯƠNG, KÍP NGỰ LAI",
  "total_verses": 4,
  "verses": {
    "1": [
      {"measure": "2", "note_index": 1, "text": "Hỡi", "syllabic": "single"},
      ...
    ]
  }
}

Thuật toán extract:
  for part in musicxml.parts:
    for measure in part.measures:
      for note in measure.notes:
        for lyric in note.lyrics:
          verse_number = lyric.number
          text = lyric.text
          syllabic = lyric.syllabic
          append(verses[verse_number], {measure, note_index, text, syllabic})
  
  # Ghép syllabic thành từ đầy đủ:
  "begin-Thá" + "middle-" + "end-nh" → "Thánh"
```

### Chế độ C: ĐẦY ĐỦ (Full Score)

```
Trigger: Export mặc định

Output: score_full.musicxml / score_full.mxl

Giữ toàn bộ:
  ✓ Tất cả nốt (tất cả parts, voices, staves)
  ✓ Lời (tất cả verses: 1, 2, 3, 4...N)
  ✓ Hợp âm <harmony>
  ✓ Chỉ dẫn biểu cảm <direction> (dynamics, tempo)
  ✓ Khoá, giọng, nhịp, tempo
  ✓ Metadata (title, composer, date)

Đóng gói .mxl (ZIP container):
  mxl_archive/
    META-INF/
      container.xml   ← trỏ đến score_full.musicxml
    score_full.musicxml
```

---

## 13. CẤU TRÚC DỮ LIỆU MUSICXML CHUẨN

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN"
  "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">

  <!-- Metadata -->
  <work>
    <work-number>001</work-number>
    <work-title>HỠI THÁNH VƯƠNG, KÍP NGỰ LAI</work-title>
  </work>

  <!-- Danh sách bè -->
  <part-list>
    <score-part id="P1">
      <part-name>Soprano/Alto</part-name>
    </score-part>
    <score-part id="P2">
      <part-name>Tenor/Bass</part-name>
    </score-part>
  </part-list>

  <!-- Part 1: Giai điệu + Lời -->
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>1</fifths></key>         <!-- G Major -->
        <time>
          <beats>3</beats>
          <beat-type>4</beat-type>             <!-- 3/4 -->
        </time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>

      <!-- Nốt Voice 1 (Soprano) với lời -->
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <voice>1</voice>
        <type>quarter</type>
        <lyric number="1">
          <syllabic>single</syllabic>
          <text>Hỡi</text>
        </lyric>
        <lyric number="2">
          <syllabic>single</syllabic>
          <text>Ngôi</text>
        </lyric>
      </note>

      <!-- Nốt Voice 2 (Alto) — không có lời riêng -->
      <note>
        <chord/>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <voice>2</voice>
        <type>quarter</type>
      </note>

      <!-- Hợp âm -->
      <harmony>
        <root><root-step>G</root-step></root>
        <kind>major</kind>
      </harmony>
    </measure>
  </part>

  <!-- Part 2: Bè trầm (không có lời) -->
  <part id="P2">
    <measure number="1">
      <attributes>
        <clef><sign>F</sign><line>4</line></clef>
      </attributes>
      <note>
        <pitch><step>G</step><octave>2</octave></pitch>
        <duration>4</duration>
        <voice>1</voice>
        <type>quarter</type>
      </note>
    </measure>
  </part>

</score-partwise>
```

---

## 14. SƠ ĐỒ LUỒNG DỮ LIỆU TỔNG THỂ

```
PDF / JPG / PNG
      │
      ▼
[Tách trang] ─── page_checkpoint.json (resume)
      │
      ▼ (từng trang)
[Pipeline OpenCV]
  Grayscale → Shadow removal → Deskew → CLAHE → Denoise
      │
      ├────────────────────────────────────────┐
      │ Zone 2: Notation Image                 │ Zone 3: Lyrics Bands
      ▼                                        ▼
[Audiveris OMR]                          [OCR Ensemble]
  Staff detect                            RapidOCR + Tesseract
  Notes / Rests                           Vietnamese context recovery
  Voices / Parts                          Syllable segmentation
  Clef / Key / Time                            │
      │                                        │
      ▼                                        ▼
raw_page_{n}.musicxml                    lyrics_{n}.json (artifact)
  (IMMUTABLE)                              (IMMUTABLE)
      │                                        │
      └─────────────────┬──────────────────────┘
                        ▼
               [Lyrics Alignment — DP]
               Needleman-Wunsch Monotonic
               Spatial + OCR confidence scoring
               Ngưỡng >= 0.55
                        │
                        ▼
          notation_with_lyrics_{n}.musicxml
                        │
                        ▼ (sau khi xử lý tất cả trang)
               [Page Merger — DOM lxml]
               Không round-trip qua music21
               Giữ all parts/voices/staves/lyrics
                        │
                        ▼
                  merged.musicxml
                        │
                        ▼
               [Chord Injection]
               Gắn <harmony> vào measure:beat
                        │
                        ▼
                  current.musicxml ←── [User Edits: Lyric/Note/Chord]
                        │
                        ▼
               [Validation — music21 + lxml]
               XML → Schema → Music Theory → OSMD
                        │
               ┌────────┼────────────────┐
               ▼        ▼                ▼
    [Option A]      [Option B]      [Option C]
  Notation Only   Lyrics Only      Full Score
  score_notation  lyrics_only      score_full
  _only.musicxml  .txt/.json       .musicxml/.mxl
```

---

## 15. BẢNG QUYẾT ĐỊNH 3 CHẾ ĐỘ XUẤT

| Thành phần | Option A (Chỉ nốt) | Option B (Lời riêng) | Option C (Đầy đủ) |
|---|---|---|---|
| Nốt nhạc `<note>` | ✅ Giữ nguyên | — | ✅ Giữ nguyên |
| Nốt lặng `<rest>` | ✅ Giữ nguyên | — | ✅ Giữ nguyên |
| Khoá nhạc `<clef>` | ✅ | — | ✅ |
| Giọng nhạc `<key>` | ✅ | — | ✅ |
| Nhịp `<time>` | ✅ | — | ✅ |
| Voice 1, 2, 3, 4 | ✅ Tất cả | — | ✅ Tất cả |
| Part 1, 2, ..., N (bè) | ✅ Tất cả | — | ✅ Tất cả |
| Nối nốt `<tie>` | ✅ | — | ✅ |
| Slur / Legato | ✅ | — | ✅ |
| Chùm nốt `<beam>` | ✅ | — | ✅ |
| Lời Verse 1..N `<lyric>` | ❌ Xoá | ✅ Xuất riêng | ✅ Giữ nguyên |
| Hợp âm `<harmony>` | ❌ Xoá | ❌ | ✅ Giữ nguyên |
| Chỉ dẫn `<direction>` | ❌ Xoá | ❌ | ✅ Giữ nguyên |
| Biểu cảm (dynamics) | ❌ Xoá | ❌ | ✅ Giữ nguyên |
| Format output | `.musicxml` | `.txt` + `.json` | `.musicxml` / `.mxl` |
| Dùng cho | Nhạc sĩ soạn đệm | Học lời/karaoke | Xuất bản hoàn chỉnh |

---

## 16. XỬ LÝ LỖI & FALLBACK

### 16.1 Fallback Strategy

```
Lỗi Audiveris (OMR thất bại):
  ├── Retry với ảnh preprocessing khác nhau
  ├── Thử ENABLE_EXPERIMENTAL_CV_FALLBACK=1 (CV OMR)
  └── Dừng trung thực, báo lỗi rõ ràng cho người dùng
      KHÔNG tự sinh nốt suy đoán

Lỗi OCR tiếng Việt (lyrics.json rỗng hoặc thiếu):
  ├── Giữ raw.musicxml không có lời
  ├── Đánh dấu alignment_status = "unreviewed"
  └── Để người dùng nhập lời thủ công trong Editor

Lỗi Alignment (confidence < 0.55):
  ├── Giữ word trong lyrics.json với status = "review"
  ├── Hiển thị trong IssuePanel với cảnh báo vàng
  └── Không ghi vào MusicXML (không sinh lời sai)

Lỗi Merge trang (page_merger thất bại):
  └── Dừng, báo lỗi trang cụ thể, cho phép retry từ checkpoint

Lỗi Validation:
  ├── ERROR → Block export, hiển thị đỏ cụ thể
  └── WARNING → Cho phép export với cảnh báo
```

### 16.2 Thông báo lỗi thân thiện

```
❌ "Không nhận diện được khuông nhạc ở trang 2"
   Gợi ý: Xoay lại ảnh · Crop sát bản nhạc · Dùng ảnh >= 300 DPI

⚠️ "15 âm tiết chưa khớp nốt (Verse 2, trang 1)"
   Gợi ý: Mở Lyrics Editor để sửa thủ công · Dùng Move Lyric

⚠️ "Ô nhịp số 8 thiếu 1 phách (underfull)"
   Gợi ý: Kiểm tra nốt lặng bị mất · Sửa trong Note Editor
```

---

## 17. ĐIỂM KIỂM CHẤT LƯỢNG (QUALITY CHECKPOINTS)

### Checkpoint 1: Sau Tiền xử lý ảnh
- [ ] Ảnh output không mờ hơn ảnh input
- [ ] Không có viền đen sau deskew (BORDER_REPLICATE)
- [ ] Khuông nhạc vẫn nhìn thấy rõ ràng

### Checkpoint 2: Sau OMR (Audiveris)
- [ ] `raw.musicxml` tồn tại và parseable
- [ ] `source.omr` được lưu
- [ ] Số measure ≈ số measure đếm tay từ ảnh gốc
- [ ] Số nốt / part hợp lý

### Checkpoint 3: Sau OCR Lời
- [ ] `lyrics.json` tồn tại với đúng số verse
- [ ] Dấu thanh tiếng Việt bảo toàn (UTF-8)
- [ ] Số word ≈ số âm tiết đếm tay từ ảnh

### Checkpoint 4: Sau Alignment
- [ ] Tỷ lệ `accepted` / `total` >= 70% (ngưỡng chất lượng tốt)
- [ ] Không có syllabic chain bị đứt (begin không có end)
- [ ] Verse 1..N đều có dữ liệu

### Checkpoint 5: Sau Validation
- [ ] 0 lỗi XML (ERROR severity)
- [ ] OSMD parse thành công
- [ ] Golden Reference test: `001 HỠI THÁNH VƯƠNG.xml` vẫn pass

### Checkpoint 6: Export
- [ ] File `.mxl` mở được bằng SheetApp / OSMD
- [ ] Notation-only không có `<lyric>` thừa
- [ ] Lyrics-only có đủ N verse
- [ ] Full score có đủ notes + lyrics + harmony

---

## PHỤ LỤC A — BẢNG KÝ HIỆU NHẠC & MusicXML MAPPING

| Ký hiệu | Tên | MusicXML | Ghi chú |
|---|---|---|---|
| Sol clef | Khoá Sol | `<clef sign="G" line="2"/>` | Treble clef |
| Fa clef | Khoá Fa | `<clef sign="F" line="4"/>` | Bass clef |
| # | Thăng | `<key><fifths>1</fifths></key>` | G Major |
| b | Giáng | `<key><fifths>-1</fifths></key>` | F Major |
| 3/4 | Nhịp 3/4 | `<beats>3</beats><beat-type>4` | |
| Quarter | Nốt đen | `<type>quarter</type>` | duration=4 (if div=4) |
| Eighth | Nốt móc | `<type>eighth</type>` | |
| Half | Nốt trắng | `<type>half</type>` | |
| Whole | Nốt tròn | `<type>whole</type>` | |
| . | Nốt chấm | `<dot/>` | Thêm vào sau type |
| Tie | Liên kết | `<tie type="start/stop"/>` | |
| Slur | Legato | `<slur type="start/stop"/>` | |
| Rest | Nốt lặng | `<note><rest/><type>quarter` | |

---

## PHỤ LỤC B — CẤU TRÚC FILE DỰ ÁN

```
storage/projects/{uuid}/
├── source/
│   └── original.pdf          ← BẤT BIẾN
│
├── pages/
│   ├── page-001.png          ← Trang gốc (BẤT BIẾN sau tách)
│   ├── page-001-prep.png     ← Sau tiền xử lý
│   └── page-checkpoint.json  ← Resume PDF nhiều trang
│
├── omr/
│   ├── source.omr            ← BẤT BIẾN (Audiveris project file)
│   ├── raw_page_1.musicxml   ← BẤT BIẾN
│   └── raw_page_2.musicxml   ← BẤT BIẾN
│
├── ocr/
│   ├── lyrics_page_1.json    ← BẤT BIẾN
│   └── lyrics_page_2.json    ← BẤT BIẾN
│
├── musicxml/
│   ├── raw.musicxml          ← BẤT BIẾN (merge của raw pages)
│   ├── normalized.musicxml   ← Sau alignment lời
│   ├── current.musicxml      ← Mutable (user edits)
│   └── final.musicxml        ← Generated (khi export)
│
├── export/
│   ├── score_full.musicxml
│   ├── score_full.mxl
│   ├── score_notation_only.musicxml
│   └── lyrics_only.txt
│
└── logs/
    ├── audiveris.log
    ├── validation.log
    └── recognition_report.json   ← confidence stats
```

---

## PHỤ LỤC C — THÔNG SỐ GOLDEN REFERENCE

Dựa trên file `001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml`:

```
Title:      HỠI THÁNH VƯƠNG, KÍP NGỰ LAI
Parts:      2 (P1: Soprano/Alto, P2: Tenor/Bass)
Measures:   16 / part
Key:        G Major (1 dấu thăng)
Time:       3/4 (3 phách, nốt đen = 1 phách)
Tempo:      104 BPM
Voices:     2 / part (Voice 1 + Voice 2)
Lyrics:     4 verse (Verse 1, 2, 3, 4)
Harmony:    17 thẻ <harmony>
Clefs:      G clef (treble) + F clef (bass)
Slurs:      Có
Dotted:     Có
Accidentals:Có

Test Cases phải PASS:
  ✓ Parse 4 Verse lời tiếng Việt từ XML
  ✓ Extract 17 thẻ <harmony>
  ✓ Phân tích Slash Chord G/B → Root=G, Bass=B
  ✓ Project lifecycle Upload → READY
  ✓ Export score_export.musicxml
  ✓ Bảo tồn dấu thanh tiếng Việt UTF-8
```

---

*Tài liệu này được tạo bởi Antigravity IDE dựa trên phân tích toàn bộ codebase SheetTools.*  
*Cập nhật theo NEXUS.md khi có thay đổi kiến trúc.*
