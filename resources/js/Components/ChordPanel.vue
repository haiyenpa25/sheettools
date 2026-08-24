<template>
  <div class="chord-panel">
    <div class="panel-top">
      <div class="quick-add-group">
        <input
          v-model="newChordInput"
          class="chord-quick-input"
          placeholder="Nhập hợp âm (vd: G/B, Am7, D7#5)..."
          @keyup.enter="addChord"
        />
        <select v-model="selectedMeasure" class="measure-select">
          <option v-for="m in totalMeasures" :key="m" :value="m">Ô nhịp M.{{ m }}</option>
        </select>
        <button class="btn btn-primary btn-sm" @click="addChord">+ Thêm Hợp Âm</button>
      </div>

      <!-- Quick Preset Badges -->
      <div class="preset-badges">
        <span
          v-for="preset in popularPresets"
          :key="preset"
          class="preset-chip"
          @click="newChordInput = preset"
        >
          {{ preset }}
        </span>
      </div>
    </div>

    <!-- Chords List by Measure -->
    <div class="chords-list">
      <div v-if="harmonies.length === 0" class="empty-state">
        Chưa có hợp âm nào được gán trong bản nhạc.
      </div>

      <div v-else class="chords-grid">
        <div
          v-for="harm in harmonies"
          :key="harm.id"
          class="chord-card"
        >
          <div class="chord-display">{{ harm.displayText || harm.rootStep }}</div>
          <div class="chord-info">
            <span>M.{{ harm.measureNumber }}</span>
            <span class="offset-tag" v-if="harm.beatOffset > 0">Offset: {{ harm.beatOffset }}</span>
          </div>
          <button class="delete-btn" title="Xóa hợp âm" @click="deleteChord(harm.id)">×</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

export interface HarmonyItem {
  id: string;
  partId: string;
  measureNumber: number;
  beatOffset: number;
  rootStep: string;
  displayText?: string;
}

const props = defineProps<{
  harmonies: HarmonyItem[];
  totalMeasures: number;
}>();

const emit = defineEmits<{
  (e: 'chord-added', chordText: string, measureNumber: number): void;
  (e: 'chord-deleted', chordId: string): void;
}>();

const newChordInput = ref('G');
const selectedMeasure = ref(1);

const popularPresets = ['G', 'C', 'D7', 'Em', 'Am', 'G/B', 'D/F#', 'Cmaj7', 'Bm7'];

function addChord() {
  if (!newChordInput.value.trim()) return;
  emit('chord-added', newChordInput.value.trim(), selectedMeasure.value);
  newChordInput.value = '';
}

function deleteChord(id: string) {
  emit('chord-deleted', id);
}
</script>

<style scoped>
.chord-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-default);
}

.panel-top {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-default);
  background-color: rgba(15, 23, 42, 0.4);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-add-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chord-quick-input {
  flex: 1;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-weight: 600;
  outline: none;
}

.chord-quick-input:focus {
  border-color: var(--accent-primary);
}

.measure-select {
  background-color: var(--bg-app);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 6px 10px;
  border-radius: 6px;
}

.preset-badges {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}

.preset-chip {
  background-color: var(--bg-app);
  color: var(--accent-primary);
  font-size: 0.75rem;
  font-family: var(--font-mono);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.2s ease;
}

.preset-chip:hover {
  background-color: var(--accent-primary);
  color: var(--bg-app);
}

.chords-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.chords-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 10px;
}

.chord-card {
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 8px;
  position: relative;
  text-align: center;
}

.chord-display {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--accent-secondary);
  font-family: var(--font-mono);
  margin-bottom: 4px;
}

.chord-info {
  font-size: 0.6875rem;
  color: var(--text-muted);
}

.delete-btn {
  position: absolute;
  top: 2px;
  right: 4px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 14px;
  cursor: pointer;
}

.delete-btn:hover {
  color: var(--status-danger);
}
</style>
