"""Synthetic layout fixture for staff/system regions and review signaling."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from preprocessing.page_layout import PageLayoutAnalyzer


class PageLayoutTest(unittest.TestCase):
    def test_two_systems_emit_regions_and_overlay(self):
        image = np.full((650, 900), 255, dtype=np.uint8)
        for top in (90, 175, 365, 450):
            for offset in (0, 12, 24, 36, 48):
                cv2.line(image, (90, top + offset), (810, top + offset), 0, 1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "page.png"
            cv2.imwrite(str(source), image)
            artifact = PageLayoutAnalyzer().analyze(str(source), str(root / "regions.json"), str(root / "overlay.png"))
            self.assertEqual(4, len(artifact["staff_candidates"]))
            self.assertEqual(2, len(artifact["systems"]))
            self.assertTrue(any(region["type"] == "music" for region in artifact["regions"]))
            self.assertTrue(any(region["type"] == "footer_candidate" for region in artifact["regions"]))
            self.assertTrue((root / "overlay.png").is_file())
            self.assertEqual(artifact["page_width"], json.loads((root / "regions.json").read_text())["page_width"])

    def test_blank_page_requires_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "blank.png"
            cv2.imwrite(str(source), np.full((250, 400), 255, dtype=np.uint8))
            artifact = PageLayoutAnalyzer().analyze(str(source), str(root / "regions.json"), str(root / "overlay.png"))
            self.assertEqual([], artifact["systems"])
            self.assertTrue(artifact["requires_review"])
            self.assertIn("STAFF_NOT_FOUND", artifact["warnings"])


if __name__ == "__main__":
    unittest.main()
