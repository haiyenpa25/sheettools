"""Regression fixtures for Vietnamese lyric/chord confusion and DPI scaling."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'workers'))
from xml_tools.text_roles import is_chord, classify_text_line, cluster_text_rows
from xml_tools.vi_lexicon import is_vietnamese_syllable
from xml_tools.vietnamese_universal_ocr import VietnameseUniversalOcrEngine


class TextRolesTest(unittest.TestCase):
    def test_strict_chord_grammar(self):
        for text in ('Em', 'Am7', 'F#m', 'G/B', 'Bb', 'Cmaj7', 'D7#5', 'Bdim', 'Csus4'):
            self.assertTrue(is_chord(text), text)
        for text in ('ca', 'em', 'ba', 'da', 'ga', 'be', 'de', 'Ba', 'Da', 'F4m', 'C?', 'C999'):
            self.assertFalse(is_chord(text), text)

    def test_band_has_priority_over_chord_spelling(self):
        for text in ('ca', 'em', 'ba', 'da', 'ga', 'Em', 'Ba'):
            self.assertEqual('lyric', classify_text_line(text, 'below')['role'], text)
        for text in ('Em', 'Am7', 'F#m', 'G/B', 'Bb'):
            self.assertEqual('chord', classify_text_line(text, 'above')['role'], text)
        self.assertEqual('unknown', classify_text_line('Em yêu Chúa', 'above')['role'])

    def test_lexicon_normalizes_case_punctuation_and_unicode(self):
        for text in ('Em,', 'ba', 'CHÚA', 'Chu\u0301a'):
            self.assertTrue(is_vietnamese_syllable(text), text)
        self.assertFalse(is_vietnamese_syllable('F#m'))

    def test_row_count_does_not_depend_on_dpi(self):
        for scale in (.5, 1, 2):
            items = [{'cy': y*scale, 'h': 20*scale, 'cx': x*scale} for y in (180, 183, 210, 213) for x in (100, 250)]
            self.assertEqual(2, len(cluster_text_rows(items)))

    def test_first_system_chords_and_ambiguous_lyrics_survive(self):
        image = np.full((500, 900, 3), 255, np.uint8)
        readings = []
        for index, text in enumerate(('Em', 'Am7', 'F#m', 'G/B', 'Bb')):
            x = 100+index*100
            readings.append(([[x, 140], [x+60, 140], [x+60, 160], [x, 160]], text, .95))
        for index, text in enumerate(('ca', 'em', 'ba', 'da', 'ga', 'Em', 'Ba')):
            x = 100+index*90
            readings.append(([[x, 285], [x+60, 285], [x+60, 305], [x, 305]], text, .95))
        engine = VietnameseUniversalOcrEngine()
        with patch.object(engine, 'get_rapid_ocr', return_value=lambda _: (readings, None)), \
             patch.object(engine, 'recognize_crop_vietocr', return_value=''), \
             patch.object(engine, 'recognize_crop_tesseract', return_value=('', 0)), \
             patch('cv_omr_engine.ComputerVisionOmrEngine.detect_staves', return_value=[[200, 212, 224, 236, 248]]):
            result = engine.decompose_sheet_3zones(image)
        self.assertEqual(['Em', 'Am7', 'F#m', 'G/B', 'Bb'], [item['chord'] for item in result['harmonies']])
        self.assertEqual(['ca', 'em', 'ba', 'da', 'ga', 'Em', 'Ba'], [item['text'] for item in result['lyrics']])


if __name__ == '__main__':
    unittest.main()
