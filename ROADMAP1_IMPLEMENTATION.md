# Roadmap 1 — triển khai và kiểm chứng (2026-10-04)

## Đã triển khai

| Mục | Thay đổi | Kiểm chứng |
|---|---|---|
| P0 | Root hợp âm in hoa, grammar chặt, ưu tiên vị trí; giữ `ca/em/ba/Em` dưới khuông; hợp âm hệ đầu; từ điển NFC; gom dòng theo chiều cao chữ | `TextRolesTest` |
| P1 | Dò khuông một lần, `page_model.json` v2, vạch nhịp/gap fallback, separator theo thung lũng trắng, dải above/between/below | `PageModelTest`, `PageLayoutTest` |
| P1 | Hộp âm tiết theo chiếu nét chữ; thiếu khoảng trắng thì ghi `character_fallback` và `geometry_needs_review` | Test chữ giãn rộng |
| P1 | Metadata tựa nhiều dòng, Nhạc/Lời/Dịch, tempo/key/note; mask metadata/lyrics/chords độc lập, bảo vệ khuông cả phần padding | `HeaderSemanticsTest`, `PageModelTest`, `NotationLayerTest` |
| P1 UI | Nút “Vai trò chữ” trong Review Studio, đọc overlay thật từ API | Vite build; overlay mẫu thật đã kiểm tra trực quan |
| P2 | Parser `.omr` ghim 5.11.0: book logical part → measure voice/slot → chord containment → head bbox; kiểm tra số nhóm/nốt, fallback tường minh | `OmrAnchorsTest` dùng **hai .omr thật** của mẫu 002/003 |
| P2 | DP pixel không kéo giãn dòng lời; gate 2.5 interline; slur/melisma và `<extend>`; neo hợp âm theo onset, nội suy `<offset>` | `OmrAnchorsTest`, `ChordAnchoringTest`, `LyricAssemblyTest` |
| P3 | Marker lời/ĐK/Coda; Viterbi theo hệ và ô nhịp; chỉ số lời theo offset y, giữ marker tường minh; lời giữa 2 khuông | `LyricStructureTest`; SATB 4 dòng kiểm tra bằng fixture tổng hợp |
| P3 | Khối thơ có số lời, chiếu theo khuôn lời 1; sai số lượng âm tiết/thiếu confidence/trùng verse để soát | Test stanza khớp và lệch; số lượng khác dù trong ±10% cũng giữ review |
| P3 | `lyrics.json` v2 sections → verses → lines → syllables, giữ `words`/`verses` cũ; bảng xem section; tên lyric ĐK/Lời; tuỳ chọn nhân bản ĐK | `LyricAssemblyTest`, `ChorusExportTest` |
| B8 | `notation.musicxml` không lời, harmony chỉ từ lớp B5; `score.musicxml` chỉ chèn alignment accepted; validator phát hiện lyric number trùng; report thống kê section/review | Regression suite và chạy pipeline thật |
| P4 nền tảng | Manifest ground truth và benchmark theo commit: note/CER/WER/header/role/section/chord/anchor/review | `RoadmapBenchmarkTest`; không xuất accuracy khi thiếu mẫu verified |

## Kết quả kiểm tra hiện tại

- `php -d zend.assertions=1 tests/run_all.php` trong image Docker mới: **44/44 bộ test đạt**, gồm 11 trường hợp fusion dấu/kiểm tra octave clef. Checkpoint `roadmap1_v2` từ chối kết quả v1 khi Retry.
- `npx tsc --noEmit` và `npm run build`: đạt. Vite vẫn cảnh báo bundle lớn hơn 500 kB.
- Hai PDF khác nhau chạy Audiveris thật: mỗi export có 91 đầu nốt có cao độ được ánh xạ. Đây là số nốt trong export, không phải số nốt được nhận đúng.
- Mẫu 003: suy luận verse 2 lời (ô nhịp 1–8), chorus 1 dòng (9–18); 29 harmony accepted, 95 âm tiết accepted, 37 review.
- Mẫu 002: 28 harmony accepted, 60 âm tiết accepted, 27 review.
- Validator mẫu 003: XML/cấu trúc/music21 đạt; còn cảnh báo ô nhịp thiếu phách 8/9/13/14. Không tự chèn nốt để che cảnh báo.
- Source PDF hash không đổi. RAW và `.omr` lưu riêng; export/assembly chỉ làm việc trên dẫn xuất.
- Retry bản 270 mới nhất hoàn thành 2/2 trang trên image mới; cả hai checkpoint v2, sửa 6/2 octave clef theo từng trang. SHA-256 của PDF nguồn, RAW và `source.omr` giữ nguyên. Trạng thái `NEEDS_REVIEW` còn giữ để soát lỗi nhận dạng.
- Kết quả ghép PDF nhiều trang chuyển tiếp `document_artifact_path` của trang mở đầu để API cung cấp metadata đã nhận dạng; `PageWorkerRetryTest` kiểm tra luồng này.

## Giới hạn và việc cần dữ liệu thật

- Báo cáo người dùng trên riêng `270.pdf`: lời đúng cả dấu trang 1 từ 57% lên 89% (187 âm tiết), trang 2 từ 87% lên 91%; cao độ và hợp âm trang 1 đã sửa. Đây là kết quả đối chiếu thủ công do người dùng cung cấp, chưa được tái đo bằng manifest ground truth trong repository.
- Bài 270 còn thiếu khoảng 18 âm tiết trang 1 (chủ yếu thiếu nốt liên ba), câu mở điệp khúc cuối trang 1 còn bị xếp lời 2; trang 2 còn thiếu C và E♭m thành Em. Không dùng các số đo một bài để kết luận accuracy chung.

- Chưa có bộ **30–50 bài ground truth được soát bởi người**. Không xác nhận bất kỳ mục tiêu accuracy nào trong Roadmap_1.
- Mẫu thật hiện chỉ là 1 khuông/hệ. SATB, khối thơ lời 2–4, thiếu dòng, chuyển section giữa hệ được test tổng hợp; cần thêm mẫu thật để nghiệm thu các trường hợp này.
- Phân loại vai trò/section là rule baseline. Nhãn suy luận ghi `needs_review`; vẫn có OCR đọc sai chữ/dấu.
- Parser cố ý từ chối phiên bản Audiveris khác 5.11.0. Hệ thiếu ánh xạ pixel không trộn đơn vị pixel/tenths; giữ lời cần soát.
- `repeat`/volta chưa được dùng làm tín hiệu phân đoạn. Poem stanza chỉ tự gắn khi số âm tiết khớp hoàn toàn; chiếu theo từng câu có độ dài khác vẫn cần soát.
- Section đa trang giữ phạm vi ô nhịp **cục bộ từng trang**, có `page` và `measure_scope=page_original`; không giả định đó là số ô nhịp sau merge.
- Audiveris trong image hiện tại báo thiếu Tesseract **legacy eng** cho OCR nội bộ; lớp OCR tiếng Việt riêng vẫn chạy. VietOCR chưa cài, engine ghi notice và dùng RapidOCR/Tesseract.
- XSD/OSMD render tự động chưa chạy trên các export mới; không ghi nhận tương thích 100%.
- P4 huấn luyện classifier, homr engine thứ hai và VLM tuỳ chọn chưa bật: cần dataset và benchmark trước khi đánh giá/nâng cấp engine.

## Chạy benchmark

Sao chép `tests/ground_truth/manifest.example.json`, bổ sung các file đối chứng và prediction, chỉ đặt `verified=true` sau khi soát thủ công.

```powershell
docker run --rm --mount 'type=bind,source=C:\CODER\SheetTools,target=/workspace' --workdir /workspace/workers --entrypoint python sheettools:local -m evaluation.roadmap_benchmark --manifest ../tests/ground_truth/manifest.json --commit <git-commit> --output ../storage/roadmap1-benchmark.json
```

Chỉ số neo âm tiết dùng exact text + part + measure + beat + verse. Đây là phép đo kết hợp OCR/vị trí, không phải đánh giá alignment độc lập đã loại lỗi OCR. F1 hợp âm dùng root/kind/bass/degrees và vị trí beat chuẩn hoá divisions.
