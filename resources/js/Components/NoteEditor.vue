<template>
  <div class="note-editor-panel">
    <div class="editor-header">
      <h4>Chỉnh sửa Nốt Nhanh (Measure {{ measureNumber }})</h4>
    </div>

    <div class="form-grid">
      <!-- Pitch Step -->
      <div class="form-field">
        <label>Cao độ (Pitch Step):</label>
        <div class="step-btn-group">
          <button
            v-for="s in ['C', 'D', 'E', 'F', 'G', 'A', 'B']"
            :key="s"
            class="chip-btn"
            :class="{ active: currentStep === s }"
            @click="currentStep = s"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <!-- Octave -->
      <div class="form-field">
        <label>Quãng (Octave):</label>
        <div class="step-btn-group">
          <button
            v-for="oct in [2, 3, 4, 5, 6]"
            :key="oct"
            class="chip-btn"
            :class="{ active: currentOctave === oct }"
            @click="currentOctave = oct"
          >
            {{ oct }}
          </button>
        </div>
      </div>

      <!-- Accidental -->
      <div class="form-field">
        <label>Dấu hóa (Accidental):</label>
        <div class="step-btn-group">
          <button
            class="chip-btn"
            :class="{ active: currentAccidental === null }"
            @click="currentAccidental = null"
          >
            Bình (♮)
          </button>
          <button
            class="chip-btn"
            :class="{ active: currentAccidental === 'sharp' }"
            @click="currentAccidental = 'sharp'"
          >
            Thăng (♯)
          </button>
          <button
            class="chip-btn"
            :class="{ active: currentAccidental === 'flat' }"
            @click="currentAccidental = 'flat'"
          >
            Giáng (♭)
          </button>
        </div>
      </div>

      <!-- Duration -->
      <div class="form-field">
        <label>Trường độ (Duration):</label>
        <select v-model="currentDuration" class="select-box">
          <option value="whole">Nốt Tròn (Whole)</option>
          <option value="half">Nốt Trắng (Half)</option>
          <option value="quarter">Nốt Đen (Quarter)</option>
          <option value="eighth">Nốt Móc Đơn (Eighth)</option>
          <option value="16th">Nốt Móc Kép (16th)</option>
        </select>
      </div>
    </div>

    <div class="editor-footer">
      <button class="btn btn-primary btn-sm" @click="saveNoteChange">
        Cập nhật Nốt vào MusicXML
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = withDefaults(defineProps<{
  measureNumber?: number;
  initialStep?: string;
  initialOctave?: number;
  initialAccidental?: string | null;
  initialDuration?: string;
}>(), {
  measureNumber: 1,
  initialStep: 'G',
  initialOctave: 4,
  initialAccidental: null,
  initialDuration: 'quarter'
});

const emit = defineEmits<{
  (e: 'note-updated', payload: {
    step: string;
    octave: number;
    accidental: string | null;
    duration: string;
  }): void;
}>();

const currentStep = ref(props.initialStep);
const currentOctave = ref(props.initialOctave);
const currentAccidental = ref(props.initialAccidental);
const currentDuration = ref(props.initialDuration);

function saveNoteChange() {
  emit('note-updated', {
    step: currentStep.value,
    octave: currentOctave.value,
    accidental: currentAccidental.value,
    duration: currentDuration.value,
  });
}
</script>

<style scoped>
.note-editor-panel {
  padding: 16px;
  background-color: var(--bg-surface);
  border-top: 1px solid var(--border-default);
}

.editor-header h4 {
  color: var(--text-primary);
  margin-bottom: 12px;
  font-size: 0.9375rem;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-field label {
  display: block;
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.step-btn-group {
  display: flex;
  gap: 4px;
}

.chip-btn {
  padding: 4px 10px;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 600;
}

.chip-btn.active {
  background-color: var(--accent-primary);
  color: var(--bg-app);
  border-color: var(--accent-primary);
}

.select-box {
  width: 100%;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  padding: 5px 8px;
  border-radius: 4px;
  outline: none;
}

.editor-footer {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
