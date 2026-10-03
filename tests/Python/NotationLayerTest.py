#!/usr/bin/env python3
"""Regression tests for notation-first image separation."""

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from workers.preprocessing.notation_layers import build_notation_layer
from workers.preprocessing.pipeline import _deskew
from workers.xml_tools.vietnamese_universal_ocr import select_ocr_candidate, select_vietnamese_candidate


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


image = np.full((240, 400, 3), 255, dtype=np.uint8)
staves = [[80.0, 90.0, 100.0, 110.0, 120.0]]

for y in [80, 90, 100, 110, 120]:
    cv2.line(image, (20, y), (380, y), (0, 0, 0), 1)

# A notehead inside the protected notation corridor.
cv2.ellipse(image, (180, 100), (7, 5), -20, 0, 360, (0, 0, 0), -1)

# Simulated OCR boxes: one false-positive over the note, one real lyric below.
cv2.putText(image, "Thanh Vuong", (140, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
boxes = [
    {"box": [170, 94, 192, 108], "text": "o", "score": 0.91},
    {"box": [140, 155, 230, 178], "text": "Thánh Vương", "score": 0.94},
]

result = build_notation_layer(image, boxes, staves)
notation = result["notation_image"]

require(int(notation[100, 180].mean()) < 50, "notehead pixels must never be erased")
require(int(notation[165, 180].mean()) > 245, "lyric pixels must be removed from notation layer")
require(len(result["removed_boxes"]) == 1, "only the lyric box should be removed")
require(len(result["protected_boxes"]) == 1, "overlapping OCR box must be protected")

# OpenCV may return HoughLinesP as (N, 1, 4) or (N, 4). Both must work.
skew_input = np.full((240, 400), 255, dtype=np.uint8)
for y in [80, 90, 100, 110, 120]:
    cv2.line(skew_input, (20, y), (380, y + 4), 0, 1)
deskewed = _deskew(skew_input)
require(deskewed.shape == skew_input.shape, "deskew must preserve image dimensions")

text, confidence, engine = select_ocr_candidate("Thanh", 0.52, "Thánh", 0.91)
require((text, engine) == ("Thánh", "tesseract"), "higher-confidence Vietnamese OCR must win")
require(confidence == 0.91, "selected OCR confidence must be preserved")
text, _, engine = select_ocr_candidate("Ngài", 0.88, "", 0.0)
require((text, engine) == ("Ngài", "rapidocr"), "blank candidates must never replace valid OCR")

text, confidence, engine = select_vietnamese_candidate([
    {"text": "Chua", "confidence": .98, "engine": "rapidocr"},
    {"text": "Chúa", "confidence": .86, "engine": "tesseract"},
])
require((text, engine) == ("Chúa", "tesseract"), "equivalent Vietnamese reading must preserve supported diacritics")
require(confidence == .86, "stored confidence must remain the engine confidence, not an inflated score")
text, _, engine = select_vietnamese_candidate([
    {"text": "Ton Vinh Chua Hang Htu", "confidence": .99, "engine": "rapidocr"},
    {"text": "Tôn Vinh Chúa Hằng Hữu", "confidence": .86, "engine": "tesseract"},
])
require(text == "Tôn Vinh Chúa Hằng Hữu" and engine.startswith("consensus:"), "minor OCR drift must not discard a strong Vietnamese reading")
text, _, engine = select_vietnamese_candidate([
    {"text": "NGOI CA TiNH YEU THIEN CHUA", "confidence": .95, "engine": "rapidocr"},
    {"text": "NGƠI ễA TÌNH YÊU THIÊN CHÚA", "confidence": .94, "engine": "tesseract"},
])
require(text == "NGƠI CA TÌNH YÊU THIÊN CHÚA", f"token consensus must reject hallucinated word: {text}")
require(engine.startswith("consensus:"), "fused OCR must expose its provenance")

print("  [Python] NotationLayerTest: PASS")
