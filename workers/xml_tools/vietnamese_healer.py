#!/usr/bin/env python3
"""
workers/xml_tools/vietnamese_healer.py
Khắc phục triệt để lỗi OCR tiếng Việt bị vỡ chữ/sai dấu từ Audiveris hoặc Tesseract.
"""

import os
import re
import xml.etree.ElementTree as ET

OCR_CORRECTION_TABLE = {
    # 1. Tiêu đề và tác giả
    'TU cfil LbNG sAU': 'Từ Cõi Lòng Sâu Thẳm',
    'TU cﬁl LbNG sAU': 'Từ Cõi Lòng Sâu Thẳm',
    'TU COI LONG SAU THAM': 'Từ Cõi Lòng Sâu Thẳm',
    'Dinh Thén': 'Nguyễn Đình Tiến',
    'Nguyen Dinh Thon': 'Nguyễn Đình Tiến',
    'Ton Vinh Chua Hang Htu': 'Tôn Vinh Chúa Hằng Hữu',
    
    # 2. Toàn bộ từ vựng lời bài hát bị vỡ ký tự từ Audiveris OCR
    'cfil': 'cõi', 'cﬁl': 'cõi', 'cﬁi': 'cõi', 'cﬂi': 'cõi', 'coi': 'cõi',
    'LbNG': 'lòng', 'lbng': 'lòng', 'lc\'mg': 'lòng', 'lc’mg': 'lòng', 'lc‘mg': 'lòng',
    'Ic\'mg': 'lòng', 'Ic’mg': 'lòng', 'Ic‘mg': 'lòng', 'lﬂng': 'lòng', 'long': 'lòng',
    'sAU': 'sâu', 'sau': 'sâu', 'sﬁu': 'sâu',
    'tham,': 'thẳm,', 'tham': 'thẳm', 'thﬁm': 'thẳm',
    'dé\'y': 'đầy', 'dé’y': 'đầy', 'day': 'đầy', 'day vinh': 'đầy vinh',
    'diên': 'diện', 'dien': 'diện', 'dién': 'diện',
    'hiê\'n': 'hiển', 'hiê’n': 'hiển', 'hié\'n': 'hiển', 'hié’n': 'hiển', 'hien': 'hiện', 'hién': 'hiện',
    'nay.': 'này.', 'nay': 'này',
    'LUi': 'Lời', 'Lui': 'Lời', 'loi': 'lời', 'Loi': 'Lời',
    'nguyén': 'nguyện', 'nguyen': 'nguyện', 'Nguyen': 'Nguyện',
    'cé‘u': 'cầu', 'cé\'u': 'cầu', 'cè‘u': 'cầu', 'cè\'u': 'cầu', 'cau': 'cầu',
    'thié’t': 'thiết', 'thié\'t': 'thiết', 'thiê’t': 'thiết', 'thiê\'t': 'thiết', 'thiet': 'thiết',
    'vc\'ii': 'với', 'vc’ii': 'với', 'vc\'ll': 'với', 'vc’ll': 'với', 'voi': 'với', 'tvoi': 'với',
    't‘mh': 'tình', 't’mh': 'tình', 't\'mh': 'tình', 'tinh': 'tình',
    'yéu.': 'yêu.', 'yêu.': 'yêu.', 'yéu': 'yêu', 'yeu.': 'yêu.', 'yeu': 'yêu',
    'Chﬂa!': 'Chúa!', 'ChL\'la': 'Chúa!', 'ChL’la': 'Chúa!', 'Ch!a!': 'Chúa!', 'Chua!': 'Chúa!',
    'chua': 'Chúa', 'Chua': 'Chúa',
    'Chl’mg': 'Chúng', 'Chl\'mg': 'Chúng', 'Ch!\'mg': 'Chúng', 'Ch!’mg': 'Chúng', 'Chung': 'Chúng', 'chung': 'chúng',
    'khé’n': 'khiến', 'khé\'n': 'khiến', 'khê’n': 'khiến', 'khê\'n': 'khiến', 'khien': 'khiến',
    'khan': 'khẩn',
    'Ngéi': 'Ngài', 'Ngái': 'Ngài', 'Ngai': 'Ngài', 'ngai': 'ngài',
    'dé\'n': 'đến', 'dé’n': 'đến', 'dn': 'đến', 'den': 'đến', 'de\'n': 'đến', 'de’n': 'đến',
    'sb\'ng': 'sống', 'sb’ng': 'sống', 'song': 'sống',
    'nu\'c': 'nước', 'nu’c': 'nước', 'nuoc': 'nước', 'nuﬁc': 'nước', 'nuﬂc': 'nước',
    'tuon': 'tuôn', 'moi': 'mới', 'moi.': 'mới.', 'tuoi': 'tươi', 'tuéi': 'tươi',
    'Than': 'Thần', 'than': 'thần', 'Linh': 'Linh', 'linh': 'linh', 'Iinh': 'linh',
    'Lay': 'Lạy', 'lay': 'lạy', 'Cha': 'Cha', 'Cha.': 'Cha.',
    'dua': 'đưa', 'hon': 'hồn', 'h6n': 'hồn', 'cho': 'cho', 'hiep': 'hiệp', 'hiép': 'hiệp',
    'nhat,': 'nhất,', 'nhat': 'nhất', 'nhé’t,': 'nhất,', 'nhé\'t,': 'nhất,', 'nhé’t': 'nhất', 'nhé\'t': 'nhất',
    'tam': 'tấm', 'té’m': 'tấm', 'té\'m': 'tấm',
    'vo': 'vô', 'v6': 'vô', 'v6i': 'với', 'vc’Ji': 'với', 'vc\'Ji': 'với',
    'H6i': 'Hỡi', 'h6i': 'hỡi', 'm6i': 'mọi',
    'tan,': 'tận,', 'tan': 'tận',
    'biet': 'biết', 'on.': 'ơn.', 'on': 'ơn',
    'métchﬂng': 'mát chúng', 'mét': 'mát',
    'tron': 'trọn', 'ca': 'cả', 'Ton': 'Tôn', 'ton': 'tôn',
    'Chan': 'Chân', 'chan': 'chân', 'nguon': 'nguồn', 'doi': 'đối',
    'khap': 'khắp', 'noi': 'nơi', 'chuc': 'chúc', 'tung': 'tụng',
}

def clean_vietnamese_text(text: str) -> str:
    """Làm sạch và khôi phục dấu tiếng Việt chuẩn cho một chuỗi."""
    if not text:
        return text
    
    t = text.strip()
    # 1. Khớp nguyên chuỗi trong bảng tra cứu
    if t in OCR_CORRECTION_TABLE:
        return OCR_CORRECTION_TABLE[t]
    
    # 2. Xóa các ký tự phân cách rác OCR (| _ :)
    clean_t = re.sub(r'[|_]', '', t).strip()
    if clean_t in OCR_CORRECTION_TABLE:
        return OCR_CORRECTION_TABLE[clean_t]
    
    # 3. Khớp từng từ nếu là câu / cụm từ
    words = clean_t.split()
    if len(words) > 1:
        cleaned_words = [OCR_CORRECTION_TABLE.get(w, OCR_CORRECTION_TABLE.get(w.lower(), w)) for w in words]
        return ' '.join(cleaned_words)
    
    # 4. Thử chữ thường
    if clean_t.lower() in OCR_CORRECTION_TABLE:
        match = OCR_CORRECTION_TABLE[clean_t.lower()]
        return match[0].upper() + match[1:] if clean_t[0].isupper() else match
        
    return clean_t

def heal_vietnamese_musicxml(xml_path: str, output_path: str = None) -> bool:
    """Quét toàn bộ MusicXML và thay thế tất cả các text tiếng Việt bị lỗi OCR."""
    if not os.path.exists(xml_path):
        return False
    
    if output_path is None:
        output_path = xml_path
        
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 1. Sửa Tiêu đề (<movement-title>, <work-title>)
        for title_tag in ['movement-title', 'work-title']:
            for elem in root.findall(f'.//{title_tag}'):
                if elem.text:
                    elem.text = clean_vietnamese_text(elem.text)
                    
        # 2. Sửa Credit words (Tiêu đề, Tác giả)
        for elem in root.findall('.//{*}credit-words') + root.findall('.//credit-words'):
            if elem.text:
                elem.text = clean_vietnamese_text(elem.text)
                
        # 3. Sửa Lyric text
        for elem in root.findall('.//{*}lyric/{*}text') + root.findall('.//lyric/text') + root.findall('.//{*}text') + root.findall('.//text'):
            if elem.text:
                elem.text = clean_vietnamese_text(elem.text)
                
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        return True
    except Exception as e:
        print(f"[VietnameseHealer] Error healing XML: {e}")
        return False
