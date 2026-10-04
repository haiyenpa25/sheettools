from . import violation
def check(m: dict) -> list[dict]:
    if m['evidence'].get('chords', {}).get('unexplained_ink'):
        candidates=[ink['candidate_chord'] for ink in m['evidence']['chords']['unexplained_ink'] if isinstance(ink,dict) and ink.get('candidate_chord')]
        detail=(' Đọc lại vùng ảnh: '+', '.join(candidates)+'.') if candidates else ''
        return [violation('C6', 'warning', 'Còn cụm mực trên khuông chưa được giải thích: có thể thiếu hợp âm.'+detail)]
    return []
