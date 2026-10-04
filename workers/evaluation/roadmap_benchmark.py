"""Repeatable benchmark restricted to explicitly verified reference samples."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from fractions import Fraction
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from .accuracy_report import compare_musicxml


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _iou(a: list, b: list) -> float:
    intersection = max(0, min(a[2], b[2])-max(a[0], b[0]))*max(0, min(a[3], b[3])-max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/max(union, 1)


def _annotations(path: Path) -> tuple[Counter, list]:
    root = ET.parse(path).getroot()
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    chords, lyrics = Counter(), []
    for part in root.findall('part'):
        divisions = Fraction(1)
        for measure in part.findall('measure'):
            divisions = Fraction(measure.findtext('attributes/divisions', str(divisions)))
            cursor, previous_onset, note_index = Fraction(0), Fraction(0), 0
            for node in measure:
                if node.tag in ('backup', 'forward'):
                    cursor += Fraction(node.findtext('duration', '0')) * (-1 if node.tag == 'backup' else 1)
                elif node.tag == 'harmony':
                    onset = (cursor+Fraction(node.findtext('offset', '0')))/divisions
                    symbol = tuple(node.findtext(tag, default) for tag, default in (
                        ('root/root-step', ''), ('root/root-alter', '0'), ('kind', ''),
                        ('bass/bass-step', ''), ('bass/bass-alter', '0')))
                    degrees = tuple(sorted((degree.findtext('degree-value'), degree.findtext('degree-alter'), degree.findtext('degree-type')) for degree in node.findall('degree')))
                    chords[(part.get('id'), measure.get('number'), str(onset), symbol, degrees)] += 1
                elif node.tag == 'note':
                    note_index += 1
                    is_chord = node.find('chord') is not None
                    onset = previous_onset if is_chord else cursor
                    for lyric in node.findall('lyric'):
                        text = unicodedata.normalize('NFC', lyric.findtext('text', '')).casefold()
                        if text:
                            lyrics.append((text, part.get('id'), measure.get('number'), str(onset/divisions),
                                           lyric.get('number', '1'), lyric.get('name', '')))
                    if not is_chord and node.find('grace') is None:
                        previous_onset = cursor
                        cursor += Fraction(node.findtext('duration', '0'))
    return chords, lyrics


def annotation_metrics(reference: Path, prediction: Path) -> dict:
    expected_chords, expected_lyrics = _annotations(reference)
    actual_chords, actual_lyrics = _annotations(prediction)
    overlap = sum((expected_chords & actual_chords).values())
    chord_count = sum(expected_chords.values())+sum(actual_chords.values())
    expected_anchors = Counter(item[:5] for item in expected_lyrics)
    actual_anchors = Counter(item[:5] for item in actual_lyrics)
    anchored = sum((expected_anchors & actual_anchors).values())
    return {'chord_f1': 2*overlap/chord_count if chord_count else None,
            'syllable_note_alignment_accuracy': anchored/len(expected_lyrics) if expected_lyrics else None,
            'verse_assignment_accuracy': sum((Counter(expected_lyrics) & Counter(actual_lyrics)).values())/len(expected_lyrics) if expected_lyrics else None,
            'annotation_metric_note': 'Exact text+part+measure+beat+verse matching; section/verse metric also checks lyric name.'}


def benchmark(manifest_path: str, commit: str) -> dict:
    manifest = Path(manifest_path).resolve()
    results = []
    for sample in _json(manifest).get('samples', []):
        if sample.get('verified') is not True:
            continue
        paths = {}
        for key in ('source', 'truth_musicxml', 'truth_document', 'truth_sections', 'truth_page_model',
                    'prediction_musicxml', 'prediction_document', 'prediction_lyrics', 'prediction_page_model'):
            value = sample.get(key)
            if not value or not (manifest.parent/value).is_file():
                raise ValueError(f"Sample {sample.get('id')}: required file missing: {key}")
            paths[key] = manifest.parent/value
        metrics = compare_musicxml(paths['truth_musicxml'], paths['prediction_musicxml'])
        metrics.update(annotation_metrics(paths['truth_musicxml'], paths['prediction_musicxml']))
        truth, prediction = _json(paths['truth_document']), _json(paths['prediction_document'])
        fields = ('title', 'composer', 'lyricist', 'hymn_number')
        metrics['header_field_accuracy'] = sum(truth.get(key, {}).get('text', '') == prediction.get(key, {}).get('text', '') for key in fields)/len(fields)
        expected_lines = _json(paths['truth_page_model']).get('text_lines', [])
        predicted_lines = _json(paths['prediction_page_model']).get('text_lines', [])
        correct, used = 0, set()
        for line in expected_lines:
            options = [(index, candidate) for index, candidate in enumerate(predicted_lines) if index not in used]
            best = max(options, key=lambda pair: _iou(line['box'], pair[1]['box']), default=None)
            if best and _iou(line['box'], best[1]['box']) >= .5:
                used.add(best[0])
                correct += best[1]['role'] == line['role']
        metrics['text_role_accuracy'] = correct/len(expected_lines) if expected_lines else None
        truth_sections = _json(paths['truth_sections']).get('sections', [])
        lyrics = _json(paths['prediction_lyrics'])
        expected_sections = [(section['type'], section['verse_count'], section.get('measure_range', [])) for section in truth_sections]
        predicted_sections = [(section['type'], section['verse_count'], section.get('measure_range', [])) for section in lyrics.get('sections', [])]
        metrics['section_structure_exact'] = expected_sections == predicted_sections
        words = lyrics.get('words', [])
        metrics['review_load'] = sum((word.get('alignment') or {}).get('status') != 'accepted' for word in words)/len(words) if words else None
        results.append({'id': sample['id'], 'stratum': sample.get('stratum'),
                        'source_sha256': hashlib.sha256(paths['source'].read_bytes()).hexdigest(), **metrics})
    return {'schema_version': 1, 'commit': commit, 'ground_truth_used': bool(results), 'accuracy_available': bool(results),
            'verified_sample_count': len(results), 'representative_dataset': 30 <= len(results) <= 50,
            'samples': results,
            'message': 'Design targets require stratified, human-verified data; synthetic tests and OCR confidence are not accuracy.'}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(benchmark(args.manifest, args.commit), ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
