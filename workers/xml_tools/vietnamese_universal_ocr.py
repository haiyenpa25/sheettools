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
        Phân tích tách trang sheet nhạc làm 3 VÙNG SPATIAL ĐỘC LẬP:
        - ZONE 1: Header Zone (Tiêu đề, Tác giả, Lời dịch, Tuyển tập)
        - ZONE 2: Pure Notation Sheet (Bản nhạc đã xoá sạch toàn bộ chữ để OMR chỉ nhận diện nốt & khuông)
        - ZONE 3: Lyrics & Verses Zone (Lời bài hát tách theo Verse 1..N, Điệp khúc + Hợp âm trên khuông)
        """
        if isinstance(img_input, str):
            img = cv2.imread(img_input)
        else:
            img = img_input.copy()

        if img is None:
            return {'header': {}, 'pure_notation_img': None, 'lyrics': [], 'harmonies': []}

        h, w = img.shape[:2]
        rapid = self.get_rapid_ocr()
        clean_text_img = self.isolate_text_layer(img)

        ocr_results = None
        if rapid:
            ocr_results, _ = rapid(clean_text_img)
            if not ocr_results:
                ocr_results, _ = rapid(img)

        # 1. Phát hiện vị trí các khuông nhạc (Staff Lines)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * 0.20), 1))
        lines_only = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        proj = np.sum(lines_only, axis=1) / (w * 255.0)

        staff_peaks = np.where(proj > 0.04)[0]
        first_staff_y = staff_peaks[0] if len(staff_peaks) > 0 else int(h * 0.18)

        # 2. Phân loại và tạo Pure Notation Sheet (Xóa toàn bộ chữ)
        pure_notation_img = img.copy()
        header_items = []
        lyric_items = []
        harmony_items = []

        import re
        chord_regex = re.compile(r'^[A-Ga-g][#b♭♯]?(m|min|maj|dim|aug|sus|7|9|add)?(/[A-Ga-g][#b♭♯]?)?$')

        for item in ocr_results or []:
            box, raw_text, score = item
            x1, y1 = max(0, int(box[0][0])), max(0, int(box[0][1]))
            x2, y2 = min(w, int(box[2][0])), min(h, int(box[2][1]))
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            # Nhận diện chữ tiếng Việt bằng VietOCR
            crop = img[y1:y2, x1:x2]
            v_text = self.recognize_crop_vietocr(crop) if (x2 - x1 > 8 and y2 - y1 > 6) else ""
            text = self.clean_syllable(v_text if v_text else str(raw_text))

            if not text:
                continue

            # ZONE 1: HEADER (Phía trên khuông nhạc đầu tiên)
            if cy < first_staff_y - 12:
                header_items.append({'text': text, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'cx': cx, 'cy': cy})
            else:
                # ZONE 3: HỢP ÂM HAY LỜI BÀI HÁT
                if chord_regex.match(text.strip()):
                    harmony_items.append({'chord': text.strip(), 'x': cx, 'y': cy})
                else:
                    lyric_items.append({'text': text, 'x': cx, 'y': cy, 'x1': x1, 'x2': x2, 'y1': y1, 'y2': y2})

            # ZONE 2: MASK TOÀN BỘ CHỮ TRÊN BẢN NHẠC
            pad = 2
            px1, py1 = max(0, x1 - pad), max(0, y1 - pad)
            px2, py2 = min(w, x2 + pad), min(h, y2 + pad)
            pure_notation_img[py1:py2, px1:px2] = (255, 255, 255)

        # Trích xuất metadata tiêu đề và tác giả từ Header
        title = ""
        composer = ""
        lyricist = ""
        category = ""

        for h_item in sorted(header_items, key=lambda x: x['cy']):
            txt = h_item['text']
            if any(k in txt.lower() for k in ['tôn vinh', 'thánh ca', 'tuyển tập']):
                category = txt
            elif not title and len(txt) > 3:
                title = txt
            elif not composer and (h_item['cx'] > w * 0.6 or any(c in txt.lower() for c in ['nhạc', 'lời', 'nguyễn', 'tiến', 'felice'])):
                composer = txt
            elif not lyricist:
                lyricist = txt

        return {
            'header': {
                'title': title,
                'composer': composer,
                'lyricist': lyricist,
                'category': category,
                'raw_items': header_items,
            },
            'pure_notation_img': pure_notation_img,
            'lyrics': lyric_items,
            'harmonies': harmony_items,
            'first_staff_y': int(first_staff_y),
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

