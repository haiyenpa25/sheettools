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
            @click="activeVersion = 'hopamchuan'"
            class="flex flex-col items-center gap-1 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all"
            :class="activeVersion === 'hopamchuan' ? 'bg-primary text-on-primary shadow-sm' : 'text-secondary hover:text-on-surface hover:bg-surface-container'"
          >
            <span class="material-symbols-outlined text-lg">queue_music</span>
            <span>3. Hợp Âm Chuẩn</span>
            <span class="text-[10px] opacity-80 font-normal">hopamchuan.net</span>
          </button>
        </div>

        <!-- ═══════════════════════════════════════════════════════════ -->
        <!-- TAB 1: FULL SCORE -->
        <!-- ═══════════════════════════════════════════════════════════ -->
        <div v-if="activeVersion === 'full'" class="space-y-3">
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
        <!-- TAB 3: HỢP ÂM CHUẨN (HOPAMCHUAN / CHORDPRO) -->
        <!-- ═══════════════════════════════════════════════════════════ -->
        <div v-else-if="activeVersion === 'hopamchuan'" class="space-y-3">
          <!-- Transpose & Style Controls Bar -->
          <div class="flex items-center justify-between bg-surface-container-low p-3 rounded-xl border border-border-subtle">
            <!-- Transpose -->
            <div class="flex items-center gap-2">
              <span class="text-xs font-semibold text-secondary">Đổi Tone:</span>
              <button
                @click="shiftTranspose(-1)"
                class="w-7 h-7 flex items-center justify-center rounded-lg bg-surface-container-high hover:bg-primary hover:text-on-primary text-xs font-bold transition-colors"
                title="Giảm 1 bán âm"
              >
                -
              </button>
              <span class="font-mono text-xs font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                {{ transposeSemitones >= 0 ? `+${transposeSemitones}` : transposeSemitones }}
              </span>
              <button
                @click="shiftTranspose(1)"
                class="w-7 h-7 flex items-center justify-center rounded-lg bg-surface-container-high hover:bg-primary hover:text-on-primary text-xs font-bold transition-colors"
                title="Tăng 1 bán âm"
              >
                +
              </button>
              <button
                v-if="transposeSemitones !== 0"
                @click="transposeSemitones = 0"
                class="text-[10px] text-secondary hover:text-primary underline ml-1"
              >
                Gốc
              </button>
            </div>

            <!-- Style Selector -->
            <div class="flex items-center gap-1.5">
              <button
                @click="chordStyle = 'above'"
                class="text-xs px-2.5 py-1 rounded-md font-medium transition-colors"
                :class="chordStyle === 'above' ? 'bg-primary/15 text-primary font-bold' : 'text-secondary hover:text-on-surface'"
              >
                Trên lời
              </button>
              <button
                @click="chordStyle = 'inline'"
                class="text-xs px-2.5 py-1 rounded-md font-medium transition-colors"
                :class="chordStyle === 'inline' ? 'bg-primary/15 text-primary font-bold' : 'text-secondary hover:text-on-surface'"
              >
                Trong ngoặc [Em]
              </button>
            </div>
          </div>

          <!-- Live Preview Textarea -->
          <div class="relative">
            <pre class="w-full h-48 p-3.5 bg-surface-container-lowest border border-border-subtle rounded-xl text-xs font-mono overflow-auto whitespace-pre leading-relaxed select-all text-on-surface">{{ hopAmChuanPreview }}</pre>
            
            <div v-if="copiedToast" class="absolute top-3 right-3 bg-success text-on-primary text-xs font-bold px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-1.5 animate-in fade-in">
              <span class="material-symbols-outlined text-sm">check</span>
              Đã sao chép!
            </div>
          </div>

          <!-- Action Buttons for HopAmChuan -->
          <div class="grid grid-cols-3 gap-2">
            <button
              @click="copyToClipboard"
              class="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-primary text-on-primary rounded-xl text-xs font-bold hover:brightness-110 active:scale-98 transition-all"
            >
              <span class="material-symbols-outlined text-sm">content_copy</span>
              <span>Sao Chép 1-Click</span>
            </button>

            <button
              @click="downloadHopAmChuanTxt"
              class="flex items-center justify-center gap-1.5 py-2.5 px-3 border border-border-subtle bg-surface-container-low hover:bg-surface-container text-on-surface rounded-xl text-xs font-semibold transition-colors"
            >
              <span class="material-symbols-outlined text-sm">description</span>
              <span>Tải file .txt</span>
            </button>

            <button
              @click="downloadChordPro"
              class="flex items-center justify-center gap-1.5 py-2.5 px-3 border border-border-subtle bg-surface-container-low hover:bg-surface-container text-on-surface rounded-xl text-xs font-semibold transition-colors"
            >
              <span class="material-symbols-outlined text-sm">audio_file</span>
              <span>Tải file .cho</span>
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

const activeVersion = ref<'full' | 'instrumental' | 'hopamchuan'>('full');
const transposeSemitones = ref<number>(0);
const chordStyle = ref<'above' | 'inline'>('above');
const copiedToast = ref<boolean>(false);

const engine = computed(() => new MusicXmlEngine(props.xmlContent));

const hopAmChuanPreview = computed(() => {
  try {
    return engine.value.generateHopAmChuanText(transposeSemitones.value, chordStyle.value);
  } catch (e) {
    return 'Đang tạo bản Hợp Âm Chuẩn...';
  }
});

function shiftTranspose(delta: number) {
  transposeSemitones.value += delta;
  if (transposeSemitones.value > 11) transposeSemitones.value -= 12;
  if (transposeSemitones.value < -11) transposeSemitones.value += 12;
}

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
  triggerDownload(props.xmlContent, `${getCleanName()}.${format}`, 'application/vnd.recordare.musicxml+xml;charset=utf-8');
  emit('close');
}

function downloadInstrumental(format: string) {
  const instXml = engine.value.getInstrumentalXml();
  triggerDownload(instXml, `${getCleanName('instrumental')}.${format}`, 'application/vnd.recordare.musicxml+xml;charset=utf-8');
  emit('close');
}

function downloadHopAmChuanTxt() {
  triggerDownload(hopAmChuanPreview.value, `${getCleanName('hopamchuan')}.txt`, 'text/plain;charset=utf-8');
}

function downloadChordPro() {
  const chordPro = engine.value.generateChordProText(transposeSemitones.value);
  triggerDownload(chordPro, `${getCleanName('chordpro')}.cho`, 'text/plain;charset=utf-8');
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(hopAmChuanPreview.value);
    copiedToast.value = true;
    setTimeout(() => {
      copiedToast.value = false;
    }, 2000);
  } catch (err) {
    console.error('Lỗi sao chép:', err);
  }
}

function printScore() {
  emit('close');
  setTimeout(() => {
    window.print();
  }, 300);
}
</script>
