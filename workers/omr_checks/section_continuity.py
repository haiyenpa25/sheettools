from __future__ import annotations
import json
import xml.etree.ElementTree as ET
from statistics import median


def _chorus(word: dict, reason: str) -> None:
    word.update(section_type='chorus',verse_number=1,lyric_name='ĐK',section_id='continued_chorus',
                continuity_reason=reason,continuity_needs_review=True)


def connect_sections(pages: list[dict]) -> None:
    """Propagate section state without changing characters or inventing syllables."""
    for previous, current in zip(pages,pages[1:]):
        prev_words, next_words = previous.get('words',[]),current.get('words',[])
        if not prev_words or not next_words: continue
        last_system = max(w.get('system_id','') for w in prev_words)
        tail = [w for w in prev_words if w.get('system_id')==last_system]
        last_word = max(tail,key=lambda w:w.get('x',0))
        if last_word.get('section_type')!='chorus': continue
        if any(w.get('explicit_verse') or w.get('explicit_section') for w in next_words): continue
        # Only inherit across a one-row continuation. Multi-staff scores retain their own labels.
        row_ids = {(w.get('staff_index',0),w.get('verse_number',1)) for w in next_words}
        if len({verse for _,verse in row_ids}) != 1: continue
        for w in next_words:
            _chorus(w,'previous_page_chorus')
            w['continuity_needs_review']=False
        next_words[0]['continuity_needs_review']=True
        chorus_words = [w for w in tail if w.get('section_type')=='chorus']
        center = median(w['y'] for w in chorus_words)
        height = median(w['box'][3]-w['box'][1] for w in chorus_words)
        first_x = min(w['x'] for w in chorus_words)
        candidates = sorted((w for w in tail if abs(w['y']-center)<.6*height and w['x']<first_x),key=lambda w:-w['x'])
        for w in candidates:
            shared = any(abs(other['x']-w['x'])<height*.6 and abs(other['y']-center)>height*.7 for other in tail)
            if shared: break
            _chorus(w,'single_row_tail_before_page_break')


def update_page_sections(results: list[dict]) -> None:
    from xml_tools.lyric_structure import structure_tree
    artifacts=[]; active=[]
    for result in results:
        path=result.get('lyrics_artifact_path')
        if not path: return
        with open(path,encoding='utf-8') as f: artifacts.append(json.load(f))
        active.append(result)
    connect_sections(artifacts)
    for result,artifact in zip(active,artifacts):
        changed=[w for w in artifact.get('words',[]) if w.get('continuity_reason')]
        if not changed: continue
        tree=ET.parse(result['xml_path']); root=tree.getroot()
        for node in root.iter(): node.tag=node.tag.rsplit('}',1)[-1]
        for w in changed:
            a=w.get('alignment') or {}
            if a.get('status')!='accepted': continue
            measure=root.find(f"part[@id='{a['part_id']}']/measure[@number='{a['measure']}']")
            if measure is None: continue
            notes=measure.findall('note'); note=notes[int(a['note_index'])-1]
            for lyric in note.findall('lyric'):
                if lyric.findtext('text')==w['text']:
                    # A collision is a review issue rather than silent deletion.
                    if any(l is not lyric and l.get('number')=='1' for l in note.findall('lyric')): continue
                    lyric.set('number','1'); lyric.set('name','ĐK')
        tree.write(result['xml_path'],encoding='utf-8',xml_declaration=True)
        sections = []
        for w in artifact.get('words',[]):
            if any(s['id']==w.get('section_id') for s in sections): continue
            sections.append({'id':w.get('section_id','unknown'),'type':w.get('section_type','verse'),
                'verse_count':1 if w.get('section_type')=='chorus' else max((int(x.get('verse_number',1)) for x in artifact['words']),default=1),
                'needs_review':True,'systems':[],'measure_range':[]})
        artifact['sections']=structure_tree(artifact.get('words',[]),sections)
        with open(result['lyrics_artifact_path'],'w',encoding='utf-8') as f: json.dump(artifact,f,ensure_ascii=False,indent=2)
