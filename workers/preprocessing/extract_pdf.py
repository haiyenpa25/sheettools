"""
PDF Multi-Page Extraction Worker using pypdfium2 / PIL
Trích xuất toàn bộ các trang PDF thành ảnh PNG độ nét cao (300 DPI)
"""

import sys
import os
import json
import argparse

def extract_pdf_pages(input_pdf: str, output_dir: str, dpi: int = 300) -> dict:
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

    try:
        os.makedirs(output_dir, exist_ok=True)
        pdf = pdfium.PdfDocument(input_pdf)
        page_count = len(pdf)
        extracted_pages = []

        # Scale factor for 300 DPI (Standard PDF is 72 DPI)
        scale = dpi / 72.0

        for i in range(page_count):
            page = pdf[i]
            # Render page to PIL image
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            
            page_filename = f"page-{i+1:03d}.png"
            page_path = os.path.join(output_dir, page_filename)
            pil_image.save(page_path, "PNG")
            extracted_pages.append(os.path.abspath(page_path).replace("\\", "/"))

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-page PDF Extraction for Sheet Music OMR")
    parser.add_argument("--input", "-i", required=True, help="Path to input PDF file")
    parser.add_argument("--output-dir", "-o", required=True, help="Directory to save page PNGs")
    parser.add_argument("--dpi", "-d", type=int, default=300, help="Rendering DPI (default 300)")
    args = parser.parse_args()

    result = extract_pdf_pages(args.input, args.output_dir, args.dpi)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["success"] else 1)
