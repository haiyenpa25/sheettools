"""Detected text rows relative to neural staff boxes; uncertain assignments stay visible."""
from __future__ import annotations
import copy
from collections import defaultdict


def staff_band_from_crop(region: dict, local_lines: list[float]) -> dict | None:
    if len(local_lines)!=5: return None
    lines=sorted(float(y)+int(region['box'][1]) for y in local_lines)
    return {**region,'recognition_crop_box':region['box'],'box':[region['box'][0],lines[0],region['box'][2],lines[-1]],
            'lines_y':lines,'source':'clarity_yolo_cv_lines','requires_review':True}


def refine_staff_regions(image_path: str, regions: list[dict]) -> list[dict]:
    import cv2
    from cv_omr_engine import ComputerVisionOmrEngine
    image=cv2.imread(image_path,cv2.IMREAD_GRAYSCALE)
    if image is None: raise ValueError('Cannot read staff crop')
    detector=ComputerVisionOmrEngine(); result=[]
    for region in regions:
        if region.get('source')!='clarity_yolo': result.append(region); continue
        x1,y1,x2,y2=map(int,region['box']); x1,y1=max(0,x1),max(0,y1); x2,y2=min(image.shape[1],x2),min(image.shape[0],y2)
        candidates=detector.detect_staves(image[y1:y2,x1:x2])
        if candidates:
            lines=min(candidates,key=lambda line:abs((line[0]+line[-1])/2-(y2-y1)/2))
            refined=staff_band_from_crop({**region,'box':[x1,y1,x2,y2]},lines)
            if refined: result.append(refined)
        else:
            result.append({**region,'type':'unresolved_staff_region','requires_review':True,
                           'warning':'STAFF_LINES_NOT_CONFIRMED_INSIDE_YOLO_CROP'})
    return result


def classify_rows(rows: list[list[dict]], regions: list[dict]) -> list[dict]:
    from xml_tools.text_roles import classify_text_line, is_chord
    staves = sorted((r for r in regions if r['type'] == 'staff'), key=lambda r: (r['box'][1], r['box'][0]))
    result = []; verses: dict[int, int] = defaultdict(int); previous_rows: dict[int, list[float]] = {}
    for row in sorted(rows, key=lambda r: min(w['box'][1] for w in r)):
        box = [min(w['box'][0] for w in row), min(w['box'][1] for w in row),
               max(w['box'][2] for w in row), max(w['box'][3] for w in row)]
        text = ' '.join(w['text'] for w in row); cy = (box[1]+box[3])/2
        candidates = []
        for index, staff in enumerate(staves):
            sx1, sy1, sx2, sy2 = staff['box']; scale = max(sy2-sy1, 1)
            if min(box[2], sx2) <= max(box[0], sx1): continue
            last = previous_rows.get(index)
            connected = last is not None and -.3*min(last[3]-last[1],box[3]-box[1]) <= box[1]-last[3] <= 1.6*max(last[3]-last[1],box[3]-box[1],1)
            before_next_staff = not any(s['box'][1]>sy2 and s['box'][1]<box[3] for s in staves)
            if box[1] >= sy2 and before_next_staff and (cy-sy2 <= 2*scale or connected):
                candidates.append((cy-sy2, index))
        role, staff_index, verse = 'unknown', None, None
        # Single Em is a chord only when positioned above a nearby staff.
        above = any(0 <= s['box'][1]-box[3] <= max(s['box'][3]-s['box'][1], 1) for s in staves)
        chord_ratio=sum(is_chord(w['text']) for w in row)/max(len(row),1)
        if above and chord_ratio>=.7: role = 'chord'
        elif candidates and any(c.isalpha() for c in text):
            candidates.sort(); staff_index = candidates[0][1]
            role = classify_text_line(text, 'below')['role']
            if role == 'lyric':
                verses[staff_index] += 1; verse = verses[staff_index]; previous_rows[staff_index]=box
        result.append({'text': text, 'box': box, 'role': role, 'staff_index': staff_index,
            'verse_number': verse, 'words': row, 'needs_review': True,
            'source': 'detected_text_and_neural_staff', 'assignment_ambiguous': len(candidates)>1})
    return result


def propose_alignment(words: list[dict], positions: list[dict], regions: list[dict]) -> list[dict]:
    """Use existing monotonic DP, retaining every match as an unverified proposal."""
    from xml_tools.lyrics_aligner import _align_group
    staves = sorted((r for r in regions if r['type']=='staff'), key=lambda r:(r['box'][1],r['box'][0]))
    notes: dict[int, list[dict]] = defaultdict(list)
    for position in positions:
        x, y = position['position']
        choices = [(abs(y-(s['box'][1]+s['box'][3])/2), i) for i,s in enumerate(staves)
                   if s['box'][0] <= x <= s['box'][2] and s['box'][1]-(s['box'][3]-s['box'][1])/2 <= y <= s['box'][3]+(s['box'][3]-s['box'][1])/2]
        if choices:
            _, index = min(choices)
            notes[index].append({**position, 'x': x, 'anchor_source': 'omr_pixel',
                                 'interline': max((staves[index]['box'][3]-staves[index]['box'][1])/4, 1)})
    result = copy.deepcopy(words); groups: dict[tuple[int,int], list[dict]] = defaultdict(list)
    for word in result:
        word['alignment']={'status':'review','requires_review':True,'reason':'no_neural_note_position'}
        groups[(word['staff_index'],word['verse_number'])].append(word)
    for (staff, verse), row in groups.items():
        row.sort(key=lambda w:w['x']); candidates=sorted(notes[staff],key=lambda n:n['x'])
        if not candidates: continue
        for wi, ni, error in _align_group(row,candidates):
            row[wi]['alignment']={'status':'proposed','note_id':candidates[ni]['id'],
                'spatial_error_interlines':round(error,4),'source':'homr_attention',
                'approximate':True,'requires_review':True}
    return result


def detect_text(image_path: str, regions: list[dict], page: int) -> dict:
    import cv2
    from xml_tools.vietnamese_universal_ocr import VietnameseUniversalOcrEngine, split_ocr_line_item
    from xml_tools.text_roles import cluster_text_rows
    image=cv2.imread(image_path)
    if image is None: raise ValueError('Cannot read comparison page')
    engine=VietnameseUniversalOcrEngine(); detector=engine.get_rapid_ocr()
    if detector is None: raise RuntimeError('RapidOCR detector is unavailable')
    # Detect text per staff neighborhood to avoid shrinking a full A4 page until marks disappear.
    detected,_=detector(image); detected=list(detected or []); tokens=[]
    staves=sorted((r for r in regions if r['type']=='staff'),key=lambda r:r['box'][1])
    windows=[]
    for index,staff in enumerate(staves):
        sy2=int(staff['box'][3]); end=int(staves[index+1]['box'][1]) if index+1<len(staves) else image.shape[0]
        windows.append((sy2,end))
    detected=[item for item in detected if not any(start<=sum(p[1] for p in item[0])/4<end for start,end in windows)]
    for start,end in windows:
        local,_=detector(image[max(0,start):min(image.shape[0],end)])
        for points,text,confidence in local or []:
            detected.append(([[float(p[0]),float(p[1])+start] for p in points],text,confidence))
    for points,text,confidence in detected:
        x1=max(0,int(min(p[0] for p in points))); x2=min(image.shape[1],int(max(p[0] for p in points)))
        y1=max(0,int(min(p[1] for p in points))-2); y2=min(image.shape[0],int(max(p[1] for p in points))+2)
        item={'text':text,'raw_ocr':text,'box':[x1,y1,x2,y2],'cx':(x1+x2)/2,'cy':(y1+y2)/2,
              'h':y2-y1,'w':x2-x1,'score':float(confidence),
              'ocr_candidates':[{'text':text,'engine':'rapidocr','confidence':float(confidence)}]}
        tokens.extend(split_ocr_line_item(item,image))
    rows=classify_rows(cluster_text_rows(tokens),regions)
    words=[]
    for row in rows:
        if row['role']!='lyric': continue
        engine.fuse_lyric_line(image,row['words'])
        row['text']=' '.join(w['text'] for w in row['words'])
        for token in row['words']:
            if not any(c.isalpha() for c in token['text']): continue
            words.append({**token,'id':f'p{page}_w{len(words)+1}','page':page,
                          'staff_index':row['staff_index'],'verse_number':row['verse_number'],
                          'x':token['cx'],'confidence':token['score'],'needs_review':True})
    return {'schema_version':2,'page':page,'rows':rows,'words':words,'requires_review':True,
            'algorithm':'neural_staff_detected_text_v1','coordinate_system':'pixels'}
