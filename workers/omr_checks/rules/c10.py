from . import violation
def check(m: dict) -> list[dict]:
    values = m['evidence'].get('chords', {}).get('out_of_key', [])
    return [violation('C10', 'warning', f"Hợp âm {', '.join(values)} ngoài tập giọng/mượn thông dụng; cần kiểm dấu hoá.")] if values else []
