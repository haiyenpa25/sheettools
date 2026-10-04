"""Read Audiveris 5.11 geometry; reject ambiguous measure mappings."""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
import xml.etree.ElementTree as ET
import zipfile


class OmrAnchorReader:
    def read(self, omr_path: str, musicxml_path: str, page_model: dict | None = None) -> dict:
        xml = ET.parse(musicxml_path).getroot()
        # Strip namespaces on a private DOM for uniform lookup.
        for node in xml.iter():
            node.tag = node.tag.rsplit('}', 1)[-1]
        xml_parts = {part.get('id'): part for part in xml.findall('part')}
        anchors, fallback = [], []
        offsets: dict[str, int] = defaultdict(int)
        with zipfile.ZipFile(omr_path) as archive:
            if any(info.file_size > 64*1024*1024 for info in archive.infolist() if info.filename.endswith('.xml')):
                raise ValueError('OMR XML member exceeds 64 MiB')
            book = ET.fromstring(archive.read('book.xml'))
            version = book.get('software-version', '')
            if version != '5.11.0':
                raise ValueError(f'Unsupported Audiveris schema: {version}; expected 5.11.0')
            sheets = sorted((name for name in archive.namelist() if name.endswith('.xml') and name != 'book.xml'),
                            key=lambda name: int(name.split('/')[0].split('#')[-1]))
            for page, name in enumerate(sheets, 1):
                sheet = ET.fromstring(archive.read(name))
                interline = float(sheet.find('scale/interline').get('main'))
                book_systems = book.findall(f"sheet[@number='{page}']/page/system")
                systems = sheet.findall('page/system')
                for system_index, system in enumerate(systems):
                    inters = {node.get('id'): node for node in system.findall('sig/inters/*')}
                    children: dict[str, list[str]] = defaultdict(list)
                    for relation in system.findall('sig/relations/relation'):
                        if relation.find('containment') is not None:
                            children[relation.get('source')].append(relation.get('target'))
                    stacks = system.findall('stack')
                    logical_parts = book_systems[system_index].findall('part') if system_index < len(book_systems) else []
                    for part_index, part in enumerate(system.findall('part')):
                        logical_id = logical_parts[part_index].get('logical-id') if part_index < len(logical_parts) else None
                        part_id = 'P'+str(logical_id) if logical_id else None
                        xml_part = xml_parts.get(part_id)
                        if xml_part is None:
                            fallback.append({'system': system.get('id'), 'reason': 'logical_part_unmapped'})
                            continue
                        xml_measures = xml_part.findall('measure')
                        divisions = 1
                        # Divisions can persist across system boundaries.
                        for measure in xml_measures[:offsets[part_id]]:
                            divisions = int(measure.findtext('attributes/divisions', str(divisions)))
                        for measure_index, omr_measure in enumerate(part.findall('measure')):
                            index = offsets[part_id] + measure_index
                            if index >= len(xml_measures):
                                fallback.append({'part_id': part_id, 'system': system.get('id'), 'reason': 'measure_unmapped'})
                                continue
                            measure = xml_measures[index]
                            divisions = int(measure.findtext('attributes/divisions', str(divisions)))
                            groups: dict[str, list[list[tuple[int, ET.Element]]]] = defaultdict(list)
                            for note_index, note in enumerate(measure.findall('note'), 1):
                                if note.find('grace') is not None:
                                    continue
                                voice = note.findtext('voice', '1')
                                if note.find('chord') is not None and groups[voice]:
                                    groups[voice][-1].append((note_index, note))
                                else:
                                    groups[voice].append([(note_index, note)])
                            pending = []
                            valid = True
                            stack = stacks[measure_index] if measure_index < len(stacks) else None
                            slots = {slot.get('id'): slot for slot in stack.findall('slot')} if stack is not None else {}
                            for voice in omr_measure.findall('voice'):
                                entries = [entry for entry in voice.findall('slots/entry') if entry.find('value').get('status') == 'BEGIN']
                                note_groups = groups.get(voice.get('id'), [])
                                if len(entries) != len(note_groups):
                                    valid = False
                                    break
                                for entry, note_group in zip(entries, note_groups):
                                    chord_id = entry.find('value').get('chord')
                                    heads = [inters[ref] for ref in children.get(chord_id, []) if ref in inters and inters[ref].tag == 'head']
                                    pitched = [(number, note) for number, note in note_group if note.find('pitch') is not None]
                                    if len(heads) != len(pitched):
                                        valid = False
                                        break
                                    heads.sort(key=lambda head: -float(head.find('bounds').get('y')))
                                    slot = slots.get(entry.findtext('key'))
                                    onset = float(Fraction(slot.get('time-offset', '0')) * 4 * divisions) if slot is not None else None
                                    for head, (note_index, note) in zip(heads, pitched):
                                        bounds = head.find('bounds')
                                        x, y, width, height = [float(bounds.get(key)) for key in ('x', 'y', 'w', 'h')]
                                        center_y = y+height/2
                                        staff_index = int(head.get('staff', '1'))-1
                                        if page_model and page_model.get('staff_candidates'):
                                            staff_index = min(range(len(page_model['staff_candidates'])), key=lambda i:
                                                abs(center_y - sum(page_model['staff_candidates'][i]['lines_y'])/5))
                                        pending.append({'id': f"{part_id}:{measure.get('number')}:{note_index}",
                                            'part_id': part_id, 'measure': measure.get('number'), 'note_index': note_index,
                                            'voice': voice.get('id'), 'page': page, 'staff_index': staff_index,
                                            'system_id': f"system_{system_index+1:03d}", 'x': x+width/2, 'y': center_y,
                                            'box': [x, y, x+width, y+height], 'interline': interline,
                                            'onset': onset, 'divisions': divisions, 'anchor_source': 'omr_pixel',
                                            'omr_head_id': head.get('id'),
                                            'measure_box': [float(stack.get('left')), float(stack.get('right'))] if stack is not None else None})
                            active_voices = {voice.get('id') for voice in omr_measure.findall('voice') if voice.findall('slots/entry')}
                            if valid and set(groups) == active_voices:
                                anchors.extend(pending)
                            else:
                                fallback.append({'part_id': part_id, 'measure': measure.get('number'),
                                                 'system': system.get('id'), 'anchor_source': 'musicxml_fallback',
                                                 'reason': 'voice_or_chord_count_mismatch'})
                        offsets[part_id] += len(part.findall('measure'))
        return {'schema_version': 1, 'audiveris_version': version, 'coordinate_system': 'pixels',
                'anchors': anchors, 'fallback_measures': fallback}
