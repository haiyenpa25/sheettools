#!/usr/bin/env python3
"""
workers/xml_tools/vietnamese_universal_ocr.py
═══════════════════════════════════════════════════════════════════════════════
SPATIAL VIETNAMESE OCR & MUSICXML TEXT LAYERS
═══════════════════════════════════════════════════════════════════════════════
Quy trình trích xuất văn bản sâu:
1. Dò bố cục và giữ hành lang khuông/nốt khi tạo các lớp chữ dẫn xuất.
2. Phân tầng không gian theo từng khuông nhạc:
   - Header Band (y < Staff₀): Tiêu đề, Tác giả, Nhạc sĩ, Điệu nhạc.
   - Chords Band (Trên khuông): Hợp âm (Em, G/B, F#m7, B7...).
   - Lyric Band (Dưới khuông): Lời hát tiếng Việt chuẩn thanh điệu.
3. Chạy VietOCR VGG-Transformer + RapidOCR trên lớp chữ đã làm sạch.
4. Căn lời/hợp âm theo hình học, giữ các kết quả không chắc chắn để soát.
"""

import os
import re
import unicodedata
from difflib import SequenceMatcher
import cv2
import numpy as np
import xml.etree.ElementTree as ET
from PIL import Image
from pathlib import Path
from .text_roles import is_chord, classify_text_line, cluster_text_rows

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
    'CÔI': 'CÕI', 'CỐI': 'CÕI', 'Côi': 'Cõi', 'côi': 'cõi',
    'THĂM': 'THẲM', 'Thăm': 'Thẳm', 'thăm': 'thẳm', 'thằm,': 'thẳm,', 'thằm': 'thẳm',
    'Thôn': 'Tiến', 'thon': 'tiến',
    'Võ': 'Vỡ', 'vo~': 'vỡ', 'Chúal': 'Chúa!', 'Chúa[': 'Chúa!', 'Chúa]': 'Chúa!',
    'nguyên': 'nguyện', 'nguyen': 'nguyện', 'tối': 'tới', 'nhất;': 'nhất',
}


def select_ocr_candidate(
    rapid_text: str,
    rapid_confidence: float,
    tesseract_text: str,
    tesseract_confidence: float,
) -> tuple[str, float, str]:
    """Select an OCR result without language-model guessing or silent correction."""
    rapid = (rapid_text or "").strip()
    tess = (tesseract_text or "").strip()
    candidates = []
    if rapid:
        candidates.append((rapid, max(0.0, min(1.0, float(rapid_confidence))), "rapidocr"))
    if tess:
        candidates.append((tess, max(0.0, min(1.0, float(tesseract_confidence))), "tesseract"))
    return max(candidates, key=lambda item: item[1]) if candidates else ("", 0.0, "none")


def select_vietnamese_candidate(candidates: list[dict]) -> tuple[str, float, str]:
    """Prefer a diacritic-preserving candidate when visual readings otherwise agree."""
    valid = [item for item in candidates if str(item.get('text', '')).strip()]
    if not valid:
        return "", 0.0, "none"

    def folded(text: str) -> str:
        normalized = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
        return ''.join(char for char in normalized if unicodedata.category(char) != 'Mn' and char.isalnum())

    def mark_count(text: str) -> int:
        return sum(1 for char in unicodedata.normalize('NFD', text) if unicodedata.category(char) == 'Mn') + text.lower().count('đ')

    best = max(valid, key=lambda item: float(item.get('confidence', 0.0)))
    best_folded = folded(str(best['text']))
    same_reading = [item for item in valid if folded(str(item['text'])) == best_folded]
    marked = max(same_reading, key=lambda item: mark_count(str(item['text'])), default=best)
    # Confidence from different OCR engines is not directly calibrated. When
    # base letters are identical, a viable Vietnamese-engine reading with
    # explicit tone marks carries more information than an accentless reading.
    if mark_count(str(marked['text'])) > mark_count(str(best['text'])) and float(marked.get('confidence', 0.0)) >= 0.60:
        best = marked

    # For line OCR, fuse tokens independently. This recovers
    # "NGOI CA TINH..." + "NGƠI ễA TÌNH..." as
    # "NGƠI CA TÌNH..." instead of accepting the hallucinated whole line.
    base_tokens = str(best['text']).split()
    tokenized = [(item, str(item['text']).split()) for item in valid]
    if len(base_tokens) > 1 and all(len(tokens) == len(base_tokens) for _, tokens in tokenized):
        fused = []
        used_engines = set()
        for index, base_token in enumerate(base_tokens):
            base_core = re.sub(r'^\W+|\W+$', '', base_token, flags=re.UNICODE)
            prefix = base_token[:len(base_token) - len(base_token.lstrip('“"\'([{'))]
            suffix_match = re.search(r'[^\wÀ-ỹĐđ]+$', base_token, flags=re.UNICODE)
            suffix = suffix_match.group(0) if suffix_match else ''
            choice = base_core
            for item, tokens in tokenized:
                candidate_token = tokens[index]
                candidate_core = re.sub(r'^\W+|\W+$', '', candidate_token, flags=re.UNICODE)
                incoherent_case = bool(candidate_core[:1].islower() and any(char.isupper() for char in candidate_core[1:]))
                similarity = SequenceMatcher(None, folded(candidate_core), folded(base_core)).ratio()
                if (
                    not incoherent_case
                    and similarity >= 0.65
                    and abs(len(candidate_core) - len(base_core)) <= 1
                    and float(item.get('confidence', 0.0)) >= 0.60
                    and mark_count(candidate_core) > mark_count(choice)
                ):
                    choice = candidate_core
                    used_engines.add(str(item.get('engine', 'unknown')))
            fused.append(prefix + choice + suffix)
        fused_text = ' '.join(fused)
        if fused_text != str(best['text']):
            return fused_text, min(float(item.get('confidence', 0.0)) for item in valid), 'consensus:' + '+'.join(sorted(used_engines or {'multi'}))
    return str(best['text']), float(best.get('confidence', 0.0)), str(best.get('engine', 'unknown'))

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

    # Danh mục từ vựng Thánh ca & Âm nhạc ngữ cảnh chuẩn
    HYMN_PHRASE_FIXES = {
        'nguyên cầu': 'nguyện cầu',
        'tha thiet': 'tha thiết',
        'khan thiết': 'khẩn thiết',
        'thần linh': 'Thần Linh',
        'vinh hiện': 'vinh hiển',
        'vinh hiến': 'vinh hiển',
        'tuoi moi': 'tươi mới',
        'nuoc song': 'nước sống',
        'hiep nhat': 'hiệp nhất',
        'vo tan': 'vỡ tan',
        'biet on': 'biết ơn',
        'dinh thon': 'Đình Tiến',
        'nguyen dinh tien': 'Nguyễn Đình Tiến',
        'ton vinh': 'Tôn vinh',
        'chan than': 'Chân Thần',
        'nguon on': 'nguồn ơn',
        'vo doi': 'vô đối',
    }

    def clean_syllable(self, text: str) -> str:
        """Chuẩn hóa và khôi phục dấu tiếng Việt chuẩn cho một âm tiết/từ/câu."""
        if not text:
            return ""
        t = text.strip()

        if t in LIGATURE_MAP:
            return LIGATURE_MAP[t]

        clean = re.sub(r'[|_~`]', '', t).strip()
        if clean in LIGATURE_MAP:
            return LIGATURE_MAP[clean]

        # Kiểm tra cụm từ ngữ cảnh Thánh ca
        clean_lower = clean.lower()
        for wrong_phr, right_phr in self.HYMN_PHRASE_FIXES.items():
            if wrong_phr in clean_lower:
                clean = re.sub(re.escape(wrong_phr), right_phr, clean, flags=re.IGNORECASE)

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
        """
        Nhận diện vùng ảnh crop bằng VietOCR Transformer với tiền xử lý đệm biên (Padding)
        và tăng cường độ nét để không bao giờ bị mất dấu mũ/nón/hỏi/ngã/nặng.
        """
        vietocr = self.get_vietocr()
        if vietocr is None or img_crop is None or img_crop.size == 0:
            return ""

        try:
            # 1. Thêm viền trắng (Padding 6px) để dấu không bị cắt mép
            pad = 6
            h_c, w_c = img_crop.shape[:2]
            if len(img_crop.shape) == 3:
                padded = cv2.copyMakeBorder(img_crop, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
            else:
                padded = cv2.copyMakeBorder(img_crop, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)

            # 2. Tăng cường độ nét nếu crop nhỏ
            if h_c < 30:
                scale = 32.0 / max(1, h_c)
                padded = cv2.resize(padded, (int(w_c * scale), 32), interpolation=cv2.INTER_CUBIC)

            pil_img = Image.fromarray(cv2.cvtColor(padded, cv2.COLOR_BGR2RGB) if len(padded.shape) == 3 else padded)
            predicted = vietocr.predict(pil_img).strip()
            return self.clean_syllable(predicted)
        except Exception:
            return ""

    def recognize_crop_tesseract(self, img_crop: np.ndarray) -> tuple[str, float]:
        """Recognize a detected word/line crop with the installed Vietnamese LSTM model."""
        if img_crop is None or img_crop.size == 0:
            return "", 0.0
        try:
            import pytesseract
            from pytesseract import Output

            height, width = img_crop.shape[:2]
            padded = cv2.copyMakeBorder(
                img_crop, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=(255, 255, 255)
            )
            target_height = max(64, int(height * 1.5))
            scale = target_height / max(1, padded.shape[0])
            padded = cv2.resize(
                padded,
                (max(1, int(padded.shape[1] * scale)), target_height),
                interpolation=cv2.INTER_CUBIC,
            )
            psm = 7 if width / max(1, height) >= 3.0 else 8
            data = pytesseract.image_to_data(
                padded,
                lang="vie",
                config=f"--oem 1 --psm {psm}",
                output_type=Output.DICT,
            )
            words = []
            confidences = []
            for text, confidence in zip(data.get("text", []), data.get("conf", [])):
                token = str(text).strip()
                try:
                    conf = float(confidence)
                except (TypeError, ValueError):
                    conf = -1.0
                if token and conf >= 0:
                    words.append(token)
                    confidences.append(conf / 100.0)
            return " ".join(words), (sum(confidences) / len(confidences) if confidences else 0.0)
        except Exception as exc:
            print(f"[VietnameseOCR] Tesseract crop notice: {exc}")
            return "", 0.0

    def recognize_line_tesseract(self, img_crop: np.ndarray, scale: float = 1.0) -> str:
        """Read a whole lyric line; line context keeps Vietnamese marks far better than word crops."""
        if img_crop is None or img_crop.size == 0:
            return ""
        try:
            import pytesseract
            resized = cv2.resize(img_crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale != 1.0 else img_crop
            padded = cv2.copyMakeBorder(resized, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            return pytesseract.image_to_string(padded, lang="vie", config="--oem 1 --psm 7").strip()
        except Exception as exc:
            print(f"[VietnameseOCR] Tesseract line notice: {exc}")
            return ""

    def fuse_lyric_line(self, img: np.ndarray, items: list[dict]) -> None:
        """Restore marks on detector tokens of one lyric row using whole-line readings."""
        from xml_tools.vi_lexicon import vietnamese_syllables
        from xml_tools.vi_syllable import fuse_line
        words = [it for it in items if not re.fullmatch(r'\d+[.)]', str(it['text']).strip())]
        if not words:
            return
        h, w = img.shape[:2]
        x1 = max(0, min(it['box'][0] for it in words) - 10)
        y1 = max(0, min(it['box'][1] for it in words) - 4)
        x2 = min(w, max(it['box'][2] for it in words) + 10)
        y2 = min(h, max(it['box'][3] for it in words) + 4)
        crop = img[y1:y2, x1:x2]
        line_readings = [(text, 1.0) for text in (self.recognize_line_tesseract(crop, 1.0),
                                                   self.recognize_line_tesseract(crop, 1.5)) if text]
        base_tokens, token_readings = [], []
        for it in words:
            candidates = it.get('ocr_candidates', [])
            rapid = next((c['text'] for c in candidates if c.get('engine') == 'rapidocr' and c.get('scope') != 'line'), None)
            base_tokens.append(str(rapid if rapid and rapid.strip() else it['text']).strip())
            token_readings.append([(c['text'], .5) for c in candidates
                                   if c.get('engine') in ('tesseract', 'vietocr') and c.get('scope') != 'line' and c.get('text')])
        fused = fuse_line(base_tokens, line_readings, token_readings, vietnamese_syllables())
        for it, base, result in zip(words, base_tokens, fused):
            rapid_conf = max((float(c.get('confidence', 0)) for c in it.get('ocr_candidates', []) if c.get('engine') == 'rapidocr'), default=float(it.get('score', 0)))
            confidence = rapid_conf * (.6 + .4 * float(result['support']))
            if result['needs_review']:
                confidence = min(confidence, .5)
            it['text'] = unicodedata.normalize('NFC', result['text'])
            it['score'] = round(confidence, 4)
            it['ocr_engine'] = 'fusion:' + result['source']
            it['diacritic_fusion'] = {'base': base, 'line_readings': [text for text, _ in line_readings], **result}

    def reocr_chord_box(self, img: np.ndarray, box: list[int]) -> tuple[str, float] | None:
        """Re-read a short above-staff box as chord symbols.

        Superscript flats (B♭, E♭) are misread on the full page ("48", "4日");
        a padded, upscaled crop is read reliably. Only a result in which every
        token satisfies the chord grammar is returned.
        """
        rapid = self.get_rapid_ocr()
        if rapid is None:
            return None
        h, w = img.shape[:2]
        x1, y1, x2, y2 = box
        crop = img[max(0, y1 - 6):min(h, y2 + 6), max(0, x1 - 8):min(w, x2 + 8)]
        if crop.size == 0:
            return None
        crop = cv2.copyMakeBorder(crop, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        for scale in (2.0, 1.0, 3.0):
            resized = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            results, _ = rapid(resized)
            results = sorted(results or [], key=lambda item: item[0][0][0])
            tokens = [token for item in results for token in str(item[1]).split()]
            if tokens and all(is_chord(token) for token in tokens):
                return ' '.join(tokens), min(float(item[2]) for item in results)
        return None

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

    def decompose_sheet_3zones(self, img_input, page_model: dict | None = None) -> dict:
        """
        Phân tích trang theo page model dùng chung và các vai trò chữ:
        - ZONE 1: Header Zone (Ghép tiêu đề nhiều dòng, tác giả lệch phải, lời dịch lệch trái, số bài)
        - ZONE 2: Notation Sheet (white-fill mask chữ ngoài hành lang bảo vệ)
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
        from preprocessing.page_layout import PageLayoutAnalyzer
        if page_model is None:
            page_model = PageLayoutAnalyzer().analyze_image(gray)
        staves = [staff['lines_y'] for staff in page_model['staff_candidates']]

        if staves:
            first_staff_top = staves[0][0]
            interline = page_model['interline']
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
            tess_text, tess_score = self.recognize_crop_tesseract(crop) if (box_w > 10 and box_h > 7) else ("", 0.0)
            candidates = [
                {'text': str(raw_text), 'confidence': float(score), 'engine': 'rapidocr'},
                {'text': tess_text, 'confidence': float(tess_score), 'engine': 'tesseract'},
            ]
            if v_text:
                candidates.append({'text': v_text, 'confidence': 0.75, 'engine': 'vietocr'})
            selected_text, selected_score, selected_engine = select_vietnamese_candidate(candidates)
            from xml_tools.vietnamese_context import restore_liturgical_diacritics
            selected_text, context_changes = restore_liturgical_diacritics(selected_text)
            if context_changes:
                selected_engine += '+context'
            text = unicodedata.normalize('NFC', selected_text).strip()

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
                'score': float(selected_score),
                'ocr_engine': selected_engine,
                'ocr_candidates': candidates,
                'context_changes': context_changes,
            }

            # ZONE 1: HEADER (Phía trên khuông nhạc đầu tiên). Header giữ nguyên
            # cả dòng; dòng lời phải tách thành từng âm tiết trước khi căn nốt.
            band_name, system_id, staff_index = 'unknown', None, None
            for system in page_model['systems']:
                band_candidates = [('above', system['bands']['above'])] + [('between', band) for band in system['bands']['between']] + [('below', system['bands']['below'])]
                for name, band in band_candidates:
                    if band['box'][1] <= cy < band['box'][3]:
                        band_name, system_id = name, system['id']
                        staff_id = band.get('staff_id', system['staff_ids'][0])
                        staff_index = next(i for i, staff in enumerate(page_model['staff_candidates']) if staff['id'] == staff_id)
                        break
                if system_id:
                    break
            compact = text.replace(' ', '')
            # Every short above-staff box is re-read: a dropped superscript flat
            # still yields a grammatical chord ("BM7" for B♭M7) with high confidence.
            if band_name == 'above' and len(compact) <= 14 and box_h <= 3.5 * interline:
                chord_reading = self.reocr_chord_box(img, [x1, y1, x2, y2])
                if chord_reading:
                    text, chord_confidence = chord_reading
                    candidates.append({'text': text, 'confidence': chord_confidence, 'engine': 'rapidocr_chord_crop'})
                    data_item.update({'text': text, 'score': chord_confidence, 'ocr_engine': 'rapidocr_chord_crop'})
                elif all(is_chord(token) for token in str(raw_text).split()):
                    # Tesseract confidence on chord glyphs is meaningless; keep the detector's.
                    data_item.update({'text': str(raw_text).strip(), 'score': float(score), 'ocr_engine': 'rapidocr'})
                    text = data_item['text']
            line_role = classify_text_line(text, band_name)
            if cy > h*.9 and re.fullmatch(r'\d{1,4}', text):
                line_role['role'] = 'footer'
            tokens = split_ocr_line_item(data_item, img)
            page_model['text_lines'].append({'id': f"text_{len(page_model['text_lines'])+1:03d}",
                **data_item, **line_role, 'system_id': system_id, 'band': band_name,
                'line_index': None, 'tokens': tokens})
            if line_role['role'] == 'chord':
                for token_item in tokens:
                    if is_chord(token_item['text']):
                        token_item['staff_index'] = staff_index
                        token_item['system_id'] = system_id
                        harmony_boxes.append(token_item)
                continue
            if cy < first_staff_top - interline * 0.8:
                header_boxes.append(data_item)
                continue

            for token_item in tokens:
                token_text = token_item['text']
                # ZONE 3: HỢP ÂM HAY LỜI BÀI HÁT
                assigned = False
                if band_name in ('below', 'between') and line_role['role'] == 'lyric' and staff_index is not None:
                    token_item['system_id'] = system_id
                    lyric_boxes_by_staff[staff_index].append(token_item)
                    assigned = True
                if not assigned:
                    other_boxes.append(token_item)

        # ─── BÓC TÁCH ZONE 1: SEMANTIC DOCUMENT HEADER ───
        title_items = []
        composer = ""
        lyricist = ""
        hymn_number = ""
        category = ""

        valid_header_boxes = header_boxes
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

        title_items = sorted(title_items, key=lambda x: (round(x['cy'] / 40.0), x['cx']))
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

        from xml_tools.document_layout import analyze_header_semantics
        document_model = analyze_header_semantics(header_boxes, w, first_staff_top)
        title = document_model['title']['text'] or title
        composer = document_model['composer']['text'] or composer
        lyricist = document_model['lyricist']['text'] or lyricist
        hymn_number = document_model['hymn_number']['text'] or hymn_number
        category = document_model['collection']['text'] or category
        for line in page_model['text_lines']:
            semantic = next((region for region in document_model['semantic_regions'] if region.get('box') == line['box']), None)
            if semantic:
                line['role'] = semantic['role']
                line['needs_review'] = False
        for system in page_model['systems']:
            for band_name in ('above', 'between', 'below'):
                lines = [line for line in page_model['text_lines'] if line['system_id'] == system['id'] and line['band'] == band_name]
                for index, row in enumerate(cluster_text_rows(lines)):
                    for line in row:
                        line['line_index'] = index

        # ─── TẠO ZONE 2: NOTATION-FIRST, KHÔNG ĐƯỢC XÓA KÝ HIỆU TRONG KHUÔNG ───
        all_text_boxes = header_boxes + harmony_boxes + [it for s_list in lyric_boxes_by_staff.values() for it in s_list] + other_boxes
        from preprocessing.notation_layers import build_notation_layers
        layer_result = build_notation_layers(img, {
            'metadata': header_boxes,
            'lyrics': [it for s_list in lyric_boxes_by_staff.values() for it in s_list],
            'chords': harmony_boxes,
        }, staves, padding=max(1, int(round(.15*interline))))
        pure_notation_img = layer_result['notation_image']

        # ─── BÓC TÁCH ZONE 3: LỜI ĐƯỢC PHÂN TÁCH ĐA VERSE (VERSE 1 & VERSE 2) THEO DÒNG Y ───
        all_lyrics_flat = []
        for s_idx, items in lyric_boxes_by_staff.items():
            # Lọc bỏ ký hiệu hợp âm nếu còn sót
            valid_lyric_items = [
                it for it in items
                if not re.fullmatch(r'[#\d,:;]+', it['text'])
                and not re.fullmatch(r'[A-Za-z]', it['text'])
            ]
            if not valid_lyric_items:
                continue

            # Phân tách các dòng Verse khác nhau dưới cùng 1 khuông theo tọa độ Y
            verse_lines = cluster_text_rows(valid_lyric_items)

            # Sắp xếp các dòng verse từ trên xuống dưới (Dòng trên = Verse 1, Dòng dưới = Verse 2)
            verse_lines = sorted(verse_lines, key=lambda vl: sum(x['cy'] for x in vl) / len(vl))

            for v_idx, vl in enumerate(verse_lines):
                vl_sorted = sorted(vl, key=lambda x: x['cx'])
                self.fuse_lyric_line(img, vl_sorted)
                for it in vl_sorted:
                    all_lyrics_flat.append({
                        'staff_index': s_idx,
                        'system_id': it.get('system_id'),
                        'interline': interline,
                        'row_offset': (it['cy']-staves[s_idx][-1])/interline if staves else 0,
                        'box_source': it.get('box_source', 'ocr_detector'),
                        'geometry_needs_review': it.get('geometry_needs_review', False),
                        'verse_number': v_idx + 1,
                        'text': it['text'],
                        'x': it['cx'],
                        'y': it['cy'],
                        'box': it['box'],
                        'confidence': float(it.get('score', 0.0)),
                        'ocr_engine': it.get('ocr_engine'),
                        'raw_ocr': it.get('raw_ocr'),
                        'ocr_candidates': it.get('ocr_candidates', []),
                        'context_changes': it.get('context_changes', []),
                        'diacritic_fusion': it.get('diacritic_fusion'),
                    })

        # A sung phrase can continue at the next system. Run context over the
        # complete spatially ordered lyric stream, preserving every word box.
        from xml_tools.vietnamese_context import restore_liturgical_items
        all_lyrics_flat = restore_liturgical_items(all_lyrics_flat)
        from xml_tools.lyric_structure import detect_poem_stanzas
        stanzas = detect_poem_stanzas(all_lyrics_flat, staves[-1][-1], interline) if staves else []
        all_lyrics_flat = [word for word in all_lyrics_flat if not re.fullmatch(r'\d+[.)]', word['text'])]

        return {
            'page_model': page_model,
            'text_masks': layer_result['masks'],
            'stanzas': stanzas,
            'header': {
                'title': title,
                'composer': composer,
                'lyricist': lyricist,
                'hymn_number': hymn_number,
                'category': category,
                'description': document_model['description']['text'],
                'scripture_reference': document_model['scripture_reference']['text'],
                'document_model': document_model,
                'raw_items': header_boxes,
            },
            'pure_notation_img': pure_notation_img,
            'lyrics': all_lyrics_flat,
            'harmonies': [{'chord': h['text'], 'x': h['cx'], 'y': h['cy'], 'box': h['box'],
                           'confidence': h['score'], 'staff_index': h['staff_index'], 'system_id': h['system_id']} for h in harmony_boxes],
            'first_staff_y': int(first_staff_top),
            'staves_count': len(staves),
            'notation_separation': {
                'removed_text_boxes': len(layer_result['removed_boxes']),
                'protected_ocr_boxes': len(layer_result['protected_boxes']),
                'protected_bands': layer_result['protected_bands'],
            },
        }

    def inject_3zone_metadata_and_lyrics(self, xml_path: str, decomp_meta: dict, inject_lyrics: bool = True) -> bool:
        """
        Gắn toàn diện Tiêu đề thật, Tác giả thật, Hợp âm và toàn bộ Lời tiếng Việt (Đa Verse) từ 3-Zone OCR vào MusicXML.
        """
        if not os.path.exists(xml_path) or not decomp_meta:
            return False

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            header = decomp_meta.get('header', {})
            title = header.get('title')
            composer = header.get('composer')

            # 1. Cập nhật Tiêu đề (<work-title>, <movement-title>)
            if title:
                work = root.find('.//work')
                if work is None:
                    work = ET.SubElement(root, 'work')
                work_title = work.find('work-title')
                if work_title is None:
                    work_title = ET.SubElement(work, 'work-title')
                work_title.text = title

                mov_title = root.find('.//movement-title')
                if mov_title is None:
                    mov_title = ET.Element('movement-title')
                    root.insert(0, mov_title)
                mov_title.text = title

            # 2. Cập nhật Tác giả (<creator type="composer">)
            if composer:
                ident = root.find('.//identification')
                if ident is None:
                    ident = ET.SubElement(root, 'identification')
                comp_elem = None
                for c in ident.findall('creator'):
                    if c.get('type') == 'composer':
                        comp_elem = c
                        break
                if comp_elem is None:
                    comp_elem = ET.SubElement(ident, 'creator', {'type': 'composer'})
                comp_elem.text = composer

            lyricist = header.get('lyricist')
            if lyricist:
                ident = root.find('identification')
                if ident is None:
                    ident = ET.SubElement(root, 'identification')
                creator = next((item for item in ident.findall('creator') if item.get('type') == 'lyricist'), None)
                if creator is None:
                    creator = ET.SubElement(ident, 'creator', {'type': 'lyricist'})
                creator.text = lyricist

            # 2b. Preserve semantic page text as MusicXML credits. The complete
            # geometry and raw OCR remain authoritative in document.json.
            document_model = header.get('document_model', {})
            credit_roles = [
                ('title', 'title'),
                ('composer', 'composer'),
                ('lyricist', 'lyricist'),
                ('collection', 'subtitle'),
                ('hymn_number', 'title-number'),
                ('description', 'subtitle'),
                ('scripture_reference', 'subtitle'),
                ('translator', 'lyricist'),
                ('tempo', 'subtitle'),
                ('key_info', 'subtitle'),
                ('note', 'subtitle'),
            ]
            for role, credit_type in credit_roles:
                field = document_model.get(role, {})
                value = str(field.get('text', '')).strip()
                if not value:
                    continue
                credit = ET.SubElement(root, 'credit', {'page': '1'})
                ET.SubElement(credit, 'credit-type').text = credit_type
                attributes = {'justify': 'left' if role in ('collection', 'hymn_number') else 'center'}
                box = field.get('box', [])
                if len(box) == 4:
                    model = decomp_meta.get('page_model', {})
                    scale = 10/max(float(model.get('interline', 10)), 1)
                    attributes['default-x'] = str(round((float(box[0]) + float(box[2])) / 2.0*scale, 2))
                    attributes['default-y'] = str(round((float(model.get('height', 0))-(float(box[1]) + float(box[3])) / 2.0)*scale, 2))
                ET.SubElement(credit, 'credit-words', attributes).text = value

            if not inject_lyrics:
                order = {'work': 0, 'movement-number': 1, 'movement-title': 2, 'identification': 3,
                         'defaults': 4, 'credit': 5, 'part-list': 6, 'part': 7}
                root[:] = sorted(list(root), key=lambda element: order.get(element.tag, 8))
                tree.write(xml_path, encoding='utf-8', xml_declaration=True)
                return True

            # 3. Thu thập tất cả các nốt nhạc hợp lệ theo từng measure trong part
            measures = root.findall('.//part/measure')
            if not measures:
                measures = root.findall('.//measure')

            all_measure_notes = []
            for m in measures:
                notes = []
                for n in m.findall('note'):
                    if n.find('rest') is None:
                        is_chord = n.find('chord') is not None
                        if not is_chord:
                            notes.append(n)
                all_measure_notes.append(notes)

            # 4. Gắn toàn bộ Lời tiếng Việt từ 3-Zone OCR
            for m in measures:
                for n in m.findall('note'):
                    for lyr in n.findall('lyric'):
                        n.remove(lyr)

            flat_notes = [n for m_notes in all_measure_notes for n in m_notes]

            verses = {}
            for item in decomp_meta.get('lyrics', []):
                verse_number = int(item.get('verse_number', 1))
                text = str(item.get('text', '')).strip()
                if text:
                    verses.setdefault(verse_number, []).append(text)
            verse_indexes = {number: 0 for number in verses}
            for note in flat_notes:
                for verse_number in sorted(verses):
                    index = verse_indexes[verse_number]
                    if index >= len(verses[verse_number]):
                        continue
                    lyric = ET.SubElement(note, 'lyric', {'number': str(verse_number)})
                    ET.SubElement(lyric, 'syllabic').text = 'single'
                    ET.SubElement(lyric, 'text').text = verses[verse_number][index]
                    verse_indexes[verse_number] += 1

            tree.write(xml_path, encoding='utf-8', xml_declaration=True)
            return True
        except Exception as e:
            print(f"[VietnameseUniversalOCR] Error injecting 3-zone metadata/lyrics: {e}")
            return False

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

def inject_3zone_metadata_and_lyrics(xml_path: str, decomp_meta: dict, inject_lyrics: bool = True) -> bool:
    return _engine.inject_3zone_metadata_and_lyrics(xml_path, decomp_meta, inject_lyrics)

def decompose_sheet_3zones(img_input, page_model: dict | None = None) -> dict:
    return _engine.decompose_sheet_3zones(img_input, page_model)
def split_ocr_line_item(item: dict, image: np.ndarray | None = None) -> list[dict]:
    """Split a line-level OCR box into Vietnamese syllable boxes by character width."""
    tokens = [token for token in re.split(r'\s+', str(item.get('text', '')).strip()) if token]
    if len(tokens) <= 1:
        return [item]
    x1, y1, x2, y2 = item['box']
    total_units = sum(max(len(token), 1) for token in tokens) + (len(tokens) - 1)
    cursor = float(x1)
    available = float(x2 - x1)
    result = []
    from xml_tools.syllable_geometry import ink_word_boxes
    ink_boxes = ink_word_boxes(image, item['box'], len(tokens)) if image is not None else None
    for index, token in enumerate(tokens):
        token_width = available * max(len(token), 1) / total_units
        token_x1 = cursor
        token_x2 = float(x2) if index == len(tokens) - 1 else cursor + token_width
        child = dict(item)
        child.update({
            'text': token,
            'box': [int(round(token_x1)), y1, int(round(token_x2)), y2],
            'cx': (token_x1 + token_x2) / 2.0,
            'w': max(1, int(round(token_x2 - token_x1))),
        })
        if ink_boxes:
            child['box'] = ink_boxes[index]
            child['cx'] = (child['box'][0]+child['box'][2])/2
            child['w'] = child['box'][2]-child['box'][0]
        child['box_source'] = 'ink_projection' if ink_boxes else 'character_fallback'
        child['geometry_needs_review'] = ink_boxes is None
        child_candidates = []
        for candidate in item.get('ocr_candidates', []):
            candidate_tokens = [value for value in re.split(r'\s+', str(candidate.get('text', '')).strip()) if value]
            candidate_copy = dict(candidate)
            candidate_copy['scope'] = 'token' if len(candidate_tokens) == len(tokens) else 'line'
            if len(candidate_tokens) == len(tokens):
                candidate_copy['text'] = candidate_tokens[index]
            child_candidates.append(candidate_copy)
        child['ocr_candidates'] = child_candidates
        result.append(child)
        cursor = token_x2 + available / total_units
    return result
