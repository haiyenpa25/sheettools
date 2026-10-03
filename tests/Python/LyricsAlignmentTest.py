#!/usr/bin/env python3
"""Regression test for monotonic spatial lyric-to-note alignment."""
import json
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from xml_tools.lyrics_aligner import align_lyrics_artifact


SCORE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list>
  <part id="P1"><measure number="1" width="100">
    <note default-x="10"><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>
    <note default-x="50"><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration></note>
    <note default-x="90"><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration></note>
  </measure></part>
</score-partwise>"""

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    score = root / "notes.musicxml"
    artifact = root / "lyrics.json"
    output = root / "full.musicxml"
    score.write_text(SCORE, encoding="utf-8")
    artifact.write_text(json.dumps({
        "schema_version": 1,
        "artifact_type": "lyrics_ocr",
        "words": [
            {"id": "w1", "page": 1, "staff_index": 0, "verse_number": 1, "text": "Xin", "x": 10, "y": 20, "confidence": .95},
            {"id": "w2", "page": 1, "staff_index": 0, "verse_number": 1, "text": "Chúa", "x": 90, "y": 20, "confidence": .93},
            {"id": "w3", "page": 1, "staff_index": 0, "verse_number": 3, "text": "Amen", "x": 10, "y": 40, "confidence": .92},
            {"id": "w4", "page": 1, "staff_index": 0, "verse_number": 4, "text": "mờ", "x": 50, "y": 60, "confidence": .20},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    summary = align_lyrics_artifact(str(score), str(artifact), str(output), str(artifact))
    assert summary["accepted"] == 3, summary
    assert summary["review"] == 1, summary

    tree = ET.parse(output)
    notes = list(tree.getroot().iter("note"))
    note_lyrics = [[(lyric.get("number"), lyric.findtext("text")) for lyric in note.findall("lyric")] for note in notes]
    assert ("1", "Xin") in note_lyrics[0]
    assert not any(number == "1" for number, _ in note_lyrics[1]), "middle melisma note must be skipped"
    assert ("1", "Chúa") in note_lyrics[2]
    assert ("3", "Amen") in note_lyrics[0], "verse 3 must align independently"
    assert not any(text == "mờ" for items in note_lyrics for _, text in items), "low-confidence OCR must not be auto-injected"

    aligned = json.loads(artifact.read_text(encoding="utf-8"))
    assert aligned["alignment_status"] == "needs_review"
    assert aligned["words"][0]["alignment"]["measure"] == "1"
    assert aligned["words"][1]["alignment"]["note_index"] == 3
    assert aligned["words"][3]["alignment"]["status"] == "review"

print("  [Python] LyricsAlignmentTest: PASS")
