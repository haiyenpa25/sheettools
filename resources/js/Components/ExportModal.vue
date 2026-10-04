<template>
  <Teleport to="body">
    <div class="fixed inset-0 bg-slate-900/70 backdrop-blur-xs flex items-center justify-center z-50 p-4" @click.self="$emit('close')">
      <div class="bg-surface-container-lowest border border-border-subtle rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-200">
        
        <!-- Header -->
        <div class="flex justify-between items-center pb-3 border-b border-border-subtle">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <span class="material-symbols-outlined text-2xl">ios_share</span>
            </div>
            <div>
              <h3 class="font-headline-sm text-lg font-bold text-on-surface">Trung Tâm Xuất Bản Đa Phiên Bản</h3>
              <p class="text-xs text-secondary">Chọn phiên bản phù hợp cho Ca đoàn, Nhạc công hoặc Đệm hát</p>
            </div>
          </div>
          <button
            @click="$emit('close')"
            class="p-1.5 text-secondary hover:text-on-surface hover:bg-surface-container-low rounded-lg transition-colors"
          >
            <span class="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        <!-- 3-Version Tab Selection -->
        <div class="grid grid-cols-3 gap-2 p-1 bg-surface-container-low rounded-xl border border-border-subtle">
          <button
            @click="activeVersion = 'full'"
            class="flex flex-col items-center gap-1 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all"
            :class="activeVersion === 'full' ? 'bg-primary text-on-primary shadow-sm' : 'text-secondary hover:text-on-surface hover:bg-surface-container'"
          >
            <span class="material-symbols-outlined text-lg">menu_book</span>
            <span>1. Bản Đầy Đủ</span>
            <span class="text-[10px] opacity-80 font-normal">Nốt + Lời + Hợp âm</span>
          </button>

          <button
            @click="activeVersion = 'instrumental'"
            class="flex flex-col items-center gap-1 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all"
            :class="activeVersion === 'instrumental' ? 'bg-primary text-on-primary shadow-sm' : 'text-secondary hover:text-on-surface hover:bg-surface-container'"
          >
            <span class="material-symbols-outlined text-lg">piano</span>
            <span>2. Bản Không Lời</span>
            <span class="text-[10px] opacity-80 font-normal">Chỉ Nốt • Đã xóa lời</span>
          </button>

          <button
            @click="activeVersion = 'lyrics'"
            class="flex flex-col items-center gap-1 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all"
            :class="activeVersion === 'lyrics' ? 'bg-primary text-on-primary shadow-sm' : 'text-secondary hover:text-on-surface hover:bg-surface-container'"
          >
            <span class="material-symbols-outlined text-lg">lyrics</span>
            <span>3. Chỉ Lời</span>
            <span class="text-[10px] opacity-80 font-normal">Lời theo từng verse</span>
          </button>
        </div>

        <!-- ═══════════════════════════════════════════════════════════ -->
        <!-- TAB 1: FULL SCORE -->
        <!-- ═══════════════════════════════════════════════════════════ -->
        <div v-if="activeVersion === 'full'" class="space-y-3">
          <label class="flex items-center gap-2 text-xs text-on-surface">
            <input v-model="duplicateChorus" type="checkbox" class="accent-primary" />
            Nhân bản điệp khúc vào mọi lời (mặc định xuất một dòng)
          </label>
          <div class="bg-success/5 border border-success/20 rounded-lg p-3 flex items-center gap-2.5 text-xs text-on-surface">
            <span class="material-symbols-outlined text-success text-sm">check_circle</span>
            <span>Bản nhạc toàn diện chuẩn MusicXML 4.0 • Tương thích SheetApp, OSMD, MuseScore 4 & Sibelius</span>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <button
              @click="downloadFull('musicxml')"
              class="text-left p-3.5 border border-border-subtle rounded-xl hover:border-primary hover:bg-primary/5 transition-all flex items-center gap-3 group"
            >
              <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-mono font-bold text-xs group-hover:bg-primary group-hover:text-on-primary transition-colors">
                XML
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-bold text-on-surface flex items-center gap-1.5">
                  <span>.musicxml</span>
                  <span class="text-[9px] bg-primary/15 text-primary px-1.5 py-0.2 rounded font-semibold">Khuyên dùng</span>
                </div>
                <p class="text-xs text-secondary truncate">Tốt nhất cho OSMD & MuseScore 4</p>
              </div>
            </button>

            <button
              @click="downloadFull('mxl')"
              class="text-left p-3.5 border border-border-subtle rounded-xl hover:border-primary hover:bg-primary/5 transition-all flex items-center gap-3 group"
            >
              <div class="w-10 h-10 rounded-lg bg-surface-container-high text-secondary flex items-center justify-center font-mono font-bold text-xs group-hover:bg-primary group-hover:text-on-primary transition-colors">
                ZIP
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-bold text-on-surface">.mxl (Compressed)</div>
                <p class="text-xs text-secondary truncate">Nén nhỏ gọn kèm container</p>
              </div>
            </button>

            <button
              @click="downloadFull('mscx')"
              class="text-left p-3.5 border border-border-subtle rounded-xl hover:border-primary hover:bg-primary/5 transition-all flex items-center gap-3 group"
            >
              <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-mono font-bold text-xs group-hover:bg-primary group-hover:text-on-primary transition-colors">
                MS
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-bold text-on-surface">.mscx</div>
                <p class="text-xs text-secondary truncate">Mở trực tiếp trong MuseScore 4</p>
              </div>
            </button>

            <button
              @click="printScore"
              class="text-left p-3.5 border border-border-subtle rounded-xl hover:border-primary hover:bg-primary/5 transition-all flex items-center gap-3 group"
            >
              <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-mono font-bold text-xs group-hover:bg-primary group-hover:text-on-primary transition-colors">
                <span class="material-symbols-outlined text-lg">print</span>
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-bold text-on-surface">In / Xuất PDF A4</div>
                <p class="text-xs text-secondary truncate">Bản in nốt + lời đầy đủ A4</p>
              </div>
            </button>
          </div>
        </div>

        <!-- ═══════════════════════════════════════════════════════════ -->
        <!-- TAB 2: INSTRUMENTAL (NO LYRICS) -->
        <!-- ═══════════════════════════════════════════════════════════ -->
        <div v-else-if="activeVersion === 'instrumental'" class="space-y-3">
          <div class="bg-primary/5 border border-primary/20 rounded-lg p-3 flex items-center gap-2.5 text-xs text-on-surface">
            <span class="material-symbols-outlined text-primary text-sm">piano</span>
            <span>Bản nhạc đã bóc tách toàn bộ lời hát • Dành riêng cho nhạc công độc tấu, hòa âm và đệm đàn</span>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <button
              @click="downloadInstrumental('musicxml')"
              class="text-left p-3.5 border border-border-subtle rounded-xl hover:border-primary hover:bg-primary/5 transition-all flex items-center gap-3 group"
            >
              <div class="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-mono font-bold text-xs group-hover:bg-primary group-hover:text-on-primary transition-colors">
                XML
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-bold text-on-surface">MusicXML Không Lời</div>
                <p class="text-xs text-secondary truncate">Bản tổng phổ nốt thuần túy</p>
              </div>
            </button>

            <button
              @click="downloadInstrumental('mxl')"
              class="text-left p-3.5 border border-border-subtle rounded-xl hover:border-primary hover:bg-primary/5 transition-all flex items-center gap-3 group"
            >
              <div class="w-10 h-10 rounded-lg bg-surface-container-high text-secondary flex items-center justify-center font-mono font-bold text-xs group-hover:bg-primary group-hover:text-on-primary transition-colors">
                ZIP
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-bold text-on-surface">.mxl Không Lời</div>
                <p class="text-xs text-secondary truncate">Nén gọn gàng cho DAW / Sequencer</p>
              </div>
            </button>
          </div>
        </div>

        <!-- ═══════════════════════════════════════════════════════════ -->
        <!-- TAB 3: LYRICS ONLY -->
        <!-- ═══════════════════════════════════════════════════════════ -->
        <div v-else-if="activeVersion === 'lyrics'" class="space-y-3">
          <div class="bg-success/5 border border-success/20 rounded-lg p-3 flex items-center gap-2.5 text-xs text-on-surface">
            <span class="material-symbols-outlined text-success text-sm">lyrics</span>
            <span>Bản lời độc lập, giữ dấu tiếng Việt và phân tách rõ từng verse.</span>
          </div>

          <div class="relative">
            <pre class="w-full h-48 p-3.5 bg-surface-container-lowest border border-border-subtle rounded-xl text-xs font-mono overflow-auto whitespace-pre-wrap leading-relaxed select-all text-on-surface">{{ lyricsOnlyPreview }}</pre>
            
            <div v-if="copiedToast" class="absolute top-3 right-3 bg-success text-on-primary text-xs font-bold px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-1.5 animate-in fade-in">
              <span class="material-symbols-outlined text-sm">check</span>
              Đã sao chép!
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2">
            <button
              @click="copyToClipboard"
              class="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-primary text-on-primary rounded-xl text-xs font-bold hover:brightness-110 active:scale-98 transition-all"
            >
              <span class="material-symbols-outlined text-sm">content_copy</span>
              <span>Sao chép lời</span>
            </button>

            <button
              @click="downloadLyricsOnly"
              class="flex items-center justify-center gap-1.5 py-2.5 px-3 border border-border-subtle bg-surface-container-low hover:bg-surface-container text-on-surface rounded-xl text-xs font-semibold transition-colors"
            >
              <span class="material-symbols-outlined text-sm">description</span>
              <span>Tải file .txt</span>
            </button>

          </div>
        </div>

        <!-- Footer -->
        <div class="flex justify-end pt-2 border-t border-border-subtle">
          <button
            @click="$emit('close')"
            class="border border-border-subtle text-secondary hover:text-on-surface px-4 py-2 rounded-xl text-xs font-semibold transition-colors"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { MusicXmlEngine } from '../Services/MusicXmlEngine';

const props = defineProps<{
  projectTitle: string;
  xmlContent: string;
  versesCount: number;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const activeVersion = ref<'full' | 'instrumental' | 'lyrics'>('full');
const copiedToast = ref<boolean>(false);
const duplicateChorus = ref(false);

const engine = computed(() => new MusicXmlEngine(props.xmlContent));

const lyricsOnlyPreview = computed(() => {
  const verses = engine.value.extractLyrics();
  return Object.keys(verses)
    .map(Number)
    .sort((a, b) => a - b)
    .map(number => `VERSE ${number}\n${verses[number].map(item => item.text).filter(Boolean).join(' ')}`)
    .join('\n\n');
});

function triggerDownload(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function getCleanName(suffix: string = ''): string {
  const base = (props.projectTitle || 'score').replace(/[^a-zA-Z0-9_\u00C0-\u024F\u1E00-\u1EFF]/g, '_');
  return suffix ? `${base}_${suffix}` : base;
}

function downloadFull(format: string) {
  triggerDownload(engine.value.getFullXml(duplicateChorus.value), `${getCleanName()}.${format}`, 'application/vnd.recordare.musicxml+xml;charset=utf-8');
  emit('close');
}

function downloadInstrumental(format: string) {
  const instXml = engine.value.getInstrumentalXml();
  triggerDownload(instXml, `${getCleanName('instrumental')}.${format}`, 'application/vnd.recordare.musicxml+xml;charset=utf-8');
  emit('close');
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(lyricsOnlyPreview.value);
    copiedToast.value = true;
    setTimeout(() => {
      copiedToast.value = false;
    }, 2000);
  } catch (err) {
    console.error('Lỗi sao chép:', err);
  }
}

function downloadLyricsOnly() {
  triggerDownload(lyricsOnlyPreview.value + '\n', `${getCleanName('lyrics_only')}.txt`, 'text/plain;charset=utf-8');
}

function printScore() {
  emit('close');
  setTimeout(() => {
    window.print();
  }, 300);
}
</script>
