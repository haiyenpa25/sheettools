"""
PDF Multi-Page Extraction Worker using pypdfium2 / PIL
Trích xuất toàn bộ các trang PDF thành ảnh PNG độ nét cao (300 DPI)
"""

import sys
import os
import json
import argparse
import re
from pathlib import Path


def list_rendered_pages(output_dir: str, max_pages: int = 50) -> list[str]:
    """Return a complete one-based page sequence; never silently skip a page."""
    root = Path(output_dir)
    numbered = []
    if root.is_dir():
        for path in root.iterdir():
            match = re.fullmatch(r"page-(\d{3})\.png", path.name)
            if match and path.is_file():
                numbered.append((int(match.group(1)), path))
    numbered.sort(key=lambda pair: pair[0])
    if not numbered or len(numbered) > max_pages:
        raise ValueError(f"Expected 1-{max_pages} rendered pages; found {len(numbered)}.")
    if [number for number, _ in numbered] != list(range(1, len(numbered) + 1)):
        raise ValueError("Rendered page sequence has a gap or duplicate index.")
    return [str(path.resolve()) for _, path in numbered]

def extract_pdf_pages(input_pdf: str, output_dir: str, dpi: int = 300, max_pages: int = 50) -> dict:
    if not os.path.exists(input_pdf):
        return {
            "success": False,
            "error": f"Input PDF not found: {input_pdf}",
            "pages": [],
            "page_count": 0
        }

    try:
        import pypdfium2 as pdfium
    except ImportError:
        return {
            "success": False,
            "error": "pypdfium2 is not installed. Run: pip install pypdfium2",
            "pages": [],
            "page_count": 0
        }

    pdf = None
    try:
        pdf = pdfium.PdfDocument(input_pdf)
        page_count = len(pdf)
        if page_count == 0 or page_count > max_pages:
            return {
                "success": False,
                "error": f"PDF has {page_count} pages; allowed range is 1-{max_pages}.",
                "pages": [],
                "page_count": page_count,
            }
        os.makedirs(output_dir, exist_ok=True)
        extracted_pages = []

        # Scale factor for 300 DPI (Standard PDF is 72 DPI)
        scale = dpi / 72.0

        for i in range(page_count):
            page = pdf[i]
            bitmap = None
            pil_image = None
            try:
                bitmap = page.render(scale=scale)
                pil_image = bitmap.to_pil()
                page_filename = f"page-{i+1:03d}.png"
                page_path = os.path.join(output_dir, page_filename)
                temporary_path = page_path + ".tmp"
                try:
                    pil_image.save(temporary_path, "PNG")
                    os.replace(temporary_path, page_path)
                finally:
                    if os.path.exists(temporary_path):
                        os.unlink(temporary_path)
                extracted_pages.append(os.path.abspath(page_path))
            finally:
                for resource in (pil_image, bitmap, page):
                    close = getattr(resource, "close", None)
                    if callable(close):
                        close()

        # A retry must not expose pages left from an earlier incomplete render.
        expected = {os.path.normcase(path) for path in extracted_pages}
        for filename in os.listdir(output_dir):
            if filename.startswith("page-") and filename.endswith(".png"):
                stale_path = os.path.join(output_dir, filename)
                if os.path.normcase(os.path.abspath(stale_path)) not in expected:
                    os.unlink(stale_path)

        return {
            "success": True,
            "page_count": page_count,
            "pages": extracted_pages
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "pages": [],
            "page_count": 0
        }
    finally:
        close = getattr(pdf, "close", None)
        if callable(close):
            close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-page PDF Extraction for Sheet Music OMR")
    parser.add_argument("--input", "-i", required=True, help="Path to input PDF file")
    parser.add_argument("--output-dir", "-o", required=True, help="Directory to save page PNGs")
    parser.add_argument("--dpi", "-d", type=int, default=300, help="Rendering DPI (default 300)")
    parser.add_argument("--max-pages", type=int, default=50, help="Reject longer PDFs before rendering")
    args = parser.parse_args()

    result = extract_pdf_pages(args.input, args.output_dir, args.dpi, args.max_pages)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["success"] else 1)
