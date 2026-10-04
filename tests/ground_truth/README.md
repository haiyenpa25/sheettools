# Ground truth cho Roadmap 1

Đặt 30–50 bài đã được con người soát tại một thư mục dữ liệu riêng.
Chia nhóm: scan sạch, ảnh điện thoại, nhiều trang, 1 khuông có hợp âm,
SATB 2 khuông, ĐK/coda, lời 2–4 dạng thơ.

Mỗi bài cần source và các file truth như `manifest.example.json`.
`truth_page_model.json` chứa các `text_lines` có box pixel và role đã soát.
`truth_sections.json` chứa type, verse_count, measure_range đã soát.
Không dùng RAW Audiveris làm truth. Fixture .omr trong tests chỉ kiểm chứng parser.

Benchmark chạy qua module `evaluation.roadmap_benchmark`; luôn ghi commit,
source hash, số mẫu verified và các chỉ số theo từng mẫu. Không có mẫu verified
thì `accuracy_available=false`. Template mặc định `verified=false`.
