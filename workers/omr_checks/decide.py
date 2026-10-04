from __future__ import annotations
from .rules import check_all, violation


def decide(entry: dict) -> dict:
    entry['violations'] = check_all(entry)
    e = entry['evidence']
    if not e['image'].get('available') or not e.get('sources_agree', False):
        entry['violations'].append(violation('EVIDENCE', 'warning', 'Chưa đủ nguồn độc lập đồng ý để tự chấp nhận.'))
    if e.get('ocr_review_count', 0):
        entry['violations'].append(violation('OCR', 'warning', f"Có {e['ocr_review_count']} chữ/dấu cần soát."))
    entry['decision'] = 'review' if any(v['severity'] != 'info' for v in entry['violations']) else 'accept'
    entry['confidence'] = None  # No invented probability; acceptance must be benchmarked.
    entry.setdefault('suggestions', [])
    entry['auto_repair_enabled'] = False
    return entry
