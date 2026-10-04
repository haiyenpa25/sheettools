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
        artifact = self.analyze_image(gray)
        self.save(artifact, gray, json_path, overlay_path)
        return artifact

    def analyze_image(self, image: np.ndarray, page: int = 1, dpi: int = 300) -> dict:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
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
                "part_hint": None,
            })

        interline = float(np.median([staff['interline'] for staff in staff_candidates])) if staff_candidates else max(1, height*.02)
        binary = (gray < 128).astype(np.uint8)
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN,
                                   cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(3, int(3*interline)))))
        groups: list[list[dict]] = []
        grouping_sources: list[str] = []
        for staff in staff_candidates:
            if not groups:
                groups.append([staff])
                grouping_sources.append('gap_fallback')
                continue
            previous = groups[-1][-1]
            gap = staff["lines_y"][0] - previous["lines_y"][-1]
            scale = max(float(previous["interline"]), float(staff["interline"]), 1.0)
            y1, y2 = int(previous['lines_y'][0]), int(staff['lines_y'][-1])+1
            linked = bool(np.any(np.mean(vertical[y1:y2], axis=0) >= .9))
            if linked or gap <= 7 * scale:
                groups[-1].append(staff)
                if linked:
                    grouping_sources[-1] = 'barline'
            else:
                groups.append([staff])
                grouping_sources.append('gap_fallback')

        systems = []
        regions = []
        separators = [0]
        for upper, lower in zip(groups, groups[1:]):
            start = int(upper[-1]['lines_y'][-1] + .5*interline)
            end = int(lower[0]['lines_y'][0] - .5*interline)
            separators.append(self.white_valley(gray, start, end))
        separators.append(height)
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
            bands = {
                'above': {'box': [0, separators[index-1], width, max(separators[index-1], int(top_staff['lines_y'][0]-.5*interline))]},
                'between': [{'box': [0, int(a['lines_y'][-1]+.5*interline), width, int(b['lines_y'][0]-.5*interline)],
                             'staff_id': a['id']} for a, b in zip(group, group[1:])],
                'below': {'box': [0, int(bottom_staff['lines_y'][-1]+.5*interline), width, separators[index]],
                          'staff_id': bottom_staff['id']},
            }
            systems.append({"id": system_id, "staff_ids": [staff["id"] for staff in group], "staves": group,
                            "box": [0, top, width, bottom], "confidence": confidence, 'bands': bands,
                            'grouping_source': grouping_sources[index-1]})
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
            "schema_version": 2,
            "page": page, "width": width, "height": height, "dpi": dpi, "interline": interline,
            "text_lines": [], "masks": {},
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
        return artifact

    @staticmethod
    def white_valley(gray: np.ndarray, start: int, end: int) -> int:
        """Longest quiet run; equal runs favor the lower system."""
        if end <= start:
            return start
        projection = np.mean(gray[start:end] < 128, axis=1)
        quiet = projection <= min(.005, float(np.min(projection)) + .001)
        runs = []
        beginning = None
        for index, value in enumerate(np.append(quiet, False)):
            if value and beginning is None:
                beginning = index
            elif not value and beginning is not None:
                runs.append((beginning, index))
                beginning = None
        left, right = max(runs, key=lambda run: (run[1]-run[0], run[1]), default=(0, end-start))
        return start + (left+right)//2

    @staticmethod
    def save(artifact: dict, image: np.ndarray, json_path: str, overlay_path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
        temporary = json_path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as target:
            json.dump(artifact, target, ensure_ascii=False, indent=2)
        os.replace(temporary, json_path)

        overlay = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) if image.ndim == 2 else image.copy()
        for region in artifact['regions']:
            x1, y1, x2, y2 = region["box"]
            color = (248, 189, 56) if region["type"] == "music" else (11, 158, 245)
            cv2.rectangle(overlay, (x1, y1), (x2 - 1, y2 - 1), color, 2)
            cv2.putText(overlay, region["id"], (x1 + 4, max(15, y1 + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        colors = {'lyric': (129, 185, 16), 'chord': (248, 189, 56), 'unknown': (68, 68, 239)}
        for line in artifact.get('text_lines', []):
            x1, y1, x2, y2 = line['box']
            role = line.get('role', 'unknown')
            color = colors.get(role, (11, 158, 245))
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
            cv2.putText(overlay, role, (x1, max(12, y1-3)), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
        os.makedirs(os.path.dirname(os.path.abspath(overlay_path)), exist_ok=True)
        if not cv2.imwrite(overlay_path, overlay):
            raise RuntimeError(f"Cannot write layout overlay: {overlay_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate staff/system page layout artifacts")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-overlay", required=True)
    args = parser.parse_args()
    PageLayoutAnalyzer().analyze(args.input, args.output_json, args.output_overlay)
