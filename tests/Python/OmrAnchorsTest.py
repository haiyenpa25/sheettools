"""Anchor extraction against genuine Audiveris 5.11 sample exports."""
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workers'))
from xml_tools.omr_anchors import OmrAnchorReader
from xml_tools.lyrics_aligner import _align_group


class OmrAnchorsTest(unittest.TestCase):
    def test_real_sample_exports_map_every_pitched_note(self):
        for name in ('002', '003'):
            base = ROOT / 'tests' / 'fixtures' / 'audiveris_5_11' / name
            result = OmrAnchorReader().read(str(base.with_suffix('.omr')), str(base.with_suffix('.musicxml')))
            self.assertEqual('5.11.0', result['audiveris_version'])
            xml = ET.parse(base.with_suffix('.musicxml'))
            expected = sum(note.find('pitch') is not None and note.find('grace') is None for note in xml.findall('.//note'))
            self.assertEqual(expected, len(result['anchors']), name)
            self.assertFalse(result['fallback_measures'], name)
            self.assertTrue(all(anchor['anchor_source'] == 'omr_pixel' for anchor in result['anchors']))
        self.assertAlmostEqual(549, result['anchors'][0]['x'])
        self.assertEqual([535, 643, 563, 665], result['anchors'][0]['box'])

    def test_partial_lyric_line_is_not_stretched(self):
        notes = [dict(x=x, anchor_source='omr_pixel', interline=20) for x in (100, 200, 300, 400)]
        words = [dict(text='ta', x=200, confidence=.95), dict(text='ca', x=300, confidence=.95)]
        matches = _align_group(words, notes)
        self.assertEqual([(0, 1), (1, 2)], [(word, note) for word, note, _ in matches])

    def test_pixel_distance_gate_rejects_far_word(self):
        self.assertEqual([], _align_group([dict(text='Chúa', x=900, confidence=.99)],
                                        [dict(x=100, anchor_source='omr_pixel', interline=20)]))


if __name__ == '__main__':
    unittest.main()
