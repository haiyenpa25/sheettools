from __future__ import annotations
import copy
import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from statistics import median
import cv2
from .head_counter import count_heads
from .tuplet_marks import detect_tuplets
from .ink_scan import scan_ink
from .decide import decide

STEPS = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}


def _beats(measure: ET.Element, divisions: int) -> float:
    cursor = end = 0
    for node in measure:
        duration = int(node.findtext('duration','0'))
        if node.tag == 'backup': cursor -= duration
        elif node.tag == 'forward': cursor += duration; end = max(end,cursor)
        elif node.tag == 'note' and node.find('chord') is None and node.find('grace') is None:
            cursor += duration; end = max(end,cursor)
    return end/divisions


def build_ledger(xml_path: str, anchor_model: dict, lyrics: dict, page_model: dict,
                 image_path: str | None, page: int = 1, clef_report: dict | None = None, chord_reader=None) -> dict:
    root = ET.parse(xml_path).getroot()
    for node in root.iter(): node.tag = node.tag.rsplit('}',1)[-1]
    image = cv2.imread(image_path,cv2.IMREAD_GRAYSCALE) if image_path else None
    anchors = anchor_model.get('anchors',[]); words = lyrics.get('words',[])
    text_lines = page_model.get('text_lines',[]); staves = page_model.get('staff_candidates',[])
    entries = []
    for part in root.findall('part'):
        divisions, expected, fifths = 1, None, 0
        measures = part.findall('measure'); rhythm = []
        for m in measures:
            divisions = int(m.findtext('attributes/divisions',str(divisions)))
            time = m.find('attributes/time')
            if time is not None:
                expected = sum(int(v) for v in time.findtext('beats','4').split('+'))*4/int(time.findtext('beat-type','4'))
            rhythm.append((_beats(m,divisions),expected))
        pickup_pair = bool(rhythm and rhythm[0][1] and rhythm[0][0] < rhythm[0][1] and
                           abs(rhythm[0][0]+rhythm[-1][0]-rhythm[0][1]) < .001)
        divisions, expected = 1, None
        for index, m in enumerate(measures):
            number = m.get('number',str(index+1)); part_id = part.get('id','P1')
            divisions = int(m.findtext('attributes/divisions',str(divisions)))
            fifths = int(m.findtext('attributes/key/fifths',str(fifths)))
            if m.find('attributes/time') is not None:
                expected = sum(int(v) for v in m.findtext('attributes/time/beats','4').split('+'))*4/int(m.findtext('attributes/time/beat-type','4'))
            local = [a for a in anchors if a['part_id']==part_id and str(a['measure'])==number]
            staff_ids = sorted({a.get('staff_index',0) for a in local}) or [0]
            for staff_index in staff_ids:
                notes_here = [a for a in local if a.get('staff_index',0)==staff_index]
                lines = staves[staff_index]['lines_y'] if staff_index < len(staves) else []
                interline = float(staves[staff_index].get('interline',20)) if staff_index < len(staves) else float(notes_here[0].get('interline',20)) if notes_here else 20
                if not lines:
                    center = median([a['y'] for a in notes_here]) if notes_here else 100
                    lines = [center+(i-2)*interline for i in range(5)]
                span = next((a['measure_box'] for a in notes_here if a.get('measure_box')),None)
                geometry_known = span is not None
                if span is None:
                    # Fallback is deliberately marked unverified, never accepted on guessed geometry.
                    xs = [a['x'] for a in notes_here]
                    span = [min(xs)-interline,max(xs)+interline] if xs else [0,page_model.get('width',100)]
                system_id = notes_here[0].get('system_id') if notes_here else None
                measure_words = [w for w in words if w.get('staff_index',0)==staff_index and
                    span[0] <= (w['box'][0]+w['box'][2])/2 < span[1]]
                counts = defaultdict(int)
                for w in measure_words:
                    if any(c.isalpha() for c in w.get('text','')): counts[str(w.get('verse_number',1))] += 1
                head_box = [span[0],lines[0]-4*interline,span[1],lines[-1]+4*interline]
                text_boxes = [line['box'] for line in text_lines if line.get('role') in
                    ('chord','lyric','title','composer','translator','collection','footer','verse_marker')]
                image_evidence = count_heads(image,head_box,lines,interline,text_boxes)
                image_evidence['reliable'] = bool(geometry_known and image is not None and page_model.get('quality',{}).get('grade') != 'poor')
                image_evidence['tuplet_marks'] = detect_tuplets(image,head_box,lines,interline,text_lines)
                image_evidence['available'] = bool(image_evidence['available'] and geometry_known)
                box = [span[0],lines[0]-4*interline,span[1],max([lines[-1]+4*interline]+[w['box'][3]+interline for w in measure_words])]
                note_indexes = {int(a['note_index']) for a in notes_here}
                all_notes = m.findall('note')
                selected = [n for i,n in enumerate(all_notes,1) if i in note_indexes] if local else all_notes
                pitched = [n for n in selected if n.find('pitch') is not None and n.find('grace') is None]
                primary = next((n.findtext('voice','1') for n in pitched), '1')
                sung = [n for n in pitched if n.findtext('voice','1')==primary and n.find('chord') is None and
                        not any(t.get('type')=='stop' for t in n.findall('tie'))]
                slur_count = 0; active = False
                for n in sung:
                    if active: slur_count += 1
                    for slur in n.findall('notations/slur'):
                        if slur.get('type')=='start': active=True
                        elif slur.get('type')=='stop': active=False
                key_classes = {(7*fifths+s)%12 for s in (0,2,4,5,7,9,11,3,8,10)}
                chord_values, outside = [], []
                for h in m.findall('harmony'):
                    step = h.findtext('root/root-step','C'); alter = int(h.findtext('root/root-alter','0'))
                    label = step+('b' if alter == -1 else '#' if alter==1 else '')+('m' if h.findtext('kind')=='minor' else '')
                    chord_values.append(label)
                    if (STEPS.get(step,0)+alter)%12 not in key_classes: outside.append(label)
                explained = [line['box'] for line in text_lines if line.get('role') in ('chord','tempo','direction','key_info','tuplet_mark')]
                explained += [mark['box'] for mark in image_evidence['tuplet_marks'] if mark.get('box')]
                explained += [[mark['bracket_span'][0],mark['y']-.25*interline,mark['bracket_span'][1],mark['y']+.25*interline]
                              for mark in image_evidence['tuplet_marks'] if mark.get('bracket_span')]
                above = [span[0],lines[0]-4*interline,span[1],lines[0]-.6*interline]
                # High notes connected to the staff are explained by head/stem geometry.
                explained += [[h['box'][0]-.25*interline,h['box'][1]-3*interline,h['box'][2]+.25*interline,h['box'][3]]
                              for h in image_evidence['components'] if h['y'] <= lines[0]]
                first_on_staff=not any(row['staff_index']==staff_index and row['part_id']==part_id for row in entries)
                if first_on_staff and image_evidence['components']:
                    first_x=min(h['x'] for h in image_evidence['components'])
                    explained.append([span[0],lines[0]-2.3*interline,first_x-interline,lines[-1]+interline])
                unexplained = scan_ink(image,above,explained,interline,chord_reader)
                section_types = {w.get('section_type','verse') for w in measure_words}
                section = {'type': next(iter(section_types)) if len(section_types)==1 else 'mixed',
                           'verse_count': len(counts), 'continuity_conflict': False}
                e = {'omr': {'notes': len(pitched),'sung_notes':len(sung),'durations':[n.findtext('type') for n in selected],
                    'tuplets':sum(n.find('time-modification') is not None for n in pitched),'beats':_beats(m,divisions),
                    'expected_beats':expected,'pickup_complement':pickup_pair and index in (0,len(measures)-1),
                    'melisma_notes':slur_count,'slurs_known':True,'fifths':fifths,
                    'midi_pitches':[12*(int(n.findtext('pitch/octave','4'))+1)+STEPS[n.findtext('pitch/step')]+int(n.findtext('pitch/alter','0')) for n in sung],
                    'clef_conflict': bool(clef_report and clef_report.get('corrected')),
                    'key_conflict': False},
                    'image':image_evidence,'lyrics':dict(counts),'lyrics_complete':bool(words and measure_words),
                    'chords':{'read':chord_values,'unexplained_ink':unexplained,'out_of_key':outside},'section':section,
                    'ocr_review_count':sum(w.get('diacritic_fusion',{}).get('needs_review',False) or
                        w.get('geometry_needs_review',False) or (w.get('alignment') or {}).get('status')=='needs_review' for w in measure_words),
                    'sources_agree':image_evidence['heads']==len(pitched) and geometry_known}
                e['lyric_anchor_samples']=[]
                for w in measure_words:
                    a=w.get('alignment') or {}; bounds=w.get('box',[])
                    anchor=next((n for n in notes_here if int(n['note_index'])==int(a.get('note_index',-1))),None)
                    if anchor and len(bounds)==4 and bounds[2]>bounds[0] and a.get('status')=='accepted':
                        value=(anchor['x']-bounds[0])/(bounds[2]-bounds[0])
                        if 0<=value<=1: e['lyric_anchor_samples'].append(value)
                item = {'id':f'p{page}_{part_id}_s{staff_index+1}_m{number}', 'page':page,'system_id':system_id,
                        'staff_index':staff_index,'part_id':part_id,'measure_number':int(number) if number.lstrip('-').isdigit() else index+1,
                        'local_measure_number':number,'box':box,'staff_lines':lines,'interline':interline,
                        'geometry_verified':geometry_known,'evidence':e,'suggestions':[]}
                entries.append(decide(item))
    return {'schema_version':1,'page':page,'measures':entries,'accuracy_available':False,'auto_repair_enabled':False}


def merge_ledgers(ledgers: list[dict]) -> dict:
    result = {'schema_version':1,'measures':[],'accuracy_available':False,'auto_repair_enabled':False}
    last_by_part = {}
    expected_by_part = {}
    for page_index, ledger in enumerate(ledgers,1):
        mapping = {}
        for entry in ledger['measures']:
            part = entry['part_id']; key = (part,str(entry['local_measure_number']))
            if key not in mapping:
                value = entry['measure_number'] if page_index==1 else last_by_part.get(part,0)+1
                mapping[key] = value; last_by_part[part] = value
            item = copy.deepcopy(entry); item['measure_number']=mapping[key]; item['page']=page_index
            omr = item['evidence']['omr']
            if omr.get('expected_beats') is None:
                omr['expected_beats'] = expected_by_part.get(part)
            else:
                expected_by_part[part] = omr['expected_beats']
            item['id']=f"p{page_index}_{part}_s{item['staff_index']+1}_m{item['local_measure_number']}"
            result['measures'].append(decide(item))
    return result


def write_artifacts(ledger: dict, directory: str, metadata: dict | None = None) -> dict:
    os.makedirs(directory,exist_ok=True)
    from pathlib import Path
    import hashlib
    for parent in (Path(directory),*Path(directory).parents):
        sources=sorted((parent/'source').glob('original.*'))
        if sources:
            ledger['source_sha256']=hashlib.sha256(sources[0].read_bytes()).hexdigest(); break
    paths = {}
    queue = [m for m in ledger['measures'] if m['decision']=='review']
    order = {'error':0,'warning':1,'info':2}
    queue.sort(key=lambda m:(min([order[v['severity']] for v in m['violations']] or [2]),
                             next((v['rule'] for v in m['violations']),'Z'),m['measure_number']))
    if metadata:
        regions = metadata.get('semantic_regions',[])
        boxes = [r['box'] for r in regions if r.get('box') and r.get('role') in ('title','composer','translator')]
        queue.insert(0,{'id':'metadata','kind':'metadata','page':1,'measure_number':None,'decision':'review',
            'box':[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)] if boxes else [],
            'metadata':metadata,'violations':[{'rule':'METADATA','severity':'warning','message':'Xác nhận tựa bài, tác giả và lời Việt.'}],'suggestions':[]})
    for name,value in [('measure_ledger',ledger),('review_queue',{'schema_version':1,'items':queue,'total_measures':len(ledger['measures']),
        'review_measures':sum(m['decision']=='review' for m in ledger['measures']), 'auto_repair_enabled':False})]:
        path = os.path.join(directory,name+'.json'); tmp=path+'.tmp'
        with open(tmp,'w',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2)
        os.replace(tmp,path); paths[name+'_path']=path
    return paths
