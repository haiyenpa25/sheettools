"""Regression fixtures for Vietnamese diacritic fusion and octave-clef verification."""
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workers'))
from xml_tools.vi_lexicon import vietnamese_syllables
from xml_tools.vi_syllable import fuse_line, fuse_syllable, is_valid_syllable, variants
from xml_tools.clef_check import correct_octave_clefs, has_octave_digit, octave_clefs

FIXTURES = ROOT / 'tests' / 'fixtures' / 'audiveris_5_11'


def texts(base, lines):
    return [item['text'] for item in fuse_line(base.split(), [(line, 1.0) for line in lines], lexicon=vietnamese_syllables())]


class DiacriticFusionTest(unittest.TestCase):
    # Readings below are real RapidOCR/Tesseract outputs from hymn 270 page 1.
    def test_line_readings_restore_marks_on_detector_letters(self):
        self.assertEqual(
            'Tôi không biết ngày mai sẽ thế nào, tôi chỉ'.split(),
            texts('Toi khong biet ngay mai sé the nao, toi chi',
                  ['Tôi không biết ngày mai sẽ thế nào, tô chỉ', 'Tôi không biết ngày mai sẽ thế nào, lô chỉ']))

    def test_garbled_reading_letters_are_not_copied(self):
        # Tesseract read "đổi" as "đổ" and "nơi" as "nơở"; letters stay from the detector.
        self.assertEqual(
            'ngời nơi trời ấy đổi thay nào hay! Tôi không'.split(),
            texts('ngoi noi troi ay d6i thay nao hay! Toi khong',
                  ['ngời nơở trời ấy đổ . thay nào hay! Tôi không']))

    def test_variant_uses_reading_shape_when_letters_differ(self):
        self.assertEqual('hơn', texts('hon', ['hơi'])[0])

    def test_uppercase_title_keeps_case(self):
        self.assertEqual('TÔI BIẾT ĐẤNG'.split(), texts('TOI BIET DANG', ['TÔI BIẾT ĐẤNG']))

    def test_conflicting_readings_are_flagged(self):
        result = fuse_syllable('mo', [('mò', 1.0), ('mờ', 1.0)], vietnamese_syllables())
        self.assertIn(result['text'], ('mò', 'mờ'))
        self.assertTrue(result['needs_review'])

    def test_no_evidence_keeps_detector_text_and_flags_review(self):
        result = fuse_syllable('ngay', [], vietnamese_syllables())
        self.assertEqual('ngay', result['text'])
        self.assertTrue(result['needs_review'])

    def test_chords_and_punctuation_are_not_vietnamized(self):
        self.assertEqual(['Bb7', '–', 'Dm'], texts('Bb7 – Dm', ['BửT - Dm']))

    def test_orthography(self):
        for word in ('ngày', 'nghe', 'quên', 'giờ', 'gì', 'khuyên', 'được', 'tất', 'hòa'):
            self.assertTrue(is_valid_syllable(word), word)
        for word in ('ngé', 'ka', 'tât', 'tat'):
            self.assertFalse(is_valid_syllable(word), word)
        self.assertIn('ngày', variants('ngay'))


class ClefCheckTest(unittest.TestCase):
    def _run(self, image):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = str(Path(tmp) / 'page.png')
            cv2.imwrite(image_path, image)
            output = str(Path(tmp) / 'checked.musicxml')
            report = correct_octave_clefs(str(FIXTURES / '003.musicxml'), str(FIXTURES / '003.omr'),
                                          image_path, output, interline=21.0)
            return report, ET.parse(output).getroot()

    def test_genuine_omr_reports_low_grade_octave_clefs(self):
        clefs = octave_clefs(str(FIXTURES / '003.omr'))
        self.assertTrue(clefs)
        self.assertTrue(all(c['shape'] == 'G_CLEF_8VB' and c['grade'] < .35 for c in clefs))

    def test_unsupported_octave_clef_is_removed_and_pitches_raised(self):
        before = [int(o.text) for o in ET.parse(FIXTURES / '003.musicxml').getroot().iter() if o.tag.endswith('}octave') or o.tag == 'octave']
        report, root = self._run(np.full((3509, 2481), 255, np.uint8))
        self.assertTrue(report['corrected'])
        self.assertFalse([n for n in root.iter() if n.tag.endswith('clef-octave-change')])
        after = [int(o.text) for o in root.iter() if o.tag.endswith('}octave') or o.tag == 'octave']
        self.assertEqual([value + 1 for value in before], after)

    def test_printed_eight_keeps_octave_clef(self):
        image = np.full((3509, 2481), 255, np.uint8)
        clefs = octave_clefs(str(FIXTURES / '003.omr'))
        for clef in clefs:
            x, y, w, h = clef['box']
            cv2.putText(image, '8', (x + w // 4, y + h + 14), cv2.FONT_HERSHEY_SIMPLEX, .8, 0, 3)
        self.assertTrue(has_octave_digit(image, clefs[0]['box'], 21.0))
        report, root = self._run(image)
        self.assertFalse(report['corrected'])
        self.assertTrue([n for n in root.iter() if n.tag.endswith('clef-octave-change')])


if __name__ == '__main__':
    unittest.main()
