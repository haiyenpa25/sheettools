#!/usr/bin/env python3
"""Semantic document model for hymn-page headers."""
from __future__ import annotations

import re


CHORD = re.compile(r'^[A-G](?:#|b|♭|♯)?(?:m|min|maj|dim|aug|sus|add)?\d*(?:/[A-G](?:#|b|♭|♯)?)?$', re.I)
SCRIPTURE = re.compile(r'((?:[1-3I]{1,3}\s+)?[^—–,:]{2,24}\s+\d{1,3}:\d{1,3})\s*[”"\']?\s*$', re.I)


def _field(item: dict | None) -> dict:
    if item is None:
        return {"text": "", "raw_text": "", "box": [], "confidence": 0.0}
    return {
        "text": str(item.get("text", "")).strip(),
        "raw_text": str(item.get("raw_ocr", item.get("text", ""))).strip(),
        "box": list(item.get("box", [])),
        "confidence": float(item.get("score", 0.0)),
        "ocr_engine": item.get("ocr_engine"),
        "ocr_candidates": list(item.get("ocr_candidates", [])),
    }


def _uppercase_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    return sum(char.isupper() for char in letters) / len(letters) if letters else 0.0


def analyze_header_semantics(items: list[dict], page_width: int, first_staff_top: float) -> dict:
    candidates = [
        item for item in items
        if str(item.get("text", "")).strip()
        and not (CHORD.fullmatch(str(item.get("text", "")).strip()) and len(str(item.get("text", ""))) <= 7)
        and float(item.get("cy", 0)) < first_staff_top
    ]
    candidates.sort(key=lambda item: (float(item.get("cy", 0)), float(item.get("cx", 0))))
    number = next((item for item in candidates if re.fullmatch(r'#?\d{1,4}[A-Za-z]?', str(item.get("text", "")).strip())), None)

    non_number = [item for item in candidates if item is not number]
    max_height = max((float(item.get("h", 1)) for item in non_number), default=1.0)
    title = max(non_number, key=lambda item: (
        0.42 * min(float(item.get("h", 0)) / max_height, 1.0)
        + 0.33 * _uppercase_ratio(str(item.get("text", "")))
        + 0.15 * min(float(item.get("w", 0)) / max(page_width * .55, 1), 1.0)
        + 0.10 * (1.0 - min(abs(float(item.get("cx", 0)) - page_width / 2) / (page_width / 2), 1.0))
    ), default=None)

    title_y = float(title.get("cy", 0)) if title else first_staff_top
    collection = next((
        item for item in candidates
        if item is not title and item is not number
        and float(item.get("cy", 0)) < title_y
        and any(word in str(item.get("text", "")).lower() for word in ('tôn vinh', 'thánh ca', 'tuyển tập', 'hymnal', 'ca nguyện'))
    ), None)
    composer = next((
        item for item in reversed(candidates)
        if item is not title and item is not number and item is not collection
        and float(item.get("cy", 0)) > title_y
        and float(item.get("cx", 0)) > page_width * .62
    ), None)

    description_items = [
        item for item in candidates
        if item is not title and item is not number and item is not collection and item is not composer
        and (collection is None or float(item.get("cy", 0)) > float(collection.get("cy", 0)))
        and float(item.get("cy", 0)) < title_y
    ]
    description_text = ' '.join(str(item.get("text", "")).strip() for item in description_items).strip()
    scripture_reference = ""
    match = SCRIPTURE.search(description_text)
    if match:
        scripture_reference = match.group(1).strip(' —–')
        description_text = description_text[:match.start()].rstrip(' —–')

    semantic_regions = []
    roles = (("collection", collection), ("description", None), ("hymn_number", number), ("title", title), ("composer", composer))
    for role, item in roles:
        if role == "description":
            for description_item in description_items:
                semantic_regions.append({"role": role, **_field(description_item)})
        elif item is not None:
            semantic_regions.append({"role": role, **_field(item)})

    description_field = {"text": description_text, "raw_text": ' '.join(str(item.get('raw_ocr', '')) for item in description_items).strip(), "box": [], "confidence": min((float(item.get('score', 0)) for item in description_items), default=0.0)}
    return {
        "schema_version": 1,
        "collection": _field(collection),
        "hymn_number": _field(number),
        "title": _field(title),
        "description": description_field,
        "scripture_reference": {"text": scripture_reference, "raw_text": scripture_reference, "box": [], "confidence": description_field["confidence"] if scripture_reference else 0.0},
        "composer": _field(composer),
        "semantic_regions": semantic_regions,
    }
