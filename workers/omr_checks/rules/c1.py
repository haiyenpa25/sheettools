from . import violation
def check(m: dict) -> list[dict]:
    e = m['evidence']; o = e['omr']; result = []
    if not e.get('lyrics_complete', False): return result
    for verse, count in e.get('lyrics', {}).items():
        n = o.get('sung_notes', 0); l = o.get('melisma_notes', 0)
        if count > n or (n-count > l and e.get('section',{}).get('type') != 'mixed'):
            result.append(violation('C1', 'error' if o.get('slurs_known') else 'warning',
                f'Lời {verse}: {count} âm tiết, {n} nốt nhận lời; {l} nốt luyến cho phép.'))
    return result
