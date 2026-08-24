<template>
  <div class="upload-container">
    <div
      class="dropzone-box"
      :class="{ 'is-dragging': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.tif"
        class="hidden-file-input"
        @change="handleFileSelect"
      />

      <div class="dropzone-content">
        <div class="dropzone-icon">🎼</div>
        <h3 class="dropzone-title">Kéo & Thả Bản nhạc PDF hoặc Ảnh vào đây</h3>
        <p class="dropzone-subtitle">Hỗ trợ PDF nhiều trang, PNG, JPG, TIFF (Tối đa 25MB)</p>

        <div class="dropzone-options" @click.stop>
          <label class="opt-label">
            <span class="opt-text">Ngôn ngữ lời:</span>
            <select v-model="selectedLanguage" class="opt-select">
              <option value="vie+eng">Tiếng Việt + Tiếng Anh (vie+eng)</option>
              <option value="vie">Chỉ Tiếng Việt (vie)</option>
              <option value="eng">Chỉ Tiếng Anh (eng)</option>
            </select>
          </label>
        </div>

        <button class="btn btn-primary" type="button" @click.stop="triggerFileInput">
          Chọn file từ máy tính
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{
  (e: 'file-selected', file: File, language: string): void;
}>();

const isDragging = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);
const selectedLanguage = ref('vie+eng');

function triggerFileInput() {
  fileInput.value?.click();
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    emit('file-selected', target.files[0], selectedLanguage.value);
  }
}

function handleDrop(event: DragEvent) {
  isDragging.value = false;
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    emit('file-selected', event.dataTransfer.files[0], selectedLanguage.value);
  }
}
</script>

<style scoped>
.upload-container {
  padding: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 450px;
}

.dropzone-box {
  border: 2px dashed var(--border-default);
  background-color: var(--bg-surface);
  border-radius: 12px;
  padding: 60px 40px;
  max-width: 650px;
  width: 100%;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.dropzone-box:hover,
.dropzone-box.is-dragging {
  border-color: var(--accent-primary);
  background-color: var(--bg-surface-hover);
  box-shadow: 0 0 25px rgba(56, 189, 248, 0.2);
}

.hidden-file-input {
  display: none;
}

.dropzone-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.dropzone-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.dropzone-subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.dropzone-options {
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

.opt-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.opt-select {
  background-color: var(--bg-app);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 6px 12px;
  border-radius: 6px;
  outline: none;
}

.opt-select:focus {
  border-color: var(--accent-primary);
}
</style>
