#!/usr/bin/env python3
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from preprocessing.pipeline import analyze_image_quality

binary = np.full((400, 600), 255, dtype=np.uint8)
binary[100:105, :] = 0
report = analyze_image_quality(binary)
assert report["profile"] == "already_binary", report
assert report["recommended"]["shadow_removal"] is False

gradient = np.tile(np.linspace(35, 245, 600, dtype=np.uint8), (400, 1))
report = analyze_image_quality(gradient)
assert report["profile"] == "uneven_lighting", report
assert report["recommended"]["shadow_removal"] is True

print("  [Python] ImageQualityTest: PASS")
