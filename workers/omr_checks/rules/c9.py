from . import violation
def check(m: dict) -> list[dict]:
    notes = m['evidence']['omr'].get('midi_pitches', [])
    if m['evidence'].get('lyrics') and (any(n < 57 or n > 81 for n in notes) or
        any(abs(b-a) > 12 and abs(c-a) <= 2 for a,b,c in zip(notes, notes[1:], notes[2:]))):
        return [violation('C9', 'info', 'Âm vực/nhảy quãng cần nghe lại; đây không phải bằng chứng chắc chắn sai cao độ.')]
    return []
