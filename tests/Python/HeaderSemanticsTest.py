#!/usr/bin/env python3
"""Regression test for semantic hymn-page header parsing."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from xml_tools.document_layout import analyze_header_semantics


def item(text, box):
    x1, y1, x2, y2 = box
    return {"text": text, "raw_ocr": text, "box": box, "cx": (x1+x2)/2, "cy": (y1+y2)/2, "w": x2-x1, "h": y2-y1, "score": .95}


result = analyze_header_semantics([
    item("Tôn Vinh Chúa Hằng Hữu", [230, 120, 847, 183]),
    item('“Này, sự yêu thương ở tại đây: ấy chẳng phải chúng ta đã yêu Đức Chúa Trời,', [362, 251, 2114, 327]),
    item('nhưng Ngài đã yêu chúng ta,', [919, 327, 1562, 390]),
    item('và sai Con Ngài làm của lễ chuộc tội chúng ta.” — I Giăng 4:10', [539, 396, 1940, 454]),
    item("57", [324, 496, 442, 610]),
    item("NGỢI CA TÌNH YÊU THIÊN CHÚA", [539, 484, 1941, 594]),
    item("J.H. Fillmore", [1862, 643, 2140, 696]),
    item("D", [995, 710, 1034, 753]),
    item("Em7", [1462, 703, 1555, 755]),
], page_width=2481, first_staff_top=785)

assert result["collection"]["text"] == "Tôn Vinh Chúa Hằng Hữu"
assert result["hymn_number"]["text"] == "57"
assert result["title"]["text"] == "NGỢI CA TÌNH YÊU THIÊN CHÚA"
assert result["composer"]["text"] == "J.H. Fillmore"
assert "sự yêu thương" in result["description"]["text"]
assert result["scripture_reference"]["text"] == "I Giăng 4:10"
assert all(region["text"] not in {"D", "Em7"} for region in result["semantic_regions"])

print("  [Python] HeaderSemanticsTest: PASS")
