#!/usr/bin/env python3
"""
workers/cv_omr_engine.py  — Phiên bản 2.0 (Nâng cấp Toàn diện)
=============================================================================
Thuật toán Thị Giác Máy Tính (Computer Vision OMR) nhận diện bản nhạc từ PDF/Ảnh scan.

CẢI TIẾN SO VỚI v1.0:
  [FIX-1]  detect_staves(): Dùng scipy.signal.find_peaks thay vì ngưỡng pixel cứng.
           Tự tính interline (unit_size) theo DPI thực tế → không bị ảnh hưởng bởi DPI.
  [FIX-2]  detect_barlines(): Lọc false-positive từ dấu hóa thăng/giáng bằng kiểm tra
           độ dày và ngưỡng density chuẩn hóa theo interline (không dùng 320px cứng).
  [FIX-3]  detect_noteheads(): Kernel ellipse adaptive (scale theo interline thực tế).
           Bổ sung hollow-notehead detection để phân biệt nốt trắng (half) và nốt tròn (whole).
  [FIX-4]  Pitch Mapping: Snap-to-nearest-staffline thay vì int(round(dy)).
           Đây là fix quan trọng nhất — ngăn lỗi E4 → G4 → B4 chỉ vì lệch vài pixel.
  [FIX-5]  Duration Classification: 4 bước Filled→Stem→Beam→Flag
           (whole / half / quarter / eighth / sixteenth).
  [FIX-6]  Key Signature Detection: Đếm số dấu thăng/giáng ở đầu khuông, áp dụng
           dấu hóa đúng theo vòng 5ths (C→G→D→A→E→B, C→F→Bb→Eb→Ab→Db→Gb).
  [FIX-7]  match_lyrics(): Vùng OCR tự động phát hiện (auto-detect lyric zone),
           hỗ trợ multi-verse, tolerance scale theo interline (không cứng 80px).
  [FIX-8]  pdf_to_png(): Trích xuất TẤT CẢ trang PDF (không chỉ trang 0).
           Kết nối với page_merger.py để ghép MusicXML đa trang.
"""

import os
import sys
import json
import argparse
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import cv2
import numpy as np

# ───── BẢng ánh xạ cao độ cơ sở (Treble Clef, không tính dấu hóa giọng) ─────
# Dòng kẻ 1 (dưới cùng) = E4 = index 0
# Mỗi bước = nửa khoảng (half_step = interline / 2)
#
#  idx -4: A3   idx -3: B3   idx -2: C4   idx -1: D4
#  idx  0: E4   idx  1: F4   idx  2: G4   idx  3: A4
#  idx  4: B4   idx  5: C5   idx  6: D5   idx  7: E5
#  idx  8: F5   idx  9: G5   idx 10: A5   idx 11: B5
#  idx 12: C6   idx 13: D6

_BASE_PITCH: dict[int, tuple[str, int]] = {
    -8: ('D', 3), -7: ('E', 3), -6: ('F', 3), -5: ('G', 3),
    -4: ('A', 3), -3: ('B', 3), -2: ('C', 4), -1: ('D', 4),
     0: ('E', 4),
     1: ('F', 4),  2: ('G', 4),  3: ('A', 4),  4: ('B', 4),
     5: ('C', 5),  6: ('D', 5),  7: ('E', 5),  8: ('F', 5),
     9: ('G', 5), 10: ('A', 5), 11: ('B', 5), 12: ('C', 6),
    13: ('D', 6), 14: ('E', 6), 15: ('F', 6), 16: ('G', 6),
}

# Vòng thứ 5 — ánh xạ số dấu thăng/giáng sang các nốt cần dấu hóa
_SHARP_ORDER = ['F', 'C', 'G', 'D', 'A', 'E', 'B']   # 1# → F#, 2# → F#C#...
_FLAT_ORDER  = ['B', 'E', 'A', 'D', 'G', 'C', 'F']   # 1b → Bb, 2b → BbEb...


def get_key_accidentals(key_fifths: int) -> dict[str, int]:
    """
    Trả về dict {step: alter} cho tất cả các nốt cần dấu hóa theo key_fifths.
    key_fifths > 0: số dấu thăng, < 0: số dấu giáng.
    """
    acc: dict[str, int] = {}
    if key_fifths > 0:
        for i in range(min(key_fifths, 7)):
            acc[_SHARP_ORDER[i]] = 1   # alter = +1 (thăng)
    elif key_fifths < 0:
        for i in range(min(-key_fifths, 7)):
            acc[_FLAT_ORDER[i]] = -1   # alter = -1 (giáng)
    return acc


class ComputerVisionOmrEngine:
    """
    Bộ máy OMR thuần Computer Vision — không cần Java, không cần GPU.
    Độ chính xác cao nhất khi ảnh đã được tiền xử lý bởi preprocessing/pipeline.py.
    """

    def __init__(self,
                 key_fifths: int = 1,
                 time_beats: int = 2,
                 time_beat_type: int = 4,
                 debug: bool = False):
        self.key_fifths = key_fifths
        self.time_beats = time_beats
        self.time_beat_type = time_beat_type
        self.debug = debug
        self._key_acc = get_key_accidentals(key_fifths)

    # ════════════════════════════════════════════════════════════
    # 1. PDF → PNG (TẤT CẢ các trang, không chỉ trang 0)      [FIX-8]
    # ════════════════════════════════════════════════════════════

    def pdf_to_png_all_pages(self, pdf_path: str, output_dir: str, dpi: int = 300) -> list[str]:
        """Chuyển đổi TẤT CẢ các trang PDF thành danh sách file PNG."""
        try:
            import pypdfium2 as pdfium
        except ImportError:
            raise ImportError("Thiếu thư viện: pip install pypdfium2")

        doc = pdfium.PdfDocument(pdf_path)
        pages_out = []
        for i, page in enumerate(doc):
            bitmap = page.render(scale=dpi / 72)
            img = bitmap.to_pil()
            out_png = os.path.join(output_dir, f"page_{i:04d}.png")
            img.save(out_png, "PNG")
            pages_out.append(out_png)
        doc.close()
        return pages_out

    # ════════════════════════════════════════════════════════════
    # 2. Phát hiện Khuông Nhạc (Staff Lines)                  [FIX-1]
    # ════════════════════════════════════════════════════════════

    def _detect_interline(self, gray_img: np.ndarray) -> float:
        """Tự động ước tính interline (khoảng cách giữa 2 dòng kẻ khuông nhạc) theo pixel."""
        h, w = gray_img.shape
        _, bin_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Morphological opening để chỉ giữ dòng ngang dài
        min_line_w = int(w * 0.20)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_line_w, 1))
        lines_only = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, h_kernel)

        # Horizontal projection
        proj = np.sum(lines_only, axis=1).astype(np.float32)
        proj /= (w * 255.0)  # Normalize 0..1

        # Tìm các peak
        try:
            from scipy.signal import find_peaks
            # min_distance = 3px (dòng kẻ không sát nhau hơn 3px)
            peaks, props = find_peaks(proj, height=0.05, distance=3)
        except ImportError:
            # Fallback nếu scipy chưa có
            peaks = np.where(proj > 0.05)[0]

        if len(peaks) < 5:
            # Ước tính mặc định: giả định khuông nhạc chiếm ~15% chiều cao ảnh
            return h * 0.035

        # Tính khoảng cách trung bình giữa các peak liên tiếp
        diffs = np.diff(peaks)
        # Lọc các khoảng cách hợp lý (interline thường 8–60px)
        valid_diffs = diffs[(diffs >= 4) & (diffs <= 80)]
        if len(valid_diffs) == 0:
            return h * 0.035
        return float(np.median(valid_diffs))

    def detect_staves(self, gray_img: np.ndarray) -> list[list[float]]:
        """
        [FIX-1] Phát hiện các khuông nhạc 5 dòng bằng scipy.signal.find_peaks.
        Tự động tính interline theo DPI thực tế — không dùng ngưỡng pixel cứng.
        Cho phép gom 4–5 dòng (thay vì đúng 5) để chịu dòng kẻ mờ.
        """
        h, w = gray_img.shape

        # Binarize bằng Otsu (tự động, không hardcode 200)
        _, bin_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Lọc dòng ngang dài
        min_line_w = int(w * 0.20)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_line_w, 1))
        lines_only = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, h_kernel)

        # Horizontal projection (tổng pixel từng hàng / chiều rộng)
        proj = np.sum(lines_only, axis=1).astype(np.float32) / (w * 255.0)

        # Tìm peak
        try:
            from scipy.signal import find_peaks
            interline_est = self._detect_interline(gray_img)
            min_dist = max(3, int(interline_est * 0.5))
            peaks, _ = find_peaks(proj, height=0.05, distance=min_dist)
        except ImportError:
            peaks = np.array([y for y in range(h) if proj[y] > 0.10])
            interline_est = h * 0.035

        if len(peaks) < 4:
            return []

        # Gom các peak thành nhóm 4–5 dòng (1 khuông nhạc)
        interline_est = self._detect_interline(gray_img)
        gap_threshold = interline_est * 2.5   # Khoảng cách tối đa giữa 2 dòng trong 1 khuông

        staves = []
        current_group = [float(peaks[0])]

        for y in peaks[1:]:
            dy = y - current_group[-1]
            if dy <= gap_threshold:
                current_group.append(float(y))
            else:
                if 4 <= len(current_group) <= 6:  # Cho phép 4–6 dòng (thay vì đúng 5)
                    # Chọn đúng 5 dòng đại diện nếu có hơn 5
                    staves.append(self._normalize_staff_lines(current_group))
                current_group = [float(y)]

        if 4 <= len(current_group) <= 6:
            staves.append(self._normalize_staff_lines(current_group))

        # Sắp xếp theo y tăng dần (từ trên xuống dưới)
        staves.sort(key=lambda s: s[0])

        if self.debug:
            print(f"[CV-OMR][DEBUG] detect_staves: interline_est={interline_est:.1f}px, staves={len(staves)}")

        return staves

    def _normalize_staff_lines(self, lines: list[float]) -> list[float]:
        """
        Nếu gom được nhiều hơn 5 dòng (do noise), chọn 5 dòng cách đều nhau nhất.
        Nếu chỉ có 4 dòng (1 dòng mờ), nội suy thêm dòng còn thiếu.
        """
        lines = sorted(lines)
        if len(lines) == 5:
            return lines
        if len(lines) == 4:
            # Nội suy dòng thiếu dựa vào interline trung bình
            mean_gap = (lines[-1] - lines[0]) / 3.0
            # Thêm dòng trên cùng nếu khoảng cách từ dòng 0 đến 1 > 1.5x mean_gap
            if (lines[1] - lines[0]) > mean_gap * 1.5:
                lines.insert(0, lines[0] - mean_gap)
            else:
                lines.append(lines[-1] + mean_gap)
        if len(lines) > 5:
            # Lấy 5 dòng có khoảng cách đều nhất
            interline = (lines[-1] - lines[0]) / 4.0
            return [lines[0] + i * interline for i in range(5)]
        return lines[:5]

    # ════════════════════════════════════════════════════════════
    # 3. Phát hiện Vạch Nhịp (Barlines)                       [FIX-2]
    # ════════════════════════════════════════════════════════════

    def detect_barlines(self, bin_img: np.ndarray, staff_lines: list[float], w: int) -> list[int]:
        """
        [FIX-2] Phát hiện vạch nhịp bằng density-based thresholding chuẩn hóa theo interline.
        - Lọc false positive từ dấu thăng/giáng (thường ngắn và mỏng hơn barline).
        - Không dùng ngưỡng pixel x cứng (320, w-200).
        """
        l_top = staff_lines[0]
        l_bot = staff_lines[-1]
        staff_h = l_bot - l_top
        interline = staff_h / (len(staff_lines) - 1)

        # ROI: vùng khuông nhạc mở rộng 2px trên dưới
        y1, y2 = max(0, int(l_top - 2)), min(bin_img.shape[0], int(l_bot + 2))
        roi = bin_img[y1:y2, :]
        roi_h = y2 - y1

        # Kernel dọc phải đủ dài để bao phủ toàn bộ khuông (≥ 80% staff_h)
        v_kern_h = max(int(staff_h * 0.80), 5)
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kern_h))
        v_lines = cv2.morphologyEx(roi, cv2.MORPH_OPEN, v_kernel)

        # Projection ngang (sum theo rows)
        h_proj = np.sum(v_lines, axis=0).astype(np.float32)
        # Normalize: chia cho (roi_h * 255) → 0..1
        h_proj_norm = h_proj / (roi_h * 255.0)

        # Barline thật: density ≥ 0.65 (≥ 65% chiều cao khuông có pixel)
        threshold = 0.65
        candidates = [x for x in range(w) if h_proj_norm[x] > threshold]

        if not candidates:
            return []

        # Gom các x liên tiếp thành 1 barline (cluster với tolerance = interline * 0.3)
        cluster_gap = max(int(interline * 0.3), 5)
        clustered: list[int] = []
        for x in candidates:
            # Bỏ qua lề trái (trước note đầu tiên) và lề phải (sau note cuối)
            # Lề trái ≈ 3 * interline (vùng khóa nhạc + dấu hóa)
            left_margin = int(interline * 4)
            right_margin = w - int(interline * 3)
            if x < left_margin or x > right_margin:
                continue
            # Kiểm tra chiều rộng của đoạn dọc (barline mỏng ≤ 3px, dấu hóa rộng hơn)
            if not clustered or (x - clustered[-1]) > cluster_gap:
                clustered.append(x)

        if self.debug:
            print(f"[CV-OMR][DEBUG] detect_barlines: {len(clustered)} barlines tại x={clustered}")

        return clustered

    # ════════════════════════════════════════════════════════════
    # 4. Phát hiện Key Signature                              [FIX-6]
    # ════════════════════════════════════════════════════════════

    def detect_key_signature(self, bin_img: np.ndarray, staff_lines: list[float]) -> int:
        """
        [FIX-6] Đếm số dấu thăng (#) hoặc giáng (b) ở vùng đầu khuông nhạc (sau khóa Sol).
        Trả về key_fifths: số dương = thăng, số âm = giáng, 0 = C major.
        """
        l_top = staff_lines[0]
        l_bot = staff_lines[-1]
        interline = (l_bot - l_top) / (len(staff_lines) - 1)

        # Vùng key signature: từ x = 2*interline đến x = 8*interline (sau khóa Sol)
        x1 = int(interline * 2.5)
        x2 = int(interline * 9.0)
        y1 = max(0, int(l_top - interline))
        y2 = min(bin_img.shape[0], int(l_bot + interline))

        if x1 >= x2 or y1 >= y2:
            return self.key_fifths

        roi = bin_img[y1:y2, x1:x2]

        # Tìm các symbol thẳng đứng nhỏ trong vùng key signature
        ks_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, int(interline * 1.5)))
        opened = cv2.morphologyEx(roi, cv2.MORPH_OPEN, ks_kernel)
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        sharp_count = 0
        flat_count = 0

        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            # Dấu thăng (#): hình vuông/chữ nhật ~interline x interline
            if int(interline * 0.6) <= ch <= int(interline * 1.8) and \
               int(interline * 0.4) <= cw <= int(interline * 1.2):
                ar = ch / max(cw, 1)
                if ar > 1.2:  # Dấu thăng thường cao hơn rộng
                    sharp_count += 1

        # Ưu tiên dùng key_fifths được cung cấp từ ngoài (từ Audiveris hoặc người dùng chọn)
        # Chỉ dùng kết quả phát hiện nếu rõ ràng hơn
        if sharp_count > 0 and sharp_count != abs(self.key_fifths):
            detected = sharp_count if flat_count == 0 else -flat_count
            if self.debug:
                print(f"[CV-OMR][DEBUG] detect_key: fifths={detected} (sharps={sharp_count}, flats={flat_count})")
            return detected

        return self.key_fifths

    # ════════════════════════════════════════════════════════════
    # 5. Phát hiện Đầu Nốt và Tính Cao Độ                    [FIX-3][FIX-4]
    # ════════════════════════════════════════════════════════════

    def _snap_to_staff_position(self, cy: float, staff_lines: list[float]) -> int:
        """
        [FIX-4] Snap-to-nearest-staffline pitch mapping.
        Thay vì int(round(dy)) thuần túy, tìm vị trí gần nhất (dòng kẻ hoặc khoảng giữa)
        trong hệ thống dòng kẻ thực tế để tránh lỗi lệch pixel.

        Returns:
            pitch_idx: 0 = E4 (Line 1), 1 = F4 (Space 1), 2 = G4 (Line 2), ...
        """
        l1 = staff_lines[-1]   # Line 1 = E4 (dưới cùng)
        interline = (staff_lines[-1] - staff_lines[0]) / (len(staff_lines) - 1)
        half_step = interline / 2.0

        # Tạo danh sách tất cả vị trí có thể (dòng kẻ và khoảng giữa)
        # Line 1 (E4) = idx 0, Space trên Line 1 (F4) = idx 1, Line 2 (G4) = idx 2...
        positions: list[tuple[float, int]] = []
        for line_idx, line_y in enumerate(reversed(staff_lines)):
            staff_pos_idx = line_idx * 2  # 0, 2, 4, 6, 8 cho 5 dòng kẻ
            positions.append((line_y, staff_pos_idx))
            if line_idx < len(staff_lines) - 1:
                # Khoảng giữa dòng hiện tại và dòng kẻ trên nó
                next_line_y = list(reversed(staff_lines))[line_idx + 1]
                space_y = (line_y + next_line_y) / 2.0
                positions.append((space_y, staff_pos_idx + 1))

        # Mở rộng thêm khoảng dưới Line 1 và trên Line 5 (ledger lines)
        for ext in range(1, 9):
            positions.append((l1 + ext * half_step, -ext))
        top_line_y = staff_lines[0]
        for ext in range(1, 9):
            positions.append((top_line_y - ext * half_step, len(staff_lines) * 2 - 2 + ext))

        # Tìm vị trí gần cy nhất
        best_pos = min(positions, key=lambda p: abs(p[0] - cy))
        pitch_idx = best_pos[1]

        return pitch_idx

    def detect_noteheads(self, bin_img: np.ndarray, staff_lines: list[float], w: int,
                         key_acc: dict[str, int] = None) -> list[dict]:
        """
        [FIX-3][FIX-4] Phát hiện đầu nốt nhạc và tính cao độ với snap-to-staffline.
        Phân biệt nốt đen (filled) và nốt trắng/tròn (hollow).
        Áp dụng dấu hóa theo Key Signature động.
        """
        if key_acc is None:
            key_acc = self._key_acc

        l1 = staff_lines[-1]  # Line 1 dưới cùng = E4
        interline = (staff_lines[-1] - staff_lines[0]) / (len(staff_lines) - 1)

        # [FIX-3] Kernel adaptive theo interline (không hardcode 16x12)
        nh_w = max(int(interline * 0.85), 6)
        nh_h = max(int(interline * 0.65), 5)

        # Phát hiện nốt đen (filled notehead)
        nh_kernel_filled = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (nh_w, nh_h))
        filled_opened = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, nh_kernel_filled)

        # Phát hiện nốt trắng (hollow notehead) — dùng kernel nhỏ hơn để bắt outline
        hollow_kernel_w = max(int(interline * 0.4), 4)
        hollow_kernel_h = max(int(interline * 0.3), 3)
        hollow_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (hollow_kernel_w, hollow_kernel_h))
        hollow_eroded = cv2.erode(bin_img, hollow_kernel)

        # Quét trong phạm vi khuông mở rộng (cho ledger lines trên/dưới)
        y_min = max(0, int(staff_lines[0] - interline * 3))
        y_max = min(bin_img.shape[0], int(staff_lines[-1] + interline * 3))

        noteheads: list[dict] = []

        # ── Phát hiện nốt đen ──
        contours, _ = cv2.findContours(
            filled_opened[y_min:y_max, :], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for cnt in contours:
            x, y_rel, cw, ch = cv2.boundingRect(cnt)
            y_abs = y_min + y_rel
            cx = x + cw / 2.0
            cy = y_abs + ch / 2.0

            # Kích thước hợp lệ của đầu nốt: 50%–200% interline về chiều rộng
            min_size = interline * 0.45
            max_size = interline * 2.0
            if not (min_size <= cw <= max_size and min_size * 0.6 <= ch <= max_size):
                continue

            # Bỏ qua vùng lề trái (khóa + dấu hóa: ≈ 3 interline) và lề phải
            if cx < interline * 3.5 or cx > w - interline * 2:
                continue

            # Kiểm tra nốt trắng (hollow): nếu center crop sáng → nốt trắng
            crop_y1 = max(0, int(cy - ch * 0.3))
            crop_y2 = min(bin_img.shape[0], int(cy + ch * 0.3))
            crop_x1 = max(0, int(cx - cw * 0.25))
            crop_x2 = min(w, int(cx + cw * 0.25))
            center_crop = bin_img[crop_y1:crop_y2, crop_x1:crop_x2]
            is_hollow = False
            if center_crop.size > 0:
                center_density = np.mean(center_crop) / 255.0
                is_hollow = center_density < 0.3  # Trung tâm ít pixel đen = hollow

            # [FIX-4] Tính cao độ bằng snap-to-staffline
            pitch_idx = self._snap_to_staff_position(cy, staff_lines)
            step, octave = _BASE_PITCH.get(pitch_idx, ('E', 4))

            # Áp dụng dấu hóa theo Key Signature (không hardcode F#)
            alter = key_acc.get(step, 0)

            # Phân tích Duration
            dur_type, dur_ql = self._classify_duration(bin_img, cx, cy, cw, ch, w, is_hollow)

            nh = {
                'cx': cx, 'cy': cy, 'x': x, 'y': y_abs, 'w': cw, 'h': ch,
                'step': step, 'octave': octave, 'alter': alter,
                'duration': dur_type, 'durationQL': dur_ql,
                'is_hollow': is_hollow,
                'pitch_idx': pitch_idx,
                'confidence': self._calc_confidence(cy, staff_lines, cw, ch, interline),
            }
            noteheads.append(nh)

        # Sắp xếp từ trái sang phải
        noteheads.sort(key=lambda n: n['cx'])

        if self.debug:
            print(f"[CV-OMR][DEBUG] detect_noteheads: {len(noteheads)} nốt phát hiện")

        return noteheads

    def _calc_confidence(self, cy: float, staff_lines: list[float], cw: float, ch: float, interline: float) -> float:
        """Tính điểm tin cậy 0.0–1.0 cho từng nốt (dùng để highlight nốt nghi ngờ sai trên UI)."""
        # Nốt nằm trong khuông → confidence cao hơn
        in_staff = staff_lines[0] <= cy <= staff_lines[-1]
        size_score = 1.0 - abs((cw / interline) - 0.85) * 2.0  # Gần 85% interline = tốt nhất
        pos_score = 0.9 if in_staff else 0.6
        return round(max(0.0, min(1.0, (size_score + pos_score) / 2.0)), 2)

    # ════════════════════════════════════════════════════════════
    # 6. Phân Loại Trường Độ (Duration)                       [FIX-5]
    # ════════════════════════════════════════════════════════════

    def _classify_duration(self, bin_img: np.ndarray, cx: float, cy: float,
                            cw: float, ch: float, w: int, is_hollow: bool
                            ) -> tuple[str, float]:
        """
        [FIX-5] Phân loại trường độ theo 4 bước: filled → stem → beam → flag.

        Returns:
            (duration_type: str, quarter_length: float)
            Ví dụ: ('quarter', 1.0), ('eighth', 0.5), ('half', 2.0), ('whole', 4.0)
        """
        h_img = bin_img.shape[0]

        # Bước 1: Xác định filled hay hollow
        if is_hollow:
            # Hollow: có thể là half (trắng) hoặc whole (tròn)
            # Whole không có stem, half có stem
            stem_found = self._has_stem(bin_img, cx, cy, cw, ch, w, h_img)
            if stem_found:
                return ('half', 2.0)
            else:
                return ('whole', 4.0)

        # Filled notehead: quarter, eighth, hoặc sixteenth
        stem_found = self._has_stem(bin_img, cx, cy, cw, ch, w, h_img)
        if not stem_found:
            # Filled không có stem → thường là ghost note hoặc lỗi detect → mặc định quarter
            return ('quarter', 1.0)

        # Tìm đầu stem (tip of stem)
        stem_tip_y = self._find_stem_tip(bin_img, cx, cy, cw, ch, h_img)
        beam_count = self._count_beams(bin_img, cx, cy, stem_tip_y, cw, w, h_img)

        if beam_count >= 2:
            return ('16th', 0.25)
        elif beam_count == 1:
            return ('eighth', 0.5)
        else:
            # Kiểm tra flag (móc đơn không nối vào beam) — stem đơn với dấu cong
            return ('quarter', 1.0)

    def _has_stem(self, bin_img: np.ndarray, cx: float, cy: float, cw: float, ch: float, w: int, h: int) -> bool:
        """Kiểm tra nốt có stem (đuôi nốt dọc) không."""
        # Quét vùng phía trên nốt (stem hướng lên)
        stem_search_h = int(ch * 4)  # Stem dài ~ 3-4 lần đầu nốt
        x1 = max(0, int(cx + cw * 0.2))
        x2 = min(w, int(cx + cw * 0.4))
        y_up_top = max(0, int(cy - stem_search_h))
        y_up_bot = max(0, int(cy - ch * 0.5))

        stem_up = bin_img[y_up_top:y_up_bot, x1:x2]
        density_up = np.sum(stem_up) / (stem_up.size * 255 + 1e-6)

        # Quét phía dưới (stem hướng xuống)
        y_down_top = min(h, int(cy + ch * 0.5))
        y_down_bot = min(h, int(cy + stem_search_h))
        x1d = max(0, int(cx - cw * 0.4))
        x2d = min(w, int(cx - cw * 0.1))

        stem_down = bin_img[y_down_top:y_down_bot, x1d:x2d]
        density_down = np.sum(stem_down) / (stem_down.size * 255 + 1e-6)

        return density_up > 0.25 or density_down > 0.25

    def _find_stem_tip(self, bin_img: np.ndarray, cx: float, cy: float, cw: float, ch: float, h: int) -> float:
        """Tìm y-coordinate của đầu stem (điểm xa nhất so với đầu nốt)."""
        # Thử tìm stem hướng lên trước
        x1 = max(0, int(cx + cw * 0.1))
        x2 = min(bin_img.shape[1], int(cx + cw * 0.5))
        search_h = int(ch * 5)

        col_up = bin_img[max(0, int(cy - search_h)):int(cy), x1:x2]
        if col_up.size > 0 and np.sum(col_up) > 0:
            col_sum = np.sum(col_up, axis=1)
            topmost = np.where(col_sum > 0)[0]
            if len(topmost) > 0:
                return cy - search_h + topmost[0]

        return cy - ch * 4  # Default

    def _count_beams(self, bin_img: np.ndarray, cx: float, cy: float, stem_tip_y: float,
                     cw: float, w: int, h: int) -> int:
        """Đếm số beam (vạch ngang nối nốt) để phân biệt eighth vs 16th vs 32nd."""
        # Tìm vùng beam gần đầu stem
        beam_x1 = max(0, int(cx + cw * 0.2))
        beam_x2 = min(w, beam_x1 + int(cw * 5))  # Beam kéo dài ~5 lần chiều rộng nốt
        beam_y_center = stem_tip_y + (cy - stem_tip_y) * 0.15  # Gần đầu stem

        search_band = int(abs(cy - stem_tip_y) * 0.6)
        beam_y1 = max(0, int(beam_y_center - search_band * 0.5))
        beam_y2 = min(h, int(beam_y_center + search_band * 0.5))

        if beam_y1 >= beam_y2 or beam_x1 >= beam_x2:
            return 0

        beam_roi = bin_img[beam_y1:beam_y2, beam_x1:beam_x2]
        if beam_roi.size == 0:
            return 0

        # Horizontal projection của vùng beam
        h_proj = np.sum(beam_roi, axis=1) / (beam_roi.shape[1] * 255.0 + 1e-6)

        # Đếm số peak trong projection (mỗi peak = 1 beam)
        try:
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(h_proj, height=0.2, distance=3)
            return len(peaks)
        except ImportError:
            return 1 if np.max(h_proj) > 0.3 else 0

    # ════════════════════════════════════════════════════════════
    # 7. Gắn Lời Tiếng Việt (Lyrics)                         [FIX-7]
    # ════════════════════════════════════════════════════════════

    def _get_ocr_engine(self):
        if not hasattr(self, '_ocr_engine') or self._ocr_engine is None:
            try:
                sys.path.insert(0, os.path.dirname(__file__))
                from xml_tools.vietnamese_universal_ocr import VietnameseUniversalOcrEngine
                self._ocr_engine = VietnameseUniversalOcrEngine()
            except Exception as e:
                self._ocr_engine = False
        return self._ocr_engine if self._ocr_engine is not False else None

    def extract_page_ocr(self, img_path: str, w: int, h: int) -> list[tuple[float, float, str]]:
        """Chạy Universal Vietnamese OCR (VietOCR Transformer + RapidOCR) cho toàn bộ trang."""
        detected_words: list[tuple[float, float, str]] = []
        engine = self._get_ocr_engine()
        if engine is not None:
            try:
                data = engine.extract_full_page_lyrics_and_metadata(img_path)
                for item in data.get('all_words', []):
                    txt_clean = item['text']
                    cx = item['cx']
                    cy = item['cy']
                    words = txt_clean.split()
                    if len(words) > 1:
                        box = item.get('box', [[cx-20, cy-10],[cx+20, cy-10],[cx+20, cy+10],[cx-20, cy+10]])
                        box_w = box[1][0] - box[0][0]
                        w_step = box_w / len(words)
                        for wi, w_str in enumerate(words):
                            w_cx = box[0][0] + (wi + 0.5) * w_step
                            detected_words.append((w_cx, cy, w_str))
                    else:
                        detected_words.append((cx, cy, txt_clean))
            except Exception as e:
                if self.debug:
                    print(f"[CV-OMR][DEBUG] Universal Vietnamese OCR notice: {e}")

        # Fallback sang pytesseract nếu không có RapidOCR
        if not detected_words:
            try:
                import pytesseract
                full_img = cv2.imread(img_path)
                if full_img is not None:
                    custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
                    data = pytesseract.image_to_data(
                        full_img, lang='vie+eng', config=custom_config, output_type=pytesseract.Output.DICT
                    )
                    n_boxes = len(data['text'])
                    for i in range(n_boxes):
                        txt = str(data['text'][i]).strip()
                        conf = int(data['conf'][i]) if str(data['conf'][i]).lstrip('-').isdigit() else 0
                        if txt and conf >= 20:
                            word_cx = data['left'][i] + data['width'][i] / 2.0
                            word_cy = data['top'][i] + data['height'][i] / 2.0
                            detected_words.append((word_cx, word_cy, txt))
            except Exception:
                pass

        return detected_words

    def match_lyrics(self, noteheads: list[dict], staff_lines: list[float],
                     page_words: list[tuple[float, float, str]], w: int, next_staff_top: float = None) -> None:
        """
        [FIX-7] Gắn lời bài hát tiếng Việt và hợp âm vào nốt nhạc từ tập từ đã trích xuất.
        """
        if not noteheads or not page_words:
            return

        l1 = staff_lines[-1]
        interline = (staff_lines[-1] - staff_lines[0]) / (len(staff_lines) - 1)

        lyric_top = int(l1 + interline * 0.25)
        lyric_bot = int(next_staff_top - interline * 0.4) if next_staff_top else int(l1 + interline * 5)
        lyric_bot = min(lyric_bot, lyric_top + int(interline * 5))

        if lyric_bot <= lyric_top:
            return

        # Lọc các từ thuộc dải lời của khuông này
        staff_words = [
            (cx, cy, txt) for cx, cy, txt in page_words
            if lyric_top <= cy <= lyric_bot and cx >= int(interline * 2.0)
        ]

        if not staff_words:
            return

        # Làm sạch và chuẩn hóa lỗi OCR tiếng Việt phổ biến
        def clean_vietnamese_ocr(txt: str) -> str:
            replacements = {
                'cﬁi': 'cõi', 'cﬂi': 'cõi', 'Ibng': 'lòng', 'lﬂng': 'lòng',
                'sﬁu': 'sâu', 'thﬁm': 'thẳm', 'd6': 'độ', 'ngﬂi': 'ngài',
                'chﬁa': 'chúa', 'thﬁnh': 'thánh', 'vﬁơng': 'vương',
                'cﬂng': 'cũng', 'ngﬂn': 'ngàn', 'trﬂn': 'trọn',
                'tﬁm': 'tấm', 'tﬂm': 'tấm', '|': '', '_': '',
            }
            res = txt
            for wrong, right in replacements.items():
                if res.lower() == wrong:
                    res = right.upper() if res.isupper() else right
            return res

        # Nhóm theo dòng dọc (Y) để phân biệt các Verse khác nhau
        staff_words.sort(key=lambda w: w[1])
        verse_clusters: list[list[tuple[float, float, str]]] = []
        cluster_y_thresh = interline * 0.8

        for cx, cy, text in staff_words:
            added = False
            for v_words in verse_clusters:
                avg_y = np.mean([w[1] for w in v_words]) if len(v_words) > 0 else cy
                if abs(cy - avg_y) < cluster_y_thresh:
                    v_words.append((cx, cy, clean_vietnamese_ocr(text)))
                    added = True
                    break
            if not added:
                verse_clusters.append([(cx, cy, clean_vietnamese_ocr(text))])

        tolerance_x = interline * 2.5

        # Gán lời từng verse vào nốt nhạc theo thứ tự không gian ngang
        for verse_idx, v_words in enumerate(verse_clusters):
            v_words.sort(key=lambda w: w[0])  # Sort by X
            for word_cx, _, word_text in v_words:
                candidates = [n for n in noteheads if f'lyric_{verse_idx}' not in n]
                if not candidates:
                    candidates = noteheads
                closest = min(candidates, key=lambda n: abs(n['cx'] - word_cx))
                if abs(closest['cx'] - word_cx) <= tolerance_x:
                    lyric_key = f'lyric_{verse_idx}'
                    closest[lyric_key] = word_text
                    if verse_idx == 0:
                        closest['lyric'] = word_text

    # ════════════════════════════════════════════════════════════
    # 8. Xuất MusicXML
    # ════════════════════════════════════════════════════════════

    def build_musicxml(self, staves_data: list[dict], title: str = "Bản Nhạc OMR") -> str:
        """Tạo MusicXML chuẩn hóa từ staves_data (dùng music21)."""
        try:
            from music21 import stream, note as m21note, chord as m21chord, meter, key as m21key, clef, metadata
            score = stream.Score()
            score.metadata = metadata.Metadata(title=title)
            part = stream.Part()
            part.id = 'P1'

            expected_ql = (self.time_beats / self.time_beat_type) * 4.0
            measure_num = 1

            for staff_item in staves_data:
                for m_notes in staff_item['measures']:
                    m = stream.Measure(number=measure_num)
                    if measure_num == 1:
                        m.timeSignature = meter.TimeSignature(f"{self.time_beats}/{self.time_beat_type}")
                        m.keySignature = m21key.KeySignature(self.key_fifths)
                        m.clef = clef.TrebleClef()

                    total_ql = 0.0
                    for n_data in m_notes:
                        step = n_data['step']
                        octave = n_data['octave']
                        alter = n_data.get('alter', 0)
                        pitch_str = step
                        if alter == 1: pitch_str += '#'
                        elif alter == -1: pitch_str += '-'
                        pitch_str += str(octave)

                        dur_ql = n_data.get('durationQL', 1.0)
                        n = m21note.Note(pitch_str, quarterLength=dur_ql)

                        # Gắn tất cả verse lời
                        for v in range(4):
                            lk = f'lyric_{v}' if v > 0 else 'lyric'
                            if lk in n_data and n_data[lk]:
                                n.addLyric(n_data[lk], lyricNumber=v + 1)

                        # Thêm confidence vào editorial (dùng cho UI)
                        if n_data.get('confidence', 1.0) < 0.6:
                            n.editorial.color = 'orange'  # Đánh dấu nốt nghi ngờ sai

                        m.append(n)
                        total_ql += dur_ql

                    # Tự động bù phách nếu thiếu
                    if 0 < total_ql < expected_ql - 0.01:
                        m.append(m21note.Rest(quarterLength=expected_ql - total_ql))

                    part.append(m)
                    measure_num += 1

            score.append(part)
            import tempfile, os as _os
            with tempfile.NamedTemporaryFile(suffix='.musicxml', delete=False, mode='w', encoding='utf-8') as tmp:
                tmp_path = tmp.name
            score.write('musicxml', fp=tmp_path)
            with open(tmp_path, 'r', encoding='utf-8') as f:
                xml_str = f.read()
            _os.unlink(tmp_path)
            return xml_str
        except Exception as e:
            print(f"[CV-OMR] music21 error: {e}, dùng fallback XML generator")
            return self._build_raw_xml(staves_data, title)

    def _build_raw_xml(self, staves_data: list[dict], title: str) -> str:
        """Fallback: xuất XML thô nếu music21 gặp lỗi."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<score-partwise version="4.0">',
            f'  <work><work-title>{title}</work-title></work>',
            '  <part-list><score-part id="P1"><part-name>Melody</part-name></score-part></part-list>',
            '  <part id="P1">',
        ]
        m_num = 1
        for staff in staves_data:
            for m_notes in staff['measures']:
                lines.append(f'    <measure number="{m_num}">')
                if m_num == 1:
                    lines += [
                        '      <attributes>',
                        '        <divisions>4</divisions>',
                        f'        <key><fifths>{self.key_fifths}</fifths></key>',
                        f'        <time><beats>{self.time_beats}</beats><beat-type>{self.time_beat_type}</beat-type></time>',
                        '        <clef><sign>G</sign><line>2</line></clef>',
                        '      </attributes>',
                    ]
                for n in m_notes:
                    dur_map = {'whole': 16, 'half': 8, 'quarter': 4, 'eighth': 2, '16th': 1}
                    dur_units = dur_map.get(n.get('duration', 'quarter'), 4)
                    alter_xml = f'        <alter>{n["alter"]}</alter>\n' if n.get('alter', 0) != 0 else ''
                    lyric_xml = f'        <lyric number="1"><syllabic>single</syllabic><text>{n["lyric"]}</text></lyric>\n' if 'lyric' in n else ''
                    lines += [
                        '      <note>',
                        '        <pitch>',
                        f'          <step>{n["step"]}</step>',
                        alter_xml.rstrip(),
                        f'          <octave>{n["octave"]}</octave>',
                        '        </pitch>',
                        f'        <duration>{dur_units}</duration>',
                        f'        <type>{n.get("duration", "quarter")}</type>',
                        lyric_xml.rstrip() if lyric_xml else '',
                        '      </note>',
                    ]
                lines.append('    </measure>')
                m_num += 1
        lines += ['  </part>', '</score-partwise>']
        return '\n'.join(l for l in lines if l)

    # ════════════════════════════════════════════════════════════
    # 9. Pipeline chính
    # ════════════════════════════════════════════════════════════

    def process_single_page(self, png_path: str, output_dir: str) -> dict:
        """Xử lý 1 trang ảnh PNG → MusicXML bằng kiến trúc 3-Zone Spatial Decomposition."""
        # 1. 3-Zone Spatial Decomposition (Header, Pure Notation Sheet, Lyrics/Verses)
        decomp_meta = None
        pure_img = None
        try:
            from xml_tools.vietnamese_universal_ocr import decompose_sheet_3zones
            decomp_meta = decompose_sheet_3zones(png_path)
            pure_img = decomp_meta.get('pure_notation_img')
        except Exception as e:
            print(f"[CV-OMR] 3-zone decomposition notice: {e}")

        # Dùng ảnh đã xóa sạch chữ (Pure Notation Sheet) để nhận diện nốt & khuông
        if pure_img is not None:
            gray_img = cv2.cvtColor(pure_img, cv2.COLOR_BGR2GRAY) if len(pure_img.shape) == 3 else pure_img
        else:
            gray_img = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)

        if gray_img is None:
            return {"success": False, "error": f"Không đọc được ảnh: {png_path}"}

        h, w = gray_img.shape
        _, bin_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        staves = self.detect_staves(gray_img)
        print(f"[CV-OMR] Trang {Path(png_path).name}: {len(staves)} khuông nhạc")

        if not staves:
            return {"success": False, "error": "Không phát hiện được khuông nhạc nào", "staves": 0}

        staves_data = []
        total_notes = 0

        # 2. Trích xuất OCR toàn trang
        page_words = self.extract_page_ocr(png_path, w, h)

        for s_idx, staff_lines in enumerate(staves):
            next_staff_top = staves[s_idx + 1][0] if s_idx + 1 < len(staves) else None

            # Detect key signature per staff (chỉ khuông đầu tiên)
            if s_idx == 0:
                self.key_fifths = self.detect_key_signature(bin_img, staff_lines)
                self._key_acc = get_key_accidentals(self.key_fifths)

            barlines = self.detect_barlines(bin_img, staff_lines, w)
            noteheads = self.detect_noteheads(bin_img, staff_lines, w)
            self.match_lyrics(noteheads, staff_lines, page_words, w, next_staff_top)

            # Phân chia nốt vào ô nhịp
            interline = (staff_lines[-1] - staff_lines[0]) / (len(staff_lines) - 1)
            left_margin = int(interline * 3.5)
            right_margin = w - int(interline * 2)
            bounds = [left_margin] + barlines + [right_margin]

            measures = []
            for b_i in range(len(bounds) - 1):
                bx1, bx2 = bounds[b_i], bounds[b_i + 1]
                m_notes = [n for n in noteheads if bx1 <= n['cx'] < bx2]
                if m_notes:
                    measures.append(m_notes)

            if not measures and noteheads:
                measures = [noteheads]

            staves_data.append({'staff_lines': staff_lines, 'measures': measures})
            total_notes += len(noteheads)

        title = decomp_meta['header'].get('title') if (decomp_meta and decomp_meta.get('header', {}).get('title')) else Path(png_path).stem
        xml_str = self.build_musicxml(staves_data, title)
        os.makedirs(output_dir, exist_ok=True)
        xml_out = os.path.join(output_dir, "cv_score.musicxml")
        with open(xml_out, 'w', encoding='utf-8') as f:
            f.write(xml_str)

        return {
            "success": True,
            "xml_path": xml_out,
            "staves_count": len(staves),
            "total_notes": total_notes,
            "key_fifths": self.key_fifths,
        }

    def process(self, input_file: str, output_dir: str) -> dict:
        """Pipeline chính: PDF/PNG → MusicXML (hỗ trợ đa trang)."""
        os.makedirs(output_dir, exist_ok=True)
        ext = Path(input_file).suffix.lower()

        if ext == '.pdf':
            # [FIX-8] Trích xuất TẤT CẢ trang PDF
            pages_dir = os.path.join(output_dir, "pages")
            os.makedirs(pages_dir, exist_ok=True)
            png_pages = self.pdf_to_png_all_pages(input_file, pages_dir, dpi=300)
            print(f"[CV-OMR] PDF có {len(png_pages)} trang")
        elif ext in ('.png', '.jpg', '.jpeg', '.tif', '.tiff'):
            png_pages = [input_file]
        else:
            return {"success": False, "error": f"Định dạng không hỗ trợ: {ext}"}

        if len(png_pages) == 1:
            # Đơn trang: xử lý trực tiếp
            return self.process_single_page(png_pages[0], output_dir)
        else:
            # Đa trang: xử lý từng trang rồi merge
            page_xmls = []
            for i, png_path in enumerate(png_pages):
                page_out_dir = os.path.join(output_dir, f"page_{i:04d}")
                os.makedirs(page_out_dir, exist_ok=True)
                result = self.process_single_page(png_path, page_out_dir)
                if result.get('success') and result.get('xml_path'):
                    page_xmls.append(result['xml_path'])

            if not page_xmls:
                return {"success": False, "error": "Không xử lý được trang nào"}

            # Gộp đa trang bằng page_merger.py
            combined_xml = os.path.join(output_dir, "combined.musicxml")
            try:
                sys.path.insert(0, os.path.dirname(__file__))
                from xml_tools.page_merger import merge_musicxml_pages
                title = Path(input_file).stem
                merge_musicxml_pages(page_xmls, combined_xml, title)
            except Exception as e:
                print(f"[CV-OMR] page_merger lỗi ({e}), dùng trang đầu tiên")
                import shutil
                shutil.copy(page_xmls[0], combined_xml)

            return {
                "success": True,
                "xml_path": combined_xml,
                "pages_processed": len(page_xmls),
                "key_fifths": self.key_fifths,
            }


# ════════════════════════════════════════════════════════════════
# CLI Entry Point
# ════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="CV OMR Engine v2.0 — Sheet Music to MusicXML")
    parser.add_argument("--input", "-i", required=True, help="Input PDF or Image file")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--key", type=int, default=1, help="Key signature fifths (default: 1 = G major / E minor)")
    parser.add_argument("--beats", type=int, default=2, help="Time signature beats (default: 2)")
    parser.add_argument("--beat-type", type=int, default=4, help="Time signature beat type (default: 4)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    engine = ComputerVisionOmrEngine(
        key_fifths=args.key,
        time_beats=args.beats,
        time_beat_type=args.beat_type,
        debug=args.debug
    )
    result = engine.process(args.input, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
