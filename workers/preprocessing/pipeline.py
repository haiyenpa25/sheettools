"""
Pipeline tiền xử lý ảnh bản nhạc sử dụng OpenCV
- Deskew (Chỉnh góc nghiêng khuông nhạc)
- Grayscale & Contrast enhancement
- Denoise & Binarize
"""

import sys
import os
import argparse
import numpy as np

def preprocess_image(input_path: str, output_path: str) -> bool:
    try:
        import cv2
    except ImportError:
        print("ERROR: OpenCV (cv2) is not installed. Run: pip install opencv-python")
        return False

    if not os.path.exists(input_path):
        print(f"ERROR: Input file does not exist: {input_path}")
        return False

    img = cv2.imread(input_path)
    if img is None:
        print(f"ERROR: Cannot decode image: {input_path}")
        return False

    # 1. Chuyển Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Khử nhiễu nhẹ
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # 3. Tăng tương phản bằng CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(denoised)

    # Đảm bảo thư mục đích tồn tại
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Lưu kết quả
    cv2.imwrite(output_path, contrast)
    print(f"SUCCESS: Preprocessed image saved to {output_path}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sheet Music Image Preprocessing Pipeline")
    parser.add_argument("--input", "-i", required=True, help="Path to input image/page")
    parser.add_argument("--output", "-o", required=True, help="Path to output preprocessed image")
    args = parser.parse_args()

    success = preprocess_image(args.input, args.output)
    sys.exit(0 if success else 1)
