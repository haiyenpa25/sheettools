#!/usr/bin/env python3
"""
workers/audiveris_runner.py
Điều phối pipeline: PDF → PNG (pypdfium2) → Audiveris OMR → MusicXML thực
Usage: python audiveris_runner.py --input <file.pdf|file.png> --output <out_dir> [--audiveris <path_to_audiveris_cli>]
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# ───────── pypdfium2 trích ảnh PNG từ PDF ─────────
def pdf_to_png_pages(pdf_path: str, output_dir: str, dpi: int = 300) -> list:
    """Chuyển mỗi trang PDF thành file PNG 300 DPI."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        raise ImportError("Cần cài: pip install pypdfium2")
    pages_out = []
    doc = pdfium.PdfDocument(pdf_path)
    for i, page in enumerate(doc):
        bitmap = page.render(scale=dpi / 72)
        img = bitmap.to_pil()
        out_path = Path(output_dir) / f"page_{i:04d}.png"
        img.save(str(out_path), 'PNG')
        pages_out.append(str(out_path))
    return pages_out


# ───────── Tiền xử lý ảnh tăng độ tương phản (OpenCV) ─────────
def preprocess_image(png_path: str, out_path: str) -> str:
    """Tăng tương phản và nhị phân hóa ảnh bản nhạc để Audiveris nhận diện tốt hơn."""
    try:
        import cv2
        img = cv2.imread(png_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return png_path  # Trả về ảnh gốc nếu không đọc được
        # Adaptive thresholding để tách nốt nhạc rõ khỏi nền
        binary = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15, C=10
        )
        cv2.imwrite(out_path, binary)
        return out_path
    except ImportError:
        # OpenCV chưa cài, dùng ảnh gốc
        return png_path


# ───────── Tìm Audiveris CLI ─────────
def find_audiveris_cli(hint=None):
    """Tìm Audiveris CLI từ các vị trí thông thường trên Windows."""
    candidates = []
    if hint:
        candidates.append(hint)

    # Các vị trí cài mặc định trên Windows
    candidates += [
        r"D:\tools\audiveris\bin\Audiveris.bat",
        r"C:\Program Files\Audiveris\bin\Audiveris.bat",
        r"D:\audiveris\bin\Audiveris.bat",
        r"C:\tools\audiveris\bin\Audiveris.bat",
    ]
    # Tìm trong PATH
    import shutil
    path_result = shutil.which("Audiveris") or shutil.which("audiveris")
    if path_result:
        candidates.insert(0, path_result)

    for c in candidates:
        if os.path.isfile(c):
            return c

    # Tìm đệ quy trong D:\tools\ và C:\Program Files\
    for search_root in [r"D:\tools", r"C:\Program Files"]:
        if os.path.isdir(search_root):
            matches = glob.glob(
                os.path.join(search_root, "**", "Audiveris.bat"),
                recursive=True
            )
            if matches:
                return matches[0]
    return None


# ───────── Gọi Audiveris CLI ─────────
def run_audiveris(input_path: str, output_dir: str, audiveris_cli: str) -> dict:
    """Gọi Audiveris CLI và trả về dict chứa đường dẫn MusicXML + log."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        audiveris_cli,
        "-batch",
        "-export",
        "-output", output_dir,
        input_path
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=180,
            encoding='utf-8', errors='replace'
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Audiveris timeout (>180s)", "xml_path": None}
    except FileNotFoundError:
        return {"success": False, "error": f"Audiveris CLI không tìm thấy: {audiveris_cli}", "xml_path": None}

    log = f"CMD: {' '.join(cmd)}\nEXIT: {exit_code}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"

    # Tìm file MusicXML output (có thể là .xml hoặc .mxl)
    xml_files = sorted(glob.glob(os.path.join(output_dir, "**", "*.xml"), recursive=True))
    mxl_files = sorted(glob.glob(os.path.join(output_dir, "**", "*.mxl"), recursive=True))

    xml_path = None

    # Ưu tiên .xml thuần, nếu không có mới dùng .mxl
    if xml_files:
        xml_path = xml_files[0]
    elif mxl_files:
        # Giải nén .mxl (thực ra là zip chứa MusicXML)
        mxl_path = mxl_files[0]
        try:
            with zipfile.ZipFile(mxl_path, 'r') as z:
                for name in z.namelist():
                    if name.endswith('.xml') and 'META-INF' not in name:
                        extract_path = Path(output_dir) / Path(name).name
                        z.extract(name, output_dir)
                        xml_path = os.path.join(output_dir, name)
                        break
        except Exception as e:
            log += f"\nLỗi giải nén MXL: {e}"

    if xml_path and os.path.isfile(xml_path):
        return {
            "success": True,
            "xml_path": xml_path,
            "exit_code": exit_code,
            "log": log
        }
    else:
        return {
            "success": False,
            "error": "Không tìm thấy file MusicXML trong output. Xem log để debug.",
            "exit_code": exit_code,
            "log": log,
            "xml_path": None
        }


# ───────── Pipeline chính ─────────
def process(input_path: str, output_dir: str, audiveris_hint=None) -> dict:
    """
    Luồng chính:
    PDF/PNG → (PDF to PNG nếu cần) → Tiền xử lý → Audiveris → MusicXML
    """
    input_path = os.path.abspath(input_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    audiveris_cli = find_audiveris_cli(audiveris_hint)
    if not audiveris_cli:
        return {
            "success": False,
            "error": "Không tìm thấy Audiveris CLI. Hãy cài Audiveris 5.11.0 tại: https://github.com/Audiveris/audiveris/releases",
            "xml_path": None
        }

    ext = Path(input_path).suffix.lower()

    # Bước 1: Chuyển PDF sang PNG nếu cần
    if ext == '.pdf':
        png_dir = os.path.join(output_dir, "pages")
        os.makedirs(png_dir, exist_ok=True)
        try:
            pages = pdf_to_png_pages(input_path, png_dir, dpi=300)
        except Exception as e:
            return {"success": False, "error": f"Lỗi trích PNG từ PDF: {e}", "xml_path": None}

        if not pages:
            return {"success": False, "error": "PDF không có trang nào.", "xml_path": None}

        # Chỉ lấy trang đầu tiên (đa số bài thánh ca 1 trang)
        source_png = pages[0]
    elif ext in ('.png', '.jpg', '.jpeg', '.tif', '.tiff'):
        source_png = input_path
    else:
        return {"success": False, "error": f"Định dạng không hỗ trợ: {ext}", "xml_path": None}

    # Bước 2: Tiền xử lý ảnh (OpenCV)
    preprocessed_png = os.path.join(output_dir, "preprocessed.png")
    final_png = preprocess_image(source_png, preprocessed_png)

    # Bước 3: Chạy Audiveris OMR
    omr_out_dir = os.path.join(output_dir, "omr_out")
    result = run_audiveris(final_png, omr_out_dir, audiveris_cli)

    # Ghi log ra file
    log_path = os.path.join(output_dir, "audiveris.log")
    if "log" in result:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(result["log"])
    result["log_path"] = log_path

    return result


# ───────── CLI Entry Point ─────────
def main():
    parser = argparse.ArgumentParser(description="Audiveris OMR Runner — SheetTools")
    parser.add_argument("--input", required=True, help="Đường dẫn file PDF hoặc PNG")
    parser.add_argument("--output", required=True, help="Thư mục output")
    parser.add_argument("--audiveris", default=None, help="Đường dẫn Audiveris CLI (tùy chọn)")
    args = parser.parse_args()

    result = process(args.input, args.output, args.audiveris)
    # Xuất kết quả JSON để PHP backend đọc
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
