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
    note_x = _normalized_positions(notes)
    if len(words) == 1 and len(notes) > 1:
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
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + skip_note_cost
        back[0][j] = ('skip_note', 0, j - 1, skip_note_cost)
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + skip_word_cost
        back[i][0] = ('skip_word', i - 1, 0, skip_word_cost)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            spatial = abs(word_x[i - 1] - note_x[j - 1])
            ocr_penalty = (1.0 - max(0.0, min(1.0, float(words[i - 1].get('confidence', 0.0))))) * 0.35
            choices = [
                (dp[i - 1][j - 1] + spatial + ocr_penalty, ('match', i - 1, j - 1, spatial)),
                (dp[i][j - 1] + skip_note_cost, ('skip_note', i, j - 1, skip_note_cost)),
                (dp[i - 1][j] + skip_word_cost, ('skip_word', i - 1, j, skip_word_cost)),
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
) -> dict:
    tree = ET.parse(musicxml_path)
    root = tree.getroot()
    namespace = _namespace(root)
    with open(artifact_path, 'r', encoding='utf-8') as source:
        artifact = json.load(source)
    anchors, note_elements = _note_anchors(root)

    for note in note_elements.values():
        for lyric in _children(note, 'lyric'):
            note.remove(lyric)

    words = artifact.get('words', [])
    grouped: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    for word in words:
        word['alignment'] = None
        grouped[(int(word.get('page', 1)), int(word.get('staff_index', 0)), int(word.get('verse_number', 1)))].append(word)

    accepted = 0
    review = 0
    for (page, staff_index, verse), group_words in grouped.items():
        group_notes = anchors.get((page, staff_index), [])
        ordered_words = sorted(group_words, key=lambda item: (float(item.get('x', 0)), int(item.get('sequence', 0))))
        matches = _align_group(ordered_words, group_notes)
        matched_word_indexes = set()
        for word_index, note_index, spatial_error in matches:
            word = ordered_words[word_index]
            note = group_notes[note_index]
            ocr_confidence = max(0.0, min(1.0, float(word.get('confidence', 0.0))))
            spatial_decay = float(os.getenv('LYRIC_ALIGN_SPATIAL_DECAY', '2.4'))
            spatial_confidence = math.exp(-spatial_decay * spatial_error)
            confidence = round(ocr_confidence * spatial_confidence, 6)
            status = 'accepted' if confidence >= acceptance_threshold else 'review'
            word['alignment'] = {
                'status': status,
                'confidence': confidence,
                'spatial_error': round(spatial_error, 6),
                'part_id': note['part_id'],
                'measure': note['measure'],
                'note_index': note['note_index'],
            }
            matched_word_indexes.add(word_index)
            if status != 'accepted':
                review += 1
                continue
            clean_text, syllabic = _syllabic(str(word.get('text', '')))
            lyric = ET.SubElement(note_elements[note['id']], namespace + 'lyric', {'number': str(verse)})
            ET.SubElement(lyric, namespace + 'syllabic').text = syllabic
            ET.SubElement(lyric, namespace + 'text').text = clean_text
            accepted += 1
        for index, word in enumerate(ordered_words):
            if index not in matched_word_indexes:
                word['alignment'] = {'status': 'review', 'confidence': 0.0, 'reason': 'no_note_candidate'}
                review += 1

    artifact['alignment_status'] = 'aligned' if review == 0 else 'needs_review'
    artifact['alignment_summary'] = {
        'accepted': accepted,
        'review': review,
        'acceptance_threshold': acceptance_threshold,
        'algorithm': 'monotonic_spatial_dp_v1',
    }
    artifact['verses'] = defaultdict(list)
    for word in words:
        artifact['verses'][str(word.get('verse_number', 1))].append(word)
    artifact['verses'] = dict(artifact['verses'])

    Path(output_musicxml_path).parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_musicxml_path, encoding='utf-8', xml_declaration=True)
    artifact_destination = output_artifact_path or artifact_path
    temporary = artifact_destination + '.tmp'
    with open(temporary, 'w', encoding='utf-8') as output:
        json.dump(artifact, output, ensure_ascii=False, indent=2)
    os.replace(temporary, artifact_destination)
    return artifact['alignment_summary']
