---
name: "Sheet Converter Design System"
version: "1.0.0"
author: "Google Labs DESIGN.md Standard"
description: "Universal design contract for Sheet Converter preventing AI visual drift and slop."

tokens:
  color:
    background:
      app: "#0f172a"          # slate-900 (Dark theme base)
      surface: "#1e293b"      # slate-800 (Card & Panel base)
      surface-hover: "#334155"# slate-700
      canvas: "#ffffff"       # Pure white for Sheet Music SVG & PDF
      canvas-dark: "#f8fafc"  # Soft paper white for score viewing
    text:
      primary: "#f8fafc"      # slate-50 (High contrast text)
      secondary: "#94a3b8"    # slate-400 (Subtle text, labels)
      muted: "#64748b"        # slate-500
      inverse: "#0f172a"      # slate-900 (Text on light canvas)
    accent:
      primary: "#38bdf8"      # sky-400 (Active elements, focus rings)
      primary-hover: "#0284c7"# sky-600
      secondary: "#818cf8"    # indigo-400
    status:
      success: "#10b981"      # emerald-500 (Pass, Verified, Ready)
      warning: "#f59e0b"      # amber-500 (Needs Review, Low Confidence)
      danger: "#ef4444"       # red-500 (OMR Error, Invalid XML)
      info: "#3b82f6"         # blue-500 (Processing, Info)
    highlight:
      measure: "rgba(56, 189, 248, 0.25)"   # Sky blue soft overlay
      note: "rgba(245, 158, 11, 0.35)"      # Amber focus overlay
      lyric: "rgba(16, 185, 129, 0.30)"     # Emerald lyric focus
      issue: "rgba(239, 68, 68, 0.35)"      # Red error highlight
    border:
      default: "#334155"      # slate-700
      focus: "#38bdf8"        # sky-400
      subtle: "#1e293b"       # slate-800

  typography:
    fontFamily:
      sans: "'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
      mono: "'JetBrains Mono', 'Fira Code', Consolas, monospace"
      music-score: "'Bravura', 'Maestro', 'Leland', serif"
    fontSize:
      xs: "0.75rem"           # 12px
      sm: "0.875rem"          # 14px
      base: "1.0rem"          # 16px
      lg: "1.125rem"          # 18px
      xl: "1.25rem"           # 20px
      "2xl": "1.5rem"         # 24px
    fontWeight:
      normal: "400"
      medium: "500"
      semibold: "600"
      bold: "700"

  spacing:
    xs: "0.25rem"             # 4px
    sm: "0.5rem"              # 8px
    md: "1.0rem"              # 16px
    lg: "1.5rem"              # 24px
    xl: "2.0rem"              # 32px

  borderRadius:
    sm: "0.25rem"             # 4px
    md: "0.5rem"              # 8px
    lg: "0.75rem"             # 12px
    full: "9999px"

  accessibility:
    wcagLevel: "AA"
    minContrastRatio: 4.5
---

# SHEET CONVERTER DESIGN CONTRACT (DESIGN.md)

Tài liệu này định nghĩa giao ước thiết kế giao diện (UI/UX) cho ứng dụng **Sheet Converter**, ngăn chặn tình trạng biến dạng giao diện ("AI Slop") và đảm bảo tính đồng nhất trên mọi màn hình.

---

## 1. NGUYÊN TẮC THIẾT KẾ (DESIGN PRINCIPLES)

1. **Chuyên nghiệp & Tinh tế (Studio-grade Dark Mode)**:
   - Giao diện chính sử dụng nền tối sâu (`#0f172a`, `#1e293b`) để làm nổi bật 2 khung hiển thị bản nhạc (Split-view Canvas).
   - Nền bản nhạc và PDF gốc sử dụng tone trắng tinh hoặc ngà nhẹ (`#ffffff`, `#f8fafc`) để mô phỏng trang giấy thật, tối ưu cho mắt khi dò từng nốt nhạc.

2. **Split-View Đối chiếu Trực quan (50/50 Desktop)**:
   - Nửa bên trái: **Bản PDF/Ảnh quét gốc** (`SourceViewer.vue`).
   - Nửa bên phải: **Bản nhạc MusicXML đã nhận dạng** render qua OSMD (`ScoreViewer.vue`).
   - Cả 2 khung phải có thanh cuộn độc lập và hỗ trợ **đồng bộ cuộn theo ô nhịp (Synchronized Measure Scroll)**.

3. **Tương tác trực tiếp & Micro-Interactions**:
   - Khi click vào bất kỳ Nốt, Lời hoặc Hợp âm nào ở bảng Score:
     - Nốt được viền sáng bằng màu nhấn Accent Focus.
     - Ô nhịp tương ứng trên PDF gốc được phủ lớp Highlight mềm (`rgba(56, 189, 248, 0.25)`).
     - Thanh công cụ chỉnh sửa (Quick Edit Toolbar / Popover) xuất hiện mượt mà ngay tại vị trí con trỏ.

---

## 2. QUY CHUẨN CÁC THÀNH PHẦN (COMPONENT SPECIFICATIONS)

### 2.1. Upload Dropzone (`UploadDropzone.vue`)
- Khung kéo thả kích thước lớn, viền nét đứt (dashed border `#334155`).
- Khi kéo file vào: Viền chuyển sang màu xanh Sky (`#38bdf8`) với hiệu ứng glow nhẹ.
- Hỗ trợ xem trước (thumbnail) PDF và hình ảnh đa trang.

### 2.2. Tiến trình Chuyển đổi (`ConversionProgress.vue`)
- Không chỉ hiển thị vòng xoay spinner đơn thuần.
- Hiển thị danh sách checklist các bước:
  1. *Chuẩn bị trang & Tiền xử lý ảnh (OpenCV)* $\rightarrow$ Done.
  2. *Nhận dạng cấu trúc & khuôn nhạc (Audiveris OMR)* $\rightarrow$ Đang chạy (kèm % tiến độ).
  3. *Nhận dạng lời tiếng Việt (Tesseract vie+eng)* $\rightarrow$ Chờ.
  4. *Tạo và kiểm định MusicXML* $\rightarrow$ Chờ.

### 2.3. Bảng Chỉnh sửa Lời (`LyricsPanel.vue` & `LyricEditor.vue`)
- Tab hiển thị linh hoạt từng Verse: `Verse 1`, `Verse 2`, `Verse 3`, `Verse 4`, `...`.
- Ô nhập text hỗ trợ đầy đủ bộ gõ tiếng Việt (Telex/VNI).
- Nút chuyển nhanh âm tiết sang nốt trước (`← Move Prev`) và nốt sau (`Move Next →`).

### 2.4. Bảng Chỉnh sửa Hợp âm (`ChordPanel.vue` & `ChordEditor.vue`)
- Hộp nhập nhanh hợp âm thông minh (ví dụ gõ `G/B`, `Am7`, `D7#5` tự động phân rã thành Root, Kind, Bass).
- Bắt dính vị trí hợp âm theo Measure và Beat Offset.

### 2.5. Hộp thoại Xuất file (`ExportDialog.vue`)
- Nút tải các định dạng: `.musicxml` (Chuẩn MusicXML 4.0), `.xml` (MusicXML 3.1 tương thích Finale/Sibelius) và `.mxl` (Nén).
- Hiển thị nhãn kiểm định: **"Tương thích 100% với SheetApp & OSMD"** kèm dấu kiểm xanh.
