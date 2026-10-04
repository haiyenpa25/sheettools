#!/usr/bin/env python3
"""Conservative notation/text separation for score images.

The notation corridor is authoritative: OCR boxes that touch it are never
erased. This intentionally leaves occasional text near a staff instead of
risking the loss of noteheads, accidentals, articulations, beams or rests.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def _protected_bands(
    staves: list[list[float]], image_height: int, margin_interlines: float = 2.0
) -> list[tuple[int, int]]:
    bands: list[tuple[int, int]] = []
    for staff in staves:
        if len(staff) < 5:
            continue
        ordered = sorted(float(y) for y in staff)
        interline = max(1.0, (ordered[-1] - ordered[0]) / 4.0)
        top = max(0, int(round(ordered[0] - margin_interlines * interline)))
        bottom = min(image_height, int(round(ordered[-1] + margin_interlines * interline)))
        bands.append((top, bottom))
    return bands


def _overlaps_band(box: list[int], bands: list[tuple[int, int]]) -> bool:
    _, y1, _, y2 = box
    return any(y2 >= top and y1 <= bottom for top, bottom in bands)


def build_notation_layer(
    image: np.ndarray,
    text_boxes: list[dict[str, Any]],
    staves: list[list[float]],
    padding: int = 2,
) -> dict[str, Any]:
    """Return a note-safe image plus an auditable mask decision report."""
    if image is None or image.size == 0:
        raise ValueError("image must be a non-empty numpy array")

    height, width = image.shape[:2]
    notation = image.copy()
    mask = np.zeros((height, width), dtype=np.uint8)
    bands = _protected_bands(staves, height)
    removed: list[dict[str, Any]] = []
    protected: list[dict[str, Any]] = []

    for item in text_boxes:
        raw_box = item.get("box")
        if not isinstance(raw_box, (list, tuple)) or len(raw_box) != 4:
            continue
        x1, y1, x2, y2 = (int(v) for v in raw_box)
        box = [max(0, x1), max(0, y1), min(width, x2), min(height, y2)]
        if box[0] >= box[2] or box[1] >= box[3]:
            continue
        if _overlaps_band(box, bands):
            protected.append(item)
            continue

        px1 = max(0, box[0] - padding)
        py1 = max(0, box[1] - padding)
        px2 = min(width, box[2] + padding)
        py2 = min(height, box[3] + padding)
        if _overlaps_band([px1, py1, px2, py2], bands):
            protected.append(item)
            continue
        mask[py1:py2, px1:px2] = 255
        removed.append(item)

    # White-fill is deterministic and cannot hallucinate staff geometry.
    notation[mask > 0] = 255
    return {
        "notation_image": notation,
        "text_mask": mask,
        "protected_bands": bands,
        "removed_boxes": removed,
        "protected_boxes": protected,
    }


def build_notation_layers(image: np.ndarray, groups: dict[str, list[dict]],
                          staves: list[list[float]], padding: int = 2) -> dict[str, Any]:
    """Keep independent masks, then white-fill their deterministic union."""
    masks = {}
    removed, protected = [], []
    for role, boxes in groups.items():
        layer = build_notation_layer(image, boxes, staves, padding)
        masks[role] = layer['text_mask']
        removed.extend(layer['removed_boxes'])
        protected.extend(layer['protected_boxes'])
    union = np.zeros(image.shape[:2], dtype=np.uint8)
    for mask in masks.values():
        union = cv2.bitwise_or(union, mask)
    notation = image.copy()
    notation[union > 0] = 255
    return {'notation_image': notation, 'text_mask': union, 'masks': masks,
            'removed_boxes': removed, 'protected_boxes': protected,
            'protected_bands': _protected_bands(staves, image.shape[0])}
