from __future__ import annotations
import cv2
import numpy as np


def scan_ink(image: np.ndarray | None, box: list[float], explained: list[list[float]], interline: float, reader=None) -> list[dict]:
    if image is None: return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    x1,y1,x2,y2 = [int(v) for v in box]; x1,y1 = max(0,x1),max(0,y1)
    crop = gray[y1:min(y2,gray.shape[0]),x1:min(x2,gray.shape[1])]
    if crop.size == 0: return []
    ink = (crop < 150).astype(np.uint8)*255
    # Remove thin bracket strokes, then join letters horizontally.
    long_lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1,max(3,round(3*interline))),np.uint8))
    ink = cv2.subtract(ink,long_lines)
    blobs = cv2.dilate(ink,np.ones((3,max(3,round(.6*interline))),np.uint8))
    count, labels, stats, centers = cv2.connectedComponentsWithStats(blobs)
    result = []
    for _, (x,y,w,h,area), (cx,cy) in zip(range(1,count),stats[1:],centers[1:]):
        bounds = [x1+int(x),y1+int(y),x1+int(x+w),y1+int(y+h)]
        if area < .15*interline**2 or h < .5*interline or h > 4*interline: continue
        if any(bounds[0] < b[2]+.4*interline and bounds[2] > b[0]-.4*interline and
               bounds[1] < b[3]+.3*interline and bounds[3] > b[1]-.3*interline for b in explained): continue
        item={'box': bounds, 'source': 'above_staff_ink', 'needs_review': True}
        if reader:
            reading=reader(image,bounds)
            if reading: item.update(candidate_chord=reading[0],ocr_confidence=reading[1],candidate_source='padded_crop_ocr')
        result.append(item)
    return result
