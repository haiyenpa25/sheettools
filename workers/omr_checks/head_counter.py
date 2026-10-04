from __future__ import annotations
import cv2
import numpy as np


def count_heads(image: np.ndarray | None, box: list[float], lines: list[float], interline: float,
                text_boxes: list[list[float]] | None = None) -> dict:
    """Count image components independently of OMR head IDs; never create notes."""
    if image is None or len(lines) != 5 or interline <= 0:
        return {'heads': None, 'head_x': [], 'components': [], 'available': False, 'reliable': False}
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    x1, y1, x2, y2 = [int(v) for v in box]
    x1, y1 = max(0, x1), max(0, y1)
    crop = gray[y1:min(gray.shape[0], y2), x1:min(gray.shape[1], x2)]
    if crop.size == 0: return count_heads(None, box, lines, interline)
    _, ink = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1, max(3, round(2*interline))), np.uint8))
    cleaned = cv2.subtract(ink, horizontal)
    hollow_candidates = []
    closed = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    hole_contours, hole_tree = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    for i, contour in enumerate(hole_contours):
        if hole_tree is None or hole_tree[0][i][3] == -1: continue
        x,y,w,h = cv2.boundingRect(contour)
        if .55*interline <= w <= 1.5*interline and .25*interline <= h <= interline and w > h:
            hollow_candidates.append({'x':x1+x+w/2,'y':y1+y+h/2,
                'box':[x1+x-2,y1+y-2,x1+x+w+2,y1+y+h+2],'hollow':True,'source':'image_enclosed_hole'})
    stems = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((max(3, round(2.5*interline)), 1), np.uint8))
    cleaned = cv2.subtract(cleaned, stems)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, hierarchy = cv2.findContours(cleaned, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    heads = []
    for index, contour in enumerate(contours):
        if hierarchy is not None and hierarchy[0][index][3] != -1: continue
        x, y, w, h = cv2.boundingRect(contour)
        cx, cy = x1+x+w/2, y1+y+h/2
        if not (.75*interline <= w <= 1.9*interline and .4*interline <= h <= 1.35*interline): continue
        area = cv2.contourArea(contour)
        if area/(w*h) < .5: continue
        holes, child = 0, hierarchy[0][index][2] if hierarchy is not None else -1
        while child != -1:
            if cv2.contourArea(contours[child]) > .03*interline*interline: holes += 1
            child = hierarchy[0][child][0]
        if holes > 1: continue
        heads.append({'x': cx, 'y': cy, 'box': [x1+x, y1+y, x1+x+w, y1+y+h],
                      'hollow': holes == 1, 'source': 'image_components'})
    for candidate in hollow_candidates:
        if not any(abs(candidate['x']-head['x']) < .6*interline and abs(candidate['y']-head['y']) < .6*interline for head in heads):
            heads.append(candidate)
    heads = [h for h in heads if not any(b[0] <= h['x'] <= b[2] and b[1] <= h['y'] <= b[3] for b in (text_boxes or []))]
    heads.sort(key=lambda head: (head['x'], head['y']))
    return {'heads': len(heads), 'head_x': [head['x'] for head in heads], 'components': heads,
            'available': True, 'reliable': True, 'source': 'image_components'}
