"""Bounded comparison using the existing hand-transcribed 270 reference."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workers'))
from external_omr.worker import score_root, write_json
from evaluation.accuracy_report import _edit_distance
from audit_270 import lyric_metric


def note_tokens(root: ET.Element) -> dict:
    result={}
    for part in root.findall('part'):
        divisions=1
        for measure in part.findall('measure'):
            divisions=int(measure.findtext('attributes/divisions',str(divisions)))
            for index,note in enumerate(measure.findall('note'),1):
                if note.find('pitch') is None: continue
                result[f"{part.get('id')}:{measure.get('number')}:{index}"]=[note.findtext('pitch/step'),
                    int(note.findtext('pitch/alter','0')),int(note.findtext('pitch/octave','0')),
                    str(Fraction(int(note.findtext('duration','0')),divisions))]
    return result


def audit(project: Path, run: Path) -> dict:
    truth=json.loads((ROOT/'tests/ground_truth/270.manual.json').read_text(encoding='utf-8'))
    source_hash=hashlib.sha256((project/'source/original.pdf').read_bytes()).hexdigest()
    if source_hash!=truth['source_sha256']: raise ValueError('Reference source hash mismatch')
    ledger=json.loads((project/'omr_out/measure_ledger.json').read_text())
    status=json.loads((run/'status.json').read_text())
    result={'engine':status['engine'],'revision':status['revision'],'scope':'Only two manually transcribed measures; no whole-score accuracy',
            'source_sha256':source_hash,'checks':[],'full_accuracy_available':False,'counts':status.get('pages',[])}
    base=run/'page_0001'; tokens=note_tokens(score_root(base/status['pages'][0]['xml']))
    if (base/'note_positions.json').exists():
        positions=json.loads((base/'note_positions.json').read_text())['positions']
        for number,expected in truth['page1_notes'].items():
            entry=next(m for m in ledger['measures'] if m['page']==1 and str(m['measure_number'])==number)
            x1,y1,x2,y2=entry['box']; il=entry['interline']; lines=entry['staff_lines']
            chosen=sorted([p for p in positions if x1<=p['position'][0]<x2 and lines[0]-2*il<=p['position'][1]<=lines[-1]+2*il and p['id'] in tokens],key=lambda p:p['position'][0])
            actual=[tokens[p['id']] for p in chosen]
            result['checks'].append({'measure':number,'expected':expected,'actual':actual,'matches':actual==expected,
                                     'mapping':'Approximate Homr coordinates inside existing verified measure boxes'})
    else:
        assembled=base/'debug/assembled_score.json'
        if assembled.exists():
            systems=json.loads(assembled.read_text())['systems']
            peers=[m for m in ledger['measures'] if m['page']==1 and m['part_id']=='P1']
            groups={}
            for m in peers: groups.setdefault(m['system_id'],[]).append(m)
            counts=[s['canonical_measure_count'] for s in systems]
            root=score_root(base/status['pages'][0]['xml']); parts=root.findall('part')
            if len(parts)==1 and counts==[len(group) for group in groups.values()] and sum(counts)==len(parts[0].findall('measure')):
                measures=parts[0].findall('measure')
                for number,expected in truth['page1_notes'].items():
                    index=next(i for i,m in enumerate(peers) if str(m['measure_number'])==number)
                    measure=measures[index]; prefix=f"{parts[0].get('id')}:{measure.get('number')}:"
                    actual=[tokens[prefix+str(i)] for i,n in enumerate(measure.findall('note'),1) if prefix+str(i) in tokens]
                    result['checks'].append({'measure':number,'expected':expected,'actual':actual,'matches':actual==expected,
                        'mapping':'Single-part score with identical per-system measure counts in the verified image ledger and Clarity assembly'})
            else: result['limitation']='System/measure correspondence cannot be confirmed; no accuracy metric emitted'
        else: result['limitation']='No image-to-measure mapping; no accuracy metric emitted'
    if (base/'lyrics.json').exists():
        artifact=json.loads((base/'lyrics.json').read_text()); words=artifact['words']; result['ocr_lyrics']={}
        for verse,expected in truth['page1_verses'].items():
            # The chorus starts on the same printed row as verse 2; this measures text, not section inference.
            if verse=='2': expected+=' '+truth['page1_chorus']
            row=sorted((w for w in words if str(w['verse_number'])==verse),key=lambda w:(w['staff_index'],w['x']))
            result['ocr_lyrics']['page1_row'+verse]=lyric_metric(expected,[w['text'] for w in row])
        page2=run/'page_0002/lyrics.json'
        if page2.exists():
            words=json.loads(page2.read_text())['words']
            result['ocr_lyrics']['page2_chorus']=lyric_metric(truth['page2_chorus'],[w['text'] for w in sorted(words,key=lambda w:(w['staff_index'],w['x']))])
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--run',type=Path,required=True); parser.add_argument('--output',type=Path,required=True); args=parser.parse_args()
    report=audit(args.project,args.run); write_json(args.output,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
