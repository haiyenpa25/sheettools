import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'workers'))
from evaluation.roadmap_benchmark import benchmark, annotation_metrics


class RoadmapBenchmarkTest(unittest.TestCase):
    def test_no_verified_ground_truth_means_no_accuracy(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory)/'manifest.json'
            manifest.write_text(json.dumps({'samples': [{'id': 'draft', 'verified': False}]}))
            report = benchmark(str(manifest), 'test-commit')
            self.assertFalse(report['accuracy_available'])
            self.assertEqual([], report['samples'])

    def test_verified_sample_requires_all_truth_files(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory)/'manifest.json'
            manifest.write_text(json.dumps({'samples': [{'id': 'missing', 'verified': True}]}))
            with self.assertRaises(ValueError):
                benchmark(str(manifest), 'test-commit')

    def test_correct_text_at_wrong_note_and_chord_offset_is_counted_wrong(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference, prediction = root/'truth.xml', root/'pred.xml'
            def score(lyric_note, offset):
                notes = ''.join('<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration>'+
                                ('<lyric number="1"><text>Xin</text></lyric>' if index == lyric_note else '')+'</note>' for index in (1, 2))
                return f'<score-partwise><part id="P1"><measure number="1"><attributes><divisions>1</divisions></attributes><harmony><root><root-step>G</root-step></root><kind>major</kind><offset>{offset}</offset></harmony>{notes}</measure></part></score-partwise>'
            reference.write_text(score(1, 0))
            prediction.write_text(score(2, 1))
            metrics = annotation_metrics(reference, prediction)
            self.assertEqual(0, metrics['chord_f1'])
            self.assertEqual(0, metrics['syllable_note_alignment_accuracy'])


if __name__ == '__main__':
    unittest.main()
