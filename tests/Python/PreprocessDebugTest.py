"""Preprocessing preserves stage images needed to diagnose layout failures."""
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from preprocessing.pipeline import preprocess_image


class PreprocessDebugTest(unittest.TestCase):
    def test_writes_stage_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            image = np.full((180, 320), 255, dtype=np.uint8)
            for y in (50, 62, 74, 86, 98):
                cv2.line(image, (20, y), (300, y), 0, 1)
            cv2.imwrite(str(source), image)
            debug = root / "debug"
            self.assertTrue(preprocess_image(str(source), str(root / "normalized.png"), debug_dir=str(debug)))
            for name in ("01_original.png", "02_gray.png", "03_deskew.png", "04_threshold.png", "05_normalized.png"):
                artifact = debug / name
                self.assertTrue(artifact.is_file(), name)
                self.assertIsNotNone(cv2.imread(str(artifact)), name)


if __name__ == "__main__":
    unittest.main()
