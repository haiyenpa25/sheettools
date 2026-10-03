#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers" / "xml_tools"))
from validator import validate_musicxml

BROKEN = """<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>X</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>1</divisions></attributes><harmony><root><root-step>H</root-step></root><kind>not-a-kind</kind></harmony><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><lyric number="1"><syllabic>middle</syllabic><text>sai</text></lyric></note></measure></part></score-partwise>"""

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "broken.xml"
    path.write_text(BROKEN, encoding="utf-8")
    result = validate_musicxml(str(path))
    kinds = {issue["kind"] for issue in result["issues"]}
    assert "invalid_harmony_root" in kinds
    assert "invalid_harmony_kind" in kinds
    assert "broken_syllabic_chain" in kinds
    assert result["capabilities"]["osmd_render"] == "not_run"

print("  [Python] ValidatorStructureTest: PASS")
