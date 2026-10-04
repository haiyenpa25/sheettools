"""Shared page geometry, true ink gaps, metadata and mask regression tests."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'workers'))
from preprocessing.page_layout import PageLayoutAnalyzer
from preprocessing.notation_layers import build_notation_layers
from xml_tools.vietnamese_universal_ocr import split_ocr_line_item, VietnameseUniversalOcrEngine
from xml_tools.document_layout import analyze_header_semantics


def item(text, box):
    x1, y1, x2, y2 = box
    return dict(text=text, box=box, cx=(x1+x2)/2, cy=(y1+y2)/2, h=y2-y1, w=x2-x1, score=.95)


class PageModelTest(unittest.TestCase):
    def test_barline_links_widely_spaced_staves(self):
        gray = np.full((600, 800), 255, np.uint8)
        staves = [[100, 110, 120, 130, 140], [250, 260, 270, 280, 290]]
        cv2.line(gray, (70, 100), (70, 290), 0, 2)
        with patch('cv_omr_engine.ComputerVisionOmrEngine.detect_staves', return_value=staves):
            model = PageLayoutAnalyzer().analyze_image(gray)
        self.assertEqual(2, model['schema_version'])
        self.assertEqual(1, len(model['systems']))
        self.assertEqual(1, len(model['systems'][0]['bands']['between']))
        self.assertEqual('barline', model['systems'][0]['grouping_source'])

    def test_separator_uses_white_valley_and_retains_lyric_space(self):
        gray = np.full((600, 800), 255, np.uint8)
        gray[160:225, 100:700] = 0
        staves = [[100, 110, 120, 130, 140], [300, 310, 320, 330, 340]]
        with patch('cv_omr_engine.ComputerVisionOmrEngine.detect_staves', return_value=staves):
            model = PageLayoutAnalyzer().analyze_image(gray)
        boundary = model['systems'][0]['bands']['below']['box'][3]
        self.assertGreater(boundary, 225)
        self.assertEqual(boundary, model['systems'][1]['bands']['above']['box'][1])

    def test_syllable_boxes_follow_ink_not_character_count(self):
        gray = np.full((40, 400), 255, np.uint8)
        gray[5:35, 5:35] = 0
        gray[5:35, 140:190] = 0
        gray[5:35, 330:390] = 0
        words = split_ocr_line_item(item('ta yêu Ngài', [0, 0, 400, 40]), gray)
        self.assertEqual([[5, 0, 35, 40], [140, 0, 190, 40], [330, 0, 390, 40]], [word['box'] for word in words])
        self.assertTrue(all(word['box_source'] == 'ink_projection' for word in words))

    def test_layers_preserve_staff_corridor_including_padding(self):
        image = np.full((300, 400, 3), 120, np.uint8)
        staves = [[100, 110, 120, 130, 140]]
        layers = build_notation_layers(image, {'metadata': [item('Title', [30, 20, 200, 50])],
                                            'lyrics': [item('Chúa', [50, 159, 100, 180])],
                                            'chords': [item('Em', [50, 60, 100, 79])]}, staves, padding=3)
        self.assertTrue(np.array_equal(layers['notation_image'][80:161], image[80:161]))
        self.assertEqual({'metadata', 'lyrics', 'chords'}, set(layers['masks']))

    def test_multiline_title_and_explicit_creators(self):
        document = analyze_header_semantics([
            item('NGỢI CA', [200, 50, 600, 100]), item('TÌNH YÊU CHÚA', [150, 110, 650, 160]),
            item('Nhạc: Nguyễn A', [550, 185, 790, 205]), item('Lời: Trần B', [50, 185, 280, 205]),
            item('Moderato', [60, 230, 200, 250]), item('Giọng: G', [600, 230, 750, 250]),
        ], 800, 300)
        self.assertEqual('NGỢI CA TÌNH YÊU CHÚA', document['title']['text'])
        self.assertEqual('Nguyễn A', document['composer']['text'])
        self.assertEqual('Trần B', document['lyricist']['text'])
        self.assertEqual('Moderato', document['tempo']['text'])
        self.assertEqual('Giọng: G', document['key_info']['text'])

    def test_decomposer_reuses_given_staves(self):
        image = np.full((400, 800, 3), 255, np.uint8)
        with patch('cv_omr_engine.ComputerVisionOmrEngine.detect_staves', return_value=[[100, 110, 120, 130, 140]]):
            model = PageLayoutAnalyzer().analyze_image(image)
        engine = VietnameseUniversalOcrEngine()
        with patch.object(engine, 'get_rapid_ocr', return_value=None), \
             patch('cv_omr_engine.ComputerVisionOmrEngine.detect_staves', side_effect=AssertionError('duplicate staff detection')):
            result = engine.decompose_sheet_3zones(image, page_model=model)
        self.assertEqual(1, result['staves_count'])
        self.assertEqual(model, result['page_model'])

    def test_four_lyric_rows_between_two_staves_survive(self):
        image = np.full((450, 800, 3), 255, np.uint8)
        cv2.line(image, (70, 100), (70, 290), (0, 0, 0), 2)
        readings = [([[150, y], [210, y], [210, y+10], [150, y+10]], text, .95)
                    for y, text in zip((160, 185, 210, 235), ('Xin', 'Chúa', 'thương', 'con'))]
        engine = VietnameseUniversalOcrEngine()
        with patch('cv_omr_engine.ComputerVisionOmrEngine.detect_staves', return_value=[[100, 110, 120, 130, 140], [250, 260, 270, 280, 290]]), \
             patch.object(engine, 'get_rapid_ocr', return_value=lambda _: (readings, None)), \
             patch.object(engine, 'recognize_crop_vietocr', return_value=''), \
             patch.object(engine, 'recognize_crop_tesseract', return_value=('', 0)):
            result = engine.decompose_sheet_3zones(image)
        self.assertEqual([1, 2, 3, 4], [word['verse_number'] for word in result['lyrics']])
        self.assertEqual([0, 0, 0, 0], [word['staff_index'] for word in result['lyrics']])


if __name__ == '__main__':
    unittest.main()
