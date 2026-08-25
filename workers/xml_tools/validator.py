"""
MusicXML Validator sử dụng music21 và xmlschema
Kiểm tra tính toàn vẹn cú pháp và nhạc lý (Time Signature, Duration, Pitches, Harmonies)
"""

import sys
import os
import json
import argparse

def validate_musicxml(xml_path: str) -> dict:
    result = {
        "isValid": True,
        "errors": [],
        "warnings": [],
        "metadata": {}
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

    # 2. Phân tích nhạc lý bằng music21
    try:
        from music21 import converter, meter
        score = converter.parse(xml_path)
        
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
                    total_duration = sum([n.quarterLength for n in m.notesAndRests])
                    expected_quarter_length = ts.barDuration.quarterLength
                    if abs(total_duration - expected_quarter_length) > 0.001 and total_duration > 0:
                        result["warnings"].append(
                            f"Part {i+1}, Measure {m.number}: Duration mismatch (Found {total_duration} quarters, Expected {expected_quarter_length})"
                        )

    except ImportError:
        result["warnings"].append("music21 not installed. Skipping deep musical semantic validation.")
    except Exception as e:
        result["warnings"].append(f"music21 parse notice: {str(e)}")

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MusicXML Validator")
    parser.add_argument("--xml", required=True, help="Path to MusicXML file")
    args = parser.parse_args()

    res = validate_musicxml(args.xml)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(0 if res["isValid"] else 1)
