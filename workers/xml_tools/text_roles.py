"""Deterministic, position-first text classification and scale-aware rows."""
from __future__ import annotations

import re
from statistics import median

from .vi_lexicon import is_vietnamese_syllable

CHORD = re.compile(
    r'^[A-G][#b♯♭]?(?:min|maj|dim|aug|sus[24]?|m|M|°|\+)?'
    r'(?:6|7|9|11|13)?(?:add(?:2|4|6|9|11|13)|maj7|[#b](?:5|9|11|13))*'
    r'(?:/[A-G][#b♯♭]?)?$'
)


def is_chord(text: str) -> bool:
    return bool(CHORD.fullmatch(text.strip()))


def classify_text_line(text: str, band: str) -> dict:
    tokens = text.split()
    chord_ratio = sum(is_chord(token) for token in tokens) / max(len(tokens), 1)
    vi_ratio = sum(is_vietnamese_syllable(token) for token in tokens) / max(len(tokens), 1)
    role = 'unknown'
    if band in ('below', 'between'):
        role = 'lyric'
        if re.fullmatch(r'(?:Đ\.?K\.?|Điệp khúc|Coda|Kết|Fine)\s*:?', text, re.I):
            role = 'section_marker'
        elif re.fullmatch(r'(?:\d+[.)]|Lời\s+\d+)\s*', text, re.I):
            role = 'verse_marker'
    elif band == 'above':
        # Ambiguous single symbols such as Em remain chords above a staff;
        # a Vietnamese phrase containing Em does not become a chord line.
        ordinary_words = sum(is_vietnamese_syllable(token) and not is_chord(token) for token in tokens)
        if chord_ratio >= .7 and ordinary_words / max(len(tokens), 1) < .3:
            role = 'chord'
        elif re.match(r'^(?:Allegro|Andante|Moderato|Adagio|Tempo|Chậm|Nhanh|Vừa phải)\b', text, re.I):
            role = 'tempo'
        elif re.match(r'^(?:Giọng|Key)\b', text, re.I):
            role = 'key_info'
        elif re.fullmatch(r'(?:D\.[CS]\.?.*|Fine|Coda)', text, re.I):
            role = 'direction'
    return {'role': role, 'role_scores': {'chord_ratio': chord_ratio, 'vietnamese_ratio': vi_ratio},
            'needs_review': role == 'unknown'}


def cluster_text_rows(items: list[dict]) -> list[list[dict]]:
    if not items:
        return []
    threshold = .6 * median(max(float(item.get('h', 1)), 1) for item in items)
    rows: list[list[dict]] = []
    for item in sorted(items, key=lambda row: (row['cy'], row.get('cx', 0))):
        nearest = min(rows, key=lambda row: abs(item['cy'] - median(word['cy'] for word in row)), default=None)
        if nearest is not None and abs(item['cy'] - median(word['cy'] for word in nearest)) <= threshold:
            nearest.append(item)
        else:
            rows.append([item])
    return [sorted(row, key=lambda word: word.get('cx', 0)) for row in rows]
