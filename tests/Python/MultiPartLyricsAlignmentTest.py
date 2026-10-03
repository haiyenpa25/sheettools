#!/usr/bin/env python3
import json
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from xml_tools.lyrics_aligner import align_lyrics_artifact

SCORE = """<score-partwise version="4.0"><part-list>
<score-part id="P1"><part-name>Upper</part-name></score-part>
<score-part id="P2"><part-name>Lower voice</part-name></score-part></part-list>
<part id="P1"><measure number="1" width="100"><note default-x="20"><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice></note></measure></part>
<part id="P2"><measure number="1" width="100"><note default-x="20"><pitch><step>C</step><octave>3</octave></pitch><duration>1</duration><voice>1</voice></note></measure></part>
</score-partwise>"""

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    score, artifact, output = root / "score.xml", root / "lyrics.json", root / "out.xml"
    score.write_text(SCORE, encoding="utf-8")
    artifact.write_text(json.dumps({"words": [{"id":"w1","page":1,"staff_index":1,"verse_number":1,"text":"Trầm","x":20,"confidence":.99}]}, ensure_ascii=False), encoding="utf-8")
    align_lyrics_artifact(str(score), str(artifact), str(output), str(artifact))
    tree = ET.parse(output)
    parts = list(tree.getroot().iter("part"))
    assert not list(parts[0].iter("lyric")), "lyrics must not be forced into P1"
    assert [node.findtext("text") for node in parts[1].iter("lyric")] == ["Trầm"]

print("  [Python] MultiPartLyricsAlignmentTest: PASS")
