"""Add review evidence to an existing conversion without rerunning or replacing RAW/OMR."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
if __package__ in (None,''): sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from omr_checks.pipeline import audit_merged, audit_page
from omr_checks.section_continuity import update_page_sections
from xml_tools.page_merger import merge_musicxml_pages

def backfill(project: Path) -> dict:
    base=project/'omr_out'
    checkpoints=sorted(base.glob('page_result_*/page_checkpoint.json'))
    if not checkpoints:
        checkpoints=[base/'page_checkpoint.json'] if (base/'page_checkpoint.json').is_file() else []
    if not checkpoints: raise ValueError('No completed recognition checkpoints; convert the project first')
    results=[json.loads(p.read_text(encoding='utf-8')) for p in checkpoints]
    current=project/'musicxml/current.musicxml'; normalized=project/'musicxml/normalized.musicxml'
    untouched=current.is_file() and normalized.is_file() and current.read_bytes()==normalized.read_bytes()
    if len(results)>1:
        update_page_sections(results)
        paths=audit_merged(results,str(base))
    else:
        audit_page(results[0],str(base)); paths={k:results[0][k] for k in ('measure_ledger_path','review_queue_path')}
    if untouched and len(results)>1:
        before=current.read_bytes()
        derived=base/'review_derived.tmp.musicxml'
        if not merge_musicxml_pages([r['xml_path'] for r in results],str(derived)):
            raise ValueError('Cannot merge the section-corrected derivative')
        snapshot=base/f'before_review_{hashlib.sha256(before).hexdigest()}.musicxml'
        if not snapshot.is_file(): snapshot.write_bytes(before)
        normalized.write_bytes(derived.read_bytes()); current.write_bytes(normalized.read_bytes())
    if not untouched:
        ledger=json.loads(Path(paths['measure_ledger_path']).read_text(encoding='utf-8'))
        for m in ledger['measures']:
            m['decision']='review'; m['violations'].append({'rule':'XML_CHANGED','severity':'warning','message':'Current XML differs from the recognition derivative; verify against the image.'})
        from omr_checks.ledger import write_artifacts
        document=json.loads(Path(results[0]['document_artifact_path']).read_text(encoding='utf-8')) if results[0].get('document_artifact_path') else None
        paths=write_artifacts(ledger,str(base),document)
    return {'success':True,'updated_derived_xml':untouched and len(results)>1,**paths}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--project',required=True)
    args=parser.parse_args(); print(json.dumps(backfill(Path(args.project).resolve())))
