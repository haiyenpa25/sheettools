# Roadmap 2 — triển khai và nghiệm thu

Ngày kiểm tra: 2026-10-04. Yêu cầu: `Roadmap_2.md`. Mốc trước thay đổi: `9ce9e6d`.

## Đã triển khai

| Phần | Kết quả | Nghiệm thu |
|---|---|---|
| P0 | Sổ từng ô; đếm đầu nốt đen/trắng/chồng; đọc số liên ba riêng; C1–C4; quyết định accept/review | Test tổng hợp, fixture Audiveris 002/003, crop nguồn 270 ô 1/3/4/5. Ô 3/5 có C1+C2+C4; ô đúng 1/4 không có lỗi lõi |
| P1 | API hàng đợi và quyết định; ảnh nguồn cạnh OSMD một ô; metadata đầu hàng; Enter/E/N/1–9/mũi tên; log giây; sửa/hoàn tác | Test PHP lưu metadata Unicode, stale hash, RAW bất biến, undo; build/TypeScript đạt. **Chưa nghiệm thu trình duyệt thật** |
| P2 | C5–C10 tách file; scan mực + crop OCR; mạch điệp khúc xuyên trang; tích hợp kiểm khoá quãng tám | 270: phát hiện C bị thiếu; “Tương lai…” và trang 2 được đổi section ĐK trên bản dẫn xuất. **C8 mới tích hợp kiểm khoá; phần kiểm hoá biểu ảnh theo đa số chưa hoàn thiện** |
| P3 | Đọc lại hệ 2×; phương án từ đầu nốt/số 3; đối chiếu crop pitch và vị trí ảnh; kiểm C1–C4; candidate gắn hash; phải chọn áp dụng | 270 ô 3/5 đã tạo candidate đủ nốt và liên ba. Chưa tự áp dụng vào CURRENT. Engine thứ hai và bật tự sửa còn chờ benchmark |
| P4 | Chọn cuốn khi upload; lưu cấu hình; liệt kê/xoá hồ sơ; anchor median; học sửa chữ ở metadata hoặc ACCEPT lời khi cấu trúc nốt không đổi | Test chống đếm trùng, ba xác nhận/ngữ cảnh, không học khi nốt đổi; áp dụng profile lên header và lời |
| P5 | CLI benchmark theo commit; hash nguồn; nhãn lỗi 270 từng ô; chỉ số null khi thiếu đáp án | **Chưa có bộ 20–30 bài có nhãn đầy đủ**. Chưa đạt cổng nghiệm thu accuracy/coverage/load |

## Kiểm tra thực tế

- Bộ test: **49/49 nhóm**, thêm test cho crop thật và các cơ chế review/profile/repair. `npm run test:export`, `npx tsc --noEmit`, Vite build đạt.
- App và worker Docker dùng image mới; API health hoạt động. Pipeline 270 được chạy lại bằng checkpoint nhận diện đã kiểm hash, sau đó kiểm chéo bằng code mới. Crop sửa ô 3/5 thực sự chạy Audiveris riêng.
- Ô 3: ảnh 4 đầu nốt, OMR ban đầu 3; crop tìm đủ 4; số 3 và vị trí đầu nốt hỗ trợ ba quarter triplet, tổng 4 phách.
- Ô 5: ảnh 5 đầu nốt, OMR ban đầu 4; crop tìm đủ 5; đối chiếu số 3 và phách còn lại hỗ trợ ba quarter triplet, tổng 4 phách.
- Trang 2 ô local 2/global 19: scan tìm vùng C bị bỏ sót; crop OCR đọc `C`. Đây là gợi ý cần xác nhận, chưa chèn hợp âm tự động.
- Hai ô nốt và hai ô hợp âm sai đã biết được đưa vào review. Nhãn này không đủ tính accuracy toàn bài.
- Lần pipeline cuối: **16/25 ô cần soát (64%)**, chưa tính thẻ metadata. Mục tiêu ≤20% chưa đạt; không hạ cảnh báo chỉ để làm đẹp chỉ số.
- PDF/RAW và bốn file `.omr` nhận diện gốc giữ nguyên hash. Các file crop/OMR đọc lại được lưu riêng; không xoá artifact.

## Các mục chưa đạt

1. Trình duyệt của phiên làm việc không kết nối được, nên chưa kiểm tra trực tiếp render, click, phím tắt và tốc độ soát trên UI. Build thành công không thay thế cổng này.
2. Bộ đếm ảnh vẫn có ô báo thiếu dù OMR đủ nốt; scan mực cũng còn cảnh báo giả. Tải soát thực tế cao hơn mục tiêu 20%; cần gán nhãn toàn bộ để đo từng luật trước khi hạ mức.
3. Kiểm hoá biểu từ ảnh theo đa số (C8) cần hoàn thiện và thêm fixture có đổi giọng hợp lệ.
4. Chưa cài engine thứ hai: roadmap yêu cầu chỉ giữ khi benchmark chứng minh có cải thiện. Chưa có dữ liệu để quyết định.
5. Tự sửa nốt luôn tắt. Benchmark có cổng dữ liệu/threshold; chưa có hệ thống tự sửa được bật trong production.
6. Chưa có số giây soát của **người dùng thật**; test chỉ kiểm cơ chế lưu giây. Không dùng thời gian chạy máy làm thời gian thao tác người dùng.

## Sử dụng

Mở bài trong Editor → **Soát từng ô nhịp**. Bài cũ chưa có sổ có thể chọn **Tạo dữ liệu soát từ kết quả có sẵn**. Chọn **Đọc lại hệ 2×** để tạo phương án; chỉ phương án đã qua kiểm điều kiện mới có nút áp dụng.

Chọn cùng tên cuốn ở Dashboard cho các bài cùng cuốn. Học chữ chỉ lấy từ sửa metadata hoặc xác nhận lời đã sửa, cùng ngữ cảnh ít nhất ba sự kiện riêng; không dùng OCR đầu ra làm đáp án học.

```powershell
docker compose build app
docker compose up -d --no-build
docker exec sheettools-app php -d zend.assertions=1 tests/run_all.php
```

Benchmark với ledger và nhãn của đúng nguồn:

```text
python workers/evaluation/review_benchmark.py --ledger <measure_ledger.json> --truth tests/ground_truth/270.review.partial.json --log <review_state.json> --commit <git-hash> --output <report.json>
```

Các phase sau chưa được coi là nghiệm thu toàn bộ khi cổng UI/bộ nhãn ở trên còn thiếu.
