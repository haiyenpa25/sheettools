#!/usr/bin/env python3
"""Regression: detect every staff despite extra horizontal peaks and split OCR lines."""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from cv_omr_engine import ComputerVisionOmrEngine
from xml_tools.vietnamese_universal_ocr import split_ocr_line_item


image = np.full((520, 900), 255, dtype=np.uint8)
for top in (80, 230, 380):
    for offset in (0, 12, 24, 36, 48):
        cv2.line(image, (100, top + offset), (820, top + offset), 0, 1)
    # Beams/text rules create extra peaks that must not invalidate a five-line staff.
    cv2.line(image, (250, top + 18), (650, top + 18), 0, 2)
    cv2.line(image, (300, top + 30), (700, top + 30), 0, 2)

staves = ComputerVisionOmrEngine().detect_staves(image)
assert len(staves) == 3, f"expected 3 staves, got {staves}"

tokens = split_ocr_line_item({
    "text": "Cùng nhau ta vui",
    "raw_ocr": "Cùng nhau ta vui",
    "box": [100, 200, 500, 240],
    "cx": 300,
    "cy": 220,
    "h": 40,
    "w": 400,
    "score": .94,
    "ocr_engine": "rapidocr",
})
assert [token["text"] for token in tokens] == ["Cùng", "nhau", "ta", "vui"]
assert all(tokens[index]["cx"] < tokens[index + 1]["cx"] for index in range(3))
assert tokens[0]["box"][0] == 100 and tokens[-1]["box"][2] == 500

print("  [Python] StaffAndLyricSegmentationTest: PASS")
