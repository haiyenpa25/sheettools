"""Strict chord grammar and pixel-to-time anchoring on derived MusicXML."""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from .text_roles import is_chord


def _harmony(symbol: str, namespace: str) -> ET.Element:
    symbol = symbol.replace('♯', '#').replace('♭', 'b')
    match = re.fullmatch(r'([A-G])([#b]?)([^/]*)(?:/([A-G])([#b]?))?', symbol)
    step, alter, quality, bass, bass_alter = match.groups()
    result = ET.Element(namespace+'harmony')
    root = ET.SubElement(result, namespace+'root')
    ET.SubElement(root, namespace+'root-step').text = step
    if alter:
        ET.SubElement(root, namespace+'root-alter').text = '1' if alter == '#' else '-1'
    kinds = {'': 'major', 'M': 'major', 'maj': 'major', 'm': 'minor', 'min': 'minor',
             '7': 'dominant', 'maj7': 'major-seventh', 'M7': 'major-seventh', 'm7': 'minor-seventh',
             'min7': 'minor-seventh', 'm7b5': 'half-diminished', 'dim': 'diminished', '°': 'diminished',
             'dim7': 'diminished-seventh', '°7': 'diminished-seventh', 'aug': 'augmented', '+': 'augmented',
             'sus': 'suspended-fourth', 'sus4': 'suspended-fourth', 'sus2': 'suspended-second',
             '6': 'major-sixth', 'm6': 'minor-sixth', '9': 'dominant-ninth', 'maj9': 'major-ninth',
             'M9': 'major-ninth', 'm9': 'minor-ninth', '11': 'dominant-11th', '13': 'dominant-13th'}
    modifiers = []
    if quality in kinds:
        kind = kinds[quality]
    else:
        modifier = re.search(r'(?:add\d+|[#b]\d+)', quality)
        base = quality[:modifier.start()] if modifier else quality
        if base not in kinds:
            raise ValueError('Unsupported chord quality')
        kind = kinds[base]
        tail = quality[len(base):]
        modifiers = re.findall(r'(add|#|b)(\d+)', tail)
        if ''.join(prefix+number for prefix, number in modifiers) != tail:
            raise ValueError('Unsupported chord extension')
    ET.SubElement(result, namespace+'kind', {'text': quality or 'major'}).text = kind
    if bass:
        bass_node = ET.SubElement(result, namespace+'bass')
        ET.SubElement(bass_node, namespace+'bass-step').text = bass
        if bass_alter:
            ET.SubElement(bass_node, namespace+'bass-alter').text = '1' if bass_alter == '#' else '-1'
    for prefix, number in modifiers:
        degree = ET.SubElement(result, namespace+'degree')
        ET.SubElement(degree, namespace+'degree-value').text = number
        ET.SubElement(degree, namespace+'degree-alter').text = {'add': '0', '#': '1', 'b': '-1'}[prefix]
        ET.SubElement(degree, namespace+'degree-type').text = 'add' if prefix == 'add' else 'alter'
    return result


def inject_chords(musicxml_path: str, chords: list[dict], anchors: list[dict]) -> dict:
    tree = ET.parse(musicxml_path)
    root = tree.getroot()
    namespace = root.tag.split('}')[0]+'}' if root.tag.startswith('{') else ''
    # B5 is the authoritative chord layer. Preserve the raw export separately.
    for parent in root.iter():
        for child in list(parent):
            if child.tag.rsplit('}', 1)[-1] == 'harmony':
                parent.remove(child)
    accepted, review = 0, []
    for chord in chords:
        candidates = [anchor for anchor in anchors if anchor.get('anchor_source') == 'omr_pixel'
                      and anchor.get('staff_index') == chord.get('staff_index') and anchor.get('onset') is not None]
        if not is_chord(chord['chord']) or float(chord.get('confidence', 0)) < .7 or not candidates:
            review.append({**chord, 'reason': 'grammar_confidence_or_anchor_missing'})
            continue
        x = float(chord['x'])
        candidates = [anchor for anchor in candidates if anchor.get('measure_box') and anchor['measure_box'][0] <= x <= anchor['measure_box'][1]]
        if not candidates:
            review.append({**chord, 'reason': 'outside_measure'})
            continue
        closest = min(candidates, key=lambda anchor: abs(x-anchor['x']))
        measure_notes = sorted([anchor for anchor in candidates if anchor['part_id'] == closest['part_id'] and anchor['measure'] == closest['measure']], key=lambda anchor: anchor['x'])
        left = max((anchor for anchor in measure_notes if anchor['x'] <= x), key=lambda anchor: anchor['x'], default=measure_notes[0])
        right = min((anchor for anchor in measure_notes if anchor['x'] >= x), key=lambda anchor: anchor['x'], default=measure_notes[-1])
        onset = float(left['onset'])
        if right['x'] > left['x']:
            onset += (x-left['x'])/(right['x']-left['x'])*(float(right['onset'])-float(left['onset']))
        measure = next((measure for part in root.findall(namespace+'part') if part.get('id') == closest['part_id']
                        for measure in part.findall(namespace+'measure') if measure.get('number') == closest['measure']), None)
        if measure is None:
            review.append({**chord, 'reason': 'measure_unmapped'})
            continue
        try:
            harmony = _harmony(chord['chord'], namespace)
        except ValueError:
            review.append({**chord, 'reason': 'unsupported_quality'})
            continue
        ET.SubElement(harmony, namespace+'offset').text = format(onset, '.6g')
        first_note = next((i for i, node in enumerate(measure) if node.tag == namespace+'note'), len(measure))
        measure.insert(first_note, harmony)
        accepted += 1
    tree.write(musicxml_path, encoding='utf-8', xml_declaration=True)
    return {'accepted': accepted, 'review': len(review), 'review_items': review}
