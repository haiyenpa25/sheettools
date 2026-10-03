"""
MusicXML Validator sử dụng music21 và xmlschema
Kiểm tra tính toàn vẹn cú pháp và nhạc lý (Time Signature, Duration, Pitches, Harmonies)
"""

import sys
import os
import json
import argparse

VALID_HARMONY_KINDS = {
    'major', 'minor', 'augmented', 'diminished', 'dominant', 'major-seventh',
    'minor-seventh', 'diminished-seventh', 'augmented-seventh', 'half-diminished',
    'major-minor', 'major-sixth', 'minor-sixth', 'dominant-ninth', 'major-ninth',
    'minor-ninth', 'dominant-11th', 'major-11th', 'minor-11th', 'dominant-13th',
    'major-13th', 'minor-13th', 'suspended-second', 'suspended-fourth',
    'Neapolitan', 'Italian', 'French', 'German', 'pedal', 'power', 'Tristan',
    'other', 'none',
}


def _local(element):
    return element.tag.rsplit('}', 1)[-1]


def _children(element, name):
    return [child for child in element if _local(child) == name]


def _child_text(element, name, default=''):
    child = next((node for node in element if _local(node) == name), None)
    return (child.text or default).strip() if child is not None else default


def _validate_structure(root, result):
    if _local(root) not in {'score-partwise', 'score-timewise'}:
        result['errors'].append('Root must be score-partwise or score-timewise')
        result['isValid'] = False
        return
    required = {'part-list', 'part'} if _local(root) == 'score-partwise' else {'part-list', 'measure'}
    present = {_local(child) for child in root}
    for name in sorted(required - present):
        result['errors'].append(f'Missing required MusicXML element: {name}')
        result['isValid'] = False

    lyric_state = {}
    for node in root.iter():
        name = _local(node)
        if name == 'harmony':
            root_node = next((child for child in node.iter() if _local(child) == 'root-step'), None)
            kind_node = next((child for child in node if _local(child) == 'kind'), None)
            if root_node is not None and (root_node.text or '').strip() not in set('ABCDEFG'):
                result['issues'].append({'type': 'harmony', 'kind': 'invalid_harmony_root', 'severity': 'error'})
            if kind_node is None or (kind_node.text or '').strip() not in VALID_HARMONY_KINDS:
                result['issues'].append({'type': 'harmony', 'kind': 'invalid_harmony_kind', 'severity': 'error'})
        elif name == 'pitch':
            octave = _child_text(node, 'octave')
            if octave and (not octave.lstrip('-').isdigit() or not 0 <= int(octave) <= 9):
                result['issues'].append({'type': 'pitch', 'kind': 'pitch_out_of_range', 'severity': 'warning'})
        elif name == 'lyric':
            number = node.get('number', '1')
            syllabic = _child_text(node, 'syllabic', 'single')
            open_chain = lyric_state.get(number, False)
            broken = (syllabic in {'middle', 'end'} and not open_chain) or (syllabic == 'begin' and open_chain)
            if broken:
                result['issues'].append({'type': 'lyric', 'kind': 'broken_syllabic_chain', 'severity': 'warning', 'verse': number})
            lyric_state[number] = syllabic in {'begin', 'middle'}
    for number, open_chain in lyric_state.items():
        if open_chain:
            result['issues'].append({'type': 'lyric', 'kind': 'broken_syllabic_chain', 'severity': 'warning', 'verse': number})

def validate_musicxml(xml_path: str) -> dict:
    result = {
        "isValid": True,
        "errors": [],
        "warnings": [],
        "issues": [],
        "metadata": {}
        ,"capabilities": {
            "xml_well_formed": "run",
            "structural_rules": "run",
            "music21_semantics": "pending",
            "xsd_schema": "not_run",
            "osmd_render": "not_run"
        }
    }

    if not os.path.exists(xml_path):
        result["isValid"] = False
        result["errors"].append(f"File not found: {xml_path}")
        return result

    # 1. Kiểm tra XML Well-formed
    try:
        try:
            from lxml import etree
            tree = etree.parse(xml_path)
        except ImportError:
            import xml.etree.ElementTree as ET
            tree = ET.parse(xml_path)
            result["warnings"].append("lxml not installed, fell back to standard xml.etree.ElementTree")
    except Exception as e:
        result["isValid"] = False
        result["errors"].append(f"Malformed XML: {str(e)}")
        return result

    root = tree.getroot()
    _validate_structure(root, result)

    # 2. Phân tích nhạc lý bằng music21
    try:
        from music21 import converter, meter
        score = converter.parse(xml_path)
        result["capabilities"]["music21_semantics"] = "run"
        
        # Trích xuất metadata
        if score.metadata:
            result["metadata"]["title"] = score.metadata.title or ""
            result["metadata"]["composer"] = score.metadata.composer or ""

        result["metadata"]["partsCount"] = len(score.parts)
        
        # Trích xuất TimeSignature chính
        main_ts = None
        for p in score.parts:
            for el in p.recurse().getElementsByClass('TimeSignature'):
                main_ts = el
                break
            if main_ts:
                break
        
        if not main_ts:
            try:
                import xml.etree.ElementTree as ET
                root = ET.parse(xml_path).getroot()
                beats = root.find('.//time/beats')
                beat_type = root.find('.//time/beat-type')
                if beats is not None and beat_type is not None:
                    main_ts = meter.TimeSignature(f"{beats.text.strip()}/{beat_type.text.strip()}")
            except Exception:
                pass

        # Kiểm tra measures và time signatures
        for i, part in enumerate(score.parts):
            measures = part.getElementsByClass('Measure')
            for m in measures:
                ts = m.timeSignature or main_ts
                if ts:
                    # Measure duration is the furthest sounding offset, not a raw
                    # sum (which double-counts chords and simultaneous voices).
                    total_duration = m.duration.quarterLength
                    expected_quarter_length = ts.barDuration.quarterLength
                    if abs(total_duration - expected_quarter_length) > 0.001 and total_duration > 0:
                        mismatch_kind = "underfull" if total_duration < expected_quarter_length else "overfull"
                        result["issues"].append({
                            "id": f"rhythm-p{i+1}-m{m.number}",
                            "part": i + 1,
                            "measure": m.number,
                            "type": "rhythm",
                            "kind": mismatch_kind,
                            "severity": "warning",
                            "found_quarters": float(total_duration),
                            "expected_quarters": float(expected_quarter_length),
                        })
                        result["warnings"].append(
                            f"Part {i+1}, Measure {m.number}: Duration mismatch [{mismatch_kind}] "
                            f"(Found {total_duration} quarters, Expected {expected_quarter_length})"
                        )

    except ImportError:
        result["warnings"].append("music21 not installed. Skipping deep musical semantic validation.")
    except Exception as e:
        result["isValid"] = False
        result["errors"].append(f"music21 could not parse the score: {str(e)}")

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MusicXML Validator")
    parser.add_argument("--xml", required=True, help="Path to MusicXML file")
    args = parser.parse_args()

    res = validate_musicxml(args.xml)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(0 if res["isValid"] else 1)
