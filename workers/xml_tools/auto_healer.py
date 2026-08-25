#!/usr/bin/env python3
"""
workers/xml_tools/auto_healer.py
MusicXML Auto-Healer & Quantizer using music21.
Tự động làm sạch, cân bằng phách và quantize trường độ OMR từ kết quả nhận diện.

CẢI TIẾN:
  - Quantize trường độ lỗi (0.33 → 0.25, 0.66 → 0.5...) do OMR tính từ pixel
  - Tự động phát hiện Time Signature từ XML nếu music21 không đọc được
  - Lọc ghost notes (duration ≤ 0)
  - Bù phách thiếu bằng rest chuẩn
"""

import sys
import os
import argparse
from pathlib import Path


# Bảng lượng tử hóa trường độ (quarter length → nearest valid QL)
# Ánh xạ từ giá trị "bẩn" (do OMR tính từ pixel) sang giá trị nhạc lý chuẩn
_VALID_QLs = [0.125, 0.25, 0.375, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]


def _quantize_ql(ql: float) -> float:
    """
    Làm tròn một giá trị quarter-length "bẩn" về giá trị nhạc lý hợp lệ gần nhất.
    Ví dụ: 0.333 → 0.25, 0.666 → 0.5, 1.1 → 1.0
    """
    if ql <= 0:
        return 0.25  # Default: quarter note
    return min(_VALID_QLs, key=lambda v: abs(v - ql))


def heal_musicxml(input_xml_path: str, output_xml_path: str = None,
                  quantize: bool = True) -> bool:
    """
    Làm sạch và cân bằng MusicXML từ OMR.

    Args:
        input_xml_path: Đường dẫn MusicXML đầu vào
        output_xml_path: Đường dẫn đầu ra (mặc định ghi đè input)
        quantize: Có quantize trường độ lỗi không (khuyến nghị True)
    Returns:
        True nếu thành công
    """
    if output_xml_path is None:
        output_xml_path = input_xml_path

    if not os.path.exists(input_xml_path):
        print(f"Error: File not found: {input_xml_path}")
        return False

    try:
        from music21 import converter, meter, note, stream
    except ImportError:
        print("Warning: music21 not available for auto-healing. Skipping.")
        return False

    try:
        score = converter.parse(input_xml_path)
    except Exception as e:
        print(f"Notice: music21 cannot parse input XML ({e}), keeping original.")
        return False

    try:
        for part in score.parts:
            # ── 1. Xác định Time Signature ──
            ts_list = list(part.recurse().getElementsByClass('TimeSignature'))
            if not ts_list:
                # Thử trích xuất từ XML trực tiếp
                ts_detected = _read_ts_from_xml(input_xml_path)
                main_ts = meter.TimeSignature(ts_detected)
            else:
                main_ts = ts_list[0]

            expected_ql = main_ts.barDuration.quarterLength

            measures = list(part.getElementsByClass('Measure'))
            if not measures:
                continue

            # Chèn TimeSignature vào measure đầu nếu chưa có
            if not ts_list:
                measures[0].insert(0, main_ts)

            for m in measures:
                # ── 2. Lọc Ghost Elements (duration ≤ 0) ──
                to_remove = []
                for el in m.elements:
                    if hasattr(el, 'duration') and el.duration.quarterLength <= 0.001:
                        to_remove.append(el)
                for el in to_remove:
                    try:
                        m.remove(el)
                    except Exception:
                        pass

                # ── 3. Quantize trường độ ──
                if quantize:
                    for el in m.notesAndRests:
                        raw_ql = el.duration.quarterLength
                        snapped_ql = _quantize_ql(raw_ql)
                        if abs(raw_ql - snapped_ql) > 0.05:
                            el.duration.quarterLength = snapped_ql

                # ── 4. Cân bằng phách ──
                total_ql = sum(el.duration.quarterLength for el in m.notesAndRests)

                # Nếu tổng phách vượt quá mức cho phép, trim note cuối cùng
                if total_ql > expected_ql + 0.01:
                    last_el = None
                    for el in reversed(list(m.notesAndRests)):
                        last_el = el
                        break
                    if last_el is not None:
                        overflow = total_ql - expected_ql
                        new_ql = max(0.125, last_el.duration.quarterLength - overflow)
                        last_el.duration.quarterLength = _quantize_ql(new_ql)
                    total_ql = sum(el.duration.quarterLength for el in m.notesAndRests)

                # Bù phách thiếu bằng rest
                if total_ql > 0 and total_ql < expected_ql - 0.01:
                    missing_ql = expected_ql - total_ql
                    pad_rest = note.Rest(quarterLength=_quantize_ql(missing_ql))
                    m.append(pad_rest)

        # ── 5. Xuất MusicXML đã làm sạch ──
        score.write('musicxml', fp=output_xml_path)
        print(f"Auto-healed MusicXML successfully saved to: {output_xml_path}")
        return True

    except Exception as e:
        print(f"Auto-healing notice: {e}. Preserving original file.")
        return False


def _read_ts_from_xml(xml_path: str) -> str:
    """Đọc Time Signature trực tiếp từ XML nếu music21 không tải được."""
    try:
        import xml.etree.ElementTree as ET
        root = ET.parse(xml_path).getroot()
        beats = root.find('.//{*}beats') or root.find('.//beats')
        beat_type = root.find('.//{*}beat-type') or root.find('.//beat-type')
        if beats is not None and beat_type is not None:
            return f"{beats.text.strip()}/{beat_type.text.strip()}"
    except Exception:
        pass
    return '2/4'  # Default


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MusicXML Auto-Healer & Quantizer")
    parser.add_argument("--input", "-i", required=True, help="Input MusicXML file")
    parser.add_argument("--output", "-o", default=None, help="Output MusicXML file")
    parser.add_argument("--no-quantize", action="store_true", help="Disable duration quantization")
    args = parser.parse_args()

    success = heal_musicxml(args.input, args.output, quantize=not args.no_quantize)
    sys.exit(0 if success else 1)
