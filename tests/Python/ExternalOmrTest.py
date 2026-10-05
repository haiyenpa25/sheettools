"""Contracts for isolated neural OMR comparison workers."""
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'workers'))
from external_omr.worker import ComparisonWorker, summarize_xml, homr_positions
from external_omr.layout import classify_rows, propose_alignment, staff_band_from_crop
from external_omr.postprocess import eligible_note_ids

XML = '<score-partwise><part id="P1"><measure number="1"><attributes><divisions>3</divisions></attributes><note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><!-- imgpos: 120, 240 --></note></measure></part></score-partwise>'


class ExternalOmrTest(unittest.TestCase):
    def test_homr_position_comments_do_not_break_lyric_eligibility(self):
        root=ET.fromstring(XML,parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
        self.assertEqual({'P1:1:1'},eligible_note_ids(root))
    def test_recognition_crop_is_not_mistaken_for_five_line_staff_band(self):
        region={'type':'staff','box':[0,80,500,180],'source':'clarity_yolo'}
        refined=staff_band_from_crop(region,[20,30,40,50,60])
        self.assertEqual([0,100,500,140],refined['box'])
        self.assertEqual(region['box'],refined['recognition_crop_box'])
        self.assertIsNone(staff_band_from_crop(region,[20,30]))
    def test_detected_lyric_rows_have_tight_boxes_and_keep_remote_text_unassigned(self):
        regions = [{'type': 'staff', 'box': [50, 100, 900, 140]}, {'type': 'staff', 'box': [50, 300, 900, 340]}]
        def word(text, x, y): return {'text': text, 'box': [x, y, x+30, y+15], 'cx': x+15, 'cy': y+7.5, 'h': 15, 'score': .9}
        rows = [[word('Tôi', 100, 160), word('đi', 150, 160)], [word('Ngài',100,185)],
                [word('Em', 100, 280)], [word('thơ',100,700)]]
        classified = classify_rows(rows, regions)
        self.assertEqual(['lyric','lyric','chord','unknown'], [r['role'] for r in classified])
        self.assertEqual([1,2], [r['verse_number'] for r in classified[:2]])
        self.assertEqual([100,160,180,175], classified[0]['box'])

    def test_third_verse_extends_detected_row_group_without_extending_to_poem(self):
        staff=[{'type':'staff','box':[0,100,500,140]}]
        rows=[[{'text':text,'box':[100,y,200,y+15],'score':.9}] for text,y in [('Tôi',160),('Ngài',190),('Chúa',220),('Thơ',500)]]
        self.assertEqual(['lyric','lyric','lyric','unknown'],[r['role'] for r in classify_rows(rows,staff)])

    def test_overlap_between_ocr_rows_and_tuplet_digits_do_not_shift_verses(self):
        staves=[{'type':'staff','box':[0,100,500,140]},{'type':'staff','box':[0,400,500,440]}]
        rows=[[{'text':text,'box':[100,y,200,y+35]}] for text,y in [('Tôi',160),('Ngài',194),('Chúa',228),('3',320)]]
        self.assertEqual(['lyric','lyric','lyric','unknown'],[r['role'] for r in classify_rows(rows,staves)])

    def test_approximate_positions_only_generate_review_proposals(self):
        words = [{'id':'w1','text':'Tôi','box':[90,155,110,170],'x':100,'staff_index':0,'verse_number':1,'confidence':.9}]
        positions = [{'id':'P1:1:1','page':1,'position':[100,125],'approximate':True}]
        result = propose_alignment(words, positions, [{'type':'staff','box':[0,100,500,140]}])
        self.assertEqual('proposed', result[0]['alignment']['status'])
        self.assertTrue(result[0]['alignment']['requires_review'])
        self.assertEqual('homr_attention', result[0]['alignment']['source'])
    def test_non_score_xml_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wrong.xml'
            path.write_text('<html/>')
            with self.assertRaises(ValueError): summarize_xml(path)

    def test_positions_keep_approximation_and_do_not_claim_verified_anchors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'score.musicxml'
            path.write_text(XML)
            result = homr_positions(path, 2)
            self.assertEqual([120.0, 240.0], result[0]['position'])
            self.assertEqual('P1:1:1', result[0]['id'])
            self.assertTrue(result[0]['approximate'])
            self.assertEqual(2, result[0]['page'])
            self.assertEqual(1, summarize_xml(path)['pitched_notes'])

    def test_failed_engine_cannot_succeed_using_old_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); project = root / 'projects/song'
            (project / 'pages').mkdir(parents=True)
            (project / 'pages/page_0001.png').write_bytes(b'image')
            (project / 'musicxml').mkdir()
            (project / 'musicxml/raw.musicxml').write_text(XML)
            worker = ComparisonWorker(root, 'homr')
            job = {'id': 'job1', 'project_uuid': 'song', 'engine': 'homr'}
            with patch.object(worker, 'run_page', side_effect=RuntimeError('engine failed')):
                result = worker.process(job)
            self.assertEqual('failed', result['status'])
            self.assertIn('engine failed', result['error'])
            self.assertEqual(XML, (project / 'musicxml/raw.musicxml').read_text())

    def test_job_paths_and_engine_are_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = ComparisonWorker(Path(directory), 'homr')
            for job in [{'id': '../x', 'project_uuid': 'song', 'engine': 'homr'},
                        {'id': 'x', 'project_uuid': '../song', 'engine': 'homr'},
                        {'id': 'x', 'project_uuid': 'song', 'engine': 'clarity'}]:
                with self.assertRaises(ValueError): worker.validate(job)

if __name__ == '__main__': unittest.main()
