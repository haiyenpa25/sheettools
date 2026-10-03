#!/usr/bin/env python3
"""Regression test: notation-only keeps notes and removes all lyrics."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from audiveris_runner import write_notation_only, write_without_chords


SOURCE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0"><defaults><lyric-font font-family="Sans Serif"/></defaults>
  <part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>
  <part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch>
  <duration>1</duration><lyric number="1"><text>Sai</text></lyric>
  <notations><ornaments><trill-mark/></ornaments><articulations><staccato/></articulations><tied type="start"/></notations>
  </note><direction><direction-type><dynamics><pp/></dynamics><pedal type="start"/></direction-type></direction>
  <harmony><root><root-step>C</root-step></root></harmony></measure></part>
</score-partwise>"""


with tempfile.TemporaryDirectory() as directory:
    source = Path(directory) / "source.musicxml"
    output = Path(directory) / "notation.musicxml"
    source.write_text(SOURCE, encoding="utf-8")
    write_notation_only(str(source), str(output), "23")
    result = output.read_text(encoding="utf-8")
    assert "<note>" in result, "notation-only must preserve notes"
    assert "<pitch>" in result, "notation-only must preserve pitch"
    assert "lyric" not in result, "notation-only must remove every lyric node"
    assert "direction" not in result and "dynamics" not in result and "pedal" not in result
    assert "ornaments" not in result and "articulations" not in result
    assert "harmony" not in result, "strict note-only mode must remove chord symbols"
    assert "tied" in result, "structural tie notation must be preserved"
    assert "<work-title>23</work-title>" in result, "missing title must use source filename"

    chords_output = Path(directory) / "without_chords.musicxml"
    write_without_chords(str(source), str(chords_output))
    chords_result = chords_output.read_text(encoding="utf-8")
    assert "harmony" not in chords_result, "chord-disabled mode must remove harmony nodes"
    assert "<lyric" in chords_result, "chord-disabled mode must preserve lyrics"
    assert "<note>" in chords_result, "chord-disabled mode must preserve notes"
    assert "direction" in chords_result, "chord-disabled mode must not remove unrelated notation"

print("  [Python] NotationOnlyModeTest: PASS")
