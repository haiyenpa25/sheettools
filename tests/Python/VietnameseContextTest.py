#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from xml_tools.vietnamese_context import restore_liturgical_diacritics, restore_liturgical_items

text, changes = restore_liturgical_diacritics("NGOI CA TINH YEU THIEN CHUA")
assert text == "NGỢI CA TÌNH YÊU THIÊN CHÚA", text
assert len(changes) == 3
text, _ = restore_liturgical_diacritics("hat khen ngoi Chua tren troi.")
assert text == "hát khen ngợi Chúa trên trời.", text
text, changes = restore_liturgical_diacritics("ngoi nhà")
assert text == "ngoi nhà" and changes == [], "single ambiguous words must never be guessed"

items = [{"text": word, "ocr_engine": "rapidocr"} for word in "hat khen ngoi Chua tren troi.".split()]
restored = restore_liturgical_items(items)
assert [item["text"] for item in restored] == ["hát", "khen", "ngợi", "Chúa", "trên", "trời."]
assert all(item["context_changes"] for item in restored)
assert all(item["ocr_engine"].endswith("+context") for item in restored)

cross_staff = [
    {"text": "hát", "staff_index": 1}, {"text": "khen", "staff_index": 1},
    {"text": "ngoi", "staff_index": 1}, {"text": "Chua", "staff_index": 1},
    {"text": "tren", "staff_index": 1}, {"text": "troi.", "staff_index": 2},
    {"text": "Cung", "staff_index": 2}, {"text": "nhau", "staff_index": 2},
]
restore_liturgical_items(cross_staff)
assert [item["text"] for item in cross_staff] == ["hát", "khen", "ngợi", "Chúa", "trên", "trời.", "Cùng", "nhau"]
assert "context_changes" in cross_staff[5], "phrase spanning systems must retain provenance"

print("  [Python] VietnameseContextTest: PASS")
