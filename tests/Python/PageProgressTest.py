"""Progress artifact reports real per-page completion and failures."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from page_progress import PageProgress


class PageProgressTest(unittest.TestCase):
    def test_tracks_completed_and_failed_pages_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            progress = PageProgress(str(path), 3)
            progress.start_page(1)
            self.assertEqual({"current_page": 1, "processed_pages": 0},
                             {key: json.loads(path.read_text())[key] for key in ("current_page", "processed_pages")})
            progress.complete_page(1)
            progress.fail_page(2, "OMR failed")
            result = json.loads(path.read_text())
            self.assertEqual(3, result["total_pages"])
            self.assertEqual(1, result["processed_pages"])
            self.assertEqual([1], result["completed_pages"])
            self.assertEqual([{"page": 2, "error": "OMR failed"}], result["failed_pages"])
            self.assertEqual("partial", result["status"])
            self.assertEqual([], list(Path(directory).glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
