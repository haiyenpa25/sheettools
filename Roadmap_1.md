# ROADMAP 1 — Ảnh/PDF → MusicXML: Tách lớp Tiêu đề · Nhạc · Hợp âm · Lời

> Ngày lập: 2026-10-04 · Phạm vi: pipeline nhận dạng trong `workers/` (OMR + OCR + căn lời) · Không đụng tới UI ngoài phần review cần thiết.
> Nguyên tắc giữ nguyên từ NEXUS: **source bất biến**, **raw.musicxml bất biến**, mọi xử lý tạo **artifact dẫn xuất**, **không tuyên bố độ chính xác khi chưa có ground truth**.

---

## 0. Tóm tắt

Hướng bạn đề xuất là đúng và khớp cách các hệ lớn làm (Audiveris cũng phân **vai trò chữ**: Title / Creator / Direction / ChordName / Lyrics…). Hệ thống hiện tại **đã có khung 3 vùng** nhưng phân loại chữ còn dựa vào **nội dung token** thay vì **vị trí + cấu trúc**, và **chưa có mô hình cấu trúc lời** (lời 1..N / điệp khúc / coda). Đó là hai chỗ làm hỏng chất lượng nhiều nhất.

Phương án đề xuất — **"Đọc 1 lần, gán vai trò, bóc từng lớp, ráp lại theo neo pixel"**:

```
Trang ảnh
  │
  ├─ B1  Bố cục: khuông → hệ (system) → các dải (band) quanh mỗi hệ
  ├─ B2  OCR toàn trang 1 lần → mỗi dòng chữ được gán VAI TRÒ (title, composer, note, tempo, chord, verse-marker, lyric, direction, footer…)
  ├─ B3  Metadata: đọc tựa / tác giả / ghi chú → ghi document.json → che (mask) trên ảnh dẫn xuất
  ├─ B4  Lớp NHẠC: ảnh đã che chữ → Audiveris → raw.musicxml + .omr (toạ độ pixel của từng nốt)
  ├─ B5  Lớp HỢP ÂM: chữ ở dải trên khuông + ngữ pháp hợp âm chặt → neo vào phách
  ├─ B6  Lớp LỜI – CẤU TRÚC: đếm số dòng lời mỗi hệ → phân đoạn bài thành [Lời 1..N] / [Điệp khúc] / [Coda]
  ├─ B7  Lớp LỜI – CĂN NỐT: âm tiết ↔ nốt bằng DP trên toạ độ pixel thật (từ .omr), xử lý luyến/melisma
  └─ B8  Ráp MusicXML: <credit>/<work>, <harmony>, <lyric number name>, <extend>; validate; hàng đợi soát
```

Đầu ra là **2 bảng (2 file) như bạn muốn** + 1 file ghép:
- `notation.musicxml` — chỉ nhạc (+ hợp âm nếu có), không lời.
- `lyrics.json` — lời có cấu trúc: section → verse → dòng → âm tiết, mỗi âm tiết có bbox + neo nốt + confidence.
- `score.musicxml` — ghép 2 bảng trên, tái tạo được bất cứ lúc nào.

---

## 1. Đánh giá hệ thống hiện tại

### 1.1 Luồng hiện có

[workers/audiveris_runner.py:360](workers/audiveris_runner.py#L360) `process()`:
1. PDF → PNG từng trang (300 DPI), checkpoint theo trang — **tốt**.
2. `preprocess_image` (CLAHE/denoise theo profile chất lượng) — **tốt**.
3. `PageLayoutAnalyzer` sinh `page_NNN_regions.json` — **chỉ để debug, không được dùng ở bước sau**.
4. `decompose_sheet_3zones` ([vietnamese_universal_ocr.py:376](workers/xml_tools/vietnamese_universal_ocr.py#L376)): dò khuông, OCR (RapidOCR + Tesseract + VietOCR tuỳ chọn), chia header / hợp âm / lời theo khuông, tạo ảnh `pure_notation.png`.
5. Audiveris chạy trên ảnh đã che chữ; chạy thêm lần 2 trên ảnh đầy đủ để lấy direction/harmony (dual-layer).
6. `align_lyrics_artifact` ([lyrics_aligner.py:177](workers/xml_tools/lyrics_aligner.py#L177)): DP đơn điệu căn âm tiết ↔ nốt theo từng (trang, khuông, verse).

### 1.2 Điểm mạnh (giữ nguyên)

| Điểm | Vị trí |
|---|---|
| Artifact bất biến, raw không bị ghi đè, checkpoint/retry theo trang | `audiveris_runner.py`, `StorageService` |
| Che chữ **bảo thủ**: không bao giờ xoá trong hành lang khuông ±2 interline | [notation_layers.py](workers/preprocessing/notation_layers.py) |
| Lời là artifact riêng `lyrics.json` có bbox, candidate, confidence; chỉ chèn vào XML khi đủ ngưỡng | `write_lyrics_artifact`, `lyrics_aligner.py` |
| DP căn lời cho phép bỏ nốt (melisma) / bỏ token (rác OCR) | `_align_group` |
| Không dùng confidence thay cho accuracy; có `accuracy_report.py` đo CER/WER khi có ground truth | `workers/evaluation/` |

### 1.3 Lỗi và điểm yếu cụ thể (đã đọc code; mục có ⚠ đã chạy thử để xác nhận)

| # | Vấn đề | Vị trí | Hậu quả |
|---|---|---|---|
| E1 ⚠ | **Bộ nhận hợp âm nuốt chữ tiếng Việt.** Regex cho phép gốc chữ thường và đuôi `[A-Ga-g]`, nên `ca, em, ba, da, ga, be, de, Em, Ba, Da` đều bị coi là hợp âm (đã chạy thử, cả 10 từ đều khớp). | [vietnamese_universal_ocr.py:421-432](workers/xml_tools/vietnamese_universal_ocr.py#L421-L432) | Chữ "ca" (ngợi ca, ca hát), "em", "ba"… **biến mất khỏi lời** và bị ghi thành hợp âm giả. |
| E2 | Phân loại hợp âm/lời **dựa vào nội dung**, không dựa vào **vị trí** (hợp âm nằm *trên* khuông, lời nằm *dưới*). | cùng hàm | Lỗi E1 không thể sửa triệt để chỉ bằng regex. |
| E3 | Hợp âm của **hệ đầu tiên** (nằm trên khuông 1) bị xếp vào header rồi bị lọc bỏ — không vào `harmony_boxes`. | điều kiện `cy < first_staff_top - 0.8*interline` | Mất toàn bộ hợp âm hệ đầu. |
| E4 | `verse_number` = **thứ tự dòng trong từng khuông**, không có mô hình toàn bài. Không đọc dấu "1.", "2.", "ĐK", "Điệp khúc", "Coda". | khối "Zone 3" trong cùng hàm | Điệp khúc 1 dòng bị gán nhầm là "Lời 1"; khi số dòng thay đổi giữa các hệ, số lời bị lệch. |
| E5 | Gom dòng lời theo ngưỡng cứng **28 px** và trung bình chạy (greedy). | `abs(it['cy'] - avg_y) < 28` | Phụ thuộc DPI; ảnh chụp điện thoại hay scan 200/600 DPI sẽ gộp/tách sai dòng. |
| E6 | Dải lời của khuông kết thúc ở **trung điểm** tới khuông kế. Với hợp xướng/piano (2 khuông/hệ) có 3–4 lời nằm giữa 2 khuông, các dòng dưới có thể vượt trung điểm → rơi vào `other_boxes` (bị bỏ). *Cần kiểm chứng trên mẫu SATB.* | tính `lyric_bottom` | Có thể mất lời 3, 4 trong thánh ca 4 bè. |
| E7 | Căn lời dùng `default-x` + `measure width` của MusicXML (đơn vị tenths) rồi **chuẩn hoá min–max** cùng toạ độ OCR (pixel). Dòng lời bắt đầu giữa hệ (nhịp lấy đà, lời chỉ phủ nửa hệ) bị **kéo giãn** → lệch có hệ thống. | [lyrics_aligner.py:103-111](workers/xml_tools/lyrics_aligner.py#L103-L111) | Âm tiết gắn lệch 1–2 nốt. |
| E8 | File `.omr` của Audiveris (chứa **bbox pixel của từng đầu nốt**) được lưu nhưng **không được đọc**. | `run_audiveris` chỉ glob tìm file | Bỏ phí nguồn neo chính xác nhất cho E7. |
| E9 | Tách dòng OCR thành âm tiết bằng **số ký tự** (nội suy độ rộng). | [split_ocr_line_item](workers/xml_tools/vietnamese_universal_ocr.py#L794) | Với chữ in giãn để khớp nốt (rất thường gặp trong bản nhạc), bbox âm tiết sai lớn. |
| E10 | Từ điển `vietnamese_syllables.txt` (1.942 âm tiết) đã commit nhưng **không được dùng ở đâu**. | `workers/xml_tools/` | Mất công cụ rẻ nhất để phân biệt lời/hợp âm/rác OCR. |
| E11 | Header: `title` = **một** box có điểm cao nhất → tựa 2 dòng bị cắt; chữ giữa tựa và khuông 1 (nhịp độ "Vừa phải", "Giọng Fa trưởng", lời dịch bên trái) không có vai trò. | [document_layout.py:30](workers/xml_tools/document_layout.py#L30) | Metadata thiếu; chữ không vai trò vẫn nằm trên ảnh gửi OMR. |
| E12 | Dò khuông bị gọi **3 lần** (page_layout, decompose, cv) với logic hệ (system) chỉ có ở `page_layout`. | 3 file | Không nhất quán; decompose không biết khuông nào thuộc cùng hệ. |
| E13 | Lời in thành **khối thơ phía dưới bản nhạc** (lời 2, 3, 4 viết như bài thơ — rất phổ biến trong thánh ca) không được xử lý. | — | Các lời đó bị bỏ hoặc gán vào khuông cuối. |

**Kết luận đánh giá:** phần nhận nốt (Audiveris) là ổn định nhất; phần **chữ** (vai trò, cấu trúc lời, neo vị trí) là nơi lợi nhuận cải tiến lớn nhất và hoàn toàn thuộc quyền kiểm soát của dự án.

---

## 2. Tham khảo các dự án lớn

| Dự án | Cách làm | Bài học áp dụng |
|---|---|---|
| **Audiveris** (Java, đang dùng) | Phân tích theo sheet → system → staff; chữ được OCR (Tesseract) rồi gán **TextRole**: Title, Creator, Direction, Number, PartName, Rights, ChordName, **Lyrics**. Lời gắn theo vị trí đầu nốt; dự án `.omr` lưu toàn bộ hình học. | Mô hình **vai trò chữ** + dùng `.omr` làm nguồn neo pixel. Tự làm OCR tiếng Việt tốt hơn rồi chỉ mượn hình học của Audiveris. |
| **oemer** (Python, UNet) | Phân đoạn ảnh thành các lớp: dòng khuông, ký hiệu, đầu nốt… rồi dựng MusicXML. Không xử lý lời. | Ý tưởng **tách lớp bằng segmentation** thay vì xoá bằng bbox — hướng nâng cấp dài hạn cho lớp nhạc. |
| **homr** (Python, transformer theo khuông) | Phân đoạn để tìm khuông, rồi mô hình transformer (gốc Polyphonic‑TrOMR) đọc **từng khuông** ra chuỗi ký hiệu. Chịu được ảnh chụp điện thoại. | Ứng viên **engine nhạc thứ 2** để benchmark/so khớp với Audiveris (P4). |
| **SMT / Sheet Music Transformer** (Ríos‑Vila, Calvo‑Zaragoza…, 2024) và bản full‑page | End‑to‑end ảnh → chuỗi ký hiệu; dataset GrandStaff, OLiMPiC. | Tham khảo cho tương lai; hiện chưa thay được Audiveris với thánh ca có lời. |
| **Dataset**: DeepScoresV2, MUSCIMA++, PrIMuS/Camera‑PrIMuS, GrandStaff, OLiMPiC | Ground truth chuẩn cho OMR. | Không có lời tiếng Việt → **phải tự xây bộ 30–50 bài** (mục 6). |
| **PaddleOCR / RapidOCR** (đang dùng RapidOCR) | Phát hiện dòng chữ (DBNet) + nhận dạng; PaddleOCR có model Latin hỗ trợ tiếng Việt. | Dùng **detector** của RapidOCR để lấy bbox dòng; nhận dạng tiếng Việt bằng VietOCR/Tesseract‑vie trên crop. |
| **VietOCR** (transformer cho tiếng Việt) | Nhận dạng 1 dòng có dấu chuẩn. | Engine chính cho **dòng lời** và tựa đề; candidate có dấu được ưu tiên như hiện nay. |
| **PlayScore 2 / ScanScore / SmartScore / Newzik** (thương mại) | Đều coi lời là lớp chữ riêng, gắn theo vị trí đầu nốt, đánh số verse theo dòng; có giao diện soát lỗi. | Xác nhận kiến trúc "lớp lời riêng + neo vị trí + soát lỗi". Dấu tiếng Việt và cấu trúc điệp khúc là chỗ SheetTools có thể làm tốt hơn. |
| **MusicXML 4.0 / MuseScore** | `<lyric number="n" name="Verse 1">`, `<syllabic>`, `<extend/>`, `<elision>`; MuseScore hiển thị `number` thành dòng lời thứ n. | Quy ước đầu ra ở B8. |

---

## 3. Nhận xét phương án của bạn và phần bổ sung

| Ý của bạn | Đánh giá | Bổ sung |
|---|---|---|
| Đọc lần lượt tựa, tác giả, ghi chú… | Đúng. | Đọc **một lần OCR toàn trang**, rồi **gán vai trò** cho từng dòng (mục 4.2). Đọc tuần tự từng loại sẽ phải OCR nhiều lần và các bước sau không biết bước trước đã bỏ gì. |
| …sau đó **xoá** để không gây nhiễu | Đúng về mục đích. | Không xoá trên ảnh gốc: **che (mask) trên ảnh dẫn xuất** và lưu mask lại. Không bao giờ che phần chạm hành lang khuông (giữ quy tắc hiện tại) — nếu không sẽ mất nốt có dòng kẻ phụ, dấu luyến… |
| Còn nhạc + lời → tạo **2 bảng**: xoá lời chỉ để nhạc (có thể có hợp âm) | Đúng — đây chính là notation layer. | Hợp âm là **lớp thứ 3** đọc riêng từ dải *trên* khuông, không để Audiveris tự đoán (Audiveris đọc hợp âm kém và hay nhầm với chữ). Ghép vào bảng nhạc dưới dạng `<harmony>` sau. |
| Lời: dòng nhạc có 3 câu → 3 lời; tới điệp khúc còn 1 dòng → điệp khúc | Đúng — đây là tín hiệu mạnh nhất. | Cần kết hợp thêm 4 tín hiệu để không bị lừa (mục 4.6): dấu "1. 2. 3.", chữ "ĐK/Điệp khúc/Coda", dấu nhắc lại/volta, và **khối thơ lời in dưới bản nhạc**. Một hệ có 1 dòng lời cũng có thể là bài chỉ có 1 lời — phải xét cả bài. |

---

## 4. Kiến trúc đích — thuật toán từng bước

### 4.0 Mô hình dữ liệu trung tâm: `page_model.json` (mỗi trang)

Mọi bước đọc/ghi vào một mô hình duy nhất, thay cho 3 lần dò khuông hiện nay (E12).

```jsonc
{
  "schema_version": 2,
  "page": 1, "width": 2480, "height": 3508, "dpi": 300,
  "interline": 21.4,                      // đơn vị đo chuẩn cho MỌI ngưỡng
  "systems": [
    {
      "id": "sys_01", "box": [x1,y1,x2,y2],
      "staves": [{ "id": "st_01", "lines_y": [..5..], "part_hint": "treble" }],
      "bands": {                           // các dải quanh hệ
        "above":  [x1,y1,x2,y2],           // hợp âm, tempo, rehearsal
        "between": [[...]],                // giữa 2 khuông của cùng hệ (lời SATB)
        "below":  [x1,y1,x2,y2]            // lời
      }
    }
  ],
  "text_lines": [
    { "id": "t_017", "box": [...], "text": "Ngợi ca danh Chúa", "role": "lyric",
      "system_id": "sys_02", "band": "below", "line_index": 0,
      "tokens": [{ "text": "Ngợi", "box": [...], "conf": 0.93 }],
      "role_scores": { "lyric": 0.91, "chord": 0.02, "direction": 0.04 } }
  ],
  "masks": { "metadata": "mask_meta.png", "lyrics": "mask_lyrics.png", "chords": "mask_chords.png" }
}
```

Quy ước: **mọi ngưỡng tính theo `interline`** (khoảng cách 2 dòng kẻ khuông), không dùng pixel cứng → độc lập DPI (sửa E5).

### 4.1 B1 — Bố cục: khuông → hệ → dải

1. Dò dòng kẻ khuông (giữ thuật toán horizontal projection + khớp mẫu 5 dòng hiện có trong `cv_omr_engine.detect_staves`), tính `interline` trung vị cho trang.
2. **Gom khuông thành hệ** bằng **barline xuyên khuông** (vạch nhịp nối liền 2 khuông = cùng hệ) — đáng tin hơn khoảng cách. Fallback: khoảng cách < 7·interline (logic hiện tại trong `page_layout.py`).
3. Với mỗi hệ, tạo các dải:
   - `above`: từ đường phân cách với hệ trước (hoặc đáy header) tới dòng kẻ trên cùng − 0.5·interline.
   - `between`: giữa 2 khuông liền nhau trong cùng hệ (lời thánh ca 4 bè nằm ở đây — sửa E6).
   - `below`: từ dòng kẻ dưới cùng + 0.5·interline tới **đường phân cách** với hệ kế.
4. **Đường phân cách giữa 2 hệ** không lấy trung điểm cố định: chiếu ngang mật độ mực trong khoảng trống, tìm **thung lũng trắng rộng nhất**; khi hoà, chọn thung lũng gần hệ dưới hơn (hợp âm của hệ dưới thường nằm sát hệ dưới). Mọi dòng chữ được gán vào dải theo **tâm y** + kiểm tra chồng lấn.
5. Header = vùng trên dải `above` của hệ 1. Footer = vùng dưới hệ cuối **sau khi** trừ khối thơ lời (4.6.4).

### 4.2 B2 — OCR toàn trang + gán VAI TRÒ cho từng dòng chữ

**Phát hiện**: RapidOCR detector lấy bbox **dòng**. **Nhận dạng**: chạy VietOCR + Tesseract‑vie trên crop dòng (như hiện tại), chọn candidate theo `select_vietnamese_candidate`.

**Tách âm tiết** (sửa E9): thay chia theo số ký tự bằng **chiếu dọc trên crop nhị phân** — khoảng trắng dọc ≥ 0.35·chiều cao chữ là ranh giới từ; ghép số khoảng trống với số token OCR (DP 1‑chiều). Tiếng Việt mỗi âm tiết là một từ cách nhau bởi dấu cách → bbox âm tiết chính xác, rất quan trọng cho B7.

**Gán vai trò** — chấm điểm từng dòng bằng đặc trưng, không chỉ regex:

| Đặc trưng | Ý nghĩa |
|---|---|
| Dải chứa dòng (`header`/`above`/`between`/`below`/`footer`) | Tín hiệu mạnh nhất. Lời ∈ below/between; hợp âm ∈ above. |
| Chiều cao chữ / interline | Tựa lớn nhất; lời ~1.2–1.8 interline. |
| Tỉ lệ token thuộc **từ điển âm tiết tiếng Việt** (`vietnamese_syllables.txt`, sửa E10) | Lời ≈ 1.0; hợp âm ≈ 0. |
| Tỉ lệ token khớp **ngữ pháp hợp âm chặt** | Xem dưới. |
| Vị trí ngang (căn giữa/trái/phải), in hoa, in nghiêng | Tựa giữa; tác giả phải; lời dịch/ghi chú trái. |
| Từ khoá | "Nhạc:", "Lời:", "Thơ:", "Ý:", "Phỏng dịch", "TV", "Thánh Ca", số bài; "ĐK", "Điệp khúc", "Coda", "Fine", "D.C.", "Vừa phải", "Chậm", "♩ = 72"… |

Vai trò: `title`, `subtitle`, `composer`, `lyricist`, `translator`, `collection`, `hymn_number`, `scripture`, `note`, `tempo`, `key_info`, `chord`, `verse_marker`, `section_marker`, `lyric`, `direction`, `footer`, `unknown`.

**Ngữ pháp hợp âm chặt** (thay regex ở E1):

```
CHORD := ROOT ACC? QUAL? EXT* ("/" ROOT ACC?)?
ROOT  := [A-G]                 ← BẮT BUỘC IN HOA
ACC   := "#" | "b" | "♯" | "♭"
QUAL  := "m" | "min" | "maj" | "M" | "dim" | "°" | "aug" | "+" | "sus" ("2"|"4")?
EXT   := "6" | "7" | "9" | "11" | "13" | "add9" | "maj7" | "b5" | "#5" | ...
```
Quy tắc quyết định: dòng là `chord` khi **(a)** nằm ở dải `above` **và (b)** ≥ 70% token khớp ngữ pháp **và (c)** < 30% token là âm tiết tiếng Việt hợp lệ. Token như "Em", "Ba" ở dải `below` giữa các âm tiết tiếng Việt → **luôn là lời**. Lỗi OCR kiểu "F4m" → "F#m" chỉ sửa khi dòng đã được xác định là `chord`.

Giai đoạn 1 dùng **luật + trọng số** (minh bạch, test được). Khi có ≥ 30 bài ground truth, huấn luyện **cây quyết định / gradient boosting** trên cùng đặc trưng; giữ luật làm baseline.

### 4.3 B3 — Metadata rồi che

1. Lấy các dòng vai trò metadata → `document.json` (mở rộng `document_layout.py`): **tựa nhiều dòng** = gom các dòng `title` liền nhau có chiều cao tương đương (sửa E11); tác giả tách "Nhạc: …" / "Lời: …"; `tempo`, `key_info`, `note` có trường riêng.
2. Tạo `mask_meta.png` = bbox các dòng metadata (+ padding 0.15·interline). **Không** che phần chạm hành lang khuông ±2 interline (giữ `notation_layers.py`).
3. Ghi `<work-title>`, `<creator type="composer|lyricist">`, `<credit>` vào MusicXML ở B8, không phụ thuộc Audiveris.

### 4.4 B4 — Lớp NHẠC (bảng 1)

1. Ảnh nhạc = ảnh tiền xử lý − (mask_meta ∪ mask_lyrics ∪ mask_chords), tô trắng tất định (không inpainting để tránh sinh ký hiệu giả).
2. Chạy Audiveris → `raw.musicxml` + `.omr`.
3. **Đọc `.omr`** (gói zip của Audiveris, chứa XML từng sheet): lấy cho mỗi đầu nốt `bounds` pixel, staff, measure, voice → bảng `note_anchors.json` (sửa E8). Ánh xạ sang phần tử `<note>` trong MusicXML theo (part, measure, thứ tự trong voice). Hệ nào không ánh xạ được → đánh dấu `anchor_source=musicxml_fallback` và dùng logic hiện tại. *Cấu trúc nội bộ `.omr` cần xác nhận trên file thật của Audiveris 5.11 trước khi code.*
4. Giữ dual‑layer chạy Audiveris trên ảnh đầy đủ **chỉ** để lấy direction/dynamics; **không** lấy harmony từ đó nữa (B5 thay thế).

### 4.5 B5 — Lớp HỢP ÂM

1. Token vai trò `chord` → parse bằng luật của `ChordParser` (đã có trong PHP; port sang Python hoặc dùng chung một bảng luật).
2. Neo: tìm **nốt/phách gần nhất theo x** trong hệ tương ứng bằng `note_anchors` (pixel). Offset = khoảng cách thời gian tới đầu ô nhịp; hợp âm giữa 2 nốt → nội suy theo x giữa 2 onset.
3. Ghi `<harmony>` với `<offset>` khi không trùng đầu nốt. Hệ 1 không còn bị mất (sửa E3 vì dải `above` của hệ 1 tách khỏi header).

### 4.6 B6 — CẤU TRÚC LỜI (trọng tâm phương án của bạn)

#### 4.6.1 Dòng lời trong mỗi hệ
Với mỗi hệ, lấy các dòng `lyric` trong `below` (và `between` nếu có), gom dòng bằng **clustering theo y với ngưỡng 0.6·chiều cao chữ trung vị** (thay 28 px, sửa E5). Kết quả: `L_s` = số dòng lời của hệ `s`, sắp xếp trên → dưới.

#### 4.6.2 Tín hiệu cho từng hệ
| Tín hiệu | Cách đọc |
|---|---|
| `L_s` | số dòng lời |
| `verse_marker` đầu dòng | token "1.", "2.", "3." hoặc "1)", "Lời 2" ở mép trái dòng lời → **số lời tường minh** của dòng đó |
| `section_marker` | "ĐK", "Đ.K.", "Điệp khúc", "Coda", "Kết", "Fine", "D.C. al Fine", "D.S." |
| Ký hiệu nhắc lại / volta | từ Audiveris: `<barline><repeat>`, `<ending number="1,2">` |
| Văn bản lặp | dòng lời giống dòng ở hệ khác (CER < 0.15) → ứng viên điệp khúc |

#### 4.6.3 Phân đoạn bài bằng Viterbi trên chuỗi hệ
Trạng thái mỗi hệ: `VERSE(N)` (đoạn N lời), `CHORUS` (1 dòng chung), `CODA`, `INTRO` (không lời).

```
Đầu vào: chuỗi hệ s = 1..S với (L_s, markers_s, repeat_s)
N* = mode(L_s với L_s ≥ 2)            # số lời của phần verse; nếu không có thì N* = 1

Điểm phát xạ:
  VERSE(N*) : +3 nếu L_s == N*   ; +2 nếu có marker "1." đầu dòng ; −3 nếu có "ĐK"
  CHORUS    : +3 nếu L_s == 1 và N* ≥ 2 ; +4 nếu có "ĐK/Điệp khúc" ; +1 nếu văn bản lặp
  CODA      : +4 nếu có "Coda/Kết" ; +1 nếu là hệ cuối
  INTRO     : +3 nếu L_s == 0
Chuyển trạng thái: ở lại trạng thái cũ +1 (đoạn nhạc liền mạch), đổi trạng thái −1.
Viterbi → nhãn cho từng hệ → gom thành sections.
```
Các trọng số trên là điểm khởi đầu; sẽ chỉnh theo bộ ground truth (P4).

Trường hợp đặc biệt:
- Chuyển section **giữa hệ** (lời 3 dòng ở nửa trái, 1 dòng ở nửa phải): xét `L` theo **từng ô nhịp** thay vì từng hệ — đếm dòng lời có âm tiết nằm trong khoảng x của ô nhịp đó (dùng `note_anchors`). Ranh giới section rơi đúng vạch nhịp.
- Dòng thiếu ở một lời (lời 3 ngắn hơn): giữ chỉ số dòng theo **vị trí y tương đối** với các hệ khác của cùng section (khớp offset y chuẩn hoá theo interline), không đánh lại số từ 1.
- `verse_marker` tường minh luôn **thắng** suy luận theo thứ tự.

#### 4.6.4 Khối thơ lời in dưới bản nhạc (sửa E13)
Thánh ca thường in: Lời 1 dưới nốt, Lời 2–4 thành đoạn thơ cuối trang.
1. Phát hiện: vùng chữ dưới hệ cuối, nhiều dòng `lyric`, mở đầu bằng "2.", "3."…, không nằm trong dải của hệ nào.
2. Tách thành stanza theo `verse_marker` và khoảng trắng dọc.
3. **Ánh xạ vào giai điệu**: lấy chuỗi nốt nhận lời của Lời 1 (đã căn ở B7) làm "khuôn". Chia stanza thành câu theo dấu câu/xuống dòng, đếm âm tiết; gán âm tiết thứ k của stanza vào nốt mà âm tiết thứ k của Lời 1 đã chiếm (giữ nguyên melisma). Nếu số âm tiết lệch > 10% so với Lời 1 → đánh dấu `needs_review` cho câu đó, không ép.

#### 4.6.5 Đầu ra cấu trúc
```jsonc
"sections": [
  { "id": "sec_1", "type": "verse", "verse_count": 3, "systems": ["sys_01","sys_02"], "measure_range": [1, 8] },
  { "id": "sec_2", "type": "chorus", "verse_count": 1, "systems": ["sys_03","sys_04"], "measure_range": [9, 16] }
]
```
Quy ước MusicXML: section verse → `<lyric number="1..N" name="Lời 1..N">`; điệp khúc → `<lyric number="1" name="ĐK">` (MuseScore hiển thị đúng 1 dòng như bản in). Tuỳ chọn export "nhân bản điệp khúc vào mọi verse" cho phần mềm cần đủ N dòng.

### 4.7 B7 — CĂN ÂM TIẾT ↔ NỐT

Thay `_align_group` hiện tại bằng DP trên **toạ độ pixel thật**:

1. **Ứng viên nốt** của mỗi (section, dòng lời) = nốt nhận lời trong khoảng hệ/ô nhịp của section, theo quy tắc hiện có (bỏ rest, grace, nốt hợp âm phụ, nốt nối tie‑stop), ưu tiên voice 1; với 2 khuông/hệ dùng khuông **gần dòng lời nhất** (lời dưới khuông trên → bè soprano).
2. **Toạ độ**: x tâm đầu nốt từ `.omr` (pixel); x của âm tiết = **mép trái + 0.4·độ rộng** (giá trị khởi đầu, đo lại trên ground truth).
3. **Chi phí DP** (không chuẩn hoá min–max nữa, sửa E7):
   ```
   match(i,j)     = |x_word_i − x_note_j| / interline           (khoảng cách thực)
                  + 0.35·(1 − conf_ocr_i)
                  + 0.5  nếu nốt j nằm GIỮA dấu luyến (slur continue) — thường là melisma
   skip_note(j)   = 0.15 nếu j là nốt trong slur/tie (melisma), ngược lại 0.6
   skip_word(i)   = 1.2 (token rác) ; 3.0 nếu token là âm tiết tiếng Việt hợp lệ
   ```
   Ràng buộc: đơn điệu; mỗi âm tiết ↔ đúng 1 nốt; khoảng cách > 2.5·interline → cấm match.
4. **Melisma**: nốt bị bỏ qua nằm sau âm tiết và trong cùng slur → thêm `<extend type="start/stop"/>` cho âm tiết trước đó.
5. **Kiểm chứng**: số âm tiết của câu vs số nốt nhận lời trong câu; lệch → `needs_review`.
6. **Tiếng Việt**: hầu hết `<syllabic>single</syllabic>`; chỉ dùng `begin/middle/end` khi có gạch nối (từ mượn, tên riêng: "Ha‑lê‑lu‑gia"). Hai âm tiết trên 1 nốt → `<elision>`.

### 4.8 B8 — Ráp MusicXML + kiểm định

1. `notation.musicxml` = raw + metadata + harmony (bảng 1, không lời).
2. `lyrics.json` v2 = sections → verses → lines → syllables (bảng 2).
3. `score.musicxml` = (1) + (2) cho các âm tiết `accepted`; âm tiết `review` chỉ ở JSON.
4. Validator (đã có) + kiểm tra mới: mỗi nốt có ≤ 1 lyric mỗi `number`; mọi section verse có đủ N dòng; không có `<harmony>` chứa âm tiết tiếng Việt.
5. `recognition_report.json` thêm: số section, N lời, tỉ lệ âm tiết accepted/review theo từng section, danh sách hệ có `anchor_source=musicxml_fallback`.

### 4.9 Lớp kiểm chứng bằng mô hình thị giác (tuỳ chọn, tắt mặc định)

Cho các hệ có confidence thấp, có thể gửi crop + kết quả đọc cho một mô hình ngôn ngữ thị giác để **chấm** (không tự sinh): "dòng này là lời hay hợp âm?", "đây là lời mấy?", "chữ này đọc là gì?". Chỉ dùng làm **candidate thêm** trong cơ chế chọn hiện có, ghi rõ nguồn `engine=vlm`, bật bằng biến môi trường, và chỉ giữ nếu benchmark mục 6 cho thấy cải thiện.

---

## 5. Lộ trình triển khai

Mỗi phase có test hồi quy trước khi sửa (theo AGENTS.md), và chỉ báo cáo số đo khi có ground truth.

### P0 — Sửa lỗi gây sai kết quả ngay (1–2 ngày)
| Task | Nội dung | File | Tiêu chí xong |
|---|---|---|---|
| P0‑1 | Ngữ pháp hợp âm chặt (root in hoa) + từ điển âm tiết; token ở dải dưới khuông không bao giờ là hợp âm (sửa E1, E2) | `vietnamese_universal_ocr.py`, `document_layout.py` | Test: `ca, em, ba, da, ga, Em, Ba` ở dải lời → lời; `Em, Am7, F#m, G/B, Bb` ở dải trên → hợp âm |
| P0‑2 | Hợp âm hệ 1 không rơi vào header (sửa E3) | cùng file | Test ảnh tổng hợp có hợp âm trên khuông 1 |
| P0‑3 | Ngưỡng gom dòng theo chiều cao chữ, không 28 px (sửa E5) | cùng file | Test cùng trang ở 150/300/600 DPI cho cùng số dòng |
| P0‑4 | Nạp `vietnamese_syllables.txt` thành module `vi_lexicon.py` (sửa E10) | mới | Unit test |

### P1 — Mô hình trang thống nhất + vai trò chữ (1 tuần)
| Task | Nội dung | Tiêu chí |
|---|---|---|
| P1‑1 | `page_model.json` v2: một lần dò khuông, gom hệ bằng barline, dải above/between/below, đường phân cách bằng thung lũng mực (4.1) | `page_layout.py` thành nguồn duy nhất; `decompose_sheet_3zones` đọc từ nó |
| P1‑2 | Tách âm tiết bằng chiếu dọc (4.2, sửa E9) | Test: dòng chữ giãn rộng → sai số bbox âm tiết < 0.3·interline |
| P1‑3 | Bộ gán vai trò theo đặc trưng (4.2) + overlay debug màu theo vai trò | Overlay hiển thị trong Review Studio |
| P1‑4 | Header: tựa nhiều dòng, Nhạc/Lời, tempo, key_info (4.3, sửa E11) | `HeaderSemanticsTest` mở rộng |
| P1‑5 | Mask theo lớp (meta/lyrics/chords) lưu thành artifact | `notation_layers.py` nhận nhiều mask |

### P2 — Neo pixel + căn lời mới (1 tuần)
| Task | Nội dung | Tiêu chí |
|---|---|---|
| P2‑1 | Parser `.omr` → `note_anchors.json` (4.4, sửa E8) | Test trên `.omr` thật từ mẫu `002`, `003` |
| P2‑2 | DP căn lời theo pixel + melisma theo slur + `<extend>` (4.7, sửa E7) | `LyricsAlignmentTest` thêm ca nhịp lấy đà, lời phủ nửa hệ |
| P2‑3 | Neo hợp âm theo phách (4.5) | Test hợp âm giữa 2 nốt có `<offset>` |

### P3 — Cấu trúc lời: verse / điệp khúc / khối thơ (1–1.5 tuần)
| Task | Nội dung | Tiêu chí |
|---|---|---|
| P3‑1 | Đọc `verse_marker`, `section_marker` | Unit test token "1.", "ĐK:", "Điệp khúc" |
| P3‑2 | Phân đoạn Viterbi trên chuỗi hệ, mức ô nhịp tại hệ chuyển tiếp (4.6.3) | Test tổng hợp: 3 lời → ĐK 1 dòng → Coda |
| P3‑3 | Lời SATB nằm giữa 2 khuông (sửa E6) | Mẫu thánh ca 4 bè 4 lời |
| P3‑4 | Khối thơ lời dưới bản nhạc → ánh xạ theo khuôn Lời 1 (4.6.4, sửa E13) | Mẫu có lời 2–4 in dưới |
| P3‑5 | `lyrics.json` v2 + export `<lyric name>`, tuỳ chọn nhân bản điệp khúc | `ExportService` + `LyricsPanel` hiển thị theo section |

### P4 — Đo lường và nâng cấp engine (liên tục)
| Task | Nội dung |
|---|---|
| P4‑1 | **Bộ ground truth 30–50 bài** (mục 6). Đây là điều kiện để mọi con số được phép công bố. |
| P4‑2 | Benchmark tự động mỗi lần đổi thuật toán; lưu bảng so sánh theo commit. |
| P4‑3 | Huấn luyện bộ phân loại vai trò từ ground truth (thay trọng số tay). |
| P4‑4 | Thử **homr** làm engine nhạc thứ 2 cho từng khuông; so khớp với Audiveris, chỗ bất đồng → `needs_review`. |
| P4‑5 | (Tuỳ chọn) lớp kiểm chứng VLM (4.9), chỉ giữ nếu benchmark cải thiện. |

---

## 6. Đo lường — định nghĩa "tốt nhất" bằng số

Hiện `public/samples` chỉ có **2 PDF khác nhau** (đã ghi trong NEXUS) — không đủ để đo. Cần bộ dữ liệu:

- 30–50 bài, phân tầng: thánh ca 1 khuông có hợp âm; 4 bè 2 khuông; có điệp khúc; có khối thơ lời dưới; scan sạch; ảnh chụp điện thoại; nhiều trang.
- Mỗi bài: `source.pdf` + `truth.musicxml` (soát bằng MuseScore) + `truth_document.json` + `truth_sections.json`.

| Chỉ số | Cách tính | Mục tiêu khi xong P3 |
|---|---|---|
| Header field accuracy | đúng/tổng trên title, composer, lyricist, number | ≥ 95% |
| Text role accuracy | đúng vai trò / tổng dòng chữ | ≥ 95% |
| Chord F1 | so ký hiệu + vị trí ô nhịp/phách | ≥ 90% |
| Lyric CER (theo âm tiết, có dấu) | `accuracy_report.py` | ≤ 3% scan sạch; ≤ 8% ảnh chụp |
| Verse/section assignment | âm tiết gán đúng số lời & section | ≥ 95% |
| Syllable→note alignment | âm tiết gắn đúng nốt | ≥ 92% |
| Note accuracy (pitch+duration) | đã có | đo baseline Audiveris trước, chưa đặt mục tiêu |
| Review load | % âm tiết `needs_review` | ≤ 10% |

Các mục tiêu trên là **mục tiêu thiết kế**, không phải kết quả đã đạt; chỉ được ghi "đạt" khi benchmark chạy trên bộ dữ liệu này.

---

## 7. Rủi ro và quyết định cần bạn chốt

| Rủi ro / câu hỏi | Đề xuất |
|---|---|
| Đọc `.omr` phụ thuộc định dạng nội bộ Audiveris 5.11 | Ghim phiên bản Audiveris; parser có test trên file thật; fallback về logic MusicXML hiện tại. |
| Điệp khúc xuất 1 dòng hay nhân bản N dòng? | Mặc định 1 dòng (đúng bản in); export có tuỳ chọn nhân bản. |
| Bản in có lời 2–4 dạng thơ nhưng giai điệu verse khác nhau (hiếm) | Chỉ ánh xạ khi số âm tiết khớp ±10%; còn lại để soát tay. |
| Hợp âm viết tay / font lạ | Ngữ pháp chặt + review; không đoán. |
| Thời gian xử lý tăng (OCR crop từng dòng) | OCR chỉ chạy 1 lần/trang; cache theo hash trang (đã có checkpoint). |

**Không làm** trong roadmap này: thay Audiveris bằng mô hình end‑to‑end; tự sinh nốt khi OMR thất bại; tự "sửa dấu" theo từ đơn không có ngữ cảnh.

---

## 8. Thứ tự làm đề xuất

1. **P0** ngay (lỗi E1 đang làm mất chữ "ca/em/ba" trong lời — lỗi dễ thấy nhất với người dùng).
2. Song song bắt đầu **P4‑1** (gom 30–50 bài ground truth) — không có nó thì không biết P1–P3 có thật sự tốt hơn.
3. P1 → P2 → P3 theo thứ tự (P3 cần neo pixel của P2 để chia section ở mức ô nhịp).
