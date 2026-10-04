#!/usr/bin/env python3
"""Constrained spatial alignment between independent OCR lyrics and MusicXML notes."""
from __future__ import annotations

import json
import math
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def _local(element: ET.Element) -> str:
    return element.tag.rsplit('}', 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local(child) == name]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in element if _local(child) == name), None)


def _namespace(root: ET.Element) -> str:
    return root.tag.split('}', 1)[0] + '}' if root.tag.startswith('{') else ''


def _eligible(note: ET.Element) -> bool:
    names = {_local(child) for child in note}
    if {'rest', 'chord', 'grace'} & names:
        return False
    ties = [tie.get('type') for tie in _children(note, 'tie')]
    return not ('stop' in ties and 'start' not in ties)


def _note_anchors(root: ET.Element) -> tuple[dict[tuple[int, int], list[dict]], dict[str, ET.Element]]:
    parts = [node for node in root.iter() if _local(node) == 'part']
    if not parts:
        return {}, {}
    # Map every part/staff in score order. Assuming P1 is always the sung
    # melody breaks SATB, duet and piano+voice scores.
    staff_counts = []
    for part in parts:
        staff_numbers = []
        for note in part.iter():
            if _local(note) != 'note':
                continue
            staff_node = _child(note, 'staff')
            staff_numbers.append(int((staff_node.text if staff_node is not None else '1') or '1'))
        staff_counts.append(max(staff_numbers or [1]))
    part_offsets = [sum(staff_counts[:index]) for index in range(len(parts))]
    staves_per_system = sum(staff_counts)
    anchors: dict[tuple[int, int], list[dict]] = defaultdict(list)
    elements: dict[str, ET.Element] = {}
    for part_index, part in enumerate(parts):
        part_id = part.get('id', f'P{part_index + 1}')
        page, system, system_measure_offset = 1, 0, 0.0
        for measure in _children(part, 'measure'):
            print_node = _child(measure, 'print')
            if print_node is not None and print_node.get('new-page') == 'yes':
                page += 1
                system = 0
                system_measure_offset = 0.0
            elif print_node is not None and print_node.get('new-system') == 'yes':
                system += 1
                system_measure_offset = 0.0

            measure_number = measure.get('number', '')
            candidates = []
            for note_index, note in enumerate(_children(measure, 'note'), start=1):
                if not _eligible(note):
                    continue
                voice_node = _child(note, 'voice')
                voice = (voice_node.text or '1') if voice_node is not None else '1'
                candidates.append((note_index, note, voice))
            # Lyrics conventionally follow the primary voice on a staff. Keep
            # other voices only when no voice 1 exists, avoiding simultaneous
            # chordal voices competing for the same OCR token.
            if any(voice == '1' for _, _, voice in candidates):
                candidates = [item for item in candidates if item[2] == '1']
            for note_index, note, _voice in candidates:
                staff_node = _child(note, 'staff')
                staff_number = int((staff_node.text if staff_node is not None else '1') or '1')
                row = system * staves_per_system + part_offsets[part_index] + staff_number - 1
                try:
                    local_x = float(note.get('default-x', note_index * 10.0))
                except ValueError:
                    local_x = note_index * 10.0
                anchor_id = f"{part_id}:{measure_number}:{note_index}"
                anchor = {'id': anchor_id, 'part_id': part_id, 'measure': measure_number,
                          'note_index': note_index, 'page': page, 'staff_index': row,
                          'x': system_measure_offset + local_x}
                anchors[(page, row)].append(anchor)
                elements[anchor_id] = note
            try:
                system_measure_offset += float(measure.get('width', '100'))
            except ValueError:
                system_measure_offset += 100.0
    return dict(anchors), elements


def _normalized_positions(items: list[dict]) -> list[float]:
    values = [float(item.get('x', 0.0)) for item in items]
    if len(values) <= 1 or max(values) == min(values):
        return [0.5 for _ in values]
    low, span = min(values), max(values) - min(values)
    return [(value - low) / span for value in values]


def _align_group(words: list[dict], notes: list[dict]) -> list[tuple[int, int, float]]:
    """Needleman-Wunsch style monotonic matching with note/token gap penalties."""
    if not words or not notes:
        return []
    words = sorted(words, key=lambda item: (float(item.get('x', 0)), int(item.get('sequence', 0))))
    notes = sorted(notes, key=lambda item: float(item.get('x', 0)))
    pixel = all(note.get('anchor_source') == 'omr_pixel' for note in notes)
    scale = max(float(notes[0].get('interline', 1)), 1)
    note_x = [float(note['x'])/scale for note in notes] if pixel else _normalized_positions(notes)
    if pixel:
        word_x = [(float(word['box'][0])+.4*(float(word['box'][2])-float(word['box'][0])))/scale
                  if len(word.get('box', [])) == 4 else float(word.get('x', 0))/scale for word in words]
    elif len(words) == 1 and len(notes) > 1:
        note_values = [float(item.get('x', 0.0)) for item in notes]
        span = max(note_values) - min(note_values)
        word_x = [max(0.0, min(1.0, (float(words[0].get('x', 0.0)) - min(note_values)) / span))] if span else [0.5]
    else:
        word_x = _normalized_positions(words)
    n, m = len(words), len(notes)
    inf = float('inf')
    dp = [[inf] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple[str, int, int, float] | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    skip_note_cost = float(os.getenv('LYRIC_ALIGN_SKIP_NOTE_COST', '0.34'))
    skip_word_cost = float(os.getenv('LYRIC_ALIGN_SKIP_WORD_COST', '1.15'))
    from .vi_lexicon import is_vietnamese_syllable
    def note_gap(j: int) -> float:
        return (.15 if notes[j].get('slur_ids') else .6) if pixel else skip_note_cost
    def word_gap(i: int) -> float:
        return (3.0 if is_vietnamese_syllable(words[i].get('text', '')) else 1.2) if pixel else skip_word_cost
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + note_gap(j-1)
        back[0][j] = ('skip_note', 0, j - 1, note_gap(j-1))
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + word_gap(i-1)
        back[i][0] = ('skip_word', i - 1, 0, word_gap(i-1))
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            spatial = abs(word_x[i - 1] - note_x[j - 1])
            ocr_penalty = (1.0 - max(0.0, min(1.0, float(words[i - 1].get('confidence', 0.0))))) * 0.35
            choices = [
                (dp[i - 1][j - 1] + (inf if pixel and spatial > 2.5 else spatial) + ocr_penalty
                 + (.5 if pixel and notes[j-1].get('slur_continuation') else 0), ('match', i - 1, j - 1, spatial)),
                (dp[i][j - 1] + note_gap(j-1), ('skip_note', i, j - 1, note_gap(j-1))),
                (dp[i - 1][j] + word_gap(i-1), ('skip_word', i - 1, j, word_gap(i-1))),
            ]
            dp[i][j], back[i][j] = min(choices, key=lambda choice: choice[0])
    matches = []
    i, j = n, m
    while i or j:
        step = back[i][j]
        if step is None:
            break
        action, previous_i, previous_j, spatial = step
        if action == 'match':
            matches.append((previous_i, previous_j, spatial))
            i, j = previous_i, previous_j
        elif action == 'skip_note':
            i, j = i, previous_j
        else:
            i, j = previous_i, j
    matches.reverse()
    return matches


def _syllabic(text: str) -> tuple[str, str]:
    leading, trailing = text.startswith('-'), text.endswith('-')
    clean = text.strip('-').strip()
    if leading and trailing:
        return clean, 'middle'
    if trailing:
        return clean, 'begin'
    if leading:
        return clean, 'end'
    return clean, 'single'


def align_lyrics_artifact(
    musicxml_path: str,
    artifact_path: str,
    output_musicxml_path: str,
    output_artifact_path: str | None = None,
    acceptance_threshold: float = 0.55,
    note_anchors_path: str | None = None,
) -> dict:
    tree = ET.parse(musicxml_path)
    root = tree.getroot()
    namespace = _namespace(root)
    with open(artifact_path, 'r', encoding='utf-8') as source:
        artifact = json.load(source)
    anchors, note_elements = _note_anchors(root)
    pixel_by_id = {}
    if note_anchors_path:
        with open(note_anchors_path, encoding='utf-8') as source:
            pixel_by_id = {anchor['id']: anchor for anchor in json.load(source).get('anchors', [])}
    artifact_pages = {int(word.get('page', 1)) for word in artifact.get('words', [])}
    if len(artifact_pages) == 1 and {page for page, _ in anchors} == {1}:
        page_number = next(iter(artifact_pages))
        anchors = {(page_number, staff): group for (_, staff), group in anchors.items()}
    rebuilt: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for (page, staff), group in anchors.items():
        active_slurs: set[str] = set()
        for note in group:
            element = note_elements[note['id']]
            slurs = [node for node in element.iter() if _local(node) == 'slur']
            for slur in slurs:
                if slur.get('type') == 'start':
                    active_slurs.add(slur.get('number', '1'))
            note['slur_ids'] = sorted(active_slurs)
            note['slur_continuation'] = bool(active_slurs) and not any(slur.get('type') == 'start' for slur in slurs)
            for slur in slurs:
                if slur.get('type') == 'stop':
                    active_slurs.discard(slur.get('number', '1'))
            if note['id'] in pixel_by_id:
                note.update(pixel_by_id[note['id']])
            else:
                note['anchor_source'] = 'musicxml_fallback'
            rebuilt[(page, int(note.get('staff_index', staff)))].append(note)
    anchors = dict(rebuilt)

    for note in note_elements.values():
        for lyric in _children(note, 'lyric'):
            note.remove(lyric)

    words = artifact.get('words', [])
    grouped: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    for word in words:
        word['alignment'] = None
        if word.get('poem_stanza'):
            continue
        grouped[(int(word.get('page', 1)), int(word.get('staff_index', 0)), int(word.get('verse_number', 1)))].append(word)

    accepted = 0
    review = 0
    for (page, staff_index, verse), group_words in grouped.items():
        group_notes = anchors.get((page, staff_index), [])
        # A partly mapped staff must not mix pixel and MusicXML units.
        if note_anchors_path and group_notes and any(note['anchor_source'] == 'musicxml_fallback' for note in group_notes):
            for word in group_words:
                word['alignment'] = {'status': 'review', 'confidence': 0, 'reason': 'musicxml_fallback',
                                     'anchor_source': 'musicxml_fallback'}
            review += len(group_words)
            continue
        ordered_words = sorted(group_words, key=lambda item: (float(item.get('x', 0)), int(item.get('sequence', 0))))
        matches = _align_group(ordered_words, group_notes)
        matched_word_indexes = set()
        for word_index, note_index, spatial_error in matches:
            word = ordered_words[word_index]
            note = group_notes[note_index]
            ocr_confidence = max(0.0, min(1.0, float(word.get('confidence', 0.0))))
            spatial_decay = .8 if note.get('anchor_source') == 'omr_pixel' else float(os.getenv('LYRIC_ALIGN_SPATIAL_DECAY', '2.4'))
            spatial_confidence = math.exp(-spatial_decay * spatial_error)
            confidence = round(ocr_confidence * spatial_confidence, 6)
            status = 'accepted' if confidence >= acceptance_threshold and not word.get('geometry_needs_review') else 'review'
            word['alignment'] = {
                'status': status,
                'confidence': confidence,
                'spatial_error': round(spatial_error, 6),
                'part_id': note['part_id'],
                'measure': note['measure'],
                'note_index': note['note_index'],
                'anchor_source': note.get('anchor_source', 'musicxml_fallback'),
                'reason': 'syllable_geometry_fallback' if word.get('geometry_needs_review') else None,
            }
            matched_word_indexes.add(word_index)
            if status != 'accepted':
                review += 1
                continue
            clean_text, syllabic = _syllabic(str(word.get('text', '')))
            lyric = ET.SubElement(note_elements[note['id']], namespace + 'lyric', {'number': str(verse),
                                       'name': word.get('lyric_name', f'Lời {verse}')})
            ET.SubElement(lyric, namespace + 'syllabic').text = syllabic
            ET.SubElement(lyric, namespace + 'text').text = clean_text
            accepted += 1
        matched_notes = {note for _, note, _ in matches}
        for position, (word_index, note_index, _) in enumerate(matches):
            word = ordered_words[word_index]
            if (word.get('alignment') or {}).get('status') != 'accepted':
                continue
            current = group_notes[note_index]
            end = matches[position+1][1] if position+1 < len(matches) else len(group_notes)
            continuation = []
            for skipped in range(note_index+1, end):
                candidate = group_notes[skipped]
                if skipped in matched_notes or not set(current.get('slur_ids', [])) & set(candidate.get('slur_ids', [])):
                    break
                continuation.append(candidate)
            if continuation:
                word['alignment']['melisma_note_ids'] = [candidate['id'] for candidate in continuation]
                start_lyric = next(lyric for lyric in _children(note_elements[current['id']], 'lyric') if lyric.get('number') == str(verse))
                ET.SubElement(start_lyric, namespace+'extend', {'type': 'start'})
                for index, candidate in enumerate(continuation):
                    lyric = ET.SubElement(note_elements[candidate['id']], namespace+'lyric', {'number': str(verse), 'name': word.get('lyric_name', f'Lời {verse}')})
                    ET.SubElement(lyric, namespace+'extend', {'type': 'stop' if index == len(continuation)-1 else 'continue'})
        for index, word in enumerate(ordered_words):
            if index not in matched_word_indexes:
                word['alignment'] = {'status': 'review', 'confidence': 0.0, 'reason': 'no_note_candidate'}
                review += 1

    from .lyric_structure import project_stanzas
    stanzas = [{**stanza, 'words': [word for word in words if word.get('poem_stanza') == stanza['id']]}
               for stanza in artifact.get('stanzas', [])]
    template = [word for word in words if not word.get('poem_stanza') and int(word.get('verse_number', 1)) == 1
                and word.get('section_type', 'verse') == 'verse']
    project_stanzas(template, stanzas)
    for stanza in stanzas:
        for word in stanza['words']:
            alignment = word.get('alignment') or {}
            anchor_id = f"{alignment.get('part_id')}:{alignment.get('measure')}:{alignment.get('note_index')}"
            element = note_elements.get(anchor_id)
            verse = str(stanza['verse_number'])
            if (alignment.get('status') != 'accepted' or element is None
                    or float(word.get('confidence', 0)) < .7
                    or any(lyric.get('number') == verse for lyric in _children(element, 'lyric'))):
                word['alignment'] = {**alignment, 'status': 'review', 'reason': 'stanza_confidence_or_duplicate'}
                review += 1
                continue
            clean, syllabic = _syllabic(word['text'])
            lyric = ET.SubElement(element, namespace+'lyric', {'number': verse, 'name': word['lyric_name']})
            ET.SubElement(lyric, namespace+'syllabic').text = syllabic
            ET.SubElement(lyric, namespace+'text').text = clean
            extensions = alignment.get('melisma_note_ids', [])
            if extensions:
                ET.SubElement(lyric, namespace+'extend', {'type': 'start'})
                for index, note_id in enumerate(extensions):
                    target = note_elements.get(note_id)
                    if target is not None and not any(item.get('number') == verse for item in _children(target, 'lyric')):
                        extension = ET.SubElement(target, namespace+'lyric', {'number': verse, 'name': word['lyric_name']})
                        ET.SubElement(extension, namespace+'extend', {'type': 'stop' if index == len(extensions)-1 else 'continue'})
            accepted += 1
    artifact['stanzas'] = stanzas
    artifact['alignment_status'] = 'aligned' if review == 0 else 'needs_review'
    artifact['alignment_summary'] = {
        'accepted': accepted,
        'review': review,
        'acceptance_threshold': acceptance_threshold,
        'algorithm': 'monotonic_pixel_dp_v2' if note_anchors_path else 'monotonic_spatial_dp_v1',
        'fallback_staffs': [staff for (_, staff), notes in anchors.items() if any(note.get('anchor_source') == 'musicxml_fallback' for note in notes)],
    }
    artifact['verses'] = defaultdict(list)
    for word in words:
        artifact['verses'][str(word.get('verse_number', 1))].append(word)
    artifact['verses'] = dict(artifact['verses'])
    from .lyric_structure import structure_tree
    if artifact.get('sections'):
        artifact['sections'] = structure_tree(words, artifact['sections'])
        artifact['schema_version'] = 2
        for section in artifact['sections']:
            section_words = [word for word in words if word.get('section_id') == section['id']]
            section['alignment_summary'] = {
                'accepted': sum((word.get('alignment') or {}).get('status') == 'accepted' for word in section_words),
                'review': sum((word.get('alignment') or {}).get('status') != 'accepted' for word in section_words),
            }

    Path(output_musicxml_path).parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_musicxml_path, encoding='utf-8', xml_declaration=True)
    artifact_destination = output_artifact_path or artifact_path
    temporary = artifact_destination + '.tmp'
    with open(temporary, 'w', encoding='utf-8') as output:
        json.dump(artifact, output, ensure_ascii=False, indent=2)
    os.replace(temporary, artifact_destination)
    return artifact['alignment_summary']
