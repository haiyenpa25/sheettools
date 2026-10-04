from . import violation
def check(m: dict) -> list[dict]:
    o = m['evidence']['omr']
    if o.get('clef_conflict') or o.get('key_conflict'):
        return [violation('C8', 'error', 'Khoá/hoá biểu chưa có bằng chứng đổi rõ ràng hoặc khoá quãng tám không được ảnh hỗ trợ.')]
    return []
