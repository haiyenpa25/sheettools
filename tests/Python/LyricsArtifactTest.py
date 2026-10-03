#!/usr/bin/env python3
"""Regression test: OCR lyrics remain an independent, mergeable artifact."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from audiveris_runner import merge_lyrics_artifacts, write_lyrics_artifact
from xml_tools.vietnamese_universal_ocr import inject_3zone_metadata_and_lyrics


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    first = root / "page1.json"
    second = root / "page2.json"
    merged = root / "lyrics.json"
    write_lyrics_artifact({
        "lyrics": [
            {"text": "Xin", "verse_number": 1, "staff_index": 0, "x": 10, "y": 20, "box": [1, 2, 3, 4], "confidence": .91},
            {"text": "Chúa", "verse_number": 3, "staff_index": 0, "x": 30, "y": 20, "box": [5, 2, 8, 4], "confidence": .82},
        ]
    }, str(first), page_number=1)
    write_lyrics_artifact({
        "lyrics": [
            {"text": "thương", "verse_number": 1, "staff_index": 2, "x": 12, "y": 40, "box": [1, 3, 4, 6], "confidence": .75},
        ]
    }, str(second), page_number=2)
    merge_lyrics_artifacts([str(first), str(second)], str(merged))

    data = json.loads(merged.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["page_count"] == 2
    assert data["word_count"] == 3
    assert data["verses"]["1"][0]["text"] == "Xin"
    assert data["verses"]["3"][0]["text"] == "Chúa", "all verse numbers must survive"
    assert data["words"][2]["page"] == 2
    assert data["words"][2]["staff_index"] == 2
    assert data["words"][0]["confidence"] == .91

    score = root / "score.musicxml"
    score.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>
<part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note></measure></part>
</score-partwise>""", encoding="utf-8")
    assert inject_3zone_metadata_and_lyrics(str(score), {
        "lyrics": [{"text": "Ba", "verse_number": 3}], "header": {}
    })
    assert 'number="3"' in score.read_text(encoding="utf-8"), "recombination must support arbitrary verses"

print("  [Python] LyricsArtifactTest: PASS")
