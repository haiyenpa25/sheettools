import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'workers'))
from xml_tools.chord_alignment import inject_chords


class ChordAnchoringTest(unittest.TestCase):
    def test_between_notes_uses_offset_from_measure_start(self):
        with tempfile.TemporaryDirectory() as directory:
            score = Path(directory)/'score.xml'
            score.write_text('<score-partwise><part id="P1"><measure number="1"><attributes><divisions>4</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration></note></measure></part></score-partwise>')
            anchors = [{'part_id': 'P1', 'measure': '1', 'staff_index': 0, 'x': x, 'onset': onset,
                        'measure_box': [70, 250], 'anchor_source': 'omr_pixel'} for x, onset in ((100, 0), (200, 4))]
            summary = inject_chords(str(score), [{'chord': 'G/B', 'x': 150, 'staff_index': 0, 'confidence': .95}], anchors)
            harmony = ET.parse(score).find('.//harmony')
            self.assertEqual('2', harmony.findtext('offset'))
            self.assertEqual('G', harmony.findtext('root/root-step'))
            self.assertEqual('B', harmony.findtext('bass/bass-step'))
            self.assertEqual(1, summary['accepted'])

    def test_vietnamese_words_are_not_written_as_harmony(self):
        with tempfile.TemporaryDirectory() as directory:
            score = Path(directory)/'score.xml'
            score.write_text('<score-partwise><part id="P1"><measure number="1"/></part></score-partwise>')
            summary = inject_chords(str(score), [{'chord': 'ca', 'x': 100, 'staff_index': 0, 'confidence': .99}], [])
            self.assertIsNone(ET.parse(score).find('.//harmony'))
            self.assertEqual(1, summary['review'])


if __name__ == '__main__':
    unittest.main()
