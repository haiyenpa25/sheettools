from __future__ import annotations
import re
import cv2
import numpy as np


def detect_tuplets(image: np.ndarray | None, box: list[float], lines: list[float], interline: float,
                   text_lines: list[dict]) -> list[dict]:
    marks = []
    candidates = list(text_lines)
    if image is not None and lines:
        import pytesseract
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        x1, x2 = max(0, int(box[0])), min(gray.shape[1], int(box[2]))
        y1, y2 = max(0, int(lines[0]-3*interline)), min(gray.shape[0], int(lines[-1]+3*interline))
        crop = gray[y1:y2, x1:x2].copy()
        # Staff lines cannot be interpreted as digits; retain bracket/number ink above.
        for y in lines:
            cv2.line(crop, (0, int(y-y1)), (crop.shape[1]-1, int(y-y1)), 255, 3)
        try:
            data = pytesseract.image_to_data(crop, lang='eng', config='--psm 11', output_type=pytesseract.Output.DICT)
            for i, text in enumerate(data['text']):
                if re.fullmatch(r'[357]', text.strip()):
                    x, y = x1+data['left'][i], y1+data['top'][i]
                    candidates.append({'text': text, 'box': [x, y, x+data['width'][i], y+data['height'][i]], 'source': 'image_tesseract'})
            # A sloping bracket often makes whole-band OCR merge the digit into a line.
            digit_band = crop[:max(0,int(lines[0]-.4*interline-y1)),:]
            ink = (digit_band < 150).astype(np.uint8)*255
            count, _, stats, _ = cv2.connectedComponentsWithStats(ink)
            for a,b,w,h,area in stats[1:]:
                if not (.3*interline <= w <= 1.3*interline and .6*interline <= h <= 2*interline): continue
                pad = max(4, round(.4*interline))
                digit = cv2.copyMakeBorder(digit_band[b:b+h,a:a+w],pad,pad,pad,pad,cv2.BORDER_CONSTANT,value=255)
                digit = cv2.resize(digit,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
                text = pytesseract.image_to_string(digit,lang='eng',config='--psm 10 -c tessedit_char_whitelist=357').strip()
                if re.fullmatch('[357]',text):
                    candidates.append({'text':text,'box':[x1+int(a),y1+int(b),x1+int(a+w),y1+int(b+h)],'source':'image_digit_crop'})
        except (RuntimeError, OSError): pass
    for item in candidates:
        bounds = item.get('box', [])
        if not re.fullmatch(r'[357]', str(item.get('text', '')).strip()) or len(bounds) != 4 or not lines: continue
        x, y = (bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2
        if not (box[0] <= x < box[2] and lines[0]-3*interline <= y <= lines[-1]+3*interline): continue
        if y >= lines[0]-.3*interline: continue
        if any(abs(mark['x']-x) < .6*interline and abs(mark['y']-y) < interline for mark in marks): continue
        span = None
        if image is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
            top, bottom = max(0, int(y-interline)), min(gray.shape[0], int(y+interline))
            left, right = max(0, int(box[0])), min(gray.shape[1], int(box[2]))
            ink = (gray[top:bottom, left:right] < 128).astype(np.uint8)*255
            segments = cv2.HoughLinesP(ink, 1, np.pi/180, max(10, int(interline)),
                minLineLength=2*interline, maxLineGap=2*interline)
            if segments is not None:
                spans = [(min(int(a),int(c))+left, max(int(a),int(c))+left) for a,b,c,d in segments.reshape(-1,4) if abs(b-d) <= .12*abs(a-c) and min(a,c)+left-interline <= x <= max(a,c)+left+interline]
                if spans: span = list(max(spans, key=lambda s: s[1]-s[0]))
        if item.get('source') == 'image_digit_crop' and (span is None or span[1]-span[0]<4*interline or not span[0]+.7*interline<x<span[1]-.7*interline): continue
        marks.append({'x': x, 'y': y, 'number': int(item['text']), 'bracket_span': span,
                      'source': item.get('source', 'page_ocr'), 'box': bounds})
    return marks
