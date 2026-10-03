#!/usr/bin/env python3
"""
workers/preprocessing/pipeline.py
Pipeline tiền xử lý ảnh bản nhạc nâng cao:
  1. Grayscale conversion
  2. Shadow removal (tăng độ đồng đều ánh sáng cho ảnh chụp điện thoại)
  3. Adaptive Binarization (Sauvola — tốt hơn ngưỡng cố định 200 trên ảnh scan không đồng đều)
  4. Deskew tự động bằng Hough Line Transform (chỉnh góc nghiêng ±10°)
  5. CLAHE Contrast Enhancement sau khi deskew
  6. Fast Non-Local Means Denoising
"""

import sys
import os
import argparse
import json
import numpy as np


def analyze_image_quality(gray: np.ndarray) -> dict:
    """Classify a page before filtering so clean scans are not overprocessed."""
    import cv2
    if gray.ndim != 2:
        raise ValueError("quality analysis requires a grayscale image")
    sampled = gray[::max(1, gray.shape[0] // 800), ::max(1, gray.shape[1] // 800)]
    near_binary = float(np.mean((sampled < 24) | (sampled > 231)))
    contrast = float(np.std(sampled))
    blur_score = float(cv2.Laplacian(sampled, cv2.CV_64F).var())
    blocks = cv2.resize(sampled, (8, 8), interpolation=cv2.INTER_AREA)
    illumination_range = float(blocks.max() - blocks.min())
    binary_threshold = float(os.getenv('IMAGE_NEAR_BINARY_THRESHOLD', '0.96'))
    illumination_threshold = float(os.getenv('IMAGE_ILLUMINATION_RANGE_THRESHOLD', '90'))
    blur_threshold = float(os.getenv('IMAGE_BLUR_SCORE_THRESHOLD', '35'))
    if near_binary > binary_threshold:
        profile = "already_binary"
    elif illumination_range > illumination_threshold:
        profile = "uneven_lighting"
    elif blur_score < blur_threshold:
        profile = "low_resolution_or_blurred"
    else:
        profile = "clean_scan"
    return {
        "profile": profile,
        "metrics": {
            "near_binary_ratio": round(near_binary, 4),
            "contrast_std": round(contrast, 2),
            "blur_score": round(blur_score, 2),
            "illumination_range": round(illumination_range, 2),
        },
        "recommended": {
            "shadow_removal": profile == "uneven_lighting",
            "clahe": profile in {"uneven_lighting", "low_resolution_or_blurred"} or contrast < 38,
            "denoise": profile not in {"already_binary", "low_resolution_or_blurred"},
            "preserve_grayscale_for_omr": True,
        },
        "thresholds": {
            "near_binary_ratio": binary_threshold,
            "illumination_range": illumination_threshold,
            "blur_score": blur_threshold,
            "calibration_status": "heuristic_requires_dataset_benchmark",
        },
    }


def _sauvola_binarize(gray: np.ndarray, window_size: int = 25, k: float = 0.15) -> np.ndarray:
    """
    Sauvola Adaptive Thresholding — chuẩn nhất cho bản nhạc scan không đồng đều ánh sáng.
    Dùng giá trị mean và std cục bộ từng vùng nhỏ để tính ngưỡng động.
    """
    try:
        from skimage.filters import threshold_sauvola
        thresh = threshold_sauvola(gray, window_size=window_size, k=k)
        binary = (gray > thresh).astype(np.uint8) * 255
        return binary
    except ImportError:
        # Fallback: Otsu global thresholding
        import cv2
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary


def _remove_shadow(gray: np.ndarray) -> np.ndarray:
    """
    Xóa đổ bóng bằng cách chia ảnh cho nền ước lượng (Morphological Dilation).
    Giúp đồng đều hóa ánh sáng của ảnh chụp điện thoại bị đổ bóng 1 góc.
    """
    import cv2
    # Ước tính nền bằng dilate rất lớn (chỉ còn nền mà không có chi tiết nhỏ)
    dilated = cv2.dilate(gray, np.ones((21, 21), np.uint8))
    blurred = cv2.GaussianBlur(dilated, (21, 21), 0)
    # Chia nguyên ảnh cho nền để chuẩn hóa ánh sáng
    norm = cv2.divide(gray.astype(np.float32), blurred.astype(np.float32))
    norm = np.clip(norm * 255, 0, 255).astype(np.uint8)
    return norm


def _deskew(gray: np.ndarray, max_angle_deg: float = 10.0) -> np.ndarray:
    """
    Chỉnh góc nghiêng tự động bằng Hough Line Transform.
    - Phát hiện các đường thẳng ngang dài trong ảnh (dòng kẻ khuông nhạc).
    - Tính góc trung vị của tất cả đường thẳng được phát hiện.
    - Xoay ảnh để căn chỉnh các đường về nằm ngang.
    Chỉ thực hiện nếu góc lệch nằm trong [-max_angle_deg, +max_angle_deg].
    """
    import cv2
    h, w = gray.shape

    # Phát hiện cạnh
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Tìm đường thẳng dài (≥ 30% chiều rộng ảnh) — chỉ tìm dòng kẻ khuông nhạc
    min_line_len = int(w * 0.25)
    lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 360,
                             threshold=80,
                             minLineLength=min_line_len,
                             maxLineGap=15)

    if lines is None or len(lines) < 3:
        return gray

    # Tính góc của từng đường thẳng (chỉ lấy đường gần nằm ngang: |angle| < 15°)
    angles = []
    # OpenCV builds return either (N, 1, 4) or (N, 4); normalize first.
    for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
        angle_deg = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle_deg) < 15.0:
            angles.append(angle_deg)

    if not angles:
        return gray

    median_angle = float(np.median(angles))

    # Chỉ deskew nếu góc đáng kể (> 0.5°) và nhỏ hơn max_angle
    if abs(median_angle) < 0.5 or abs(median_angle) > max_angle_deg:
        return gray

    # Xoay ảnh quanh tâm
    cx, cy = w / 2.0, h / 2.0
    M = cv2.getRotationMatrix2D((cx, cy), -median_angle, 1.0)
    # Dùng BORDER_REPLICATE để tránh viền đen sau khi xoay
    rotated = cv2.warpAffine(gray, M, (w, h),
                              flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
    return rotated


def preprocess_image(input_path: str, output_path: str,
                     enable_deskew: bool = True,
                     enable_shadow_removal: bool | None = None,
                     enable_sauvola: bool = False,
                     report_path: str | None = None,
                     debug_dir: str | None = None) -> bool:
    """
    Pipeline tiền xử lý ảnh bản nhạc nâng cao.

    Args:
        input_path: Đường dẫn ảnh đầu vào (PNG, JPG, TIF)
        output_path: Đường dẫn ảnh đầu ra đã xử lý
        enable_deskew: Bật/tắt chỉnh góc nghiêng tự động (khuyến nghị: True)
        enable_shadow_removal: Bật/tắt xóa đổ bóng (khuyến nghị: True với ảnh chụp)
        enable_sauvola: Bật/tắt Sauvola binarization (nếu tắt, giữ grayscale để CLAHE xử lý)
    Returns:
        True nếu thành công, False nếu thất bại
    """
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

    def save_debug(name: str, image: np.ndarray) -> None:
        if debug_dir is None:
            return
        os.makedirs(debug_dir, exist_ok=True)
        path = os.path.join(debug_dir, name)
        if not cv2.imwrite(path, image):
            raise RuntimeError(f"Could not save preprocessing debug image: {path}")

    save_debug("01_original.png", img)

    # ── Bước 1: Grayscale ──
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()
    save_debug("02_gray.png", gray)

    quality = analyze_image_quality(gray)
    recommendations = quality["recommended"]

    # ── Bước 2: Shadow Removal chỉ cho ảnh có ánh sáng không đều ──
    use_shadow_removal = recommendations["shadow_removal"] if enable_shadow_removal is None else enable_shadow_removal
    if use_shadow_removal:
        gray = _remove_shadow(gray)

    # ── Bước 3: Deskew ──
    if enable_deskew:
        gray = _deskew(gray, max_angle_deg=10.0)
    save_debug("03_deskew.png", gray)

    # ── Bước 4: CLAHE Contrast Enhancement ──
    if recommendations["clahe"]:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    # ── Bước 5: Fast Denoising ──
    if recommendations["denoise"]:
        gray = cv2.fastNlMeansDenoising(gray, h=5, templateWindowSize=7, searchWindowSize=21)

    # ── Bước 6: Adaptive Binarization (tùy chọn) ──
    if enable_sauvola:
        gray = _sauvola_binarize(gray, window_size=25, k=0.15)

    threshold_preview = gray if enable_sauvola else cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 25, 15
    )
    save_debug("04_threshold.png", threshold_preview)
    save_debug("05_normalized.png", gray)

    # ── Lưu kết quả ──
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, gray)
    if report_path:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as report_file:
            json.dump(quality, report_file, ensure_ascii=False, indent=2)
    print(f"SUCCESS: Preprocessed image saved to {output_path}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sheet Music Image Preprocessing Pipeline (Advanced: Deskew + Shadow Removal + CLAHE)"
    )
    parser.add_argument("--input", "-i", required=True, help="Path to input image/page")
    parser.add_argument("--output", "-o", required=True, help="Path to output preprocessed image")
    parser.add_argument("--no-deskew", action="store_true", help="Disable auto deskew")
    parser.add_argument("--no-shadow", action="store_true", help="Disable shadow removal")
    parser.add_argument("--sauvola", action="store_true", help="Enable Sauvola binarization")
    parser.add_argument("--report", help="Write image quality/profile report as JSON")
    parser.add_argument("--debug-dir", help="Write numbered stage images for diagnosis")
    args = parser.parse_args()

    success = preprocess_image(
        args.input, args.output,
        enable_deskew=not args.no_deskew,
        enable_shadow_removal=False if args.no_shadow else None,
        enable_sauvola=args.sauvola,
        report_path=args.report,
        debug_dir=args.debug_dir,
    )
    sys.exit(0 if success else 1)
