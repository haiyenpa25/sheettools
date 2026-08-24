---
name: omr-pipeline
description: Hướng dẫn chuyên sâu và quy trình điều phối Audiveris OMR, Tesseract OCR vie+eng, OpenCV tiền xử lý ảnh, lxml patcher và music21 validator cho MusicXML.
---

# OMR MUSICXML PIPELINE SKILL

Skill này cung cấp kiến thức, lệnh điều khiển và phương pháp xử lý sự cố cho toàn bộ chuỗi xử lý OMR trong **Sheet Converter**.

---

## 1. TIỀN XỬ LÝ ẢNH (OPENCV PIPELINE)

Trước khi chuyển vào Audiveris, ảnh cần qua các bước tiền xử lý để tối ưu độ chính xác:
1. **Deskew (Chỉnh góc nghiêng)**: Dùng phép biến đổi Hough Lines để phát hiện góc nghiêng của các dòng kẻ khuông nhạc và xoay về 0 độ.
2. **Grayscale & Contrast**: Tăng cường độ tương phản giữa nốt nhạc đen và nền giấy trắng.
3. **Binarization (Otsu/Adaptive Thresholding)**: Khử bóng đổ và vết bẩn giấy cũ.
4. **Margin Crop**: Cắt bỏ viền thừa của scanner hoặc camera.

---

## 2. ĐIỀU PHỐI AUDIVERIS & TESSERACT OCR

### Lệnh thực thi Audiveris không đầu (Headless CLI):
```bash
java -cp "audiveris.jar" org.audiveris.omr.Main -batch -export -output "output_dir" "input_file.png"
```

### Cấu hình ngôn ngữ OCR Tesseract:
- Ngôn ngữ: `vie+eng` (Tiếng Việt + Tiếng Anh).
- Thư mục dữ liệu: `TESSDATA_PREFIX` trỏ đến thư mục chứa `vie.traineddata` và `eng.traineddata`.
- Chú ý: Audiveris cần được cấu hình nhận đúng tham số OCR trong file cấu hình `audiveris.properties` hoặc biến môi trường.

---

## 3. PATCHING MUSICXML VỚI PYTHON LXML

Khi người dùng sửa Lyric, Harmony hoặc Note:
- **Không parse lại toàn bộ bằng framework nặng**.
- Dùng `lxml.etree` để định vị XPath chính xác:
  ```python
  # Tìm measure và note cụ thể
  measure = tree.xpath(f"//part[@id='{part_id}']/measure[@number='{measure_num}']")[0]
  # Cập nhật hoặc chèn thẻ <lyric>
  # Cập nhật hoặc chèn thẻ <harmony>
  ```
- Ghi lại vào `current.musicxml` với định dạng UTF-8.

---

## 4. VALIDATION VỚI MUSIC21 & XML SCHEMA

Trước khi xuất file:
1. Kiểm tra tính hợp lệ XML (`xmlschema` / MusicXML XSD).
2. Dùng `music21.converter.parse('current.musicxml')` để kiểm tra:
   - Các measure có tổng thời lượng (beats) vượt quá Time Signature hay không.
   - Thẻ `<harmony>` có chứa Root/Kind hợp lệ không.
   - Có nốt/lời nào bị mồ côi (orphan) không.
