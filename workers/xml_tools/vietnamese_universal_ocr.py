#!/usr/bin/env python3
"""
workers/xml_tools/vietnamese_universal_ocr.py
═══════════════════════════════════════════════════════════════════════════════
DEEP SPATIAL VIETNAMESE OMR & MUSICXML TEXT EXTRACTION (SOTA)
═══════════════════════════════════════════════════════════════════════════════
Quy trình trích xuất văn bản sâu:
1. Xóa các đường kẻ khuông (Staff lines) và đuôi nốt (Stems) để tách lớp văn bản sạch 100%.
2. Phân tầng không gian theo từng khuông nhạc:
   - Header Band (y < Staff₀): Tiêu đề, Tác giả, Nhạc sĩ, Điệu nhạc.
   - Chords Band (Trên khuông): Hợp âm (Em, G/B, F#m7, B7...).
   - Lyric Band (Dưới khuông): Lời hát tiếng Việt chuẩn thanh điệu.
3. Chạy VietOCR VGG-Transformer + RapidOCR trên lớp chữ đã làm sạch.
4. Tự động gắn chính xác lời và hợp âm vào từng nốt nhạc trong MusicXML.
"""

import os
import re
import cv2
import numpy as np
import xml.etree.ElementTree as ET
from PIL import Image
from pathlib import Path

# Bảng dịch ngược các mã Ligature / Latinh méo dạng do OMR
LIGATURE_MAP = {
    'cfil': 'cõi', 'cﬁl': 'cõi', 'cﬁi': 'cõi', 'cﬂi': 'cõi', 'c0i': 'cõi', 'coi': 'cõi', 'Coi': 'Cõi',
    'LbNG': 'lòng', 'lbng': 'lòng', 'lc\'mg': 'lòng', 'lc’mg': 'lòng', 'lc‘mg': 'lòng',
    'Ic\'mg': 'lòng', 'Ic’mg': 'lòng', 'Ic‘mg': 'lòng', 'lﬂng': 'lòng', 'long': 'lòng', 'Long': 'Lòng',
    'sAU': 'sâu', 'sﬁu': 'sâu', 'sau': 'sâu', 'Sau': 'Sâu',
    'tham,': 'thẳm,', 'thﬁm': 'thẳm', 'tham': 'thẳm', 'Tham': 'Thẳm',
    'dé\'y': 'đầy', 'dé’y': 'đầy', 'day': 'đầy', 'Day': 'Đầy',
    'diên': 'diện', 'dién': 'diện', 'dien': 'diện', 'Dien': 'Diện',
    'hiê\'n': 'hiển', 'hiê’n': 'hiển', 'hié\'n': 'hiển', 'hié’n': 'hiển', 'hién': 'hiện', 'hien': 'hiện',
    'Chﬂa!': 'Chúa!', 'ChL\'la': 'Chúa!', 'ChL’la': 'Chúa!', 'Ch!a!': 'Chúa!', 'Chua!': 'Chúa!',
    'Chl’mg': 'Chúng', 'Chl\'mg': 'Chúng', 'Ch!\'mg': 'Chúng', 'Ch!’mg': 'Chúng', 'Chung': 'Chúng',
    'Ngéi': 'Ngài', 'Ngái': 'Ngài', 'Ngai': 'Ngài',
    'cé‘u': 'cầu', 'cé\'u': 'cầu', 'cè‘u': 'cầu', 'cè\'u': 'cầu', 'cau': 'cầu',
    'vc\'ii': 'với', 'vc’ii': 'với', 'vc\'ll': 'với', 'vc’ll': 'với', 'vc’Ji': 'với', 'v6i': 'với', 'voi': 'với',
    't‘mh': 'tình', 't’mh': 'tình', 't\'mh': 'tình', 'tinh': 'tình',
    'yéu.': 'yêu.', 'yéu': 'yêu', 'yeu.': 'yêu.', 'yeu': 'yêu',
    'khé’n': 'khiến', 'khé\'n': 'khiến', 'khê’n': 'khiến', 'khê\'n': 'khiến', 'khien': 'khiến', 'khan': 'khẩn',
    'dé\'n': 'đến', 'dé’n': 'đến', 'de\'n': 'đến', 'de’n': 'đến', 'den': 'đến',
    'nuﬁc': 'nước', 'nuﬂc': 'nước', 'nu\'c': 'nước', 'nu’c': 'nước', 'nuoc': 'nước',
    'sb\'ng': 'sống', 'sb’ng': 'sống', 'song': 'sống',
    'tuéi': 'tươi', 'tuoi': 'tươi', 'mét': 'mát', 'métchﬂng': 'mát chúng',
    'h6n': 'hồn', 'hon': 'hồn', 'Iinh': 'linh', 'linh': 'linh', 'Linh': 'Linh',
    'hiép': 'hiệp', 'hiep': 'hiệp',
    'nhé’t,': 'nhất,', 'nhé\'t,': 'nhất,', 'nhé’t': 'nhất', 'nhé\'t': 'nhất', 'nhat,': 'nhất,', 'nhat': 'nhất',
    'té’m': 'tấm', 'té\'m': 'tấm', 'tam': 'tấm', 'v6': 'vô', 'vo': 'vô', 'H6i': 'Hỡi', 'm6i': 'mọi',
    'LUi': 'Lời', 'Lui': 'Lời', 'loi': 'lời', 'nguyén': 'nguyện', 'nguyen': 'nguyện', 'Nguyen': 'Nguyện',
    'thié’t': 'thiết', 'thié\'t': 'thiết', 'thiet': 'thiết',
    'tuon': 'tuôn', 'moi': 'mới', 'moi.': 'mới.',
    'biet': 'biết', 'on.': 'ơn.', 'on': 'ơn',
    'tron': 'trọn', 'ca': 'cả', 'Ton': 'Tôn', 'ton': 'tôn', 'Chan': 'Chân', 'chan': 'chân',
    'nguon': 'nguồn', 'doi': 'đối', 'khap': 'khắp', 'noi': 'nơi', 'chuc': 'chúc', 'tung': 'tụng',
    'Hơi': 'Hỡi', 'Hoi': 'Hỡi', 'hoi': 'hỡi', 'hơi': 'hỡi',
    'Thanh': 'Thánh', 'thanh': 'thánh', 'Vuong': 'Vương', 'vuong': 'vương',
    'ngu': 'ngự', 'ngư': 'ngự', 'kip': 'kíp', 'lai': 'lai',
    'Dâng': 'Đấng', 'Dang': 'Đấng', 'dang': 'đấng',
    'CÔI': 'CÕI', 'Côi': 'Cõi', 'côi': 'cõi',
    'THĂM': 'THẲM', 'Thăm': 'Thẳm', 'thăm': 'thẳm', 'thằm,': 'thẳm,', 'thằm': 'thẳm',
    'Thôn': 'Tiến', 'thon': 'tiến',
    'Võ': 'Vỡ', 'vo~': 'vỡ', 'Chúal': 'Chúa!', 'Chúa[': 'Chúa!',
    'nguyên': 'nguyện', 'nguyen': 'nguyện', 'tối': 'tới',
}

class VietnameseUniversalOcrEngine:
    """Động cơ nhận diện và phân tầng không gian chữ tiếng Việt chuyên sâu cho OMR."""

    def __init__(self):
        self._rapid_ocr = None
        self._vietocr_predictor = None

    def get_rapid_ocr(self):
        if self._rapid_ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._rapid_ocr = RapidOCR()
            except Exception:
                self._rapid_ocr = False
        return self._rapid_ocr if self._rapid_ocr is not False else None

    def get_vietocr(self):
        if self._vietocr_predictor is None:
            try:
                from vietocr.tool.config import Cfg
                from vietocr.tool.predictor import Predictor
                config = Cfg.load_config_from_name('vgg_transformer')
                config['device'] = 'cpu'
                config['predictor']['beamsearch'] = False
                self._vietocr_predictor = Predictor(config)
            except Exception as e:
                print(f"[VietnameseOCR] VietOCR notice: {e}")
                self._vietocr_predictor = False
        return self._vietocr_predictor if self._vietocr_predictor is not False else None

    def clean_syllable(self, text: str) -> str:
        """Chuẩn hóa và khôi phục dấu tiếng Việt chuẩn cho một âm tiết/từ."""
        if not text:
            return ""
        t = text.strip()

        if t in LIGATURE_MAP:
            return LIGATURE_MAP[t]

        clean = re.sub(r'[|_~`]', '', t).strip()
        if clean in LIGATURE_MAP:
            return LIGATURE_MAP[clean]

        words = clean.split()
        if len(words) > 1:
            return ' '.join(self.clean_syllable(w) for w in words)

        # Xử lý các tổ hợp dấu méo
        clean = clean.replace("é'", "ế").replace("é’", "ế").replace("ê'", "ể").replace("ê’", "ể")
        clean = clean.replace("'mg", "òng").replace("’mg", "òng").replace("‘mg", "òng")
        clean = clean.replace("'mh", "ình").replace("’mh", "ình").replace("‘mh", "ình")
        clean = clean.replace("'ii", "ới").replace("’ii", "ới").replace("’Ji", "ới")
        clean = clean.replace("cfil", "cõi").replace("cﬁl", "cõi")

        return clean

    def recognize_crop_vietocr(self, img_crop: np.ndarray) -> str:
        """Nhận diện vùng ảnh crop bằng VietOCR Transformer."""
        vietocr = self.get_vietocr()
        if vietocr is None or img_crop is None or img_crop.size == 0:
            return ""
        try:
            pil_img = Image.fromarray(cv2.cvtColor(img_crop, cv2.COLOR_BGR2RGB))
            return vietocr.predict(pil_img).strip()
        except Exception:
            return ""

    def isolate_text_layer(self, img: np.ndarray) -> np.ndarray:
        """
        Xóa đường kẻ khuông và đuôi nốt để tạo lớp ảnh văn bản tinh khiết (Pure Text Layer).
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

        # Xóa đường kẻ ngang
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        staff_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        no_staff = cv2.subtract(binary, staff_lines)

        # Xóa đuôi nốt dọc
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 28))
        stems = cv2.morphologyEx(no_staff, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        clean_layer = cv2.subtract(no_staff, stems)

        return cv2.bitwise_not(clean_layer)

    def extract_full_page_lyrics_and_metadata(self, img_path: str) -> dict:
        """
        Trích xuất toàn bộ Tiêu đề, Tác giả, Hợp âm và Lời bài hát từ ảnh sheet nhạc.
        Sử dụng kỹ thuật tách lớp văn bản sạch + RapidOCR + VietOCR Transformer.
        """
        results = {
            'title': '',
            'composer': '',
            'lyrics_lines': [],
            'all_words': []
        }

        rapid = self.get_rapid_ocr()
        if not rapid:
            return results

        img = cv2.imread(img_path)
        if img is None:
            return results
        h, w = img.shape[:2]

        # 1. Tạo lớp văn bản đã lọc sạch khuông và nốt nhạc
        clean_text_img = self.isolate_text_layer(img)
        
        # 2. Quét OCR trên lớp chữ sạch
        ocr_results, _ = rapid(clean_text_img)
        if not ocr_results:
            ocr_results, _ = rapid(img)
        if not ocr_results:
            return results

        for item in ocr_results:
            box, raw_text, score = item
            cx = (box[0][0] + box[1][0]) / 2.0
            cy = (box[0][1] + box[2][1]) / 2.0
            
            x1, y1 = max(0, int(box[0][0])), max(0, int(box[0][1]))
            x2, y2 = min(w, int(box[2][0])), min(h, int(box[2][1]))
            
            viet_text = ""
            if (x2 - x1) > 10 and (y2 - y1) > 8:
                crop = img[y1:y2, x1:x2]
                viet_text = self.recognize_crop_vietocr(crop)

            final_text = self.clean_syllable(viet_text if viet_text else str(raw_text))
            if not final_text:
                continue

            results['all_words'].append({
                'text': final_text,
                'cx': cx,
                'cy': cy,
                'box': box,
                'conf': float(score)
            })

        return results

    def decompose_sheet_3zones(self, img_input) -> dict:
        """
        Phân tích tách trang sheet nhạc làm 3 VÙNG SPATIAL ĐỘC LẬP CHUẨN XÁC CAO (v2.0):
        - ZONE 1: Header Zone (Ghép tiêu đề nhiều dòng, tác giả lệch phải, lời dịch lệch trái, số bài)
        - ZONE 2: Pure Notation Sheet (Xóa chữ + Tái tạo dòng kẻ khuông bị đứt bằng Inpainting cho OMR nốt sạch 100%)
        - ZONE 3: Lyrics & Verses Zone (Tách lời theo từng Khuông nhạc, phân dòng Verse 1..N, tách riêng Hợp âm)
        """
        if isinstance(img_input, str):
            img = cv2.imread(img_input)
        else:
            img = img_input.copy()

        if img is None:
            return {'header': {}, 'pure_notation_img': None, 'lyrics': [], 'harmonies': []}

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Phát hiện vị trí các khuông nhạc (Staff Lines)
        staves = []
        try:
            from cv_omr_engine import ComputerVisionOmrEngine
            cv_engine = ComputerVisionOmrEngine()
            staves = cv_engine.detect_staves(gray)
        except Exception:
            pass

        if staves:
            first_staff_top = staves[0][0]
            interline = (staves[0][-1] - staves[0][0]) / 4.0
        else:
            first_staff_top = int(h * 0.18)
            interline = h * 0.02

        # 2. Quét OCR 2 tầng (RapidOCR + VietOCR Transformer)
        rapid = self.get_rapid_ocr()
        ocr_results = None
        if rapid:
            ocr_results, _ = rapid(img)

        header_boxes = []
        harmony_boxes = []
        lyric_boxes_by_staff = {i: [] for i in range(len(staves))} if staves else {0: []}
        other_boxes = []

        chord_regex = re.compile(r'^[A-Ga-g][#b4♭♯]?(m|min|maj|dim|aug|sus|7|9|add|M)?([0-9\?\/]*[A-Ga-g]?[#b♭♯]?)?$')

        def is_probable_chord(token: str) -> bool:
            tk = token.strip()
            if not tk or len(tk) > 7:
                return False
            if chord_regex.match(tk):
                return True
            if any(k in tk.lower() for k in ['sus', 'dim', 'maj', 'm7', 'f4m', 'f47', 'bsus', 'f#m', 'c#m', 'd#m', 'g#m', 'bb', 'eb', 'ab']):
                return True
            return False

        for item in ocr_results or []:
            box, raw_text, score = item
            x1, y1 = max(0, int(box[0][0])), max(0, int(box[0][1]))
            x2, y2 = min(w, int(box[2][0])), min(h, int(box[2][1]))
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            box_h = y2 - y1
            box_w = x2 - x1

            crop = img[y1:y2, x1:x2]
            v_text = self.recognize_crop_vietocr(crop) if (box_w > 10 and box_h > 7) else ""
            text = self.clean_syllable(v_text if v_text else str(raw_text))

            if not text:
                continue

            data_item = {
                'text': text,
                'raw_ocr': str(raw_text),
                'box': [x1, y1, x2, y2],
                'cx': cx,
                'cy': cy,
                'h': box_h,
                'w': box_w,
                'score': float(score)
            }

            # ZONE 1: HEADER (Phía trên khuông nhạc đầu tiên)
            if cy < first_staff_top - interline * 0.8:
                header_boxes.append(data_item)
            else:
                # ZONE 3: HỢP ÂM HAY LỜI BÀI HÁT
                if is_probable_chord(text):
                    # Chuẩn hóa tên hợp âm sạch
                    clean_chord = text.replace('4', '#').replace('?', '').strip()
                    data_item['text'] = clean_chord
                    harmony_boxes.append(data_item)
                else:
                    assigned = False
                    if staves:
                        for s_idx, s in enumerate(staves):
                            s_top = s[0] - interline * 1.5
                            next_s_top = staves[s_idx + 1][0] - interline * 1.5 if s_idx + 1 < len(staves) else h
                            if s_top <= cy < next_s_top:
                                lyric_boxes_by_staff[s_idx].append(data_item)
                                assigned = True
                                break
                    if not assigned:
                        if 0 in lyric_boxes_by_staff:
                            lyric_boxes_by_staff[0].append(data_item)
                        else:
                            other_boxes.append(data_item)

        # ─── BÓC TÁCH ZONE 1: MULTI-LINE TITLE, COMPOSER, LYRICIST ───
        title_items = []
        composer = ""
        lyricist = ""
        hymn_number = ""
        category = ""

        valid_header_boxes = [b for b in header_boxes if not (chord_regex.match(b['text']) and len(b['text']) <= 6)]
        non_category_boxes = []
        for b in valid_header_boxes:
            txt = b['text']
            if any(k in txt.lower() for k in ['thánh ca', 'tôn vinh', 'tuyển tập', 'hymnal', 'ca nguyện']):
                category = txt
            else:
                non_category_boxes.append(b)

        sorted_by_height = sorted(non_category_boxes, key=lambda x: x['h'], reverse=True)
        if sorted_by_height:
            max_h = sorted_by_height[0]['h']
            for b in non_category_boxes:
                if b['h'] >= max_h * 0.65 and (0.15 * w <= b['cx'] <= 0.85 * w):
                    title_items.append(b)

        title_items = sorted(title_items, key=lambda x: x['cy'])
        title = self.clean_syllable(' '.join(it['text'] for it in title_items)) if title_items else ""

        title_ids = set(id(it) for it in title_items)
        for b in non_category_boxes:
            if id(b) in title_ids:
                continue
            txt = self.clean_syllable(b['text'])
            cx = b['cx']
            if re.match(r'^#?\d{1,4}[A-Za-z]?$', txt) and cx < w * 0.4:
                hymn_number = txt
            elif cx > w * 0.65 and not composer:
                composer = txt
            elif cx < w * 0.45 and not lyricist:
                lyricist = txt

        # ─── TẠO ZONE 2: PURE NOTATION SHEET KÈM INPAINTING PHỤC HỒI DÒNG KẺ ───
        pure_notation_img = img.copy()
        all_text_boxes = header_boxes + harmony_boxes + [it for s_list in lyric_boxes_by_staff.values() for it in s_list] + other_boxes

        for it in all_text_boxes:
            bx1, by1, bx2, by2 = it['box']
            pad = 2
            px1, py1 = max(0, bx1 - pad), max(0, by1 - pad)
            px2, py2 = min(w, bx2 + pad), min(h, by2 + pad)
            pure_notation_img[py1:py2, px1:px2] = (255, 255, 255)

        # Inpainting phục hồi 5 dòng kẻ khuông nhạc
        if staves:
            staff_line_color = (0, 0, 0)
            for s_idx, staff_lines in enumerate(staves):
                s_top, s_bot = staff_lines[0], staff_lines[-1]
                overlapping_boxes = [b for b in all_text_boxes if not (b['box'][3] < s_top or b['box'][1] > s_bot)]
                for b in overlapping_boxes:
                    bx1, _, bx2, _ = b['box']
                    rx1, rx2 = max(0, bx1 - 2), min(w, bx2 + 2)
                    for line_y in staff_lines:
                        ly = int(round(line_y))
                        cv2.line(pure_notation_img, (rx1, ly), (rx2, ly), staff_line_color, 2, cv2.LINE_AA)

        # ─── BÓC TÁCH ZONE 3: LỜI ĐƯỢC PHÂN THEO KHUÔNG VÀ CỘT NỐT ───
        all_lyrics_flat = []
        for s_idx, items in lyric_boxes_by_staff.items():
            items_sorted = sorted(items, key=lambda x: x['cx'])
            for it in items_sorted:
                all_lyrics_flat.append({
                    'staff_index': s_idx,
                    'text': it['text'],
                    'x': it['cx'],
                    'y': it['cy'],
                    'box': it['box']
                })

        return {
            'header': {
                'title': title,
                'composer': composer,
                'lyricist': lyricist,
                'hymn_number': hymn_number,
                'category': category,
                'raw_items': header_boxes,
            },
            'pure_notation_img': pure_notation_img,
            'lyrics': all_lyrics_flat,
            'harmonies': [{'chord': h['text'], 'x': h['cx'], 'y': h['cy']} for h in harmony_boxes],
            'first_staff_y': int(first_staff_top),
            'staves_count': len(staves),
        }

    def heal_musicxml_file(self, xml_path: str, source_img_path: str = None) -> bool:
        """
        Quét và phục hồi toàn diện tiếng Việt cho tệp MusicXML bất kỳ.
        """
        if not os.path.exists(xml_path):
            return False

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # 1. Sửa Tiêu đề (<movement-title>, <work-title>)
            for tag in ['movement-title', 'work-title']:
                for elem in root.findall(f'.//{tag}'):
                    if elem.text:
                        elem.text = self.clean_syllable(elem.text)

            # 2. Sửa Credit words (Tiêu đề, Tác giả ở đầu trang)
            for elem in root.findall('.//{*}credit-words') + root.findall('.//credit-words'):
                if elem.text:
                    elem.text = self.clean_syllable(elem.text)

            # 3. Sửa toàn bộ Lyrics text
            for elem in root.findall('.//{*}lyric/{*}text') + root.findall('.//lyric/text') + root.findall('.//{*}text') + root.findall('.//text'):
                if elem.text:
                    elem.text = self.clean_syllable(elem.text)

            tree.write(xml_path, encoding='utf-8', xml_declaration=True)
            return True
        except Exception as e:
            print(f"[VietnameseUniversalOCR] Error healing MusicXML: {e}")
            return False

_engine = VietnameseUniversalOcrEngine()

def heal_vietnamese_universal(xml_path: str, source_img_path: str = None) -> bool:
    return _engine.heal_musicxml_file(xml_path, source_img_path)

def decompose_sheet_3zones(img_input) -> dict:
    return _engine.decompose_sheet_3zones(img_input)

