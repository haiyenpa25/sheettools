"""Verify Audiveris octave clefs (G_CLEF_8VB / 8VA) against the page image.

Audiveris sometimes merges the hook of a system bracket under a treble clef
and reports a low-grade G_CLEF_8VB, which drops every note by an octave. An
octave clef is kept unless (a) Audiveris graded it low and (b) the image has no
"8" glyph (an ink component with two enclosed holes) next to the clef. A
correction is applied only when it holds for every octave clef on the page, and
only to a derived MusicXML copy; the raw export stays untouched.
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
import zipfile

import cv2
import numpy as np

LOW_GRADE = float(os.getenv('CLEF_OCTAVE_MIN_GRADE', '0.35'))


def _local(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def octave_clefs(omr_path: str) -> list[dict]:
    clefs = []
    with zipfile.ZipFile(omr_path) as archive:
        for name in archive.namelist():
            if not re.fullmatch(r'sheet#\d+/sheet#\d+\.xml', name):
                continue
            root = ET.fromstring(archive.read(name))
            for clef in root.iter('clef'):
                shape = clef.get('shape', '')
                if not shape.endswith(('_8VB', '_8VA')):
                    continue
                bounds = clef.find('bounds')
                clefs.append({
                    'shape': shape,
                    'grade': float(clef.get('grade', '0') or 0),
                    'staff': clef.get('staff'),
                    'box': [int(bounds.get(k)) for k in ('x', 'y', 'w', 'h')] if bounds is not None else None,
                })
    return clefs


def has_octave_digit(gray: np.ndarray, box: list[int], interline: float) -> bool:
    """True when an '8'-like component (two holes) sits below or above the clef."""
    x, y, w, h = box
    pad = int(round(interline))
    height, width = gray.shape[:2]
    for top, bottom in ((y + h - 3 * pad, y + h + 2 * pad), (y - 2 * pad, y + 3 * pad)):
        crop = gray[max(0, top):min(height, bottom), max(0, x - pad):min(width, x + w + pad)]
        if crop.size == 0:
            continue
        _, binary = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            continue
        for index, (_, _, first_child, parent) in enumerate(hierarchy[0]):
            if parent != -1:
                continue
            holes, child = 0, first_child
            while child != -1:
                if cv2.contourArea(contours[child]) >= 0.04 * interline * interline:
                    holes += 1
                child = hierarchy[0][child][0]
            _, _, cw, ch = cv2.boundingRect(contours[index])
            if holes == 2 and ch <= 1.6 * interline and cw <= 1.4 * interline:
                return True
    return False


def correct_octave_clefs(musicxml_path: str, omr_path: str | None, image_path: str, output_path: str,
                         interline: float) -> dict:
    """Write `output_path`; drop unsupported clef octave shifts and re-pitch the notes."""
    report: dict = {'checked': 0, 'corrected': False, 'reason': 'no_octave_clef'}
    tree = ET.parse(musicxml_path)
    clefs = octave_clefs(omr_path) if omr_path and os.path.isfile(omr_path) else []
    report['checked'] = len(clefs)
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE) if clefs else None
    if clefs and gray is not None:
        unsupported = [c for c in clefs if c['grade'] < LOW_GRADE and c['box']
                       and not has_octave_digit(gray, c['box'], interline)]
        report['unsupported'] = len(unsupported)
        if len(unsupported) == len(clefs):
            shifted = 0
            for part in (node for node in tree.getroot().iter() if _local(node.tag) == 'part'):
                changes = [node for node in part.iter() if _local(node.tag) == 'clef-octave-change']
                if not changes or len({node.text for node in changes}) != 1 or changes[0].text not in ('-1', '1'):
                    continue
                delta = -int(changes[0].text)
                for clef in (node for node in part.iter() if _local(node.tag) == 'clef'):
                    for child in list(clef):
                        if _local(child.tag) == 'clef-octave-change':
                            clef.remove(child)
                for octave in (node for node in part.iter() if _local(node.tag) == 'octave'):
                    octave.text = str(int(octave.text) + delta)
                    shifted += 1
                report.update({'corrected': True, 'octave_shift': delta, 'shifted_pitches': shifted})
            report['reason'] = 'low_grade_without_octave_digit' if report['corrected'] else 'mixed_octave_changes'
        else:
            report['reason'] = 'octave_clef_supported_by_image_or_grade'
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    return report
