"""Locate OCR word boxes from whitespace in a line crop."""
from __future__ import annotations

import cv2
import numpy as np


def ink_word_boxes(image: np.ndarray, box: list[int], count: int) -> list[list[int]] | None:
    x1, y1, x2, y2 = (int(value) for value in box)
    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = np.any(binary > 0, axis=0)
    occupied = np.flatnonzero(ink)
    if not len(occupied):
        return None
    left, right = int(occupied[0]), int(occupied[-1])+1
    gaps = []
    beginning = None
    for x in range(left, right):
        if not ink[x] and beginning is None:
            beginning = x
        elif ink[x] and beginning is not None:
            if x-beginning >= .35*(y2-y1):
                gaps.append((beginning, x))
            beginning = None
    if len(gaps) < count-1:
        return None
    # One-dimensional partition: maximize total whitespace at count-1
    # boundaries. This additive DP has the same optimum as selecting the
    # largest gaps; no font/character-width assumptions enter the boxes.
    chosen = sorted(sorted(gaps, key=lambda gap: gap[1]-gap[0], reverse=True)[:count-1])
    starts = [left] + [gap[1] for gap in chosen]
    ends = [gap[0] for gap in chosen] + [right]
    return [[x1+start, y1, x1+end, y2] for start, end in zip(starts, ends)]
