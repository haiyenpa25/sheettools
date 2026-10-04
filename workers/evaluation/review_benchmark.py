"""Measure-level review metrics; design thresholds are never assumed achieved."""
from __future__ import annotations
import argparse, json
from pathlib import Path


def benchmark(ledger: dict, truth: dict | None, log: list[dict]) -> dict:
    rows=ledger.get('measures',[]); decisions={m['id']:m['decision'] for m in rows}
    source_matches=not ledger.get('source_sha256') or ledger['source_sha256']==(truth or {}).get('source_sha256')
    labels={m['id']:m['correct'] for m in (truth or {}).get('measures',[]) if type(m.get('correct')) is bool} if (truth or {}).get('verified') and source_matches else {}
    labeled={key:value for key,value in labels.items() if key in decisions}
    accepted=[key for key in labeled if decisions[key]=='accept']; wrong=[key for key in labeled if not labeled[key]]
    complete=bool(decisions) and set(labeled)==set(decisions)
    precision=sum(labeled[k] for k in accepted)/len(accepted) if accepted else None
    coverage=sum(decisions[k]=='review' for k in wrong)/len(wrong) if wrong else None
    load=sum(m['decision']=='review' for m in rows)/len(rows) if rows else None
    evaluable=complete and bool(accepted) and bool(wrong)
    met=bool(evaluable and precision>=.99 and coverage>=.95 and load<=.20)
    sources={s.get('source_sha256') for s in (truth or {}).get('sources',[]) if s.get('manually_verified') and len(s.get('source_sha256',''))==64}
    eligible=met and len(sources)>=20
    return {'schema_version':1,'accuracy_available':bool(labeled),'complete_labels':complete,'labeled_measures':len(labeled),
        'total_measures':len(rows),'accept_precision':sum(labeled[k] for k in accepted)/len(accepted) if accepted else None,
        'error_coverage':sum(decisions[k]=='review' for k in wrong)/len(wrong) if wrong else None,
        'review_load':sum(m['decision']=='review' for m in rows)/len(rows) if rows else None,
        'human_seconds':sum(max(0,float(e.get('seconds',0))) for e in log),
        'targets_evaluable':evaluable,'performance_targets_met':met,'verified_source_count':len(sources),
        'auto_repair_eligible':eligible,
        'targets':{'accept_precision':.99,'error_coverage':.95,'review_load':.20},'targets_achieved':eligible}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--ledger',required=True); p.add_argument('--truth'); p.add_argument('--log'); p.add_argument('--commit',required=True); p.add_argument('--output',required=True)
    a=p.parse_args(); load=lambda path:json.loads(Path(path).read_text(encoding='utf-8')) if path else None
    result=benchmark(load(a.ledger),load(a.truth),(load(a.log) or {}).get('log',[])); result['commit']=a.commit
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(result,ensure_ascii=False))
