import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'workers'))
from xml_tools.lyric_structure import LyricStructureAnalyzer, parse_markers, project_stanzas, detect_poem_stanzas


def words(system, rows, marker=''):
    result = []
    for row in range(rows):
        for index, text in enumerate(('Xin', 'Chúa', 'thương')):
            result.append(dict(text=text, x=100+index*100, y=200+row*30, h=20, box=[95+index*100, 190+row*30, 125+index*100, 210+row*30],
                               system_id=f'system_{system:03d}', staff_index=system-1, verse_number=row+1, confidence=.95))
    return result


class LyricStructureTest(unittest.TestCase):
    def test_markers(self):
        self.assertEqual(2, parse_markers('2. Trọn đời')['verse'])
        self.assertEqual(3, parse_markers('Lời 3: Xin Chúa')['verse'])
        self.assertEqual('chorus', parse_markers('Đ.K.: Nguyện làm')['section'])
        self.assertEqual('chorus', parse_markers('Điệp khúc')['section'])
        self.assertEqual('coda', parse_markers('Coda')['section'])

    def test_three_verses_chorus_and_coda(self):
        lyrics = words(1, 3)+words(2, 3)+words(3, 1)+words(4, 1)
        lines = [dict(text='ĐK:', system_id='system_003', box=[50, 100, 90, 120]),
                 dict(text='Coda', system_id='system_004', box=[50, 100, 90, 120])]
        result = LyricStructureAnalyzer().analyze(lyrics, lines)
        self.assertEqual(['verse', 'chorus', 'coda'], [section['type'] for section in result['sections']])
        self.assertEqual(3, result['sections'][0]['verse_count'])
        self.assertTrue(all(word['lyric_name'] == 'ĐK' and word['verse_number'] == 1 for word in lyrics if word['system_id'] == 'system_003'))

    def test_explicit_verse_marker_wins_over_row_order(self):
        lyrics = words(1, 2)
        lines = [dict(text='3. Xin Chúa thương', system_id='system_001', box=[95, 220, 325, 240])]
        LyricStructureAnalyzer().analyze(lyrics, lines)
        self.assertEqual(3, lyrics[-1]['verse_number'])

    def test_poem_stanza_mismatch_stays_for_review(self):
        template = [dict(text='Xin', alignment=dict(status='accepted', measure='1', note_index=1, part_id='P1'))]
        stanza = [dict(text='Nguyện'), dict(text='Chúa')]
        project_stanzas(template, [{'verse_number': 2, 'words': stanza}])
        self.assertTrue(all(word['alignment']['status'] == 'review' for word in stanza))

    def test_poem_stanza_uses_verse_one_anchors(self):
        template = [dict(text=text, alignment=dict(status='accepted', measure='1', note_index=index+1, part_id='P1')) for index, text in enumerate(('Xin', 'Chúa'))]
        stanza = [dict(text='Nguyện'), dict(text='Ngài')]
        project_stanzas(template, [{'verse_number': 2, 'words': stanza}])
        self.assertEqual([1, 2], [word['alignment']['note_index'] for word in stanza])
        self.assertTrue(all(word['alignment']['anchor_source'] == 'verse_one_template' for word in stanza))

    def test_distant_numbered_poem_is_not_an_extra_staff_row(self):
        lyrics = words(1, 1)
        poem = dict(text='2.', x=100, y=500, box=[95, 490, 125, 510], staff_index=0, system_id='system_001', confidence=.95)
        lyrics += [poem, {**poem, 'text': 'Nguyện', 'x': 200}, {**poem, 'text': 'Ngài', 'x': 300}]
        stanzas = detect_poem_stanzas(lyrics, last_staff_bottom=150, interline=20)
        self.assertEqual(1, len(stanzas))
        self.assertEqual(2, stanzas[0]['verse_number'])
        self.assertEqual(['Nguyện', 'Ngài'], [word['text'] for word in stanzas[0]['words']])
        self.assertTrue(all(word.get('poem_stanza') for word in lyrics[-2:]))

    def test_missing_middle_verse_keeps_its_original_row_number(self):
        lyrics = words(1, 3)+words(2, 2)
        for word in lyrics:
            word['row_offset'] = (word['y']-200)/20
            if word['system_id'] == 'system_002' and word['verse_number'] == 2:
                word['row_offset'] = 3.0
        LyricStructureAnalyzer().analyze(lyrics, [])
        self.assertEqual(3, lyrics[-1]['verse_number'])

    def test_chorus_can_start_at_a_measure_inside_one_system(self):
        lyrics = words(1, 3)
        for word in lyrics:
            word['x'] = 100
        lyrics += [{**word, 'x': 500, 'y': 200, 'box': [495, 190, 525, 210]} for word in words(1, 1)]
        anchors = [dict(system_id='system_001', measure=str(number), staff_index=0, x=x, measure_box=box)
                   for number, x, box in ((1, 100, [50, 300]), (2, 500, [300, 700]))]
        lines = [dict(text='ĐK:', system_id='system_001', box=[320, 170, 370, 190])]
        result = LyricStructureAnalyzer().analyze(lyrics, lines, anchors)
        self.assertEqual(['verse', 'chorus'], [section['type'] for section in result['sections']])
        self.assertEqual([2, 2], result['sections'][1]['measure_range'])


if __name__ == '__main__':
    unittest.main()
