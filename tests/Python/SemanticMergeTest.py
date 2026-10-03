#!/usr/bin/env python3
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from audiveris_runner import merge_semantic_elements

PRIMARY = '<score-partwise><part-list/><part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch></note></measure></part></score-partwise>'
AUX = '<score-partwise><part-list/><part id="P1"><measure number="1"><direction><direction-type><words>Allegro</words></direction-type></direction><harmony><root><root-step>G</root-step></root><kind>major</kind></harmony><note><pitch><step>D</step><octave>5</octave></pitch></note></measure></part></score-partwise>'

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    primary, auxiliary, output = root/'primary.xml', root/'auxiliary.xml', root/'output.xml'
    primary.write_text(PRIMARY, encoding='utf-8')
    auxiliary.write_text(AUX, encoding='utf-8')
    merge_semantic_elements(str(primary), str(auxiliary), str(output))
    score = ET.parse(output).getroot()
    assert len(list(score.iter('note'))) == 1
    assert score.find('.//note/pitch/step').text == 'C', 'auxiliary OMR must never replace primary notes'
    assert score.find('.//direction') is not None and score.find('.//harmony') is not None

print('  [Python] SemanticMergeTest: PASS')
