<template>
  <div class="lyrics-panel">
    <!-- Verse Tabs Header -->
    <div class="verse-tabs">
      <button
        v-for="v in availableVerses"
        :key="v"
        class="verse-tab-btn"
        :class="{ active: activeVerse === v }"
        @click="activeVerse = v"
      >
        Verse {{ v }}
      </button>
      <button class="btn btn-secondary btn-sm" @click="addVerse">+ Thêm Verse</button>
    </div>

    <!-- Lyrics Table by Measure -->
    <div class="lyrics-table-container">
      <div v-if="currentVerseLyrics.length === 0" class="empty-state">
        Chưa có dữ liệu lời cho Verse {{ activeVerse }}. Bạn có thể nhập trực tiếp.
      </div>

      <div v-else class="lyrics-grid">
        <div
          v-for="(lyric, idx) in currentVerseLyrics"
          :key="lyric.id || idx"
          class="lyric-card"
          :class="{ 'is-selected': selectedLyricId === lyric.id }"
          @click="selectLyric(lyric)"
        >
          <div class="lyric-meta">
            <span class="m-badge">M.{{ lyric.measureNumber }}</span>
            <span class="v-badge">{{ lyric.noteId }}</span>
          </div>

          <div class="lyric-input-wrap">
            <input
              v-model="lyric.text"
              class="lyric-input"
              @input="onLyricChange(lyric)"
              placeholder="..."
            />
          </div>

          <div class="lyric-actions">
            <button
              class="action-btn"
              title="Dịch chuyển sang nốt trước"
              @click.stop="shiftLyric(idx, -1)"
            >
              ←
            </button>
            <button
              class="action-btn"
              title="Dịch chuyển sang nốt sau"
              @click.stop="shiftLyric(idx, 1)"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Bulk Lyrics Modal / Paste area -->
    <div class="bulk-footer">
      <button class="btn btn-secondary btn-sm" @click="showBulkModal = true">
        📝 Sửa Hàng Loạt (Bulk Editor)
      </button>
      <span class="auto-save-indicator" :class="{ saving: isSaving }">
        {{ isSaving ? 'Đang lưu...' : '✓ Đã đồng bộ MusicXML' }}
      </span>
    </div>

    <!-- Bulk Edit Modal -->
    <div v-if="showBulkModal" class="modal-backdrop" @click.self="showBulkModal = false">
      <div class="modal-card">
        <h3>Chỉnh sửa Hàng loạt Lời — Verse {{ activeVerse }}</h3>
        <p class="modal-desc">Nhập toàn bộ câu lời (ngăn cách bởi khoảng trắng). Hệ thống sẽ tự động map vào các ô nhịp.</p>
        <textarea v-model="bulkText" class="bulk-textarea" rows="6" placeholder="Nhập lời bài hát..."></textarea>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showBulkModal = false">Hủy</button>
          <button class="btn btn-primary" @click="applyBulkLyrics">Áp dụng vào Sheet</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';

export interface LyricItem {
  id: string;
  partId: string;
  measureNumber: number;
  noteId: string;
  verseNumber: number;
  text: string;
  syllabic: string;
}

const props = defineProps<{
  lyricsData: Record<number, LyricItem[]>;
}>();

const emit = defineEmits<{
  (e: 'lyric-updated', lyric: LyricItem): void;
  (e: 'lyric-selected', lyric: LyricItem): void;
  (e: 'bulk-updated', verse: number, words: string[]): void;
}>();

const activeVerse = ref(1);
const selectedLyricId = ref<string | null>(null);
const showBulkModal = ref(false);
const bulkText = ref('');
const isSaving = ref(false);

const availableVerses = computed(() => {
  const keys = Object.keys(props.lyricsData).map(Number);
  return keys.length > 0 ? keys : [1, 2, 3, 4];
});

const currentVerseLyrics = computed(() => {
  return props.lyricsData[activeVerse.value] || [];
});

watch(activeVerse, () => {
  bulkText.value = currentVerseLyrics.value.map(l => l.text).join(' ');
}, { immediate: true });

function selectLyric(lyric: LyricItem) {
  selectedLyricId.value = lyric.id;
  emit('lyric-selected', lyric);
}

let saveTimeout: any = null;
function onLyricChange(lyric: LyricItem) {
  isSaving.value = true;
  clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    emit('lyric-updated', lyric);
    isSaving.value = false;
  }, 600);
}

function shiftLyric(index: number, direction: number) {
  const targetIdx = index + direction;
  const list = currentVerseLyrics.value;
  if (targetIdx >= 0 && targetIdx < list.length) {
    const temp = list[index].text;
    list[index].text = list[targetIdx].text;
    list[targetIdx].text = temp;
    emit('lyric-updated', list[index]);
    emit('lyric-updated', list[targetIdx]);
  }
}

function addVerse() {
  const nextVerse = Math.max(...availableVerses.value, 0) + 1;
  activeVerse.value = nextVerse;
}

function applyBulkLyrics() {
  const words = bulkText.value.trim().split(/\s+/).filter(Boolean);
  emit('bulk-updated', activeVerse.value, words);
  showBulkModal.value = false;
}
</script>

<style scoped>
.lyrics-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-default);
}

.verse-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-default);
  background-color: rgba(15, 23, 42, 0.4);
}

.verse-tab-btn {
  padding: 6px 14px;
  background-color: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  border-radius: 6px;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.verse-tab-btn.active {
  background-color: var(--accent-primary);
  color: var(--bg-app);
  border-color: var(--accent-primary);
}

.lyrics-table-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.lyrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 10px;
}

.lyric-card {
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 8px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.lyric-card:hover,
.lyric-card.is-selected {
  border-color: var(--status-success);
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.25);
}

.lyric-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 0.6875rem;
}

.m-badge {
  color: var(--accent-primary);
  font-weight: 600;
}

.v-badge {
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.lyric-input {
  width: 100%;
  background-color: rgba(30, 41, 59, 0.8);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  outline: none;
}

.lyric-input:focus {
  border-color: var(--status-success);
}

.lyric-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
}

.action-btn {
  background-color: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-muted);
  border-radius: 3px;
  padding: 1px 6px;
  font-size: 0.75rem;
  cursor: pointer;
}

.action-btn:hover {
  background-color: var(--bg-surface-hover);
  color: var(--text-primary);
}

.bulk-footer {
  padding: 10px 16px;
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: rgba(15, 23, 42, 0.4);
}

.auto-save-indicator {
  font-size: 0.75rem;
  color: var(--status-success);
  font-family: var(--font-mono);
}

.auto-save-indicator.saving {
  color: var(--accent-primary);
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 10px;
  padding: 24px;
  max-width: 500px;
  width: 90%;
}

.modal-card h3 {
  margin-bottom: 8px;
  color: var(--text-primary);
}

.modal-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.bulk-textarea {
  width: 100%;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  padding: 10px;
  border-radius: 6px;
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  margin-bottom: 16px;
  outline: none;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 0.75rem;
}
</style>
