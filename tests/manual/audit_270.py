"""Reproduce a bounded quality audit of hymn 270; never a general accuracy claim."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import unicodedata
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workers'))
from evaluation.accuracy_report import _edit_distance


def tokens(text: str) -> list[str]:
    return [''.join(c for c in word if c.isalpha()) for word in
            unicodedata.normalize('NFC', text).casefold().split() if any(c.isalpha() for c in word)]


def lyric_metric(expected: str, predicted: list[str]) -> dict:
    reference, actual = tokens(expected), tokens(' '.join(predicted))
    distance = _edit_distance(reference, actual)
    return {'reference_syllables': len(reference), 'output_syllables': len(actual),
            'edit_errors': distance, 'word_error_rate': round(distance / max(len(reference), 1), 4),
            'output_text': ' '.join(predicted)}


def audit(project: Path) -> dict:
    truth = json.loads((ROOT / 'tests/ground_truth/270.manual.json').read_text(encoding='utf-8'))
    source_hash = hashlib.sha256((project / 'source/original.pdf').read_bytes()).hexdigest()
    if source_hash != truth['source_sha256']:
        raise ValueError('Ground truth belongs to a different source PDF')
    roots = [ET.parse(project / f'omr_out/page_result_{i:04d}/score.musicxml').getroot() for i in (1, 2)]
    report = {'source_sha256': source_hash, 'scope': truth['review_method'], 'lyrics': {}, 'note_checks': [], 'chord_checks': []}
    for verse, expected in truth['page1_verses'].items():
        lyrics = [l.findtext('text', '') for l in roots[0].iter('lyric')
                  if l.get('number') == verse and l.get('name') != 'ĐK']
        report['lyrics'][f'page1_verse{verse}'] = lyric_metric(expected, lyrics)
    report['lyrics']['page1_chorus'] = lyric_metric(truth['page1_chorus'],
        [l.findtext('text', '') for l in roots[0].iter('lyric') if l.get('name') == 'ĐK'])
    # Page 2 is all chorus, regardless of the pipeline's current section label.
    report['lyrics']['page2_chorus_text'] = lyric_metric(truth['page2_chorus'],
        [l.findtext('text', '') for l in roots[1].iter('lyric')])
    report['page2_chorus_label_correct'] = all(l.get('name') == 'ĐK' for l in roots[1].iter('lyric'))
    divisions = 1
    for measure in roots[0].find('part').findall('measure'):
        divisions = int(measure.findtext('attributes/divisions', str(divisions)))
        number = measure.get('number')
        if number not in truth['page1_notes']:
            continue
        actual = [[n.findtext('pitch/step'), int(n.findtext('pitch/alter', '0')),
                   int(n.findtext('pitch/octave', '0')), str(Fraction(int(n.findtext('duration', '0')), divisions))]
                  for n in measure.findall('note') if n.find('pitch') is not None]
        expected = truth['page1_notes'][number]
        report['note_checks'].append({'page': 1, 'measure': number, 'expected': expected,
                                     'actual': actual, 'matches': actual == expected})
    for number, expected in truth['page2_chords'].items():
        measure = roots[1].find(f"part/measure[@number='{number}']")
        actual = [[h.findtext('root/root-step'), int(h.findtext('root/root-alter', '0')), h.findtext('kind')]
                  for h in measure.findall('harmony')]
        report['chord_checks'].append({'page': 2, 'measure': number, 'expected': expected,
                                      'actual': actual, 'matches': actual == expected})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.project)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name, metric in report['lyrics'].items():
        print(name, {k: v for k, v in metric.items() if k != 'output_text'})
    print('Note checks:', report['note_checks'])
    print('Chord checks:', report['chord_checks'])
    print('Page 2 chorus label correct:', report['page2_chorus_label_correct'])
