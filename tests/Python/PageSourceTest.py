"""Page-source and checkpoint invariants for resumable multi-page OMR."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from preprocessing.extract_pdf import list_rendered_pages
from audiveris_runner import _load_page_checkpoint


class PageSourceTest(unittest.TestCase):
    def test_numbered_pages_are_contiguous_and_ordered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in (10, 2, 1):
                (root / f"page-{index:03d}.png").write_bytes(b"png")
            with self.assertRaises(ValueError):
                list_rendered_pages(str(root), 50)
            for index in range(3, 10):
                (root / f"page-{index:03d}.png").write_bytes(b"png")
            pages = list_rendered_pages(str(root), 50)
            self.assertEqual(10, len(pages))
            self.assertEqual("page-001.png", Path(pages[0]).name)
            self.assertEqual("page-010.png", Path(pages[-1]).name)
            with self.assertRaises(ValueError):
                list_rendered_pages(str(root), 9)

    def test_checkpoint_requires_matching_page_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.xml"
            score = root / "score.xml"
            raw.write_text("raw")
            score.write_text("score")
            checkpoint = root / "page_checkpoint.json"
            checkpoint.write_text(json.dumps({
                "success": True,
                "raw_xml_path": str(raw),
                "xml_path": str(score),
                "source_sha256": hashlib.sha256(b"page one").hexdigest(),
            }))
            self.assertIsNotNone(_load_page_checkpoint(str(checkpoint), source_sha256=hashlib.sha256(b"page one").hexdigest()))
            self.assertIsNone(_load_page_checkpoint(str(checkpoint), source_sha256=hashlib.sha256(b"page two").hexdigest()))
            checkpoint.write_text(json.dumps({"success": True, "raw_xml_path": str(raw), "xml_path": str(score)}))
            self.assertIsNone(_load_page_checkpoint(str(checkpoint), source_sha256=hashlib.sha256(b"page one").hexdigest()))


if __name__ == "__main__":
    unittest.main()
