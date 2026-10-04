from . import violation
def check(m: dict) -> list[dict]:
    e = m['evidence']; values = list(e.get('lyrics', {}).values())
    if e.get('lyrics_complete') and e.get('section',{}).get('type')!='mixed' and values and max(values)-min(values) > e['omr'].get('melisma_notes', 0):
        return [violation('C5', 'warning', 'Các lời có số âm tiết khác nhau, chưa giải thích được bằng luyến.')]
    return []
