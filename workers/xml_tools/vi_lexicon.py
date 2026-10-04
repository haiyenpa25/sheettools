"""Read the bundled Vietnamese vocabulary without guessing diacritics."""
from __future__ import annotations

import unicodedata
from functools import lru_cache
from pathlib import Path


def normalize_syllable(text: str) -> str:
    return unicodedata.normalize('NFC', text).casefold().strip(' .,;:!?"“”\'()[]{}')


@lru_cache(maxsize=1)
def vietnamese_syllables() -> frozenset[str]:
    # The source contains both syllables and phrases; each space-separated
    # word is useful for classification. Never replace the recognized text.
    content = Path(__file__).with_name('vietnamese_syllables.txt').read_text(encoding='utf-8-sig')
    return frozenset(normalize_syllable(word) for line in content.splitlines() for word in line.split()) | frozenset(
        ('ca', 'da', 'ga', 'chúa', 'thánh', 'nguyện', 'đấng', 'hỡi')
    )


def is_vietnamese_syllable(text: str) -> bool:
    return normalize_syllable(text) in vietnamese_syllables()
