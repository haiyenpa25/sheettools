#!/usr/bin/env python3
"""Lossless multi-page, multi-part MusicXML merger."""
from __future__ import annotations

import argparse
import copy
import os
import shutil
import sys
from lxml import etree


def _children(element, name):
    return element.xpath(f"./*[local-name()='{name}']")


def _first(element, name):
    values = _children(element, name)
    return values[0] if values else None


def _qualified_like(element, name):
    namespace = etree.QName(element).namespace
    return f"{{{namespace}}}{name}" if namespace else name


def _mark_new_page(measure):
    prints = _children(measure, "print")
    if prints:
        prints[0].set("new-page", "yes")
    else:
        measure.insert(0, etree.Element(_qualified_like(measure, "print"), {"new-page": "yes"}))


def _definitions(root):
    part_list = _first(root, "part-list")
    if part_list is None:
        return {}
    return {item.get("id"): item for item in _children(part_list, "score-part") if item.get("id")}


def merge_musicxml_pages(xml_files: list[str], output_file: str, title: str | None = None) -> bool:
    """Merge pages without converting their musical content through another model."""
    if not xml_files or any(not os.path.isfile(path) for path in xml_files):
        return False
    if len(xml_files) == 1:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        shutil.copy2(xml_files[0], output_file)
        return True

    try:
        parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False, no_network=True)
        trees = [etree.parse(path, parser) for path in xml_files]
        roots = [tree.getroot() for tree in trees]
        if any(etree.QName(root).localname != "score-partwise" for root in roots):
            raise ValueError("Only score-partwise MusicXML can be merged safely")

        merged_tree = copy.deepcopy(trees[0])
        merged_root = merged_tree.getroot()
        merged_parts = {part.get("id"): part for part in _children(merged_root, "part") if part.get("id")}
        counters = {part_id: len(_children(part, "measure")) for part_id, part in merged_parts.items()}
        merged_part_list = _first(merged_root, "part-list")

        if title:
            work = _first(merged_root, "work")
            if work is None:
                work = etree.Element(_qualified_like(merged_root, "work"))
                merged_root.insert(0, work)
            work_title = _first(work, "work-title")
            if work_title is None:
                work_title = etree.SubElement(work, _qualified_like(work, "work-title"))
            work_title.text = title

        for page_index, page_root in enumerate(roots[1:], start=2):
            page_definitions = _definitions(page_root)
            page_parts = {part.get("id"): part for part in _children(page_root, "part") if part.get("id")}
            if not page_parts:
                raise ValueError(f"Page {page_index} contains no parts")
            for part_id, page_part in page_parts.items():
                if part_id not in merged_parts:
                    if merged_part_list is None or part_id not in page_definitions:
                        raise ValueError(f"Page {page_index} introduces undefined part {part_id}")
                    merged_part_list.append(copy.deepcopy(page_definitions[part_id]))
                    new_part = etree.Element(_qualified_like(page_part, "part"), {"id": part_id})
                    merged_root.append(new_part)
                    merged_parts[part_id] = new_part
                    counters[part_id] = 0
                measures = _children(page_part, "measure")
                for measure_index, measure in enumerate(measures):
                    cloned = copy.deepcopy(measure)
                    counters[part_id] += 1
                    cloned.set("number", str(counters[part_id]))
                    if measure_index == 0:
                        _mark_new_page(cloned)
                    merged_parts[part_id].append(cloned)

        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        merged_tree.write(output_file, encoding="UTF-8", xml_declaration=True, pretty_print=False)
        return True
    except Exception as error:
        print(f"[PageMerger] Merge failed: {error}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Lossless multi-page MusicXML merger")
    parser.add_argument("--inputs", "-i", nargs="+", required=True)
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--title", "-t", default="Bản Nhạc Hoàn Chỉnh")
    args = parser.parse_args()
    sys.exit(0 if merge_musicxml_pages(args.inputs, args.output, args.title) else 1)


if __name__ == "__main__":
    main()
