<template>
  <Teleport to="body">
    <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4" @click.self="$emit('close')">
      <div class="bg-surface-container-lowest border border-border-subtle rounded-xl max-w-lg w-full p-6 shadow-xl space-y-6">
        <!-- Header -->
        <div class="flex justify-between items-center pb-3 border-b border-border-subtle">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary text-2xl">download</span>
            <h3 class="font-headline-sm text-lg font-bold text-on-surface">Xuất bản MusicXML</h3>
          </div>
          <button
            @click="$emit('close')"
            class="p-1 text-secondary hover:text-on-surface hover:bg-surface-container-low rounded transition-colors"
          >
            <span class="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        <!-- Compatibility Checklist -->
        <div class="bg-success/5 border border-success/20 rounded-lg p-4 space-y-2">
          <div class="flex items-center gap-2 text-xs font-medium text-on-surface">
            <span class="material-symbols-outlined text-success text-sm">check_circle</span>
            <span>Chuẩn MusicXML 4.0 / 3.1 Partwise Schema</span>
          </div>
          <div class="flex items-center gap-2 text-xs font-medium text-on-surface">
            <span class="material-symbols-outlined text-success text-sm">check_circle</span>
            <span>Tương thích hoàn toàn với OpenSheetMusicDisplay (OSMD) & SheetApp</span>
          </div>
          <div class="flex items-center gap-2 text-xs font-medium text-on-surface">
            <span class="material-symbols-outlined text-success text-sm">check_circle</span>
            <span>Tương thích MuseScore 4, Finale, Sibelius, Logic Pro, Cubase</span>
          </div>
          <div class="flex items-center gap-2 text-xs font-medium text-on-surface">
            <span class="material-symbols-outlined text-success text-sm">check_circle</span>
            <span>Bảo toàn {{ versesCount }} Verse lời tiếng Việt chuẩn UTF-8 & hợp âm Slash Chord</span>
          </div>
        </div>

        <!-- Export Format Options -->
        <div class="space-y-3">
          <button
            @click="download('musicxml')"
            class="w-full text-left p-4 border border-border-subtle rounded-lg hover:border-primary hover:bg-sync-active-highlight transition-all flex items-center gap-4 group"
          >
            <div class="w-10 h-10 rounded bg-primary/10 text-primary flex items-center justify-center font-mono-label font-bold text-sm group-hover:bg-primary group-hover:text-on-primary transition-colors">
              XML
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-body-md text-sm font-bold text-on-surface">.musicxml</span>
                <span class="bg-primary/10 text-primary text-[10px] font-semibold px-2 py-0.5 rounded-full">Khuyên dùng</span>
              </div>
              <p class="font-label-sm text-xs text-secondary mt-0.5">MusicXML 4.0 tiêu chuẩn • Tốt nhất cho SheetApp, OSMD & MuseScore 4</p>
            </div>
            <span class="material-symbols-outlined text-secondary group-hover:text-primary transition-colors">arrow_forward</span>
          </button>

          <button
            @click="download('xml')"
            class="w-full text-left p-4 border border-border-subtle rounded-lg hover:border-primary hover:bg-sync-active-highlight transition-all flex items-center gap-4 group"
          >
            <div class="w-10 h-10 rounded bg-surface-container-high text-secondary flex items-center justify-center font-mono-label font-bold text-sm group-hover:bg-primary group-hover:text-on-primary transition-colors">
              .xml
            </div>
            <div class="flex-1 min-w-0">
              <span class="font-body-md text-sm font-bold text-on-surface">.xml</span>
              <p class="font-label-sm text-xs text-secondary mt-0.5">Tương thích Finale, Sibelius, Capella & các phần mềm nhạc cụ cũ</p>
            </div>
            <span class="material-symbols-outlined text-secondary group-hover:text-primary transition-colors">arrow_forward</span>
          </button>

          <button
            @click="download('mxl')"
            class="w-full text-left p-4 border border-border-subtle rounded-lg hover:border-primary hover:bg-sync-active-highlight transition-all flex items-center gap-4 group"
          >
            <div class="w-10 h-10 rounded bg-surface-container-high text-secondary flex items-center justify-center font-mono-label font-bold text-sm group-hover:bg-primary group-hover:text-on-primary transition-colors">
              ZIP
            </div>
            <div class="flex-1 min-w-0">
              <span class="font-body-md text-sm font-bold text-on-surface">.mxl (Compressed)</span>
              <p class="font-label-sm text-xs text-secondary mt-0.5">Nén ZIP dung lượng nhỏ kèm META-INF/container.xml</p>
            </div>
            <span class="material-symbols-outlined text-secondary group-hover:text-primary transition-colors">arrow_forward</span>
          </button>

          <button
            @click="printScore"
            class="w-full text-left p-4 border border-border-subtle rounded-lg hover:border-primary hover:bg-sync-active-highlight transition-all flex items-center gap-4 group"
          >
            <div class="w-10 h-10 rounded bg-primary/10 text-primary flex items-center justify-center font-mono-label font-bold text-sm group-hover:bg-primary group-hover:text-on-primary transition-colors">
              <span class="material-symbols-outlined text-xl">print</span>
            </div>
            <div class="flex-1 min-w-0">
              <span class="font-body-md text-sm font-bold text-on-surface">In bản nhạc / Xuất PDF</span>
              <p class="font-label-sm text-xs text-secondary mt-0.5">In trực tiếp qua máy in hoặc xuất file PDF độ nét cao A4</p>
            </div>
            <span class="material-symbols-outlined text-secondary group-hover:text-primary transition-colors">arrow_forward</span>
          </button>
        </div>

        <!-- Footer -->
        <div class="flex justify-end pt-2">
          <button
            @click="$emit('close')"
            class="border border-border-subtle text-secondary hover:text-on-surface px-4 py-2 rounded text-sm font-semibold transition-colors"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const props = defineProps<{
  projectTitle: string;
  xmlContent: string;
  versesCount: number;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

function download(format: string) {
  const blob = new Blob([props.xmlContent], { type: 'application/vnd.recordare.musicxml+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const cleanName = (props.projectTitle || 'score').replace(/[^a-zA-Z0-9_\u00C0-\u024F\u1E00-\u1EFF]/g, '_');
  a.download = `${cleanName}.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  emit('close');
}

function printScore() {
  emit('close');
  setTimeout(() => {
    window.print();
  }, 300);
}
</script>
