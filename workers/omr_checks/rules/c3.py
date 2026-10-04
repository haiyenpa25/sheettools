from . import violation
def check(m: dict) -> list[dict]:
    o = m['evidence']['omr']
    if o.get('expected_beats') and abs(o['beats']-o['expected_beats']) > .001 and not o.get('pickup_complement'):
        return [violation('C3', 'error', f"Có {o['beats']:g} phách, chỉ nhịp yêu cầu {o['expected_beats']:g}.")]
    return []
