#!/usr/bin/env python3
"""Validator must report both underfull and overfull measures."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers" / "xml_tools"))
from validator import validate_musicxml

XML = """<?xml version="1.0"?>
<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list>
<part id="P1">
<measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><rest/><duration>4</duration><voice>1</voice></note></measure>
<measure number="2"><note><rest/><duration>3</duration><voice>1</voice></note></measure>
<measure number="3"><note><rest/><duration>5</duration><voice>1</voice></note></measure>
</part></score-partwise>"""

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "durations.musicxml"
    path.write_text(XML, encoding="utf-8")
    result = validate_musicxml(str(path))
    warnings = "\n".join(result["warnings"])
    assert "Measure 2" in warnings and "underfull" in warnings
    assert "Measure 3" in warnings and "overfull" in warnings
    assert [issue["measure"] for issue in result["issues"]] == [2, 3]
    assert [issue["kind"] for issue in result["issues"]] == ["underfull", "overfull"]

print("  [Python] ValidatorDurationTest: PASS")
