from . import violation
def check(m: dict) -> list[dict]:
    e = m['evidence']; marks = e['image'].get('tuplet_marks', []); n = e['omr'].get('tuplets', 0)
    if marks and not n: return [violation('C4', 'error', 'Ảnh có dấu liên ba/chùm nhưng OMR không có time-modification.')]
    if n and not marks and e['image'].get('available'):
        return [violation('C4', 'warning', 'OMR có liên ba/chùm, chưa tìm được bằng chứng số trên ảnh.')]
    return []
