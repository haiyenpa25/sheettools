from __future__ import annotations
import json
import os
from .ledger import build_ledger, merge_ledgers, write_artifacts
from .decide import decide
from functools import lru_cache

@lru_cache(maxsize=1)
def _chord_reader():
    from xml_tools.vietnamese_universal_ocr import VietnameseUniversalOcrEngine
    return VietnameseUniversalOcrEngine().reocr_chord_box


def _load(path: str | None) -> dict:
    if not path or not os.path.isfile(path): return {}
    with open(path,encoding='utf-8') as f: return json.load(f)


def audit_page(result: dict, directory: str, page: int = 1) -> dict:
    ledger=build_ledger(result['xml_path'],_load(result.get('note_anchors_path')),
        _load(result.get('lyrics_artifact_path')),_load(os.path.join(directory,'page_model.json')),
        os.path.join(directory,'preprocessed.png') if os.path.isfile(os.path.join(directory,'preprocessed.png')) else None,
        page,result.get('clef_check'),_chord_reader())
    words=_load(result.get('lyrics_artifact_path')).get('words',[])
    for m in ledger['measures']:
        # A correction already applied to derived XML is historical evidence, not an unresolved error.
        m['evidence']['omr']['clef_conflict']=bool(result.get('clef_check',{}).get('unsupported') and not result.get('clef_check',{}).get('corrected'))
        m['evidence']['section']['continuity_conflict']=any(w.get('continuity_needs_review') for w in
            words if str((w.get('alignment') or {}).get('measure'))==str(m['local_measure_number']))
        decide(m)
    result.update(write_artifacts(ledger,directory,_load(result.get('document_artifact_path'))))
    return ledger


def audit_merged(results: list[dict], directory: str) -> dict:
    ledgers=[]
    for page,result in enumerate(results,1):
        page_dir=os.path.dirname(result['xml_path'])
        ledgers.append(audit_page(result,page_dir,page))
    ledger=merge_ledgers(ledgers)
    by_part={m['part_id'] for m in ledger['measures']}
    for part in by_part:
        measures=[m for m in ledger['measures'] if m['part_id']==part]
        first,last=measures[0],measures[-1]
        o1,o2=first['evidence']['omr'],last['evidence']['omr']
        if o1.get('expected_beats') and o1['beats']<o1['expected_beats'] and abs(o1['beats']+o2['beats']-o1['expected_beats'])<.001:
            for m in (first,last): m['evidence']['omr']['pickup_complement']=True; decide(m)
    return write_artifacts(ledger,directory,_load(results[0].get('document_artifact_path')))
