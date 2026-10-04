import sys
import unittest
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workers'))
from omr_checks.head_counter import count_heads
from omr_checks.ink_scan import scan_ink
from omr_checks.tuplet_marks import detect_tuplets
from omr_checks.decide import decide
from omr_checks.rules import check_all
from omr_checks.ledger import build_ledger, merge_ledgers
from xml_tools.omr_anchors import OmrAnchorReader


def entry():
    return {'evidence': {'omr': {'notes': 4, 'sung_notes': 4, 'beats': 4, 'expected_beats': 4,
        'tuplets': 3, 'melisma_notes': 0, 'slurs_known': True},
        'image': {'heads': 4, 'reliable': True, 'tuplet_marks': [{'number': 3}], 'available': True},
        'lyrics': {'1': 4, '2': 4}, 'lyrics_complete': True,
        'chords': {'read': [], 'unexplained_ink': []}, 'section': {'type': 'verse'},
        'sources_agree': True}, 'id': 'm1'}


class ImageChecksTest(unittest.TestCase):
    def test_real_missing_c_is_not_hidden_by_tuplet_bracket(self):
        import json
        from xml_tools.vietnamese_universal_ocr import VietnameseUniversalOcrEngine
        base=ROOT/'tests/fixtures/omr_checks'; truth=json.loads((base/'270_missing_c.json').read_text())
        im=cv2.imread(str(base/'270_missing_c.png'))
        ink=scan_ink(im,[0,0,im.shape[1],im.shape[0]],truth['explained'],truth['interline'],VietnameseUniversalOcrEngine().reocr_chord_box)
        self.assertIn('C',[item.get('candidate_chord') for item in ink])
    def test_real_270_correct_measures_and_second_missing_tuplet(self):
        import json
        base=ROOT/'tests/fixtures/omr_checks'
        for number in (1,4,5):
            truth=json.loads((base/f'270_m{number}.json').read_text())
            im=cv2.imread(str(base/f'270_m{number}.png'),0); box=[0,0,im.shape[1],im.shape[0]]
            self.assertEqual(truth['heads'],count_heads(im,box,truth['staff_lines'],truth['interline'],truth['text_boxes'])['heads'])
            marks=detect_tuplets(im,box,truth['staff_lines'],truth['interline'],[])
            self.assertEqual(truth['tuplet'],bool(marks),f'measure {number}')
    def test_independent_real_270_missing_triplet(self):
        import json
        base=ROOT/'tests/fixtures/omr_checks'
        truth=json.loads((base/'270_m3.json').read_text())
        image=cv2.imread(str(base/'270_m3.png'),0)
        box=[0,0,image.shape[1],image.shape[0]]
        heads=count_heads(image,box,truth['staff_lines'],truth['interline'],truth['text_boxes'])
        marks=detect_tuplets(image,box,truth['staff_lines'],truth['interline'],[])
        self.assertEqual(truth['heads'],heads['heads'])
        self.assertTrue(any(m['number']==3 and m['bracket_span'] for m in marks))
    def test_black_white_chord_and_accidental(self):
        image = np.full((240, 420), 255, np.uint8)
        lines = [80, 100, 120, 140, 160]
        for y in lines: cv2.line(image, (0, y), (419, y), 0, 1)
        for x, y, filled in [(75, 120, True), (165, 130, False), (260, 100, True), (260, 140, True)]:
            cv2.ellipse(image, (x, y), (14, 9), -15, 0, 360, 0, -1 if filled else 3)
            cv2.line(image, (x+12, y), (x+12, y-55), 0, 2)
        cv2.putText(image, '#', (220, 120), cv2.FONT_HERSHEY_SIMPLEX, .8, 0, 2)
        result = count_heads(image, [30, 40, 380, 210], lines, 20)
        self.assertEqual(4, result['heads'], result)

    def test_tuplet_text_requires_staff_proximity(self):
        marks = detect_tuplets(None, [0, 50, 400, 200], [80, 100, 120, 140, 160], 20,
            [{'text': '3', 'box': [180, 45, 195, 64]}, {'text': '3', 'box': [80, 400, 95, 420]}])
        self.assertEqual(1, len(marks))
        self.assertEqual([], detect_tuplets(None, [0, 50, 400, 200], [80, 100, 120, 140, 160], 20, []))


class RuleChecksTest(unittest.TestCase):
    def test_c1_c2_c4_find_hidden_triplet_error(self):
        m = entry()
        m['evidence']['omr'].update(notes=3, sung_notes=3, tuplets=0)
        self.assertTrue({'C1', 'C2', 'C4'} <= {v['rule'] for v in check_all(m)})
        decide(m)
        self.assertEqual('review', m['decision'])

    def test_correct_measure_has_no_core_violation(self):
        self.assertFalse(check_all(entry()))
        m = entry(); decide(m)
        self.assertEqual('accept', m['decision'])

    def test_missing_independent_source_cannot_accept(self):
        m = entry(); m['evidence']['image']['available'] = False
        decide(m); self.assertEqual('review', m['decision'])

    def test_melisma_and_incomplete_ocr_do_not_claim_missing_notes(self):
        m = entry(); m['evidence']['lyrics'] = {'1': 2, '2': 2}
        m['evidence']['omr']['melisma_notes'] = 2
        self.assertNotIn('C1', {v['rule'] for v in check_all(m)})
        m['evidence']['omr']['melisma_notes'] = 0
        m['evidence']['lyrics_complete'] = False
        self.assertNotIn('C1', {v['rule'] for v in check_all(m)})

    def test_pickup_complement_is_not_bad_rhythm(self):
        m = entry(); m['evidence']['omr'].update(beats=1, pickup_complement=True)
        self.assertNotIn('C3', {v['rule'] for v in check_all(m)})

    def test_remaining_rules(self):
        cases = [('C5', lambda e: e.update(lyrics={'1': 4, '2': 3})),
                 ('C6', lambda e: e['chords'].update(unexplained_ink=[[1, 2, 3, 4]])),
                 ('C7', lambda e: e['section'].update(continuity_conflict=True)),
                 ('C8', lambda e: e['omr'].update(clef_conflict=True)),
                 ('C9', lambda e: e['omr'].update(midi_pitches=[90])),
                 ('C10', lambda e: e['chords'].update(out_of_key=['Em']))]
        for rule, mutate in cases:
            m = entry(); mutate(m['evidence'])
            self.assertIn(rule, {v['rule'] for v in check_all(m)})


class LedgerChecksTest(unittest.TestCase):
    def test_real_omr_fixtures_and_global_pickup_mapping(self):
        ledgers = []
        for number in ('002', '003'):
            base = ROOT / 'tests/fixtures/audiveris_5_11'
            anchors = OmrAnchorReader().read(str(base / f'{number}.omr'), str(base / f'{number}.musicxml'))
            ledger = build_ledger(str(base / f'{number}.musicxml'), anchors, {}, {}, None)
            self.assertTrue(ledger['measures'])
            self.assertTrue(all(m['box'] and m['part_id'] for m in ledger['measures']))
            ledgers.append(ledger)
        merged = merge_ledgers(ledgers)
        self.assertEqual(len(ledgers[0]['measures'])+len(ledgers[1]['measures']), len(merged['measures']))
        first_page_last = max(m['measure_number'] for m in merged['measures'] if m['page'] == 1)
        second_page_first = min(m['measure_number'] for m in merged['measures'] if m['page'] == 2)
        self.assertEqual(first_page_last+1, second_page_first)


if __name__ == '__main__': unittest.main()
