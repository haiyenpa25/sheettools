# SHEETTOOLS — KẾ HOẠCH SỬA LỖI & NÂNG CẤP (09/2026)

> **Dành cho:** AI agent thực thi (ChatGPT / Codex).
> **Nguồn:** Rà soát tĩnh toàn bộ source ngày 24/09/2026 (PHP backend, Python workers, Vue frontend). Chưa chạy test vì máy dev không có PHP/Python ngoài Docker.
> **Thay thế:** các mục chưa xong trong `SHEETTOOLS_SOURCE_OPTIMIZATION_ROADMAP.md`. Nếu hai file mâu thuẫn, **file này được ưu tiên**.

---

## 0. QUY TẮC BẮT BUỘC KHI THỰC THI

1. Không viết lại toàn bộ dự án. Giữ stack hiện tại: PHP 8.3 thuần + Vue 3/Vite/TS + Python workers + Audiveris, chạy trong Docker.
2. Làm theo thứ tự các phase, từ **P0 → P1 → P2 → P3**. Hết mỗi phase phải: chạy test → cập nhật `NEXUS.md` → commit → báo cáo → **dừng lại chờ duyệt**.
3. Số dòng (`file:line`) trong tài liệu này là **gần đúng**. Phải đọc code và xác minh trước khi sửa.
4. Mỗi lỗi sửa xong phải có ít nhất **một test tái hiện lỗi đó**: test fail trước khi sửa, pass sau khi sửa.
5. Không bao giờ tự "sửa" dữ liệu người dùng (lời, nốt, dấu tiếng Việt) một cách âm thầm. Mọi chỉnh sửa tự động chỉ được là **gợi ý**, người dùng bấm chấp nhận mới áp dụng.
6. Không có kết quả giả: không fallback về file mẫu, không có nốt hoặc giai điệu hard-code, không dùng đuôi file giả.
7. Chạy test **trong Docker**:
   - PHP: `docker compose run --rm web php -d zend.assertions=1 -d assert.exception=1 tests/run_all.php`
   - Python: dùng pytest (xem P1-T6).
8. Tài liệu (`NEXUS.md`, `THUATTOAN.md`) phải mô tả đúng code thực tế. Không được ghi "PASS 100%" khi test chưa thực sự chạy.

---

## 1. ĐÁNH GIÁ NHANH

### Điểm mạnh (giữ nguyên)
- Kiến trúc tách lớp hợp lý: Services / Adapter (`OmrEngineInterface`) / Repository / DTO.
- `raw.musicxml` được giữ bất biến, `current.musicxml` là bản để sửa. Ghi file theo kiểu atomic (ghi file tạm rồi rename).
- Job queue lưu trên file, nhận job bằng atomic rename, có checkpoint từng trang PDF, có retry.
- Có Thùng rác kèm tombstone, nên worker không thể làm project đã xóa sống lại.
- `lyrics.json` là artifact độc lập, lưu cả toạ độ, confidence và candidates. Căn lời theo DP đơn điệu, chỗ không chắc được đánh `needs_review`.
- Frontend có split-view, thumbnail trang, sửa lời/hợp âm inline trên SVG, `tsconfig` bật strict.

### Điểm yếu cốt lõi
| Mảng | Mức | Vấn đề chính |
|---|---|---|
| Bảo mật | **Nghiêm trọng** | Ghi file tuỳ ý qua path traversal (có thể dẫn tới RCE trên XAMPP), đọc file tuỳ ý qua `format`, không có auth, CORS `*`, XPath injection |
| Sửa nhạc | **Hỏng** | Undo/redo không hoạt động, Play lỗi, phím tắt lỗi, sửa lời vào sai nốt, hợp âm bị nhân đôi, sửa trường độ làm hỏng nhịp |
| OMR / lời | **Yếu** | Lời từ trang 2 trở đi không bao giờ được căn; từ điển "sửa dấu" làm hỏng chữ đúng; CV fallback chạy âm thầm |
| Export | **Sai** | Frontend xuất `.mxl`/`.mscx` giả (thực chất là XML đổi đuôi) |
| Test | **Yếu** | Không có test HTTP, frontend không có test nào, `ApiTest.php` không assert gì mà vẫn in "PASS" |
| Code rác | Trung bình | ~40KB code demo, 7 component không dùng, `EditorView.vue` dài 2.400 dòng |
| Độ chính xác | **Chưa đo được** | Không có bộ dữ liệu ground truth và không có benchmark |

---

## 2. PHASE P0 — BẢO MẬT & LỖI LÀM HỎNG DỮ LIỆU (làm trước tiên)

### P0-T1. Chặn path traversal khi tạo project
- **Vị trí:** `api.php:95`, `app/Services/StorageService.php:69-72` (`getSourcePath`), `app/Services/ConversionService.php:~68`.
- **Lỗi:** `$json['filename']` do người dùng gửi được nối thẳng vào path. Với `../../x.php`, file được ghi ra ngoài thư mục project.
- **Làm:**
  - Không dùng tên file gốc làm tên lưu. Lưu thành `source/original.<ext>`, với `ext` lấy từ whitelist `pdf|png|jpg|jpeg`. Tên gốc chỉ lưu dạng metadata trong `project.json`.
  - Kiểm tra `realpath()` của file đích phải nằm trong thư mục project.
  - Multipart upload: kiểm tra `$_FILES[..]['error']`, `is_uploaded_file()`, kích thước (`max_file_size_mb`), MIME thật (`finfo`) và extension. Đọc giới hạn từ `config/omr.php`; hiện các giá trị này bị bỏ qua.
  - Thêm giới hạn `max_pages` khi tách PDF.
  - Thêm `storage/.htaccess` với nội dung `Require all denied`, đề phòng chạy trên XAMPP.
- **Test:** tạo project với filename `../../evil.php` phải trả về 422 và không có file nào bị ghi ra ngoài `storage/projects/{uuid}/`.

### P0-T2. Chặn đọc file tuỳ ý khi download
- **Vị trí:** `api.php:399-405`.
- **Làm:** whitelist `format ∈ {xml, musicxml, mxl}` và `variant ∈ {full, notation, lyrics}` trước khi dựng path. Giá trị khác trả về 400.
- **Test:** `?format=/../../project.json` phải trả về 400.

### P0-T3. XPath injection & validate input
- **Vị trí:** `NoteService.php:~71`, `HarmonyXmlWriter.php:~29`, `MusicXmlIndexService.php:~35,~90`, `workers/xml_tools/patcher.py:~28`.
- **Làm:**
  - `partId` phải khớp regex `^[A-Za-z0-9_-]{1,32}$`.
  - Measure, noteIndex, verse phải là số nguyên dương.
  - Python: dùng biến XPath của lxml (`xpath("...[@id=$pid]", pid=...)`), không dùng f-string.
- **Làm thêm:**
  - `PATCH status` (`api.php:~168`): chỉ cho phép một số trạng thái chuyển đổi qua lại, không được đặt `READY` từ client.
  - `PUT /musicxml` (`api.php:~203`): phải parse XML thành công và root phải là `score-partwise`. Nếu không, trả về 422.

### P0-T4. Auth tối thiểu + CORS
- **Vị trí:** `api.php:6-8`.
- **Làm:**
  - Thêm API token đơn giản qua env `SHEETTOOLS_API_TOKEN`, gửi trong header `Authorization: Bearer`. Nếu env trống (chế độ dev local) thì bỏ qua.
  - CORS lấy từ env `CORS_ORIGIN`, không dùng `*`.
  - `/api/health` public chỉ trả liveness (`{"ok":true}`). Chẩn đoán đầy đủ chuyển sang `/api/health/full` và yêu cầu token.
  - Không trả về đường dẫn server trong response.

### P0-T5. Shell & subprocess
- `AudiverisOmrEngine.php:~186-191`: lệnh fallback MXL chưa escape. Thay bằng `escapeshellarg`, hoặc tốt hơn là giải nén `.mxl` bằng `ZipArchive` trong PHP.
- `audiveris_runner.py:~317`: `z.extract` không kiểm tra path (zip-slip). Phải kiểm tra từng entry: không có `..`, không phải path tuyệt đối.
- UUID (`ConversionProject.php:~53-62`): thay `mt_rand` bằng `random_bytes`.

### P0-T6. Lỗi sửa lời vào sai nốt
- **Vị trí:** `MusicXmlService.php:~39` sinh `noteId = n_{m}_{i}`; `api.php:~263` mặc định `'n_0'`; `MusicXmlIndexService.php:~43-46` hiểu sai đó là part id rồi fallback sang measure của mọi part.
- **Làm:** thiết kế **locator ổn định** dùng chung cho cả BE và FE:
  ```
  { partId, measureIndex (0-based, không dùng @number), staff, voice, noteIndex (đếm theo cùng một quy tắc: bỏ <chord/>? bỏ rest?) }
  ```
  - Quy tắc đếm note phải **giống hệt nhau** giữa lúc extract (GET `/lyrics`) và lúc resolve (PATCH).
  - Không được fallback. Nếu không tìm thấy nốt thì trả về 404.
  - Bỏ hard-code `staff=1` và `voice=1` ở `api.php:~260,262,318,320`; lấy từ request.
- **Test:** trên golden XML (2 part), sửa lời verse 2 của nốt thứ 3 ở measure 5 part P2. Chỉ đúng nốt đó thay đổi; file diff chỉ khác đúng 1 `<lyric>`.

### P0-T7. Hợp âm bị nhân đôi
- **Vị trí:** `HarmonyXmlWriter.php:~36-76`. Hàm `addOrUpdate` luôn thêm mới.
- **Làm:**
  - Tìm `<harmony>` hiện có theo `(partId, measureIndex, beatOffset)`. Nếu có thì update, chưa có thì insert đúng vị trí theo `offset`/thứ tự so với các `<note>`.
  - Thêm API `DELETE /harmonies/{id}`.
  - Sửa hiển thị (`MusicXmlService.php:~103`) để có đủ root-alter (b/#), kind và bass.
- **Test:** PATCH cùng một hợp âm 3 lần thì số `<harmony>` không tăng. Kiểm tra `G/B`, `Bb`, `Cm7b5` và `D7#5` giữ được dạng text sau vòng đọc–ghi.

### P0-T8. Thứ tự phần tử MusicXML khi ghi
- **Vị trí:**
  - `NoteService.php:~141,~173` (`accidental`, `dot` bị append cuối).
  - `NoteService.php:~109` (đọc `root-alter` trong `<pitch>`; đúng phải là `<alter>`).
  - `LyricService.php:~88`: `createElement('text', $userText)` làm hỏng ký tự `&`. Dùng `textContent`.
  - `MusicXmlEngine.ts:~700-705` (FE append `type`/`dot`/`accidental` cuối).
  - `vietnamese_universal_ocr.py:~652,668,692` (`work`, `identification`, `credit` bị append sau `<part>`).
- **Làm:** viết helper `insertInSchemaOrder(noteEl, childName)` dựa trên thứ tự XSD của `<note>`: `grace, chord, pitch|rest|unpitched, duration, tie, instrument, voice, type, dot, accidental, time-modification, stem, notehead, staff, beam, notations, lyric`. Viết tương tự cho `<score-partwise>`: `work, movement-number, movement-title, identification, defaults, credit, part-list, part`. Dùng cùng logic ở PHP, TS và Python.
- **Test:** validate file sau khi sửa bằng XSD MusicXML 4.0 (P1-T5).

### P0-T9. Sửa trường độ phải cập nhật `<duration>`
- **Vị trí:** `MusicXmlEngine.ts:~700`, `NoteService.php`.
- **Làm:**
  - Khi đổi `<type>` hoặc `<dot>`, tính lại `<duration>` theo `<divisions>` đang có hiệu lực.
  - Sau khi sửa, chạy lại kiểm tra độ dài ô nhịp và hiện cảnh báo `overfull`/`underfull`. **Không** tự chèn hoặc xoá nốt.
  - Bỏ fallback `notes[noteIndex-1] || notes[0]` (`MusicXmlEngine.ts:~652`). Index sai thì báo lỗi.
  - Tìm measure theo part cụ thể, không lấy measure đầu tiên của mọi part.

### P0-T10. Gỡ bỏ "sửa dấu tiếng Việt" mù
- **Vị trí:**
  - `vietnamese_universal_ocr.py:28-67` (`LIGATURE_MAP`), `:~189` (`HYMN_PHRASE_FIXES`), `:~253,~456` (`clean_syllable` chạy trên cả chữ đã có dấu).
  - `vietnamese_healer.py`.
  - `cv_omr_engine.py:~697`.
  - `MusicXmlEngine.ts:~308-360` (nút "Sửa dấu TV").
- **Làm:**
  - Xoá các bảng map theo bài cụ thể (ví dụ `tối→tới`, `ca→cả`, `on→ơn`, `Thanh→Thánh`, tên tác giả hard-code).
  - Chỉ giữ một module gợi ý duy nhất, `vietnamese_context.py`, và chỉ áp dụng cho **token không có dấu**. Kiểm tra với `vietnamese_syllables.txt` (hiện chưa được load) và bigram theo ngữ cảnh. Kết quả ghi vào `lyrics.json` dạng `suggestions`, **không ghi đè `text`**.
  - FE: nút "Sửa dấu TV" đổi thành "Gợi ý dấu", mở danh sách gợi ý để người dùng chọn từng mục hoặc chấp nhận tất cả.
- **Test:** với chuỗi `"tối côi sau Hơi on ca"` có dấu đúng, output phải giống hệt input.

### P0-T11. CV fallback không được chạy âm thầm
- **Vị trí:** `audiveris_runner.py:~359-371` (khi thiếu Audiveris thì nhảy sang CV engine), trái với flag `ENABLE_EXPERIMENTAL_CV_FALLBACK` ở `:~496`.
- **Làm:**
  - Nếu Audiveris không có hoặc thất bại và flag ≠ 1, project phải chuyển sang `FAILED`, kèm thông báo tiếng Việt dễ hiểu (spec §46).
  - Nếu flag = 1: kết quả phải gắn `engine: "cv_experimental"` và status `NEEDS_REVIEW`, UI hiện banner cảnh báo.

### P0-T12. Frontend: undo/redo, Play, phím tắt
- **Vòng lặp prop:** `EditorView.vue:~2190` emit `update:xmlContent` → `App.vue:~317` → `watch(props.xmlContent)` (`EditorView.vue:~2378`) → `initXml()` tạo `MusicXmlEngine` mới, làm mất history.
  - Sửa: chỉ gọi `initXml` khi **project id đổi** hoặc khi XML mới ≠ `xmlEngine.getXmlString()`.
  - Mỗi lần sửa chỉ được render OSMD **một lần**.
- **Play:** `AudioPlaybackEngine.ts:352` gọi `extractMeasureNotes`, trong khi `MusicXmlEngine.ts:933` cũng gọi hàm này nhưng hàm không tồn tại (tên đúng là `getNotesInMeasure`). Đổi `xmlEngine: any` thành kiểu `MusicXmlEngine`.
  - Bỏ giai điệu hard-code (`AudioPlaybackEngine.ts:~139-169`).
  - Bỏ giới hạn 32 measure (`:~351`); duyệt theo số measure thực.
  - Tính thời lượng theo `duration/divisions` (có dot, 16th, triplet).
- **Phím tắt:** `EditorView.vue:2299-2367` dùng `measureNotes.value` chưa khai báo (tên đúng là `activeMeasureNotes`).
  - Phím tắt phải áp dụng cho `selectedNoteId`, không phải nốt đầu tiên.
  - Bỏ giới hạn measure 30 (`:~2294`).
  - Không bắt phím khi đang gõ trong input.
- **Lịch sử undo:** `onLyricChange` (`:~1932`) đang lưu history mỗi phím gõ. Gộp lại theo debounce 800ms hoặc khi blur.

### P0-T13. Export giả ở frontend
- **Vị trí:** `ExportModal.vue:~85,98,149,261`. `.mxl` và `.mscx` thực chất là XML đổi đuôi.
- **Làm:**
  - Mọi export đi qua backend `POST /export` rồi `GET /download`.
  - `.mxl` phải là ZIP có `META-INF/container.xml`.
  - Bỏ `.mscx` khỏi UI cho tới khi có converter thật (MuseScore CLI). `ExportService.php:~132` hiện chỉ copy file; xoá luôn.
  - Bỏ `:verses-count="4"` hard-code (`App.vue:~73`); lấy số verse thực từ XML.

**Tiêu chí hoàn thành P0:** tất cả test mới đều pass; đi hết 13 bước Acceptance Test trong `SHEET_CONVERTER_ANTIGRAVITY_SPEC.md §57` trên golden XML mà không có lỗi console; undo/redo được ít nhất 10 bước.

---

## 3. PHASE P1 — ĐỘ TIN CẬY PIPELINE & TEST

### P1-T1. Lời trang 2 trở đi không bao giờ được căn
- **Vị trí:** `audiveris_runner.py:~120` (word có `page = page_index`); `lyrics_aligner.py:~58` (XML mỗi trang không có `new-page`, nên mọi anchor đều là page 1); `:~430` (không căn lại sau khi merge).
- **Làm:** căn lời theo từng trang trên XML của **chính trang đó**, với key `(page_index, system_row)` nhất quán. Hoặc căn lại một lần sau merge, dùng mốc `new-page` mà merger chèn vào.
- **Làm thêm:**
  - Staff index của OCR (từ CV) và system của Audiveris có thể lệch nhau (`lyrics_aligner.py:~85`). Ghép bằng toạ độ y thực: lấy geometry từ file `.omr` nếu có, không ghép theo thứ tự.
  - Normalize x theo từng dòng (`:~103`) đang sai với dòng có pickup hoặc bắt đầu bằng dấu lặng. Dùng toạ độ tuyệt đối của nốt.
- **Test:** PDF 2 trang (`public/samples/002_tu_coi_long/source.pdf`) → lời trang 2 phải có trong MusicXML, tỉ lệ `no_note_candidate` < 20%.

### P1-T2. Page merger
- **Vị trí:** `audiveris_runner.py:~417,420`, `page_merger.py:~79-95`.
- **Làm:**
  - Giữ title thật, không ghi đè thành `"Merged Audiveris score"`.
  - Không đánh số lại measure pickup (`implicit="yes"`).
  - Ghép part theo thứ tự và tên/clef khi id khác nhau giữa các trang.
  - Part vắng mặt ở một trang thì chèn measure rest cho đủ.
  - Giữ credit của trang 1, bỏ credit lặp.

### P1-T3. Job queue cứng cáp
- **Vị trí:** `JobQueueService.php`, `workers/job_worker.php`, `AudiverisOmrEngine.php`.
- **Làm:**
  - Timeout thật: dùng `proc_open`, đọc `OMR_TIMEOUT_SECONDS`, khi quá hạn thì kill cả cây tiến trình (Java con của `.bat` trên Windows; `setsid` + `killpg` trên Linux). Python runner bỏ hard-code 180s (`audiveris_runner.py:~288`).
  - Lease/heartbeat: job đang xử lý ghi `heartbeat_at` mỗi 15s. Job quá 2 phút không có heartbeat thì trả về pending. Bỏ việc recover tất cả job khi worker khởi động.
  - `max_attempts = 3`; vượt quá thì `FAILED`.
  - Mỗi project chỉ có tối đa 1 job pending/processing.
  - Tự dọn `completed/` và `failed/` cũ hơn 7 ngày.
  - Worker xử lý SIGTERM để dừng êm.

### P1-T4. Audiveris adapter
- **Vị trí:** `audiveris_runner.py:~263-309`.
- **Làm:**
  - Mỗi lần chạy dùng output dir mới.
  - Kiểm tra exit code và sự tồn tại của `.omr` cùng `.mxl`/`.xml`. Không lấy `xml_files[0]` từ glob đệ quy (có thể trúng file cũ).
  - Tìm Audiveris qua env `AUDIVERIS_PATH` hoặc PATH. Bỏ glob `D:\tools`, `C:\Program Files` và các path Windows hard-code (`AudiverisOmrEngine.php:~58`, `HealthCheckService.php:~127`).
  - Chỉ chạy Audiveris một lần mỗi trang (dual-layer hiện chạy 2 lần, `:~487`), trừ khi người dùng bật chế độ chất lượng cao.

### P1-T5. Validator đầy đủ
- **Vị trí:** `workers/xml_tools/validator.py`.
- **Làm:**
  - Kiểm tra XSD MusicXML 4.0 bằng `xmlschema`. Đặt XSD trong repo.
  - Time signature theo từng measure (hiện chỉ lấy cái đầu tiên).
  - Không cảnh báo measure pickup là underfull.
  - Kiểm tra tie start/stop thành cặp; timing của voice/backup/forward; divisions; lyric mồ côi; verse thiếu.
  - Issue có severity `error` phải làm `isValid = false` (hiện harmony error bị bỏ qua, `:~53`).
  - Chặn đánh dấu `READY` và chặn export khi `isValid = false` (spec §35).
- Cập nhật `THUATTOAN.md §11` cho khớp với code.

### P1-T6. Hạ tầng test
- **Python:**
  - Chuyển 15 script test sang **pytest**.
  - Sửa `ZipInputTest.py` (import `extract_zip_pages`, hàm này chưa tồn tại): implement hàm hoặc xoá test.
  - Bổ sung vào `docker/requirements.txt` những gói đang thiếu: `scipy`, `scikit-image`, `xmlschema` (và `vietocr`/`torch` nếu giữ VietOCR).
- **PHP:**
  - Thêm test HTTP cho `api.php` (khởi động `php -S` trong test rồi gọi bằng curl). Phủ create/status/lyrics/harmonies/notes/export/download và **các case bảo mật** ở P0.
  - Viết lại `tests/Feature/ApiTest.php`: phải assert thật, dùng thư mục storage tạm, và được đưa vào `run_all.php`.
  - `FailureHandlingTest`: phải assert đúng loại lỗi, không được pass với bất kỳ exception nào.
  - Thêm test adapter với Audiveris giả (script trả về `.mxl` cố định hoặc exit ≠ 0, hoặc treo quá timeout).
- **Frontend:** thêm `vue-tsc --noEmit`, ESLint (vue + ts) và Vitest. Viết unit test cho `MusicXmlEngine` với golden XML: sửa lời, sửa nốt kèm duration, transpose, undo/redo.
- **CI:** thêm GitHub Actions chạy cả 3 bộ test cùng typecheck trên mỗi PR.

### P1-T7. Storage & quyền file
- `ConversionProjectRepository::save()` (`:~52`): ghi atomic (tmp + rename) và dùng `flock`. Web và worker ghi cùng file nên cần merge theo field hoặc có `revision` (optimistic lock). PATCH title không được bị worker ghi đè.
- `api.php:~104-105, ~207`: ghi XML trực tiếp; chuyển sang dùng helper atomic chung. Gộp 3 bản copy-paste thành một `AtomicFileWriter`.
- `compose.yaml`: worker chạy `user: www-data` (hiện chạy root, tạo file mà Apache không sửa được).
- `listAll()`: thêm phân trang, hoặc file index `projects_index.json`.

### P1-T8. Config thống nhất
- Tạo một loader `.env` duy nhất (`app/Config.php`). Sửa `.env.example` cho khớp tên biến code đang đọc: `MAX_FILE_SIZE_MB`, `MAX_PAGES`, `AUDIVERIS_PATH`, `TESSDATA_PATH`, `OMR_TIMEOUT_SECONDS`, `PROJECT_STORAGE_PATH`, `PYTHON_BIN`, `SHEETTOOLS_API_TOKEN`, `CORS_ORIGIN`, `ENABLE_EXPERIMENTAL_CV_FALLBACK`.
- Thay `python` hard-code (`ExportService.php:~39,127`, `ImagePreprocessService.php:~56,88`, `HealthCheckService.php:~107`, `tests/run_all.php:~62`) bằng `PYTHON_BIN`.

**Tiêu chí hoàn thành P1:** CI xanh; PDF 2 trang convert đủ nốt và lời cả 2 trang; job treo bị kill đúng timeout; không còn path hard-code Windows.

---

## 4. PHASE P2 — DỌN CODE & CẤU TRÚC FRONTEND

### P2-T1. Xoá code demo/chết
- **Frontend:**
  - Xoá `resources/js/Services/OmrTranscriptionService.ts`. File này không OMR gì cả, chỉ chọn bài mẫu theo tên file.
  - Xoá các component không được import: `ChordPanel`, `LyricsPanel`, `NoteEditor`, `IssuePanel`, `ExportDialog`, `ConversionProgress`, `UploadDropzone`. Có thể giữ lại để tái dùng ở P2-T2 nếu được viết lại.
  - Bỏ dữ liệu bài mẫu hard-code:
    - `EditorView.vue:~1650-1657` (title/composer).
    - `:~1730` (match chuỗi "HỠI THÁNH VƯƠNG").
    - `App.vue:~96,107,214-218` (đổi tên file `001 →` tên bài).
    - `App.vue:~323-333` (seed `/golden.xml` vào project chưa có XML).
    - `ProjectStore.ts:~41` (`activeProjectId = 'p_002'`).
    - `:~137` (fallback `projects[0]`).
  - Xoá "tracing canvas" mock (`EditorView.vue:~458-546, 1451-1497`) và công cụ 3-zone chưa chạy (`~1258-1436`). Nếu muốn giữ, phải nối với backend thật.
- **Backend:**
  - Xoá `MusicXmlValidatorInterface` không dùng, `LyricService::updateHarmony/updateNote` (stub trả `true`), các hàm songbook không có route (`StorageService.php:~181-240`), `extractMetadata`, `cleanAndNormalizeMusicXml`, và các `require_once` thừa (đã có PSR-4).
  - `ScoreVersion` và `RecognitionIssue`: nối vào luồng thật (P3-T3) hoặc xoá.
  - `HealthCheckService::checkAll` đang trả mỗi mục 2 lần; sửa lại.
- **Python:**
  - Xoá `vietnamese_healer.py`.
  - `auto_healer.py`: nếu không dùng thì xoá, hoặc để nó ghi issue vào report như `THUATTOAN §5.4` mô tả.
  - Gộp 3 bản code render PDF (`audiveris_runner.py:~210`, `cv_omr_engine.py:~102`, `extract_pdf.py:~11`) thành một.
  - Gộp các helper `_local`/`_children` đang copy ở 4 file.
- **Repo:**
  - Xoá khỏi repo: `DockerDesktopInstaller.exe` (625MB), `sheettools-main.zip`, thư mục `download/` (bản cũ), `dist/`, thư mục `.agents.disabled/`.
  - Giữ **một** bản golden XML duy nhất ở `tests/fixtures/golden_hymn.musicxml`. Xoá bản trùng ở root và ở `public/golden.xml`.
  - Cập nhật `.gitignore` và `.dockerignore` (không copy `tests/`, sample, `nodejs`/`npm` vào runtime image, `Dockerfile:~37,66-67`).

### P2-T2. Tách `EditorView.vue` (2.400 dòng)
- **Cấu trúc đích:**
  ```
  Components/editor/
    EditorToolbar.vue
    SourcePane.vue        (ảnh trang + highlight + thumbnails)
    ScorePane.vue         (wrapper OSMD, chỉ render + emit click)
    LyricsPanel.vue       (Verse 1..N động, bulk edit, move prev/next)
    ChordPanel.vue        (add/edit/delete/move, parser)
    NoteEditor.vue        (pitch/octave/duration/dot/accidental/rest/voice)
    IssuePanel.vue        (danh sách issue, next/prev)
  composables/
    useScoreDocument.ts   (MusicXmlEngine + undo/redo + dirty state)
    useOsmd.ts            (load/render 1 lần, map SVG ↔ note)
    usePlayback.ts
    useAutosave.ts        (debounce 1.5s, trạng thái saving/saved/error)
  ```
- Dùng **Pinia** thay cho singleton `ProjectStore`.
- Bỏ các giới hạn hard-code: picker chỉ có 16 measure (`~860, 936`), verse 1–4 (`~740`), octave 3–5 (`~1021`).

### P2-T3. Router & API client
- Thêm `vue-router`: `/`, `/library`, `/projects/:uuid/processing`, `/projects/:uuid/editor`, `/settings`, `/trash`. Reload trang phải giữ nguyên project đang mở.
- Tạo `api/client.ts` có kiểu dữ liệu đầy đủ, timeout, `AbortController` và error envelope thống nhất. Bỏ các `fetch` rải rác.
- Polling (`App.vue:~151-167`): huỷ khi rời trang, backoff tăng dần, tối đa 30 phút.
- Thay `alert()`/`confirm()` bằng toast và modal xác nhận.
- **Autosave:**
  - Debounce 1.5s và gửi PATCH có `revision`. Server trả 409 khi xung đột.
  - Không lưu `xmlContent` vào localStorage (hết quota 5MB); chỉ lưu id/metadata.
  - Chỉ báo "Đã lưu" khi server trả 200 (`ProjectStore.ts:~244-249` hiện gửi PUT mỗi phím, không báo lỗi).

### P2-T4. Chuẩn hoá API backend
- Tách `api.php` (425 dòng `if`/`preg_match`) thành router nhỏ kèm controller theo nhóm: Conversions, Edits, Export, Trash, Health.
- Mọi response dùng một envelope thống nhất: `{ "ok": bool, "data": ..., "error": { "code", "message_vi", "details" } }`.
- Global exception handler trả JSON, không trả HTML 500. Body JSON sai định dạng thì trả 400.
- Mã trạng thái nhất quán: create → 202; chưa sẵn sàng → 409; không tìm thấy → 404.
- Thêm route **bulk lyrics** (service đã có, chưa có route) và `DELETE harmony`.
- Log sự kiện theo spec §45 (`project_created`, `conversion_*`, `lyric_updated`, …) vào `storage/logs/events.log` dạng JSON lines.

---

## 5. PHASE P3 — NÂNG CẤP TÍNH NĂNG (chỉ làm khi P0–P2 xong)

Sắp xếp theo giá trị với người dùng, từ cao xuống thấp:

### P3-T1. Bộ ground truth + benchmark độ chính xác (ưu tiên cao nhất)
- Tạo `tests/benchmark/` gồm 20–50 trang thánh ca Việt Nam (PDF/ảnh) kèm MusicXML đã được người kiểm duyệt.
- Script `workers/evaluation/run_benchmark.py` báo cáo:
  - Note accuracy, với duration **đã chuẩn hoá theo `<divisions>`**. Hiện `accuracy_report.py:~43` so sánh raw duration.
  - Lyric CER/WER.
  - Alignment F1.
  - Chord accuracy.
- CI lưu kết quả; mọi thay đổi pipeline không được làm tụt điểm quá 2%.
- Không có số đo thì không được tuyên bố độ chính xác trong UI hoặc tài liệu.

### P3-T2. Liên kết chính xác Score ↔ Source
- **Score → model:** dùng graphic model của OSMD (`GraphicSheet.MeasureList`, `GraphicalNote.getSVGGElement()`) để map SVG sang note. Hiện `EditorView.vue:~1821` map theo thứ tự DOM modulo, `:~1785` match text lời, nên chọn sai nốt.
- **Score → ảnh nguồn:** backend trích bounding box của measure/note từ file `.omr` của Audiveris (XML bên trong zip) và trả về qua `GET /api/conversions/{uuid}/geometry`.
  - Source pane highlight đúng vùng, thay cho công thức "4 measure/dòng" (`EditorView.vue:~1631`).
  - Hai pane cuộn đồng bộ.
- Hiện highlight trên score cho nốt/measure đang chọn và khi playback (OSMD cursor).

### P3-T3. Review workflow theo confidence
- Sinh `RecognitionIssue` thật từ validator, từ lời `needs_review`, và từ nốt/lời có confidence thấp.
- IssuePanel có next/prev (phím F8 / Shift+F8), "Chấp nhận" và "Bỏ qua". Click vào issue thì highlight cả score lẫn source.
- Tô màu nốt/lời có confidence thấp trên score.
- Project chỉ được chuyển `READY` khi hết issue `error` và validator pass.

### P3-T4. Hợp âm từ OCR
- Harmony OCR đã được trích nhưng chưa bao giờ ghi vào score (`vietnamese_universal_ocr.py:~623`).
- Nối qua `ChordParser` (đã có ở PHP; cần bản tương đương ở Python hoặc gọi chung) để sinh `<harmony>` có `offset` theo beat, anchor theo `(part, measure, beatOffset)`.
- Đưa vào issue để người dùng duyệt, không tự commit.

### P3-T5. Gợi ý lời thông minh
- Ràng buộc số âm tiết với số nốt (không tính melisma/tie) cho mỗi câu, để phát hiện âm tiết bị gộp hoặc tách sai.
- "Dán lời đầy đủ" cho mỗi verse: tự map vào nốt, hiện bản xem trước trước khi áp dụng (spec §14).
- Gợi ý dấu dựa trên từ điển âm tiết và ngữ cảnh bigram (tiếp nối P0-T10).

### P3-T6. Hiệu năng OCR/OMR
- Đổi mọi hằng số pixel sang bội số của **interline** (khoảng cách dòng kẻ): `vietnamese_universal_ocr.py:~307,312,528,577`, các ngưỡng trong `cv_omr_engine.py`.
- Chỉ chạy một OCR engine chính; engine thứ hai chỉ chạy khi confidence thấp. Batch VietOCR. Gom Tesseract về một lần chạy mỗi dòng hoặc mỗi trang thay vì mỗi box.
- Xử lý các trang PDF song song (pool có giới hạn theo CPU/RAM).

### P3-T7. Version history
- Lưu snapshot `current.musicxml` mỗi lần autosave thành công (tối đa 50 bản, xoay vòng) vào `musicxml/history/`.
- UI xem danh sách phiên bản, so sánh diff theo measure, và khôi phục.
- Undo/redo theo command pattern (không snapshot toàn bộ DOM) và gộp các thao tác gõ liên tiếp.

### P3-T8. UX, giao diện, khả năng truy cập
- **Design token:** thay khoảng 83 màu hard-code (khoảng 55 trong `EditorView.vue`) bằng token. Làm cho `app.css` khớp với `DESIGN.md` (`surface-container-lowest`, `surface-tint`, fallback `#004ac6`). Load font JetBrains Mono.
- **i18n:** thêm `vue-i18n`, mặc định tiếng Việt. Bỏ các nhãn trộn Việt–Anh ("Lời nhạc (Lyrics)"). Việt hoá severity.
- **Accessibility:**
  - Modal có `role="dialog"`, focus trap và phím Esc.
  - Tabs có `role="tab"`.
  - Nút icon có `aria-label`.
  - Bỏ `select-none` ở root.
- **Responsive:** sidebar thu gọn được; dưới 1024px chuyển sang tab SOURCE / SCORE / EDIT (spec §9).

### P3-T9. Thay CV fallback
- `cv_omr_engine.py` chưa phải OMR thật:
  - Chỉ nhận treble clef; key/time mặc định.
  - Không nhận rest, accidental, dot hay tie.
  - Không đếm flat; không tách được nốt trắng/tròn.
  - Tự bịa rest để đủ measure (`:~793`).
- **Lựa chọn:** (a) xoá hẳn, hoặc (b) thay bằng model học sâu có sẵn (ví dụ `oemer`) qua một adapter mới `OmrEngineInterface`. Chỉ bật khi benchmark P3-T1 cho thấy nó tốt hơn Audiveris trên một nhóm ảnh cụ thể (ví dụ ảnh chụp điện thoại).

### P3-T10. Làm theo lô & tuyển tập
- Upload nhiều file hoặc một ZIP, xếp hàng convert. Gán vào songbook (API cho các hàm songbook đang có trong `StorageService`).
- Export cả tuyển tập (ZIP gồm MusicXML/MXL và `lyrics.txt`), và export PDF bằng Verovio thay cho `window.print`.

---

## 6. KHÔNG LÀM (giữ đúng phạm vi spec)
- Không làm DAW, full notation editor, MIDI, WebSocket/live sync, collaboration nhiều người, training model.
- Không thêm engine OMR mới khi chưa có benchmark P3-T1 để so sánh.
- Không đổi sang Laravel hoặc DB lớn trong các phase này. Nếu cần DB thì dùng SQLite, và chỉ khi P1-T7 chứng minh được là cần.

---

## 7. MẪU BÁO CÁO SAU MỖI PHASE

```text
PHASE: P0 | P1 | P2 | P3
TASKS DONE: P0-T1, P0-T2, ...
TASKS SKIPPED/BLOCKED: <id> — <lý do>
FILES CHANGED: <danh sách>
TESTS: <lệnh đã chạy> → <số pass/fail, dán output tóm tắt>
KNOWN ISSUES: <còn tồn đọng>
DOCS UPDATED: NEXUS.md, THUATTOAN.md (mục nào)
NEXT: chờ duyệt để sang phase tiếp theo
```
