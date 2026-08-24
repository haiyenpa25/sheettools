"""
MusicXML Fast Patcher sử dụng lxml.etree
Cho phép sửa Lyric, Harmony, Note mà không phá vỡ cấu trúc và layout gốc của file MusicXML.
"""

import sys
import os
import json
import argparse

def patch_lyric(xml_path: str, part_id: str, measure_num: int, note_index: int, verse_num: int, new_text: str, syllabic: str = "single") -> bool:
    try:
        from lxml import etree
        use_lxml = True
    except ImportError:
        import xml.etree.ElementTree as etree
        use_lxml = False

    if not os.path.exists(xml_path):
        print(f"ERROR: XML file not found: {xml_path}")
        return False

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(xml_path, parser)
    root = tree.getroot()

    # Tìm Measure
    xpath_measure = f"//part[@id='{part_id}']/measure[@number='{measure_num}']"
    measures = root.xpath(xpath_measure)
    if not measures:
        print(f"ERROR: Measure {measure_num} in part {part_id} not found.")
        return False

    measure = measures[0]
    notes = measure.xpath("./note[not(rest)]")
    if not notes or note_index >= len(notes):
        print(f"ERROR: Note index {note_index} not found in measure {measure_num}.")
        return False

    target_note = notes[note_index]
    
    # Tìm hoặc tạo thẻ lyric theo verse
    existing_lyrics = target_note.xpath(f"./lyric[@number='{verse_num}']")
    if existing_lyrics:
        lyric_node = existing_lyrics[0]
        text_node = lyric_node.xpath("./text")
        if text_node:
            text_node[0].text = new_text
        else:
            t = etree.SubElement(lyric_node, "text")
            t.text = new_text
        
        s_node = lyric_node.xpath("./syllabic")
        if s_node:
            s_node[0].text = syllabic
        else:
            s = etree.SubElement(lyric_node, "syllabic")
            s.text = syllabic
    else:
        # Thêm mới
        lyric_node = etree.SubElement(target_note, "lyric", number=str(verse_num))
        s = etree.SubElement(lyric_node, "syllabic")
        s.text = syllabic
        t = etree.SubElement(lyric_node, "text")
        t.text = new_text

    tree.write(xml_path, encoding="utf-8", xml_declaration=True, pretty_print=True)
    print(f"SUCCESS: Patched lyric verse {verse_num} at measure {measure_num} -> '{new_text}'")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MusicXML Fast Patcher")
    parser.add_argument("--xml", required=True, help="Path to MusicXML file")
    parser.add_argument("--action", choices=["patch-lyric", "patch-harmony", "patch-note"], required=True)
    parser.add_argument("--payload", required=True, help="JSON string of patch payload")
    args = parser.parse_args()

    payload = json.loads(args.payload)

    if args.action == "patch-lyric":
        ok = patch_lyric(
            xml_path=args.xml,
            part_id=payload.get("partId", "P1"),
            measure_num=payload["measureNumber"],
            note_index=payload.get("noteIndex", 0),
            verse_num=payload.get("verseNumber", 1),
            new_text=payload["text"],
            syllabic=payload.get("syllabic", "single")
        )
        sys.exit(0 if ok else 1)
