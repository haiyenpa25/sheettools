# Tích hợp và đánh giá OMR học sâu — 2026-10-05

## Đã triển khai

- Homr và Clarity chạy trong container CPU riêng, qua hàng đợi file và API của SheetTools. Không cấp Docker socket cho ứng dụng.
- Profile Compose `neural-omr` gồm `homr`, `clarity`, `comparison-analysis`. Homr tải model khi build; Clarity tải model khi chạy lần đầu. Hai engine chạy bằng UID 33, cùng quyền lưu trữ với PHP.
- Homr source: `560ca5ce254db129b1b2167598bdc7a20ac5d6b0` (AGPL-3.0). Clarity source: `c6bb8a4d2a5b52842a9c41bd0f761f58d02f6f82` (GPL-3.0). Dependency snapshot nằm trong `/opt/runtime-requirements.txt` của từng image. Đây là phiên bản code đã chạy; không phải tuyên bố mọi model/package được khóa vĩnh viễn.
- Chạy trên toàn trang PNG gốc đã render. Clarity nhận PDF tạo từ PNG nhúng không mất dữ liệu, không nén lại JPEG.
- Mỗi lần chạy có thư mục `omr_comparisons/{run}/`, MusicXML riêng từng trang, source hash, vùng khuông, tọa độ Homr gần đúng, ảnh overlay và log.
- OCR phát hiện chữ theo từng vùng khuông để giữ độ phân giải, ghép dấu tiếng Việt theo cả dòng. Nhóm các dòng chữ sát nhau; giữ vùng chưa phân loại để soát.
- Khung YOLO của Clarity là vùng đọc có thể chứa lời. Bộ phân tích kiểm tra năm đường khuông trong crop trước khi dùng làm mép khuông; giữ nguyên khung YOLO trong artifact gốc và ghi `analysis_regions.json` riêng.
- Bản ghép lời thử nghiệm và các tọa độ từ attention đều cần soát. Clarity chưa cung cấp tọa độ từng nốt trong adapter này, nên không tự ghép lời theo thứ tự đoán.
- Nút **Phương án Homr** trong hàng soát lấy một ô từ kết quả đã chạy. Chỉ mở áp dụng khi khớp source page hash, số nốt/đầu nốt/lời, cao độ từ ảnh, trường độ liên ba và divisions. Phạm vi gate hiện là liên ba nốt đen được xác nhận từ ảnh, không phải mọi ký hiệu nhạc.

## Kết quả chạy thực tế

Số nốt bên dưới là lượng đầu ra, **không phải độ chính xác**.

| Bài | Homr: khuông / nốt có cao độ | Clarity: khuông / nốt có cao độ |
| --- | --- | --- |
| 270 trang 1 | 6 / 67 | 6 / 63 |
| 270 trang 2 | 2 / 23 | 2 / 23 |
| 002 | 9 / 91 | 9 / 94 |
| 003 | 8 / 92 | 8 / 95 |

Hai engine hoàn thành cả bốn trang của ba bài. Không có đáp án nốt toàn bài cho 002/003 nên chưa tính accuracy.

### Hai ô liên ba của bài 270

Đáp án: `tests/ground_truth/270.manual.json`, đã chép tay từ ảnh trước lần tích hợp này. Source PDF SHA-256: `68735aad8563c376cee765421eb36ac9a816ca62735373d268b2f3aecd2b59d5`.

| Ô | Homr | Clarity |
| --- | --- | --- |
| 3 | Đúng cả 4 cao độ và trường độ; ba nốt cuối mỗi nốt 2/3 phách | Cao độ đúng, ba trường độ thành 1, 1/2, 1/2 phách |
| 5 | Đúng cả 5 cao độ và trường độ | Thiếu B♭ cuối, liên ba bị đọc thành nốt đen |

Homr được đối chiếu qua tọa độ nốt nằm trong box ô nhịp đã xác nhận. Clarity được đối chiếu theo hệ trong assembly và số ô từng hệ trùng ledger; không dùng giả định số ô MusicXML phải giống số ô nguồn. Hai phương án Homr được đưa vào hàng soát, chưa áp dụng vào current.

### OCR lời trên vùng khuông Homr của bài 270

Đo văn bản OCR **trước khi gắn vào MusicXML**; chuẩn hóa hoa/thường và dấu câu, giữ dấu tiếng Việt. Dòng 2 bao gồm câu mở đầu điệp khúc vì nó nằm cùng hàng chữ in. Không phải điểm phân đoạn điệp khúc.

| Phần chữ | Âm tiết đáp án | Phép sửa theo edit distance | WER |
| --- | --- | --- | --- |
| Trang 1, hàng lời 1 | 60 | 0 | 0% |
| Trang 1, hàng lời 2 + đầu điệp khúc | 67 | 3 | 4,48% |
| Trang 1, hàng lời 3 | 60 | 5 | 8,33% |
| Trang 2, điệp khúc | 23 | 2 | 8,70% |

Tổng trang 1: 8 phép sửa / 187 âm tiết, WER 4,28%. Các số này không chứng minh lời đã gắn đúng nốt. Bản ghép thử vẫn bỏ qua nhiều chỗ do tọa độ attention/box âm tiết không đủ chắc chắn. Các lỗi như `mò/mờ`, `chỉm/chim`, `hể/hề`, `chăn/chân` còn tồn tại.

## Kiểm thử và bảo toàn dữ liệu

- PHP/Python regression runner: 52/52 suites đạt; nhóm External OMR có 10 test, Homr candidate kiểm việc từ chối xung đột cao độ và nguồn ảnh cũ, cùng thứ tự XML/tuplet marker.
- TypeScript `tsc --noEmit` và Vite production build đạt.
- Đã dùng Chromium headless mở bài 270 → Soát từng ô nhịp → Xem bản nhạc: OSMD dựng được SVG và ảnh đối chiếu. Ảnh QA ở workspace `storage/cache/omr-research/ui-comparison.png`.
- SHA-256 trước/sau của source PDF, `raw.musicxml`, `current.musicxml`, `omr/source.omr` giống nhau. Không áp dụng sửa tự động trong lần đánh giá này.

## Cách dùng

Trên máy đã triển khai: mở bài → **Soát từng ô nhịp** → **Chạy Homr** hoặc **Chạy Clarity**. Xem bản nhạc, ảnh vùng và nhật ký. Chọn ô cần sửa → **Phương án Homr** → xem đề xuất; người dùng quyết định áp dụng.

Khởi động trên máy khác:

```sh
docker compose --profile neural-omr build app homr clarity
docker compose --profile neural-omr up -d app worker homr clarity comparison-analysis
```

API:

- `POST /api/conversions/{uuid}/omr-comparisons` với `{"engine":"homr"}` hoặc `{"engine":"clarity"}`.
- `GET /api/conversions/{uuid}/omr-comparisons`: trạng thái engine, run và phân tích lời.
- `POST /api/conversions/{uuid}/review/{measure-id}/repair?engine=homr`: đề xuất sửa có kiểm định, không ghi current.

Tái lập đánh giá bằng `tests/manual/prepare_omr_comparison.php` và `tests/manual/audit_external_270.py --project ... --run ... --output ...`. Các bài benchmark được lưu riêng với tên `benchmark-*`, không thêm vào thư viện người dùng.

## Giới hạn và quyết định

Ưu tiên Homr để bổ sung bằng chứng và sửa các ô liên ba có kiểm định. Giữ Clarity làm nguồn đối chiếu: trong bài 270 nó bỏ sót liên ba; bước assembly còn thêm nghỉ để đủ nhịp. Không chọn Clarity làm engine mặc định chỉ vì XML vượt kiểm định cấu trúc.

Chưa nghiệm thu nhận dạng toàn bài, SATB hoặc ảnh chụp cong. Chưa huấn luyện model phân biệt lời/khuông riêng. Việc tách đoạn điệp khúc nằm giữa một hàng lời còn cần cải thiện. Luồng chuyển đổi mặc định vẫn dùng Audiveris; Homr/Clarity là chức năng chạy đối chiếu và tạo đề xuất đã hoạt động trên web.
