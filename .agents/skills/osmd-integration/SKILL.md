---
name: osmd-integration
description: Hướng dẫn tích hợp OpenSheetMusicDisplay (OSMD) trên Vue 3 / TypeScript, quản lý sự kiện tương tác (click note, lyric, measure) và cơ chế đồng bộ Split-view với PDF/Ảnh gốc.
---

# OPENSHEETMUSICDISPLAY (OSMD) INTEGRATION SKILL

Skill này cung cấp các nguyên tắc, mẫu mã (code patterns) và giải pháp xử lý sự kiện tương tác trên OSMD cho giao diện **Sheet Converter**.

---

## 1. KHỞI TẠO VÀ RENDER OSMD TRÊN VUE 3

```typescript
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
import { ref, onMounted } from 'vue';

export function useOSMD(containerRef: Ref<HTMLElement | null>) {
  const osmd = ref<OpenSheetMusicDisplay | null>(null);

  const init = () => {
    if (!containerRef.value) return;
    osmd.value = new OpenSheetMusicDisplay(containerRef.value, {
      autoResize: true,
      backend: 'svg',
      drawTitle: true,
      drawSubtitle: true,
      drawComposer: true,
      drawLyricist: true,
      drawPartNames: true,
      drawFingerings: true,
      drawMeasureNumbers: true,
      renderSingleHorizontalStaffline: false,
    });
  };

  const loadAndRender = async (musicXmlString: string) => {
    if (!osmd.value) return;
    await osmd.value.load(musicXmlString);
    osmd.value.render();
  };

  return { osmd, init, loadAndRender };
}
```

---

## 2. BẮT SỰ KIỆN CLICK VÀ ĐỒNG BỘ VỊ TRÍ (CLICK-TO-SYNC)

### Lấy thông tin khi click vào nốt hoặc ô nhịp:
1. Đăng ký sự kiện click trên SVG container của OSMD.
2. Trích xuất thuộc tính SVG element hoặc đối tượng `GraphicalNote` / `GraphicalMeasure`.
3. Lấy thông tin: `measureNumber`, `voice`, `notePitch`, `verseNumber`.
4. Phát (emit) sự kiện sang `SourceViewer` (PDF/Ảnh gốc) để tự động cuộn (auto-scroll) và hiển thị bounding box highlight lên ô nhịp tương ứng.

---

## 3. CƠ CHẾ RE-RENDER TỐI ƯU KHI SỬA LỜI / HỢP ÂM

- Khi người dùng sửa lyric hoặc thêm chord trên UI:
  1. Gửi request patch về backend (debounce 1-2 giây) hoặc patch cục bộ DOM XML trên client.
  2. Nạp lại XML đã patch vào OSMD: `await osmd.load(updatedXml); osmd.render();`.
  3. Duy trì vị trí cuộn (Scroll Position) của người dùng, không làm nhảy trang.
