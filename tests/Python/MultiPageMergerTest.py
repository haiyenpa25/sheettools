#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
from xml_tools.page_merger import merge_musicxml_pages
from audiveris_runner import _load_page_checkpoint, _save_page_checkpoint


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def page(page_number):
    parts, definitions = [], []
    for part_id, step, voice in (("P1", "C", "1"), ("P2", "E", "2")):
        definitions.append(f'<score-part id="{part_id}"><part-name>{part_id}</part-name></score-part>')
        measures = []
        for number in (1, 2):
            measures.append(f'<measure number="{number}"><note><pitch><step>{step}</step><octave>4</octave></pitch><duration>1</duration><voice>{voice}</voice><lyric number="1"><text>p{page_number}{part_id}</text></lyric></note></measure>')
        parts.append(f'<part id="{part_id}">{"".join(measures)}</part>')
    return f'<?xml version="1.0" encoding="UTF-8"?><score-partwise version="4.0"><part-list>{"".join(definitions)}</part-list>{"".join(parts)}</score-partwise>'


with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    page1, page2, output = folder / "p1.xml", folder / "p2.xml", folder / "merged.xml"
    page1.write_text(page(1), encoding="utf-8")
    page2.write_text(page(2), encoding="utf-8")
    require(merge_musicxml_pages([str(page1), str(page2)], str(output), "Two pages"), "merge must succeed")
    root = etree.parse(str(output)).getroot()
    parts = root.xpath("./*[local-name()='part']")
    require([part.get("id") for part in parts] == ["P1", "P2"], "both parts must survive")
    for part in parts:
        measures = part.xpath("./*[local-name()='measure']")
        require([m.get("number") for m in measures] == ["1", "2", "3", "4"], "measure sequence must be continuous")
        require(measures[2].xpath("./*[local-name()='print'][@new-page='yes']"), "page boundary must be marked")
        require(len(part.xpath(".//*[local-name()='voice']")) == 4, "voices must survive")
        require(len(part.xpath(".//*[local-name()='lyric']")) == 4, "lyrics must survive")

    checkpoint = folder / "page_checkpoint.json"
    _save_page_checkpoint(str(checkpoint), {
        "success": True,
        "raw_xml_path": str(page1),
        "xml_path": str(page2),
        "log": "large transient log",
    })
    restored = _load_page_checkpoint(str(checkpoint))
    require(restored is not None and restored["success"], "valid completed page must resume")
    require("log" not in restored, "checkpoint must not duplicate large process logs")
    page2.unlink()
    require(_load_page_checkpoint(str(checkpoint)) is None, "missing artifact must invalidate checkpoint")

print("  [Python] MultiPageMergerTest: PASS")
