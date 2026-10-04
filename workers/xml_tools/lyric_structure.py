"""Section inference and conservative projection of printed poem stanzas."""
from __future__ import annotations

from collections import Counter, defaultdict
from difflib import SequenceMatcher
import re
from statistics import median
from .text_roles import cluster_text_rows


def parse_markers(text: str) -> dict:
    verse = re.match(r'^\s*(?:Lời\s+)?(\d+)(?:[.):]|\s*:)', text, re.I)
    section = None
    if re.match(r'^\s*(?:Đ\.?K\.?|Điệp khúc)\s*[:.]?(?:\s|$)', text, re.I):
        section = 'chorus'
    elif re.match(r'^\s*(?:Coda|Kết|Fine|D\.[CS]\.)\b', text, re.I):
        section = 'coda'
    return {'verse': int(verse.group(1)) if verse else None, 'section': section}


class LyricStructureAnalyzer:
    """Infer a contiguous section path; explicit markers override inference."""
    def analyze(self, words: list[dict], text_lines: list[dict], anchors: list[dict] | None = None) -> dict:
        words = [word for word in words if not word.get('poem_stanza')]
        systems = sorted({word.get('system_id') for word in words if word.get('system_id')} |
                         {line['system_id'] for line in text_lines if line.get('system_id')})
        frames = []
        for system in systems:
            by_staff = defaultdict(list)
            for word in words:
                if word.get('system_id') == system:
                    box = word.get('box', [])
                    by_staff[word.get('staff_index', 0)].append({**word, 'cy': word.get('y', 0), 'cx': word.get('x', 0),
                        'h': box[3]-box[1] if len(box) == 4 else word.get('h', 20), '_source': word})
            rows = [row for staff_words in by_staff.values() for row in cluster_text_rows(staff_words)]
            marker = None
            for line in text_lines:
                if line.get('system_id') != system:
                    continue
                parsed = parse_markers(line['text'])
                if parsed['section']:
                    marker = parsed['section']
                if parsed['verse']:
                    center = (line['box'][1]+line['box'][3])/2
                    nearest = min(rows, key=lambda row: abs(median(word['cy'] for word in row)-center), default=None)
                    if nearest:
                        for word in nearest:
                            word['_source']['verse_number'] = parsed['verse']
                            word['_source']['explicit_verse'] = True
            count = max((len(cluster_text_rows(staff_words)) for staff_words in by_staff.values()), default=0)
            system_anchors = [anchor for anchor in (anchors or []) if anchor.get('system_id') == system]
            measures = sorted({int(anchor['measure']) for anchor in system_anchors if str(anchor.get('measure', '')).isdigit()})
            frames.append({'system_id': system, 'count': count, 'marker': marker, 'rows': rows,
                           'words': [word['_source'] for row in rows for word in row], 'measures': measures})
        measure_frames = []
        for frame in frames:
            system_anchors = [anchor for anchor in (anchors or []) if anchor.get('system_id') == frame['system_id']]
            if not frame['measures']:
                measure_frames.append(frame)
                continue
            by_measure = defaultdict(list)
            for word in frame['words']:
                staff_notes = [anchor for anchor in system_anchors if anchor.get('staff_index') == word.get('staff_index')]
                if staff_notes:
                    nearest = min(staff_notes, key=lambda anchor: abs(anchor['x']-word['x']))
                    word['measure_hint'] = str(nearest['measure'])
                    by_measure[int(nearest['measure'])].append(word)
            markers = {}
            for line in text_lines:
                if line.get('system_id') != frame['system_id']:
                    continue
                section_marker = parse_markers(line['text'])['section']
                if section_marker:
                    x = line['box'][0]
                    candidate = next((anchor for anchor in system_anchors if anchor.get('measure_box')
                                      and anchor['measure_box'][0] <= x <= anchor['measure_box'][1]), None)
                    if candidate:
                        markers[int(candidate['measure'])] = section_marker
            for number in frame['measures']:
                measure_words = by_measure[number]
                rows = [[word for word in row if word['_source'] in measure_words] for row in frame['rows']]
                rows = [row for row in rows if row]
                count_by_staff = Counter(row[0]['_source'].get('staff_index', 0) for row in rows)
                measure_frames.append({**frame, 'words': measure_words, 'rows': rows,
                    'count': max(count_by_staff.values(), default=0), 'measures': [number], 'marker': markers.get(number)})
        frames = measure_frames
        multi = [frame['count'] for frame in frames if frame['count'] >= 2]
        verse_count = Counter(multi).most_common(1)[0][0] if multi else 1
        states = ('verse', 'chorus', 'coda', 'intro')
        paths = {}
        for index, frame in enumerate(frames):
            scores = {
                'verse': (3 if frame['count'] == verse_count else 0) + (2 if any(word.get('explicit_verse') for word in frame['words']) else 0),
                'chorus': 3 if frame['count'] == 1 and verse_count >= 2 else 0,
                'coda': 1 if index == len(frames)-1 else 0,
                'intro': 3 if frame['count'] == 0 else -3,
            }
            if frame['marker']:
                scores = {state: 10 if state == frame['marker'] else -100 for state in states}
            phrase = ' '.join(word['text'] for word in frame['words']).casefold()
            if any(SequenceMatcher(None, phrase, ' '.join(word['text'] for word in prior['words']).casefold()).ratio() > .85
                   for prior in frames[:index]) and frame['count'] == 1:
                scores['chorus'] += 1
            next_paths = {}
            for state in states:
                if not paths:
                    next_paths[state] = (scores[state], [state])
                else:
                    best_score, best_path = max((score+(1 if previous == state else -1), path)
                                                for previous, (score, path) in paths.items())
                    next_paths[state] = (best_score+scores[state], best_path+[state])
            paths = next_paths
        labels = max(paths.values(), key=lambda entry: entry[0])[1] if paths else []
        sections = []
        for frame, label in zip(frames, labels):
            if not sections or sections[-1]['type'] != label:
                sections.append({'id': f'sec_{len(sections)+1}', 'type': label, 'verse_count': verse_count if label == 'verse' else 1,
                                 'systems': [], 'measure_range': [], 'confidence_source': 'rule_viterbi', 'needs_review': not bool(frame['marker'])})
            section = sections[-1]
            if frame['system_id'] not in section['systems']:
                section['systems'].append(frame['system_id'])
            if frame['measures']:
                previous = section['measure_range']
                section['measure_range'] = [min((previous or frame['measures'])[0], frame['measures'][0]), frame['measures'][-1]]
            for word in frame['words']:
                word['section_id'] = section['id']
                word['section_type'] = label
                if label == 'chorus':
                    word['verse_number'], word['lyric_name'] = 1, 'ĐK'
                elif label == 'coda':
                    word['verse_number'], word['lyric_name'] = 1, 'Coda'
                else:
                    reference = max((candidate for candidate, state in zip(frames, labels) if state == 'verse'),
                                    key=lambda candidate: candidate['count'], default=frame)
                    reference_offsets = sorted({round(median(word['_source'].get('row_offset', 0) for word in row), 2)
                                                for row in reference['rows']})
                    if 'row_offset' in word and not word.get('explicit_verse') and reference_offsets:
                        word['verse_number'] = min(range(len(reference_offsets)),
                            key=lambda index: abs(reference_offsets[index]-word['row_offset']))+1
                    word['lyric_name'] = f"Lời {word.get('verse_number', 1)}"
        for section in sections:
            if section['type'] == 'verse':
                section['verse_count'] = max(section['verse_count'], max((int(word.get('verse_number', 1))
                    for word in words if word.get('section_id') == section['id']), default=1))
        return {'sections': sections, 'verse_count': verse_count}


def detect_poem_stanzas(words: list[dict], last_staff_bottom: float, interline: float) -> list[dict]:
    candidates = [{**word, 'cy': word.get('y', 0), 'cx': word.get('x', 0),
                   'h': word['box'][3]-word['box'][1], '_source': word}
                  for word in words if len(word.get('box', [])) == 4 and word.get('y', 0) > last_staff_bottom]
    rows = cluster_text_rows(candidates)
    stanzas, active, previous_y = [], None, last_staff_bottom
    for row in rows:
        first = min(row, key=lambda word: word['cx'])
        marker = parse_markers(first['text'])['verse']
        center = median(word['cy'] for word in row)
        row_height = median(word['h'] for word in row)
        distant = center-previous_y > 3*row_height or center-last_staff_bottom > 12*interline
        if marker and marker >= 2 and (active is not None or distant):
            active = {'id': f'stanza_{len(stanzas)+1}', 'verse_number': marker, 'words': []}
            stanzas.append(active)
        if active:
            for token in row:
                word = token['_source']
                word['poem_stanza'] = active['id']
                if re.fullmatch(r'\d+[.)]', word['text']):
                    word['is_marker'] = True
                    continue
                active['words'].append(word)
        previous_y = center
    words[:] = [word for word in words if not word.get('is_marker')]
    return stanzas


def project_stanzas(template: list[dict], stanzas: list[dict]) -> None:
    accepted = [word for word in template if (word.get('alignment') or {}).get('status') == 'accepted']
    for stanza in stanzas:
        words = stanza['words']
        mismatch = abs(len(words)-len(template))/max(len(template), 1)
        # Within 10% is only a candidate. Different counts are retained for
        # human review rather than guessing which syllable was omitted.
        if mismatch > .1 or len(words) != len(template) or len(accepted) != len(template):
            for word in words:
                word['alignment'] = {'status': 'review', 'confidence': 0, 'reason': 'stanza_template_mismatch'}
            continue
        for source, word in zip(template, words):
            word['alignment'] = {**source['alignment'], 'anchor_source': 'verse_one_template'}
            word['verse_number'] = stanza['verse_number']
            word['lyric_name'] = f"Lời {stanza['verse_number']}"


def structure_tree(words: list[dict], sections: list[dict]) -> list[dict]:
    """Build sections → verses → lines → syllables, retaining flat compatibility."""
    result = []
    for section in sections:
        verses = defaultdict(lambda: defaultdict(list))
        for word in words:
            if word.get('section_id') == section['id']:
                verses[int(word.get('verse_number', 1))][(word.get('page', 1), word.get('staff_index', 0))].append(word)
        missing = [number for number in range(1, section.get('verse_count', 1)+1) if number not in verses]
        result.append({**section, 'missing_verses': missing, 'needs_review': bool(section.get('needs_review') or missing),
                       'verses': [{'number': number, 'lines': [
            {'page': page, 'staff_index': staff, 'syllables': syllables} for (page, staff), syllables in lines.items()]}
            for number, lines in sorted(verses.items())]})
    return result
