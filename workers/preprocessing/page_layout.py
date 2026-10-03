#!/usr/bin/env python3
"""Conservative staff/system layout artifacts for page-level review."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cv_omr_engine import ComputerVisionOmrEngine


class PageLayoutAnalyzer:
    def __init__(self) -> None:
        self.staff_detector = ComputerVisionOmrEngine()

    def analyze(self, image_path: str, json_path: str, overlay_path: str) -> dict:
        gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if gray is None or gray.size == 0:
            raise ValueError(f"Cannot decode page image: {image_path}")
        height, width = gray.shape
        detected = self.staff_detector.detect_staves(gray)
        staff_candidates = []
        for index, lines in enumerate(detected, start=1):
            ordered = sorted(float(y) for y in lines)
            gaps = np.diff(ordered)
            interline = float(np.median(gaps))
            regularity = max(0.0, 1.0 - float(np.std(gaps)) / max(interline, 1.0))
            span = gray[max(0, int(round(ordered[0]))):min(height, int(round(ordered[-1])) + 1)]
            ink_ratio = float(np.mean(span < 128)) if span.size else 0.0
            confidence = round(min(1.0, 0.75 * regularity + 0.25 * min(ink_ratio * 8, 1.0)), 3)
            staff_candidates.append({
                "id": f"staff_{index:03d}",
                "lines_y": [round(y, 2) for y in ordered],
                "interline": round(interline, 2),
                "confidence": confidence,
            })

        groups: list[list[dict]] = []
        for staff in staff_candidates:
            if not groups:
                groups.append([staff])
                continue
            previous = groups[-1][-1]
            gap = staff["lines_y"][0] - previous["lines_y"][-1]
            scale = max(float(previous["interline"]), float(staff["interline"]), 1.0)
            if gap <= 7 * scale:
                groups[-1].append(staff)
            else:
                groups.append([staff])

        systems = []
        regions = []
        if staff_candidates:
            first = staff_candidates[0]
            header_bottom = max(0, int(first["lines_y"][0] - 2 * first["interline"]))
            if header_bottom > 0:
                regions.append({"id": "header_001", "type": "header_candidate", "box": [0, 0, width, header_bottom], "confidence": 0.5})
        for index, group in enumerate(groups, start=1):
            top_staff, bottom_staff = group[0], group[-1]
            top = max(0, int(top_staff["lines_y"][0] - 2 * top_staff["interline"]))
            bottom = min(height, int(bottom_staff["lines_y"][-1] + 2 * bottom_staff["interline"]))
            confidence = round(min(staff["confidence"] for staff in group), 3)
            system_id = f"system_{index:03d}"
            systems.append({"id": system_id, "staff_ids": [staff["id"] for staff in group], "box": [0, top, width, bottom], "confidence": confidence})
            regions.append({"id": f"music_{index:03d}", "type": "music", "system_id": system_id, "box": [0, top, width, bottom], "confidence": confidence})
            footer_top = int(height * 0.92)
            next_top = (max(0, int(groups[index][0]["lines_y"][0] - 2 * groups[index][0]["interline"]))
                        if index < len(groups) else max(bottom, footer_top))
            if next_top - bottom >= 2 * bottom_staff["interline"]:
                regions.append({"id": f"lyrics_{index:03d}", "type": "lyrics_candidate", "system_id": system_id,
                                "box": [0, bottom, width, next_top], "confidence": 0.35})

        if systems and systems[-1]["box"][3] < int(height * 0.92):
            regions.append({"id": "footer_001", "type": "footer_candidate",
                            "box": [0, int(height * 0.92), width, height], "confidence": 0.3})

        warnings = [] if staff_candidates else ["STAFF_NOT_FOUND"]
        overall = round(min((staff["confidence"] for staff in staff_candidates), default=0.0), 3)
        artifact = {
            "schema_version": 1,
            "page_width": width,
            "page_height": height,
            "coordinate_system": "pixels",
            "classification": "music_page" if staff_candidates else "unknown",
            "staff_candidates": staff_candidates,
            "systems": systems,
            "regions": regions,
            "warnings": warnings,
            "confidence": {"staff_system": overall},
            "requires_review": overall < 0.65,
        }
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
        temporary = json_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as target:
            json.dump(artifact, target, ensure_ascii=False, indent=2)
        os.replace(temporary, json_path)

        overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        for region in regions:
            x1, y1, x2, y2 = region["box"]
            color = (248, 189, 56) if region["type"] == "music" else (11, 158, 245)
            cv2.rectangle(overlay, (x1, y1), (x2 - 1, y2 - 1), color, 2)
            cv2.putText(overlay, region["id"], (x1 + 4, max(15, y1 + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        os.makedirs(os.path.dirname(os.path.abspath(overlay_path)), exist_ok=True)
        if not cv2.imwrite(overlay_path, overlay):
            raise RuntimeError(f"Cannot write layout overlay: {overlay_path}")
        return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate staff/system page layout artifacts")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-overlay", required=True)
    args = parser.parse_args()
    PageLayoutAnalyzer().analyze(args.input, args.output_json, args.output_overlay)
