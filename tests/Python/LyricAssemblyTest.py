"""Pixel/slur assembly, duplicate lyrics and structured artifact integration."""
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'workers'))
from xml_tools.lyrics_aligner import align_lyrics_artifact
from xml_tools.validator import validate_musicxml


class LyricAssemblyTest(unittest.TestCase):
    def test_pixel_melisma_and_structured_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            score, lyrics, anchors = folder/'score.xml', folder/'lyrics.json', folder/'anchors.json'
            notes = ''.join(f'<note default-x="{x}"><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><notations>{slur}</notations></note>'
                            for x, slur in ((100, '<slur type="start" number="1"/>'), (130, ''), (160, '<slur type="stop" number="1"/>'), (230, '')))
            score.write_text(f'<score-partwise><part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list><part id="P1"><measure number="1">{notes}</measure></part></score-partwise>')
            words = [dict(id=f'w{index}', text=text, x=x, y=200, confidence=.99, page=1, staff_index=0, verse_number=1,
                          section_id='sec_1', section_type='verse') for index, (text, x) in enumerate((('Xin', 100), ('Chúa', 230)))]
            lyrics.write_text(json.dumps(dict(words=words, sections=[dict(id='sec_1', type='verse', verse_count=1)])))
            anchors.write_text(json.dumps(dict(anchors=[dict(id=f'P1:1:{index}', part_id='P1', measure='1', note_index=index,
                x=x, staff_index=0, page=1, anchor_source='omr_pixel', interline=20) for index, x in enumerate((100, 130, 160, 230), 1)])))
            summary = align_lyrics_artifact(str(score), str(lyrics), str(score), note_anchors_path=str(anchors))
            self.assertEqual(2, summary['accepted'])
            self.assertEqual(['start', 'continue', 'stop'], [node.get('type') for node in ET.parse(score).findall('.//lyric/extend')])
            artifact = json.loads(lyrics.read_text())
            self.assertEqual(2, artifact['schema_version'])
            self.assertEqual(2, len(artifact['sections'][0]['verses'][0]['lines'][0]['syllables']))
            for word in words:
                word['geometry_needs_review'] = True
            lyrics.write_text(json.dumps(dict(words=words)))
            summary = align_lyrics_artifact(str(score), str(lyrics), str(score), note_anchors_path=str(anchors))
            self.assertEqual(0, summary['accepted'], 'Estimated character boxes must stay in review')

    def test_validator_rejects_duplicate_lyric_number(self):
        with tempfile.TemporaryDirectory() as directory:
            score = Path(directory)/'score.xml'
            score.write_text('<score-partwise><part-list/><part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><lyric number="1"><text>Xin</text></lyric><lyric number="1"><text>Chúa</text></lyric></note></measure></part></score-partwise>')
            result = validate_musicxml(str(score))
            self.assertIn('duplicate_lyric_number', {issue['kind'] for issue in result['issues']})
            self.assertFalse(result['isValid'])


if __name__ == '__main__':
    unittest.main()
