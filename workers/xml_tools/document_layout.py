#!/usr/bin/env python3
"""Semantic document model for hymn-page headers."""
from __future__ import annotations

import re
from .text_roles import CHORD, classify_text_line


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
    prefixes = {'composer': r'^(?:Nhạc|Music|Composer)\s*:\s*',
                'lyricist': r'^(?:Lời|Lyrics|Lyricist)\s*:\s*',
                'translator': r'^(?:Dịch|Lời dịch|Lời Việt|LV|Phỏng dịch|PD|Translator)\s*:\s*',
                'note': r'^(?:Chú thích|Ghi chú|Note)\s*:\s*'}
    explicit = {}
    for role, pattern in prefixes.items():
        match_item = next((item for item in candidates if re.match(pattern, item['text'], re.I)), None)
        if match_item:
            explicit[role] = {**match_item, 'text': re.sub(pattern, '', match_item['text'], flags=re.I),
                              'source_box': match_item['box']}
    for role in ('tempo', 'key_info'):
        match_item = next((item for item in candidates if classify_text_line(item['text'], 'above')['role'] == role), None)
        if match_item:
            explicit[role] = match_item
    explicit_boxes = {tuple(item['box']) for item in explicit.values()}
    number = next((item for item in candidates if re.fullmatch(r'#?\d{1,4}[A-Za-z]?', str(item.get("text", "")).strip())), None)

    non_number = [item for item in candidates if item is not number and tuple(item['box']) not in explicit_boxes]
    max_height = max((float(item.get("h", 1)) for item in non_number), default=1.0)
    title = max(non_number, key=lambda item: (
        0.42 * min(float(item.get("h", 0)) / max_height, 1.0)
        + 0.33 * _uppercase_ratio(str(item.get("text", "")))
        + 0.15 * min(float(item.get("w", 0)) / max(page_width * .55, 1), 1.0)
        + 0.10 * (1.0 - min(abs(float(item.get("cx", 0)) - page_width / 2) / (page_width / 2), 1.0))
    ), default=None)

    title_items = [title] if title else []
    if title:
        # Only nearby lines of comparable height and case can join a title.
        # Scripture paragraphs and creator lines stay separate.
        for candidate in non_number:
            if candidate is title:
                continue
            same_height = .8 <= float(candidate['h']) / max(float(title['h']), 1) <= 1.25
            same_case = abs(_uppercase_ratio(candidate['text'])-_uppercase_ratio(title['text'])) < .2
            near = abs(float(candidate['cy'])-float(title['cy'])) <= 1.5*max(float(title['h']), float(candidate['h']))
            if same_height and same_case and near:
                title_items.append(candidate)
    title_items.sort(key=lambda item: (item['cy'], item['cx']))
    title_field = _field(title)
    if len(title_items) > 1:
        title_field.update(text=' '.join(item['text'] for item in title_items),
                           raw_text=' '.join(str(item.get('raw_ocr', item['text'])) for item in title_items),
                           box=[min(item['box'][0] for item in title_items), min(item['box'][1] for item in title_items),
                                max(item['box'][2] for item in title_items), max(item['box'][3] for item in title_items)],
                           confidence=min(float(item.get('score', 0)) for item in title_items))
    title_ids = {id(item) for item in title_items}
    leading_number = re.match(r'^(#?\d{1,4}[A-Za-z]?)\s+(\S.*)$', title_field.get('text', ''))
    if number is None and leading_number:
        # Hymnals often print the number on the title line: "270 TÔI BIẾT ...".
        x1, y1, x2, y2 = title['box']
        split_x = x1 + int((x2 - x1) * (len(leading_number.group(1)) + .5) / max(len(title_field['text']), 1))
        number = {**title, 'text': leading_number.group(1), 'box': [x1, y1, split_x, y2]}
        title_field['text'] = leading_number.group(2)
        title_field['box'] = [split_x, y1, x2, y2] if len(title_items) == 1 else title_field['box']

    title_y = float(title.get("cy", 0)) if title else first_staff_top
    collection = next((
        item for item in candidates
        if item is not title and item is not number
        and float(item.get("cy", 0)) < title_y
        and any(word in str(item.get("text", "")).lower() for word in ('tôn vinh', 'thánh ca', 'tuyển tập', 'hymnal', 'ca nguyện'))
    ), None)
    composer = explicit.get('composer') or next((
        item for item in reversed(candidates)
        if id(item) not in title_ids and item is not number and item is not collection
        and tuple(item['box']) not in explicit_boxes
        and float(item.get("cy", 0)) > title_y
        and float(item.get("cx", 0)) > page_width * .62
    ), None)

    description_items = [
        item for item in candidates
        if id(item) not in title_ids and item is not number and item is not collection and item is not composer
        and tuple(item['box']) not in explicit_boxes
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
    roles = (("collection", collection), ("description", None), ("hymn_number", number), ("composer", composer))
    for role, item in roles:
        if role == "description":
            for description_item in description_items:
                semantic_regions.append({"role": role, **_field(description_item)})
        elif item is not None:
            semantic_regions.append({"role": role, **_field(item)})
    semantic_regions.extend({'role': 'title', **_field(item)} for item in title_items)
    semantic_regions.extend({'role': role, **_field(item)} for role, item in explicit.items() if role != 'composer')

    description_field = {"text": description_text, "raw_text": ' '.join(str(item.get('raw_ocr', '')) for item in description_items).strip(), "box": [], "confidence": min((float(item.get('score', 0)) for item in description_items), default=0.0)}
    return {
        "schema_version": 2,
        "collection": _field(collection),
        "hymn_number": _field(number),
        "title": title_field,
        "description": description_field,
        "scripture_reference": {"text": scripture_reference, "raw_text": scripture_reference, "box": [], "confidence": description_field["confidence"] if scripture_reference else 0.0},
        "composer": _field(composer),
        **{role: _field(explicit.get(role)) for role in ('lyricist', 'translator', 'tempo', 'key_info', 'note')},
        "semantic_regions": semantic_regions,
    }
