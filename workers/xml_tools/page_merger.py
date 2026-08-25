#!/usr/bin/env python3
"""
workers/xml_tools/page_merger.py
Ghép nối các tệp MusicXML từ nhiều trang thành một tệp MusicXML hoàn chỉnh duy nhất (Multi-Page MusicXML Merger).
Lấy cảm hứng từ cơ chế ghép trang của PDF2Muse kết hợp thư viện music21 chuẩn công nghiệp.
"""

import os
import sys
import argparse
import glob
from pathlib import Path

# UTF-8 stdout cho Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def merge_musicxml_pages(xml_files: list, output_file: str, title: str = None) -> bool:
    """
    Ghép danh sách các tệp MusicXML từng trang theo thứ tự thành 1 tệp duy nhất.
    """
    if not xml_files:
        print("Error: Danh sách tệp MusicXML trống.")
        return False

    # Nếu chỉ có 1 trang, copy trực tiếp
    if len(xml_files) == 1:
        import shutil
        shutil.copy(xml_files[0], output_file)
        print(f"Single page copied to: {output_file}")
        return True

    try:
        from music21 import converter, stream, metadata
        print(f"[PageMerger] Đang ghép {len(xml_files)} trang MusicXML...")

        combined_score = stream.Score()
        if title:
            combined_score.metadata = metadata.Metadata(title=title)

        combined_part = stream.Part()
        combined_part.id = 'P1'

        current_measure_num = 1

        for page_idx, xml_path in enumerate(xml_files):
            print(f"  - Nạp trang {page_idx + 1}: {xml_path}")
            page_score = converter.parse(xml_path)

            if not page_score.parts:
                continue

            first_part = page_score.parts[0]
            measures = list(first_part.getElementsByClass('Measure'))

            for m in measures:
                # Đánh lại số thứ tự ô nhịp liên tục
                m.number = current_measure_num
                # Thêm dấu ngắt trang vào đầu trang mới (trừ trang đầu tiên)
                if page_idx > 0 and m.number == current_measure_num and m == measures[0]:
                    from music21 import layout
                    m.insert(0, layout.PageLayout(isNew=True))

                combined_part.append(m)
                current_measure_num += 1

        combined_score.append(combined_part)

        # Xuất tệp MusicXML đã gộp
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        combined_score.write('musicxml', fp=output_file)
        print(f"[PageMerger] Ghép thành công {current_measure_num - 1} ô nhịp vào: {output_file}")
        return True

    except Exception as e:
        print(f"[PageMerger] Lỗi ghép MusicXML bằng music21 ({e}), sử dụng cơ chế gộp dự phòng...")
        return fallback_xml_merge(xml_files, output_file)


def fallback_xml_merge(xml_files: list, output_file: str) -> bool:
    """Cơ chế gộp XML thuần dự phòng"""
    try:
        import xml.etree.ElementTree as ET
        first_tree = ET.parse(xml_files[0])
        first_root = first_tree.getroot()
        first_part = first_root.find('.//part')

        if first_part is None:
            return False

        current_m_num = len(first_part.findall('measure')) + 1

        for xml_path in xml_files[1:]:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            part = root.find('.//part')
            if part is not None:
                for m in part.findall('measure'):
                    m.set('number', str(current_m_num))
                    first_part.append(m)
                    current_m_num += 1

        first_tree.write(output_file, encoding='utf-8', xml_declaration=True)
        print(f"[PageMerger-Fallback] Đã gộp thành công vào {output_file}")
        return True
    except Exception as err:
        print(f"[PageMerger-Fallback] Lỗi: {err}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Multi-Page MusicXML Merger")
    parser.add_argument("--inputs", "-i", nargs="+", required=True, help="List of page MusicXML files")
    parser.add_argument("--output", "-o", required=True, help="Combined output MusicXML file")
    parser.add_argument("--title", "-t", default="Bản Nhạc Hoàn Chỉnh", help="Score title")
    args = parser.parse_args()

    success = merge_musicxml_pages(args.inputs, args.output, args.title)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
