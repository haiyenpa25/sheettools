"""Regression checks for multi-page extraction boundaries and page artifacts."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers" / "preprocessing"))
from extract_pdf import extract_pdf_pages


class FakeImage:
    def __init__(self, closed=None):
        self.closed = closed

    def save(self, path, _format):
        Path(path).write_bytes(b"rendered page")

    def close(self):
        if self.closed is not None:
            self.closed.append("image")


class FakePage:
    def __init__(self, calls, closed=None):
        self.calls = calls
        self.closed = closed

    def render(self, scale):
        self.calls.append(scale)
        return types.SimpleNamespace(
            to_pil=lambda: FakeImage(self.closed),
            close=lambda: self.closed.append("bitmap") if self.closed is not None else None,
        )

    def close(self):
        if self.closed is not None:
            self.closed.append("page")


class PdfExtractionTest(unittest.TestCase):
    def test_closes_pdf_render_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(b"pdf")
            closed = []

            class FakeDocument:
                def __len__(self):
                    return 1

                def __getitem__(self, _index):
                    return FakePage([], closed)

                def close(self):
                    closed.append("document")

            pdfium = types.SimpleNamespace(PdfDocument=lambda _: FakeDocument())
            with patch.dict(sys.modules, {"pypdfium2": pdfium}):
                self.assertTrue(extract_pdf_pages(str(source), str(Path(directory) / "pages"))["success"])
            self.assertEqual(["image", "bitmap", "page", "document"], closed)

    def test_accepts_fifty_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(b"pdf")
            calls = []
            pdfium = types.SimpleNamespace(PdfDocument=lambda _: [FakePage(calls)] * 50)
            with patch.dict(sys.modules, {"pypdfium2": pdfium}):
                result = extract_pdf_pages(str(source), str(Path(directory) / "pages"), max_pages=50)
            self.assertTrue(result["success"])
            self.assertEqual(50, result["page_count"])
            self.assertEqual("page-050.png", Path(result["pages"][-1]).name)
            self.assertEqual(50, len(calls))

    def test_rejects_oversized_pdf_before_rendering(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(b"pdf")
            calls = []
            pdfium = types.SimpleNamespace(PdfDocument=lambda _: [FakePage(calls)] * 51)
            with patch.dict(sys.modules, {"pypdfium2": pdfium}):
                result = extract_pdf_pages(str(source), str(Path(directory) / "pages"), max_pages=50)
            self.assertFalse(result["success"])
            self.assertEqual([], calls)
            self.assertEqual([], list(Path(directory).glob("pages/page-*.png")))

    def test_renders_ordered_pages_and_prunes_stale_page(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            source.write_bytes(b"pdf")
            pages = Path(directory) / "pages"
            pages.mkdir()
            (pages / "page-003.png").write_bytes(b"stale")
            calls = []
            pdfium = types.SimpleNamespace(PdfDocument=lambda _: [FakePage(calls), FakePage(calls)])
            with patch.dict(sys.modules, {"pypdfium2": pdfium}):
                result = extract_pdf_pages(str(source), str(pages), dpi=300, max_pages=50)
            self.assertTrue(result["success"])
            self.assertEqual(2, result["page_count"])
            self.assertEqual([str(pages / "page-001.png"), str(pages / "page-002.png")], result["pages"])
            self.assertEqual([300 / 72, 300 / 72], calls)
            self.assertFalse((pages / "page-003.png").exists())
            self.assertEqual([], list(pages.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
