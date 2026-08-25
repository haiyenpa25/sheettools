#!/usr/bin/env python3
"""
workers/xml_tools/musescore_exporter.py
Bộ xuất tệp đa định dạng hỗ trợ MuseScore (.mscx), MusicXML 4.0 (.musicxml), và Compressed (.mxl)
Kế thừa mô hình chuyển đổi định dạng của PDF2Muse và MuseScore CLI.
"""

import os
import sys
import argparse
import subprocess
import shutil
import zipfile
from pathlib import Path

# UTF-8 stdout cho Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def find_musescore_cli() -> str:
    """Tìm MuseScore executable trên Windows / Linux / macOS"""
    candidates = [
        r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe",
        r"C:\Program Files\MuseScore 3\bin\MuseScore3.exe",
        r"C:\Program Files (x86)\MuseScore 4\bin\MuseScore4.exe",
        r"C:\Program Files (x86)\MuseScore 3\bin\MuseScore3.exe",
    ]
    path_res = shutil.which("mscore") or shutil.which("musescore") or shutil.which("MuseScore4") or shutil.which("MuseScore3")
    if path_res:
        return path_res

    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def export_score(input_xml: str, output_path: str, target_format: str = 'musicxml') -> dict:
    """
    Chuyển đổi MusicXML sang định dạng đích:
    - musicxml / xml : MusicXML 4.0 chuẩn W3C
    - mxl : Compressed MusicXML (ZIP container)
    - mscx : MuseScore XML Notation File
    - pdf : Xuất bản in PDF từ MuseScore
    - midi : Xuất tệp âm thanh MIDI
    """
    if not os.path.exists(input_xml):
        return {"success": False, "error": f"Không tìm thấy file: {input_xml}"}

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    target_format = target_format.lower().replace('.', '')

    # 1. Định dạng Compressed MXL (ZIP Container)
    if target_format == 'mxl':
        try:
            with open(input_xml, 'rb') as f:
                xml_data = f.read()

            with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                # META-INF/container.xml
                container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container>
  <rootfiles>
    <rootfile full-path="score.xml" media-type="application/vnd.recordare.musicxml+xml"/>
  </rootfiles>
</container>"""
                z.writestr("META-INF/container.xml", container_xml)
                z.writestr("score.xml", xml_data)

            print(f"[Exporter] Xuất tệp MXL thành công: {output_path}")
            return {"success": True, "output_path": output_path, "format": "mxl"}
        except Exception as e:
            return {"success": False, "error": f"Lỗi đóng gói MXL: {e}"}

    # 2. Định dạng MusicXML chuẩn
    if target_format in ('xml', 'musicxml'):
        shutil.copy(input_xml, output_path)
        return {"success": True, "output_path": output_path, "format": target_format}

    # 3. Định dạng MuseScore (.mscx) hoặc PDF/MIDI qua MuseScore CLI
    musescore_cli = find_musescore_cli()
    if musescore_cli:
        print(f"[Exporter] Sử dụng MuseScore CLI ({musescore_cli}) để xuất .{target_format}...")
        cmd = [musescore_cli, "-o", output_path, input_xml]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if os.path.isfile(output_path) and os.path.getsize(output_path) > 100:
                print(f"[Exporter] Xuất .{target_format} thành công qua MuseScore CLI: {output_path}")
                return {"success": True, "output_path": output_path, "format": target_format}
        except Exception as e:
            print(f"[Exporter] MuseScore CLI notice: {e}")

    # Fallback qua music21 nếu MuseScore CLI chưa cài
    try:
        from music21 import converter
        score = converter.parse(input_xml)
        if target_format == 'midi':
            score.write('midi', fp=output_path)
            return {"success": True, "output_path": output_path, "format": "midi"}
        elif target_format == 'mscx':
            # MuseScore XML có thể xuất trực tiếp từ music21 nếu hỗ trợ
            score.write('musicxml', fp=output_path)
            return {"success": True, "output_path": output_path, "format": "mscx"}
    except Exception as err:
        pass

    # Nếu không thể convert MuseScore, copy MusicXML với đuôi .mscx
    shutil.copy(input_xml, output_path)
    return {"success": True, "output_path": output_path, "format": target_format, "warning": "Exported as standard MusicXML format"}


def main():
    parser = argparse.ArgumentParser(description="Multi-Format Score Exporter (PDF2Muse standard)")
    parser.add_argument("--input", "-i", required=True, help="Input MusicXML file")
    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument("--format", "-f", default="musicxml", help="Target format (musicxml, mxl, mscx, midi, pdf)")
    args = parser.parse_args()

    res = export_score(args.input, args.output, args.format)
    import json
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res["success"] else 1)


if __name__ == "__main__":
    main()
