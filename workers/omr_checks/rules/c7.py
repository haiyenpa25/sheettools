from . import violation
def check(m: dict) -> list[dict]:
    if m['evidence'].get('section', {}).get('continuity_conflict'):
        return [violation('C7', 'warning', 'Mạch lời qua trang/ô nhịp mâu thuẫn; cần xác nhận đoạn điệp khúc.')]
    return []
