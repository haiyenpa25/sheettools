#!/usr/bin/env python3
"""Regression tests for ground-truth recognition metrics."""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from workers.evaluation.accuracy_report import compare_musicxml


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def score(pitch: str = "C", lyric: str = "Thánh") -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>1</divisions></attributes>
<note><pitch><step>{pitch}</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice>
<lyric><text>{lyric}</text></lyric></note></measure></part></score-partwise>'''


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    reference = root / "reference.musicxml"
    identical = root / "identical.musicxml"
    wrong = root / "wrong.musicxml"
    reference.write_text(score(), encoding="utf-8")
    identical.write_text(score(), encoding="utf-8")
    wrong.write_text(score("D", "Thanh"), encoding="utf-8")

    perfect = compare_musicxml(reference, identical)
    require(perfect["note_sequence_accuracy"] == 1.0, "identical notes must score 100%")
    require(perfect["lyric_character_accuracy"] == 1.0, "identical lyrics must score 100%")

    mismatch = compare_musicxml(reference, wrong)
    require(mismatch["note_sequence_accuracy"] == 0.0, "wrong single note must score 0%")
    require(mismatch["lyric_character_accuracy"] < 1.0, "missing diacritic must be measured as an OCR error")

print("  [Python] AccuracyReportTest: PASS")
