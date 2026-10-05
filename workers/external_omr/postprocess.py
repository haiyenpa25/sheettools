"""Run Vietnamese OCR in the existing app environment after neural recognition."""
from __future__ import annotations
import argparse
import json
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from external_omr.worker import write_json, score_root
from external_omr.layout import detect_text, propose_alignment, refine_staff_regions
ANALYSIS_VERSION='neural_layout_v4'


def eligible_note_ids(root: ET.Element) -> set[str]:
    from xml_tools.lyrics_aligner import _eligible
    result=set()
    for part in root.findall('part'):
        for measure in part.findall('measure'):
            for index,note in enumerate(measure.findall('note'),1):
                # ET's comment tags are functions; the existing lyric parser expects XML element tags.
                plain=ET.fromstring(ET.tostring(note,encoding='utf-8'))
                if _eligible(plain): result.add(f"{part.get('id')}:{measure.get('number')}:{index}")
    return result


def analyze_run(directory: Path) -> dict:
    # The deployed processor runs on Linux. A manual audit must not race the watcher.
    import fcntl
    lock_path=directory/'.analysis.lock'
    try:
        with lock_path.open('x'): pass
    except FileExistsError: pass
    with lock_path.open('r') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return {'status':'running','message':'Another processor owns this run'}
        return _analyze_run(directory)


def _analyze_run(directory: Path) -> dict:
    status=json.loads((directory/'status.json').read_text())
    result={'status':'running','version':ANALYSIS_VERSION,'pages':[],'requires_review':True,'accuracy_available':False}
    target=directory/'analysis.json'; write_json(target,result)
    try:
        for page in status['pages']:
            base=directory/f"page_{page['page']:04d}"
            regions=json.loads((base/'regions.json').read_text())
            regions['regions']=refine_staff_regions(str(base/'page.png'),regions['regions'])
            write_json(base/'analysis_regions.json',regions)
            artifact=detect_text(str(base/'page.png'),regions['regions'],page['page'])
            tree=score_root(base/page['xml'],comments=True)
            eligible=eligible_note_ids(tree)
            if (base/'note_positions.json').exists():
                positions=json.loads((base/'note_positions.json').read_text())['positions']
                artifact['words']=propose_alignment(artifact['words'],[p for p in positions if p['id'] in eligible],regions['regions'])
            else:
                for word in artifact['words']: word['alignment']={'status':'review','requires_review':True,'reason':'engine_has_no_note_positions'}
            write_json(base/'lyrics.json',artifact)
            proposed={}
            for word in artifact['words']:
                alignment=word['alignment']
                if alignment['status']=='proposed' and alignment.get('spatial_error_interlines',99)<=1 and not word.get('geometry_needs_review'):
                    proposed[(alignment['note_id'],str(word['verse_number']))]=word
            for part in tree.findall('part'):
                for measure in part.findall('measure'):
                    for index,note in enumerate(measure.findall('note'),1):
                        for old in note.findall('lyric'): note.remove(old)
                        key=f"{part.get('id')}:{measure.get('number')}:{index}"
                        for (note_id,verse),word in proposed.items():
                            if note_id==key:
                                lyric=ET.SubElement(note,'lyric',{'number':verse,'name':f'Lời {verse} (cần soát)'})
                                ET.SubElement(lyric,'text').text=word['text']
            ET.ElementTree(tree).write(base/'aligned.musicxml',encoding='utf-8',xml_declaration=True)
            # Overlay detected rows, preserving unknown text rather than treating all gaps as lyrics.
            from PIL import Image,ImageDraw
            with Image.open(base/'page.png') as original:
                overlay=original.convert('RGB'); draw=ImageDraw.Draw(overlay)
                for region in regions['regions']: draw.rectangle(region['box'],outline='#38bdf8',width=3)
                for row in artifact['rows']:
                    draw.rectangle(row['box'],outline='#10b981' if row['role']=='lyric' else '#f59e0b',width=2)
                overlay.save(base/'regions.png'); overlay.close()
            result['pages'].append({'page':page['page'],'lyric_rows':sum(r['role']=='lyric' for r in artifact['rows']),
                'words':len(artifact['words']),'proposed':sum(w['alignment']['status']=='proposed' for w in artifact['words']),
                'inserted_for_review':len(proposed)})
            write_json(target,result)
        result['status']='completed'
    except Exception as error:
        result['status']='failed'; result['error']=str(error)
        (directory/'analysis.log').write_text(traceback.format_exc())
    write_json(target,result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--storage',type=Path,default=Path('/var/www/html/storage'))
    parser.add_argument('--run',type=Path); args=parser.parse_args()
    if args.run:
        result=analyze_run(args.run); print(json.dumps(result)); sys.exit(1 if result['status']=='failed' else 0)
    for path in args.storage.glob('projects/*/omr_comparisons/*/analysis.json'):
        try:
            analysis=json.loads(path.read_text())
            if analysis.get('status')=='running':
                analysis['status']='queued'; write_json(path,analysis)
        except Exception: traceback.print_exc()
    while True:
        for path in args.storage.glob('projects/*/omr_comparisons/*/status.json'):
            try:
                analysis_path=path.parent/'analysis.json'
                if analysis_path.exists():
                    analysis=json.loads(analysis_path.read_text())
                    if analysis.get('version')==ANALYSIS_VERSION and analysis.get('status')!='queued': continue
                status=json.loads(path.read_text())
                if status.get('status')=='completed': analyze_run(path.parent)
            except Exception: traceback.print_exc()
        time.sleep(5)
