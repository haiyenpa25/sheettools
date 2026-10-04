from . import violation
def check(m: dict) -> list[dict]:
    e = m['evidence']; image = e['image']
    if image.get('available') and image.get('heads') != e['omr']['notes']:
        return [violation('C2', 'error' if image.get('reliable') else 'warning',
            f"Ảnh có {image.get('heads')} đầu nốt; OMR có {e['omr']['notes']}.")]
    return []
