"""Generate traceable repair candidates; no automatic note changes."""
from __future__ import annotations
import argparse, copy, json, os, sys
from fractions import Fraction
from pathlib import Path
import xml.etree.ElementTree as ET
import cv2
if __package__ in (None,''): sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def reconcile_tuplet(entry: dict, candidate: ET.Element, divisions: int) -> bool:
    """Reconcile crop pitches with image positions/bracket; no missing note is synthesized."""
    from omr_checks.ledger import _beats
    heads=sorted(entry['evidence']['image'].get('components',[]),key=lambda h:h['x'])
    notes=candidate.findall('note')
    if len(notes)!=len(heads) or any(n.find('pitch') is None or n.find('chord') is not None for n in notes): return False
    marks=[m for m in entry['evidence']['image'].get('tuplet_marks',[]) if m.get('number')==3 and m.get('bracket_span')]
    if len(marks)!=1: return False
    span=marks[0]['bracket_span']; il=entry['interline']
    indexes=[i for i,h in enumerate(heads) if span[0]-il<=h['x']<=span[1]+il]
    if len(indexes)!=3 or any(heads[i]['hollow'] or notes[i].findtext('type')!='quarter' or notes[i].find('dot') is not None for i in indexes): return False
    fifths=entry['evidence']['omr'].get('fifths',0); altered=('FCGDAEB' if fifths>0 else 'BEADGCF')[:abs(fifths)]
    for head,note in zip(heads,notes):
        absolute=30+round((entry['staff_lines'][-1]-head['y'])/(il/2)); step='CDEFGAB'[absolute%7]; octave=absolute//7
        alter=(1 if fifths>0 else -1) if step in altered else 0
        if (note.findtext('pitch/step'),int(note.findtext('pitch/octave','0')),int(note.findtext('pitch/alter','0')))!=(step,octave,alter): return False
        if head['hollow'] != (note.findtext('type') in ('half','whole')): return False
    outside=sum(Fraction(int(n.findtext('duration','0')),divisions) for i,n in enumerate(notes) if i not in indexes)
    remaining=Fraction(str(entry['evidence']['omr'].get('expected_beats') or 0))-outside
    # Three printed quarter heads under “3” justify exactly two quarter beats.
    if remaining!=2 or (remaining*divisions/3).denominator!=1: return False
    for i in indexes:
        note=notes[i]; note.find('duration').text=str(int(remaining*divisions/3))
        for old in note.findall('time-modification'): note.remove(old)
        tm=ET.Element('time-modification'); ET.SubElement(tm,'actual-notes').text='3'; ET.SubElement(tm,'normal-notes').text='2'; ET.SubElement(tm,'normal-type').text='quarter'
        position=next((j for j,node in enumerate(note) if node.tag in ('stem','notehead','staff','beam','notations','lyric')),len(note))
        note.insert(position,tm)
        if i in (indexes[0],indexes[-1]):
            notation=note.find('notations')
            if notation is None: notation=ET.SubElement(note,'notations')
            ET.SubElement(notation,'tuplet',{'type':'start' if i==indexes[0] else 'stop','number':'1',**({'bracket':'yes'} if i==indexes[0] else {})})
    return abs(_beats(candidate,divisions)-float(entry['evidence']['omr']['expected_beats']))<.001


def image_proposal(entry: dict) -> dict | None:
    image=entry['evidence']['image']; heads=sorted(image.get('components',[]),key=lambda h:h['x'])
    marks=[m for m in image.get('tuplet_marks',[]) if m['number']==3 and m.get('bracket_span')]
    if not marks or len(heads)<3 or not entry.get('staff_lines'): return None
    span=marks[0]['bracket_span']; group=[h for h in heads if span[0]-entry['interline']<=h['x']<=span[1]+entry['interline']]
    if len(group)!=3 or any(h['hollow'] for h in group): return None
    outside=[h for h in heads if h not in group]
    # Only white heads can justify a half-note duration without a stem/beam recognizer.
    if not outside or not all(h['hollow'] for h in outside): return None
    remaining=Fraction(str(entry['evidence']['omr'].get('expected_beats') or 0))-2*len(outside)
    if remaining not in (Fraction(1),Fraction(2)): return None
    notes=[]
    for head in heads:
        position=round((entry['staff_lines'][-1]-head['y'])/(entry['interline']/2))
        absolute=4*7+2+position
        # E4 is bottom line; diatonic index C4=28.
        letter=['C','D','E','F','G','A','B'][absolute%7]; octave=absolute//7
        notes.append({'step':letter,'octave':octave,'quarters':str(remaining/3 if head in group else Fraction(2)),
                      'source_box':head.get('box'),'accidental_unverified':True})
    return {'id':entry['id']+'_image','source':'image_heads_tuplet','summary':'Ảnh: '+', '.join(f"{n['step']}{n['octave']} ({n['quarters']} phách)" for n in notes),
            'notes':notes,'verified':False,'requires_human_confirmation':True,'satisfies':['C1','C2','C3','C4'],
            'limitation':'Chưa xác nhận dấu hoá và trường độ từ thân/chùm; chỉ là phương án để soát.'}


def reread_system(project: Path, entry: dict, scale: float = 2.0) -> dict:
    from audiveris_runner import run_audiveris, find_audiveris_cli
    from omr_checks.ledger import _beats
    page=entry['page']; base=project/'omr_out'/f'page_result_{page:04d}'
    if not base.is_dir(): base=project/'omr_out'
    model=json.loads((base/'page_model.json').read_text(encoding='utf-8'))
    system=next(s for s in model['systems'] if s['id']==entry['system_id'])
    image=cv2.imread(str(base/'preprocessed.png')); x1,y1,x2,y2=map(int,system['box']); pad=round(3*entry['interline'])
    x1,y1=max(0,x1),max(0,y1-pad); x2,y2=min(image.shape[1],x2),min(image.shape[0],y2+pad)
    crop=image[y1:y2,x1:x2]; crop=cv2.resize(crop,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
    import uuid
    directory=project/'omr_out'/'repair_candidates'/entry['id']/uuid.uuid4().hex
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/'system_2x.png'; cv2.imwrite(str(path),crop)
    cli=find_audiveris_cli(os.getenv('AUDIVERIS_EXE')); result=run_audiveris(str(path),str(directory/'audiveris'),cli)
    if not result.get('success'): return {'source':'audiveris_crop_2x','verified':False,'summary':'Đọc lại hệ không tạo được MusicXML','error':result.get('error')}
    if result.get('omr_paths'):
        from xml_tools.clef_check import correct_octave_clefs
        checked=directory/'clef_checked.musicxml'
        correct_octave_clefs(result['xml_path'],result['omr_paths'][0],str(path),str(checked),entry['interline']*scale)
        result['xml_path']=str(checked)
    ledger=json.loads((project/'omr_out'/'measure_ledger.json').read_text(encoding='utf-8'))
    peers=[m for m in ledger['measures'] if m['page']==page and m['system_id']==entry['system_id'] and m['part_id']==entry['part_id'] and m['staff_index']==entry['staff_index']]
    index=next(i for i,m in enumerate(peers) if m['id']==entry['id'])
    tree=ET.parse(result['xml_path']); root=tree.getroot()
    for node in root.iter(): node.tag=node.tag.rsplit('}',1)[-1]
    part=root.find(f"part[@id='{entry['part_id']}']")
    if part is None or len(part.findall('measure'))!=len(peers):
        return {'id':entry['id']+'_crop','source':'audiveris_crop_2x','verified':False,'summary':'Đọc lại có số ô/part khác; cần kiểm tra artifact crop.'}
    candidate=copy.deepcopy(part.findall('measure')[index]); divisions=1
    for m in part.findall('measure')[:index+1]: divisions=int(m.findtext('attributes/divisions',str(divisions)))
    if divisions%3 and entry['evidence']['image'].get('tuplet_marks'):
        # Crop OMR without tuplets often chooses divisions=2; exact thirds need divisions=6.
        for duration in candidate.findall('.//duration'): duration.text=str(3*int(duration.text))
        divisions*=3
    reconciled=reconcile_tuplet(entry,candidate,divisions)
    pitched=[n for n in candidate.findall('note') if n.find('pitch') is not None and n.find('chord') is None]
    e=entry['evidence']; heads=e['image'].get('heads'); counts=list(e.get('lyrics',{}).values())
    verified=(len(pitched)==heads and bool(counts) and all(n==len(pitched) for n in counts) and
        abs(_beats(candidate,divisions)-(e['omr'].get('expected_beats') or 0))<.001 and
        (not e['image'].get('tuplet_marks') or any(n.find('time-modification') is not None for n in pitched)))
    for parent in candidate.iter():
        for n in list(parent):
            if n.tag=='lyric': parent.remove(n)
    # Restore lyrics exclusively from detected image tokens, never Audiveris crop OCR.
    artifact=json.loads((base/'lyrics.json').read_text(encoding='utf-8'))
    words=[w for w in artifact['words'] if w.get('staff_index')==entry['staff_index'] and entry['box'][0]<=w['x']<entry['box'][2]]
    for verse in sorted({w['verse_number'] for w in words}):
        row=sorted([w for w in words if w['verse_number']==verse],key=lambda w:w['x'])
        if len(row)!=len(pitched): verified=False; continue
        for note,word in zip(pitched,row):
            lyric=ET.SubElement(note,'lyric',{'number':str(verse),'name':word.get('lyric_name',f'Lời {verse}')}); ET.SubElement(lyric,'text').text=word['text']
    # Scale durations to the current part's divisions and preserve its attributes/harmony.
    current=ET.parse(project/'musicxml/current.musicxml').getroot(); target=current.find(f"part[@id='{entry['part_id']}']/measure[@number='{entry['measure_number']}']")
    if target is None: verified=False
    else:
        current_divisions=1
        for m in current.find(f"part[@id='{entry['part_id']}']").findall('measure'):
            current_divisions=int(m.findtext('attributes/divisions',str(current_divisions)))
            if m is target: break
        for duration in candidate.findall('.//duration'):
            value=Fraction(int(duration.text),divisions)*current_divisions
            if value.denominator!=1: verified=False
            else: duration.text=str(value.numerator)
        for a in list(candidate):
            if a.tag in ('attributes','harmony','print','direction'): candidate.remove(a)
        for node in reversed([n for n in target if n.tag in ('attributes','harmony','print','direction')]): candidate.insert(0,copy.deepcopy(node))
    return {'id':entry['id']+'_crop','source':'audiveris_crop_2x','summary':f'Đọc lại hệ 2×: {len(pitched)} nốt, {sum(n.find("time-modification") is not None for n in pitched)} nốt liên ba',
        'verified':verified,'satisfies':['C1','C2','C3','C4'] if verified else [],'measure_xml':ET.tostring(candidate,encoding='unicode'),
        'timing_reconciled_from_image':reconciled,
        'source_artifact':str(path),'requires_human_confirmation':True,'xml_sha256':__import__('hashlib').sha256((project/'musicxml/current.musicxml').read_bytes()).hexdigest()}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--project',required=True); p.add_argument('--measure-id',required=True); a=p.parse_args()
    project=Path(a.project).resolve(); ledger_path=project/'omr_out/measure_ledger.json'; ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
    entry=next(m for m in ledger['measures'] if m['id']==a.measure_id)
    before_hash=__import__('hashlib').sha256((project/'musicxml/current.musicxml').read_bytes()).hexdigest()
    suggestions=[s for s in [image_proposal(entry),reread_system(project,entry)] if s]
    entry['suggestions']=suggestions
    if __import__('hashlib').sha256((project/'musicxml/current.musicxml').read_bytes()).hexdigest()!=before_hash:
        raise RuntimeError('Current XML changed while rereading; discard this candidate')
    temporary=ledger_path.with_suffix('.json.tmp'); temporary.write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(temporary,ledger_path)
    queue_path=project/'omr_out/review_queue.json'; queue=json.loads(queue_path.read_text(encoding='utf-8'))
    for item in queue['items']:
        if item['id']==entry['id']: item['suggestions']=suggestions
    temporary=queue_path.with_suffix('.json.tmp'); temporary.write_text(json.dumps(queue,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(temporary,queue_path)
    print(json.dumps({'success':True,'suggestions':suggestions},ensure_ascii=False))
