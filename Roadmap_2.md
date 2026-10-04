# ROADMAP 2 — Làm sheet nhanh: Đọc nhiều nguồn · Kiểm chéo bằng luật âm nhạc · Chỉ hỏi người chỗ mâu thuẫn

> Ngày lập: 2026-10-04 · Tiếp nối [Roadmap_1.md](Roadmap_1.md) (tách lớp tiêu đề / nhạc / hợp âm / lời) và [QA_270_2026-10-04.md](QA_270_2026-10-04.md).
> Nguyên tắc giữ nguyên: source và RAW bất biến; mọi sửa là artifact dẫn xuất; **không tự sinh nốt/chữ để che lỗi**; không công bố accuracy khi chưa có ground truth.

---

## 0. Mục tiêu đổi hướng

Roadmap 1 làm cho máy **đọc tốt hơn**. Roadmap 2 làm cho cả quy trình **nhanh hơn**: từ lúc upload đến lúc có sheet đúng.

Không hệ OMR nào tự động đúng 100%, kể cả hàng thương mại. Thời gian làm một sheet thực tế là:

```
Thời gian = thời gian máy chạy + thời gian người TÌM lỗi + thời gian người SỬA lỗi
```

Hiện nay phần lớn thời gian nằm ở **tìm lỗi**: hệ thống không biết mình sai ở đâu, nên người phải dò cả bài. Ví dụ trong bài 270, Audiveris mất nốt liên ba ở ô 3 và ô 5 rồi kéo dài nốt còn lại cho đủ phách, nên validator **không báo gì**.

**Mục tiêu Roadmap 2:**

> Máy tự chấp nhận những ô nhịp chắc chắn đúng, tự sửa những gì sửa được có bằng chứng, và đưa ra **danh sách ngắn các ô nhịp cần người xem, kèm lý do và gợi ý**. Người soát theo ô nhịp, không dò cả bài.

Cách làm là **luật chung cho mọi bài**, không chỉnh theo từng bài. Mỗi luật dưới đây đúng với mọi bản nhạc in có lời tiếng Việt.

---

## 1. Thuật toán tổng thể

```
           ┌────────────── Roadmap 1 (đã có) ──────────────┐
Trang ảnh → bố cục → OCR vai trò chữ → lớp nhạc → lớp hợp âm → lớp lời
           └───────────────────────────────────────────────┘
                                   │
                                   ▼
 B1  ĐỌC NHIỀU NGUỒN ĐỘC LẬP  (mỗi lớp ≥ 2 nguồn)
                                   │
                                   ▼
 B2  SỔ Ô NHỊP (Measure Ledger): gom mọi bằng chứng theo từng ô nhịp
                                   │
                                   ▼
 B3  KIỂM CHÉO bằng ràng buộc C1…C10  →  mỗi ô có danh sách vi phạm
                                   │
                                   ▼
 B4  QUYẾT ĐỊNH theo ô:  ACCEPT  |  REPAIR (thử cách đọc khác)  |  REVIEW
                                   │
                                   ▼
 B5  HÀNG ĐỢI SOÁT theo ô nhịp: ảnh gốc ô đó ‖ bản dựng ‖ lý do ‖ gợi ý  → phím tắt
                                   │
                                   ▼
 B6  HỌC THEO CUỐN SÁCH: mỗi lần người sửa → cập nhật hồ sơ của cuốn
```

Điểm mấu chốt: **không có bước nào tin một nguồn duy nhất.** Một ô nhịp chỉ được tự chấp nhận khi các nguồn độc lập đồng ý và mọi ràng buộc đều thoả.

---

## 2. B1 — Đọc nhiều nguồn độc lập

| Lớp | Nguồn A (đã có) | Nguồn B (độc lập, cần làm) | Nguồn C (về sau) |
|---|---|---|---|
| Nốt | Audiveris (`raw.musicxml` + `.omr`) | **Bộ đếm đầu nốt** trên ảnh theo từng ô nhịp (B1.1) | Engine thứ 2 theo khuông, ví dụ homr (P3) |
| Liên ba / chùm | `<time-modification>` của Audiveris | **Bộ dò dấu "3"** và ngoặc liên ba (B1.2) | — |
| Lời | RapidOCR (mặt chữ, vị trí) + Tesseract đọc cả dòng (dấu) — đã có | Số âm tiết theo ô nhịp (từ `lyrics.json` + `measure_box`) | — |
| Hợp âm | OCR toàn trang + đọc lại ô cắt — đã có | **Quét mực dải trên khuông** (B1.3) | — |
| Cấu trúc lời | Số dòng lời mỗi hệ + marker (Roadmap 1) | **Mạch lời xuyên trang** (B1.4) | — |

### B1.1 Bộ đếm đầu nốt (head counter)

Mục đích: một con số **độc lập với Audiveris** về số nốt trong mỗi ô nhịp.

```
Với mỗi khuông s, mỗi ô nhịp m (measure_box từ .omr, đã có trong omr_anchors.py):
  1. Cắt vùng [x_left..x_right] × [dòng kẻ trên − 4·interline .. dòng kẻ dưới + 4·interline]
  2. Xoá dòng kẻ khuông (morphology mở theo chiều ngang, kernel dài 3·interline)
  3. Xoá thân nốt (mở theo chiều dọc, kernel 2.5·interline) → còn đầu nốt, dấu hoá, dấu lặng
  4. Ứng viên đầu nốt = thành phần liên thông có:
       rộng ≈ 1.1–1.6 · interline, cao ≈ 0.8–1.2 · interline, tâm y thẳng hàng với dòng/khe (sai ≤ 0.25·interline)
     - đầu đen: độ đặc ≥ 0.7
     - đầu trắng: có đúng 1 lỗ bên trong
  5. Loại dấu hoá (♯ ♭ ♮: tỉ lệ cao/rộng > 1.8 hoặc nằm sát bên trái một đầu nốt)
  6. Đầu nốt chồng dọc cùng x (hợp âm) → đếm từng đầu
Kết quả: H_img(s, m) = số đầu nốt, kèm toạ độ từng đầu
```

Đây là CV cổ điển, không cần huấn luyện, đủ tin cậy với bản in. Bộ đếm **không thay** Audiveris; nó chỉ dùng để phát hiện Audiveris thiếu hoặc thừa nốt.

### B1.2 Bộ dò dấu liên ba

- Nguồn chữ: các hộp OCR text `"3"` nằm trong dải ±3·interline quanh khuông. Hiện các hộp này đang bị gán vai trò `unknown` trong `page_model.json`, nên chỉ cần đổi sang vai trò `tuplet_mark`.
- Nguồn hình: ngoặc liên ba là đoạn ngang có 2 móc dọc ở hai đầu, chữ số nằm ở giữa.
- Kết quả: `tuplet_marks(s, m) = [{x, number: 3, bracket_span: [x1, x2]}]`.

### B1.3 Quét mực dải trên khuông

Trong dải `above` của mỗi hệ, tìm mọi cụm mực (dilate theo chiều ngang 0.6·interline rồi lấy thành phần liên thông). Mỗi cụm phải được **giải thích** bởi một trong các thứ sau: hợp âm đã đọc, dấu liên ba, ký hiệu Audiveris (dynamics, fermata…), hoặc phần nốt cao nhô lên từ khuông. Cụm nào không được giải thích → đọc lại bằng ô cắt (đã có `reocr_chord_box`). Nếu vẫn không đọc được → vi phạm C6.

Nhờ vậy bắt được trường hợp **detector bỏ sót hẳn hợp âm**, như hợp âm C ở trang 2 bài 270. Cách đọc lại ô cắt hiện tại không bắt được trường hợp này, vì nó chỉ sửa những hộp đã được phát hiện.

### B1.4 Mạch lời xuyên trang

Trạng thái section (VERSE(N) / CHORUS / CODA) của **ô nhịp cuối trang k** được truyền làm trạng thái khởi đầu cho Viterbi của **trang k+1**. Bỏ giả định "mỗi trang tự phân đoạn từ đầu".

Ngoài ra, nếu một dòng lời bắt đầu ở cuối trang k và trang k+1 chỉ có 1 dòng lời, thì dòng cuối trang k là **đầu điệp khúc**, kể cả khi nó được in ở vị trí của lời 2. Đây đúng là trường hợp "Tương lai tôi còn có bao nhiêu" trong bài 270.

---

## 3. B2 — Sổ ô nhịp (Measure Ledger)

Đây là cấu trúc dữ liệu trung tâm mới. Mỗi trang có một `measure_ledger.json`; khi ghép trang thì nối các sổ lại theo số ô nhịp toàn bài.

```jsonc
{
  "schema_version": 1,
  "measures": [
    {
      "id": "p1_s2_m3",              // trang_khuông_ô
      "page": 1, "system_id": "system_002", "staff_index": 1,
      "measure_number": 3,           // số ô toàn bài sau merge
      "box": [x1, y1, x2, y2],       // pixel trên ảnh trang, để cắt ảnh soát
      "evidence": {
        "omr":   { "notes": 3, "sung_notes": 3, "durations": ["half","quarter","quarter"], "tuplets": 0, "beats": 4.0 },
        "image": { "heads": 4, "head_x": [412, 520, 571, 622], "tuplet_marks": [{ "x": 570, "number": 3 }] },
        "lyrics": { "1": 4, "2": 4, "3": 4 },          // số âm tiết theo từng lời
        "chords": { "read": ["Eb"], "unexplained_ink": [] },
        "section": { "type": "verse", "verse_count": 3 }
      },
      "violations": [
        { "rule": "C2", "severity": "error", "message": "Ảnh có 4 đầu nốt, OMR có 3" },
        { "rule": "C1", "severity": "error", "message": "Lời 1–3 có 4 âm tiết, chỉ 3 nốt nhận lời" },
        { "rule": "C4", "severity": "error", "message": "Có dấu liên ba nhưng OMR không có nhóm liên ba" }
      ],
      "decision": "review",          // accept | repaired | review
      "suggestions": [
        { "id": "sg1", "source": "audiveris_crop_2x", "summary": "G4 trắng + liên ba Bb4 A4 G4", "satisfies": ["C1","C2","C3","C4"] }
      ],
      "confidence": 0.12
    }
  ]
}
```

`RecognitionIssue` (PHP) đã có `measureNumber`, `entityType`, `severity`, `boundingCoords`. Sổ ô nhịp sẽ sinh `RecognitionIssue` cho mọi ô `review`, nên không phải tạo model mới.

---

## 4. B3 — Các ràng buộc kiểm chéo (luật chung cho mọi bài)

Ký hiệu: m = ô nhịp, ℓ = một dòng lời của section chứa m, S(ℓ,m) = số âm tiết có tâm nằm trong ô m, N(m) = số nốt nhận lời (voice 1, không phải dấu lặng, không phải nốt nối tie‑stop, không phải nốt phụ của hợp âm), L(m) = số nốt nằm giữa một dấu luyến (melisma được phép).

| Mã | Ràng buộc | Điều kiện vi phạm | Mức | Bắt được lỗi gì |
|---|---|---|---|---|
| **C1** | Âm tiết ↔ nốt | S(ℓ,m) > N(m), hoặc N(m) − S(ℓ,m) > L(m) | error | OMR thiếu nốt; lời gắn lệch |
| **C2** | Đầu nốt ảnh ↔ OMR | H_img(m) ≠ số nốt OMR (tính cả nốt hợp âm) | error | OMR thiếu/thừa nốt |
| **C3** | Đủ phách | Tổng trường độ ≠ số chỉ nhịp (trừ ô lấy đà + ô cuối cộng lại đủ 1 ô) | error | Sai trường độ |
| **C4** | Liên ba | Có `tuplet_mark` trong ô mà OMR không có `<time-modification>` tương ứng, hoặc ngược lại | error | Lỗi liên ba bị che bởi C3 |
| **C5** | Các lời cùng đoạn nhất quán | S(ℓ₁,m) ≠ S(ℓ₂,m) và chênh lệch không giải thích được bằng luyến | warning | OCR mất/thừa chữ ở một lời |
| **C6** | Mực trên khuông được giải thích | Còn cụm mực trong dải `above` chưa có vai trò | warning | Hợp âm bị bỏ sót |
| **C7** | Mạch section | Section đổi ở đầu trang mà không có marker hay thay đổi số dòng lời | warning | Điệp khúc tách sai qua trang |
| **C8** | Khoá / hoá biểu nhất quán | Khoá hoặc hoá biểu đổi giữa các hệ mà không có ký hiệu đổi rõ ràng; khoá quãng tám không có số 8 (đã có `clef_check.py`) | error | Lệch quãng tám, sai dấu hoá |
| **C9** | Âm vực hợp lý | Giai điệu có lời vượt ngoài khoảng A3–A5, hoặc nhảy > 1 quãng tám rồi quay lại ngay | info | Sai cao độ do đọc nhầm dòng kẻ |
| **C10** | Hợp âm hợp giọng | Gốc hợp âm không thuộc giọng và không phải hợp âm mượn thông dụng (ví dụ B trong giọng B♭) | warning | Mất dấu ♭/♯ trong hợp âm |

Mỗi luật là một hàm thuần: `check(measure_ledger_entry) -> list[Violation]`. Luật nào cũng có test riêng với ô nhịp tổng hợp. Thêm luật mới không phải sửa luật cũ.

**Ví dụ áp vào bài 270** (đối chiếu với QA):

| Lỗi trong QA | Luật bắt được |
|---|---|
| Ô 3: thiếu G4 trong liên ba | C1 (4 chữ, 3 nốt), C2 (4 đầu, 3 nốt), C4 (có dấu "3") |
| Ô 5: thiếu B♭4 trong liên ba | C1, C2, C4 |
| "Tương lai" ghi là Lời 2 | C7 (trang 2 chỉ còn 1 dòng, mạch nối từ cuối trang 1) |
| Thiếu hợp âm C (trang 2, ô 2) | C6 |
| E♭m đọc thành Em | C10 (E không thuộc giọng B♭) → đọc lại ô cắt |
| "NĂM" thay vì "NẮM" (tựa) | Không có luật âm nhạc → hàng đợi soát metadata (B5) |

---

## 5. B4 — Quyết định theo từng ô nhịp

```
for m in ledger:
    v = check_all(m)
    if no error/warning in v:
        m.decision = ACCEPT
        continue
    candidates = repair_strategies(m, v)          # B4.1
    good = [c for c in candidates if check_all(apply(m, c)) has no error
                                   and c is supported by ≥ 2 independent sources]
    if len(good) == 1 and auto_repair_enabled(rule set of v):
        m.decision = REPAIRED;   m.applied = good[0]    # ghi vết đầy đủ, hoàn tác được
    else:
        m.decision = REVIEW;     m.suggestions = rank(candidates)
```

**Quy tắc an toàn:** chỉ tự sửa khi **đúng một** phương án thoả mọi ràng buộc **và** được ít nhất 2 nguồn độc lập ủng hộ. Mặc định giai đoạn đầu là `auto_repair_enabled = False` với lỗi nốt: mọi phương án sửa nốt đều chỉ là **gợi ý**, người bấm 1 phím để chấp nhận. Chỉ bật tự sửa cho một loại lỗi khi benchmark cho thấy tỉ lệ tự sửa đúng ≥ 99%.

### B4.1 Chiến lược sửa (theo loại vi phạm)

| Vi phạm | Thử theo thứ tự |
|---|---|
| C1/C2/C4 (thiếu nốt, liên ba) | (1) Chạy lại Audiveris trên **ảnh cắt của cả hệ** phóng to 1.5–2× · (2) engine thứ 2 trên khuông đó (P3) · (3) **dựng phương án từ ảnh**: vị trí đầu nốt (B1.1) + cao độ theo dòng kẻ + nhóm liên ba (B1.2) + phần trường độ còn lại cho đủ ô → chỉ làm *gợi ý* |
| C3 đơn lẻ | Gợi ý chấm dôi / đổi trường độ nốt có độ tin cậy thấp nhất |
| C5 | Đọc lại dòng lời thiếu chữ bằng ô cắt sát ô nhịp đó |
| C6, C10 | Đọc lại cụm mực bằng `reocr_chord_box`; với C10 thử thêm biến thể có ♭/♯ khớp giọng |
| C7 | Chạy lại Viterbi với trạng thái truyền từ trang trước |
| C8 | `clef_check.py` (đã có); hoá biểu lấy theo đa số các hệ |

---

## 6. B5 — Hàng đợi soát theo ô nhịp

Đây là nơi tiết kiệm thời gian nhất. Mục tiêu: **≤ 10 giây cho mỗi ô cần soát.**

```
┌──────────────────────────────────────────────────────────────────────┐
│  Ô 3 / 24  ·  Trang 1, hệ 2  ·  còn 4 ô cần soát                      │
├───────────────────────────────┬──────────────────────────────────────┤
│  [ẢNH GỐC — cắt đúng ô 3]      │  [BẢN DỰNG — OSMD chỉ ô 3 + lời]      │
│                               │                                      │
├───────────────────────────────┴──────────────────────────────────────┤
│  ⚠ Ảnh có 4 đầu nốt, OMR có 3 · Có dấu liên ba · Lời có 4 chữ         │
│  Gợi ý:  [1] G4 trắng + liên ba B♭4 A4 G4   (thoả C1–C4)              │
│          [2] Giữ nguyên                                               │
├──────────────────────────────────────────────────────────────────────┤
│  1–9 chọn gợi ý · Enter chấp nhận · E sửa tay · N bỏ qua · ←/→ ô trước/sau │
└──────────────────────────────────────────────────────────────────────┘
```

- Thứ tự: `error` trước, `warning` sau. Ô cùng loại lỗi được xếp liền nhau.
- Metadata (tựa, tác giả, số bài) là **thẻ đầu tiên** của hàng đợi, kèm ảnh cắt dòng tựa.
- Sửa tay (E) mở `NoteEditor`/`LyricsPanel` đã có, nhưng chỉ cho ô đó.
- Mỗi thao tác ghi log: `{measure_id, rule, action, suggestion_id, seconds}`. Log này dùng cho B6 và cho đo lường (mục 9).
- Thành phần: `MeasureReviewQueue.vue` mới, dùng `IssuePanel.vue` + `RecognitionIssue` hiện có làm nguồn dữ liệu; ảnh cắt lấy qua API trang hiện có (`/pages/{index}`) theo `box`.

---

## 7. B6 — Học theo cuốn sách (Book Profile)

Bài cùng một cuốn dùng chung font, chung cách căn lời, chung dấu ngoặc khuông và chung bố cục tiêu đề. Học **một lần cho cả cuốn** thay vì sửa từng bài.

```jsonc
// storage/profiles/{book_slug}.json
{
  "book": "ton-vinh-chua-hang-huu",
  "songs_seen": 12,
  "params": {
    "lyric_anchor_fraction": 0.5,          // đo từ các ô đã ACCEPT
    "chord_reocr_scale": 2.0,
    "clef_bracket_hook": true,             // đã thấy lỗi 8VB giả do ngoặc khuông
    "verse_marker_style": "N.",
    "running_header": "Tôn Vinh Chúa Hằng Hữu",   // loại khỏi tiêu đề trang 2+
    "page_number_position": "footer_left"
  },
  "ocr_confusions": [                      // học từ thao tác sửa của người
    { "from": "NĂM", "to": "NẮM", "context": "ĐẤNG _ GIỮ", "confirmations": 1 }
  ]
}
```

Luật học:
- **Tham số** (ví dụ `lyric_anchor_fraction`) được cập nhật tự động bằng thống kê trên các ô đã ACCEPT hoặc đã được người xác nhận.
- **Sửa chữ** chỉ được tự áp dụng khi cùng cặp (from → to, ngữ cảnh) đã được người xác nhận **≥ 3 lần**. Trước ngưỡng đó, nó chỉ là gợi ý trong hàng đợi.
- Hồ sơ không bao giờ sửa nốt.
- Người dùng chọn cuốn sách lúc upload, hoặc hệ thống gợi ý theo `collection` đọc được ở header (Roadmap 1 đã có).

---

## 8. Kiến trúc file

| Thành phần | File | Ghi chú |
|---|---|---|
| Bộ đếm đầu nốt | `workers/omr_checks/head_counter.py` | dùng `measure_box` từ `xml_tools/omr_anchors.py` |
| Dò liên ba | `workers/omr_checks/tuplet_marks.py` | đọc `page_model.json` (hộp `"3"`) + hình ngoặc |
| Quét mực trên khuông | `workers/omr_checks/ink_scan.py` | gọi lại `reocr_chord_box` |
| Sổ ô nhịp | `workers/omr_checks/ledger.py` | dựng ledger từ MusicXML + anchors + lyrics + page_model |
| Luật C1–C10 | `workers/omr_checks/rules/*.py` | mỗi luật một file, một hàm `check()` |
| Quyết định + sửa | `workers/omr_checks/decide.py`, `repair.py` | gọi lại Audiveris trên ảnh cắt |
| Mạch xuyên trang | sửa `xml_tools/lyric_structure.py` + `audiveris_runner.py` (truyền trạng thái khi ghép trang) | |
| Hồ sơ cuốn sách | `workers/omr_checks/book_profile.py` + `storage/profiles/` | |
| API | `GET /api/conversions/{uuid}/review-queue`, `POST /api/conversions/{uuid}/review/{measure_id}` | trong `api.php`, service mới `ReviewQueueService` |
| UI | `resources/js/Components/MeasureReviewQueue.vue` | mở từ `EditorView.vue` |
| Đo lường | `workers/evaluation/review_benchmark.py` | mục 9 |

`audiveris_runner.py` chỉ thêm một bước sau khi đã có `score.musicxml`: `ledger = build_ledger(...); decide(ledger)`. Bước này ghi `measure_ledger.json` và `review_queue.json`, không đổi các artifact của Roadmap 1.

---

## 9. Đo lường — "nhanh" phải đo được

Thước đo chính không còn là "% nốt đúng" mà là bốn con số sau:

| Chỉ số | Định nghĩa | Mục tiêu |
|---|---|---|
| **Độ tin của ACCEPT** | Trong các ô máy tự chấp nhận, bao nhiêu % thực sự đúng | **≥ 99%**. Nếu thấp hơn, người lại phải dò cả bài. |
| **Độ phủ lỗi** | Trong các ô thực sự sai, bao nhiêu % bị đưa vào hàng đợi | ≥ 95% |
| **Tải soát** | % ô nhịp vào hàng đợi | ≤ 20% (bản in sạch) |
| **Thời gian người / bài** | Tổng giây trong hàng đợi (từ log B5) | đo baseline trước, rồi theo dõi theo từng commit |

Dữ liệu cần có:
- Ground truth **theo ô nhịp** (đúng/sai cho từng ô), không chỉ toàn văn. `tests/ground_truth/270.manual.json` đã có lời; cần thêm nhãn nốt cho cả 24 ô.
- **20–30 bài** phân tầng: 1 khuông có hợp âm; 4 bè 2 khuông; có điệp khúc; có liên ba hoặc chấm dôi dày; lời in thành thơ cuối trang; ảnh chụp điện thoại; nhiều trang.
- Cách gán nhãn nhanh: dùng chính hàng đợi B5 ở chế độ "soát toàn bộ". Người bấm đúng/sai cho từng ô, và đó chính là ground truth.

Các mục tiêu trên là **mục tiêu thiết kế**. Chỉ được ghi "đạt" sau khi chạy benchmark trên bộ dữ liệu này.

---

## 10. Lộ trình

### P0 — Sổ ô nhịp + 4 luật cốt lõi (1 tuần)
| Task | Nội dung | Tiêu chí xong |
|---|---|---|
| P0‑1 | `ledger.py`: dựng sổ ô nhịp từ MusicXML + `note_anchors.json` + `lyrics.json` + `page_model.json`, kể cả đánh số ô toàn bài sau merge | Test trên fixture `002`, `003` (`.omr` thật) |
| P0‑2 | `head_counter.py` (B1.1) | Test ảnh tổng hợp: đầu đen, đầu trắng, hợp âm 2 nốt, dấu hoá sát nốt |
| P0‑3 | `tuplet_marks.py` (B1.2) | Test có/không dấu "3" |
| P0‑4 | Luật C1, C2, C3, C4 | **Bài 270: ô 3 và ô 5 phải bị gắn `review`**; các ô đúng không bị gắn lỗi C1–C4 |
| P0‑5 | Ghi `measure_ledger.json`, `review_queue.json`; sinh `RecognitionIssue` | API trả danh sách ô cần soát |

### P1 — Hàng đợi soát (1 tuần)
| Task | Nội dung | Tiêu chí xong |
|---|---|---|
| P1‑1 | API review-queue + ghi quyết định | Test PHP |
| P1‑2 | `MeasureReviewQueue.vue`: ảnh cắt ‖ OSMD một ô ‖ lý do ‖ gợi ý ‖ phím tắt | Kiểm thử trình duyệt thật trên bài 270 |
| P1‑3 | Thẻ metadata ở đầu hàng đợi | Sửa được "NĂM" → "NẮM" trong 1 thao tác |
| P1‑4 | Log thời gian thao tác | Có số giây/ô cho bài 270 |

### P2 — Luật còn lại + mạch xuyên trang (1 tuần)
| Task | Nội dung | Tiêu chí xong |
|---|---|---|
| P2‑1 | C5, C9, C10 | Test tổng hợp |
| P2‑2 | `ink_scan.py` + C6 | Bài 270 trang 2: phát hiện hợp âm C bị thiếu |
| P2‑3 | Mạch section xuyên trang + C7 | Bài 270: "Tương lai…" và cả trang 2 là ĐK |
| P2‑4 | C8 gom `clef_check.py` và hoá biểu theo đa số | Test fixture |

### P3 — Sửa có bằng chứng (1–2 tuần)
| Task | Nội dung | Tiêu chí xong |
|---|---|---|
| P3‑1 | Chạy lại Audiveris trên ảnh cắt hệ phóng to | Gợi ý cho ô 3, ô 5 bài 270 thoả C1–C4 |
| P3‑2 | Dựng phương án nhịp từ ảnh (đầu nốt + liên ba + phách còn lại) — chỉ gợi ý | Test tổng hợp |
| P3‑3 | Engine thứ 2 theo khuông (homr hoặc tương đương): adapter + benchmark | Chỉ giữ nếu tăng độ phủ lỗi hoặc giảm tải soát trên bộ benchmark |
| P3‑4 | Cơ chế bật tự sửa theo từng loại lỗi khi đạt ngưỡng 99% | Mặc định tắt |

### P4 — Hồ sơ cuốn sách (1 tuần)
| Task | Nội dung | Tiêu chí xong |
|---|---|---|
| P4‑1 | `book_profile.py`: đọc/ghi, cập nhật tham số từ ô ACCEPT | Test |
| P4‑2 | Học cặp sửa chữ từ log, ngưỡng ≥ 3 xác nhận | Test |
| P4‑3 | Chọn cuốn lúc upload / gợi ý theo header | UI Dashboard |

### P5 — Benchmark liên tục
| Task | Nội dung |
|---|---|
| P5‑1 | Bộ 20–30 bài có nhãn theo ô nhịp (gán bằng chính hàng đợi B5) |
| P5‑2 | `review_benchmark.py`: 4 chỉ số mục 9, lưu theo commit |
| P5‑3 | Báo cáo so sánh trước/sau mỗi phase |

**Thứ tự đề xuất:** P0 → P1 là đủ để thấy tốc độ thay đổi rõ, vì người chỉ còn soát danh sách ô bị đánh dấu. P2–P4 giảm dần độ dài danh sách đó. P5 bắt đầu song song từ P1.

---

## 11. Rủi ro và giới hạn

| Rủi ro | Cách xử lý |
|---|---|
| Luật bắt sai quá nhiều (báo động giả) → hàng đợi dài | Mỗi luật có mức `error/warning/info` và ngưỡng chỉnh được; đo tỉ lệ báo động giả của từng luật trong P5, luật nào > 30% thì hạ mức |
| Bộ đếm đầu nốt kém với ảnh chụp điện thoại | Phân loại chất lượng ảnh (đã có `analyze_image_quality`); ảnh kém thì C2 hạ xuống `warning` |
| Melisma hợp lệ bị C1 báo lỗi | C1 trừ đi số nốt nằm trong dấu luyến; luyến không đọc được thì C1 chỉ là `warning` |
| Tự sửa sai mà không ai biết | Mặc định không tự sửa nốt; mọi sửa đều có vết và hoàn tác được; chỉ bật theo loại lỗi khi benchmark ≥ 99% |
| Hồ sơ cuốn sách "học" lỗi | Chỉ học từ thao tác người xác nhận; sửa chữ cần ≥ 3 lần; có nút xoá hồ sơ |
| Phụ thuộc định dạng `.omr` của Audiveris 5.11 | Giữ ghim phiên bản như Roadmap 1; ledger vẫn chạy với `measure_box` ước lượng từ vạch nhịp nếu thiếu `.omr` |

**Không làm** trong roadmap này: tự sinh nốt khi không có bằng chứng ảnh; thay Audiveris bằng engine học sâu khi chưa có benchmark; công bố tỉ lệ chính xác chung khi mới đo trên vài bài.
