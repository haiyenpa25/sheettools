#!/usr/bin/env python3
"""
workers/xml_tools/auto_healer.py
MusicXML Auto-Healer & Quantizer using music21
Tự động làm sạch, cân bằng phách từng ô nhịp theo Time Signature và chuẩn hóa MusicXML từ OMR.
"""

import sys
import os
import argparse
from pathlib import Path

def heal_musicxml(input_xml_path: str, output_xml_path: str = None) -> bool:
    if output_xml_path is None:
        output_xml_path = input_xml_path

    if not os.path.exists(input_xml_path):
        print(f"Error: File not found: {input_xml_path}")
        return False

    try:
        from music21 import converter, meter, note, chord, stream, clef, key
    except ImportError:
        print("Warning: music21 not available for auto-healing. Skipping.")
        return False

    try:
        score = converter.parse(input_xml_path)
    except Exception as e:
        print(f"Notice: music21 cannot parse input XML ({e}), keeping original.")
        return False

    try:
        # 1. Duyệt qua từng part để làm sạch và cân bằng ô nhịp
        for part in score.parts:
            # Lấy time signature chính
            ts_list = part.getTimeSignatures()
            main_ts = ts_list[0] if ts_list else meter.TimeSignature('2/4')
            expected_ql = main_ts.barDuration.quarterLength

            measures = list(part.getElementsByClass('Measure'))
            for m in measures:
                # Loại bỏ các nốt hoặc chord có duration <= 0 (ghost elements)
                to_remove = []
                for el in m.elements:
                    if hasattr(el, 'duration') and el.duration.quarterLength <= 0.001:
                        to_remove.append(el)
                for el in to_remove:
                    m.remove(el)

                # Tính tổng phách hiện tại của ô nhịp
                total_ql = sum(el.duration.quarterLength for el in m.notesAndRests)
                
                # Nếu ô nhịp bị thiếu phách nhẹ, thêm dấu lặng bù vào cuối để đủ nhịp
                if total_ql > 0 and total_ql < expected_ql - 0.01:
                    missing_ql = expected_ql - total_ql
                    pad_rest = note.Rest(quarterLength=missing_ql)
                    m.append(pad_rest)

        # 2. Xuất lại file MusicXML đã được làm sạch và chuẩn hóa
        score.write('musicxml', fp=output_xml_path)
        print(f"Auto-healed MusicXML successfully saved to: {output_xml_path}")
        return True
    except Exception as e:
        print(f"Auto-healing notice: {e}. Preserving original file.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MusicXML Auto-Healer")
    parser.add_argument("--input", "-i", required=True, help="Input MusicXML file")
    parser.add_argument("--output", "-o", default=None, help="Output MusicXML file")
    args = parser.parse_args()

    success = heal_musicxml(args.input, args.output)
    sys.exit(0 if success else 1)
