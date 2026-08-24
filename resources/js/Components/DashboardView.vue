<template>
  <div class="flex-1 overflow-y-auto p-margin-main">
    <div class="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-margin-main">
      <!-- Main Upload Area (2 cols) -->
      <div class="lg:col-span-2 space-y-margin-main">
        <!-- Upload Section -->
        <section class="bg-surface-container-lowest rounded-xl border border-border-subtle p-margin-main shadow-xs">
          <h2 class="font-headline-sm text-xl text-on-surface font-semibold mb-6">Tải lên bản nhạc</h2>

          <!-- Dropzone -->
          <div
            class="border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center text-center transition-all cursor-pointer group"
            :class="[
              isDragging ? 'border-primary bg-sync-active-highlight' : 'border-outline-variant hover:bg-surface-container-low',
              selectedFile ? 'border-success bg-success/5' : ''
            ]"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
            @click="triggerFileInput"
          >
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.xml,.musicxml"
              class="hidden"
              @change="onFileSelected"
            />

            <!-- Empty State -->
            <template v-if="!selectedFile">
              <div class="w-16 h-16 bg-surface-container-high rounded-full flex items-center justify-center mb-4 group-hover:bg-primary-fixed transition-colors">
                <span class="material-symbols-outlined text-3xl text-secondary group-hover:text-primary transition-colors">cloud_upload</span>
              </div>
              <p class="font-body-lg text-base text-on-surface font-semibold mb-2">Kéo thả file PDF hoặc ảnh vào đây</p>
              <p class="font-body-md text-sm text-secondary mb-6">Hỗ trợ định dạng: PDF, PNG, JPG, TIFF, MusicXML (Tối đa 50MB)</p>
              <button
                type="button"
                class="bg-primary text-on-primary px-6 py-2.5 rounded-lg font-label-sm text-sm font-semibold hover:bg-primary-container transition-colors shadow-sm"
              >
                Chọn file từ máy tính
              </button>
            </template>

            <!-- File Selected Preview State -->
            <template v-else>
              <div class="flex flex-col items-center gap-3 w-full max-w-md">
                <div class="w-16 h-16 rounded-full bg-success/15 text-success flex items-center justify-center">
                  <span class="material-symbols-outlined text-3xl">description</span>
                </div>
                <div class="text-center">
                  <p class="font-body-lg text-base font-semibold text-on-surface truncate">{{ selectedFile.name }}</p>
                  <p class="font-label-sm text-xs text-secondary mt-0.5">{{ formatFileSize(selectedFile.size) }} • Sẵn sàng chuyển đổi</p>
                </div>

                <div class="flex items-center gap-3 mt-4" @click.stop>
                  <button
                    @click="onStartConvert"
                    class="bg-primary text-on-primary px-6 py-2.5 rounded-lg font-label-sm text-sm font-semibold hover:bg-primary-container transition-all flex items-center gap-2 shadow-sm"
                  >
                    <span class="material-symbols-outlined text-lg">play_arrow</span>
                    Bắt đầu chuyển đổi OMR
                  </button>
                  <button
                    @click="clearFile"
                    class="border border-border-subtle text-secondary hover:text-error hover:bg-error-container/20 px-4 py-2.5 rounded-lg font-label-sm text-sm transition-colors"
                  >
                    Đổi file khác
                  </button>
                </div>
              </div>
            </template>
          </div>
        </section>

        <!-- Recent Projects Section -->
        <section>
          <div class="flex justify-between items-center mb-4">
            <h2 class="font-headline-sm text-xl text-on-surface font-semibold">Dự án gần đây</h2>
            <button
              @click="$emit('navigate', 'library')"
              class="font-label-sm text-sm text-primary hover:underline font-semibold"
            >
              Xem tất cả ({{ projectStore.projects.length }}) →
            </button>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div
              v-for="project in projectStore.projects.slice(0, 4)"
              :key="project.id"
              @click="openRecentProject(project)"
              class="bg-surface-container-lowest border border-border-subtle rounded-xl p-panel-padding hover:border-primary hover:shadow-sm transition-all cursor-pointer flex gap-4 group"
            >
              <div class="w-16 h-20 bg-surface-container-low rounded-lg border border-border-subtle flex items-center justify-center shrink-0 group-hover:bg-primary/10 transition-colors overflow-hidden">
                <img
                  v-if="project.sourceImageUrl"
                  :src="project.sourceImageUrl"
                  alt="Preview"
                  class="w-full h-full object-cover"
                />
                <span v-else class="material-symbols-outlined text-secondary group-hover:text-primary">description</span>
              </div>
              <div class="flex flex-col justify-center flex-1 min-w-0">
                <h3 class="font-body-md text-sm font-semibold text-on-surface truncate group-hover:text-primary transition-colors">
                  {{ project.title }}
                </h3>
                <p class="font-label-sm text-xs text-secondary mt-1">{{ project.composer || 'Felice de Giardini' }} • {{ project.date }}</p>
                <div class="mt-2 flex items-center gap-2">
                  <span
                    class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold"
                    :class="project.status === 'READY' ? 'bg-success/15 text-success' : 'bg-warning/15 text-warning'"
                  >
                    {{ project.status }}
                  </span>
                  <span class="text-[10px] text-secondary">{{ project.verses }} Verses</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- Right Sidebar: Configuration (1 col) -->
      <div class="lg:col-span-1">
        <section class="bg-surface-container-lowest rounded-xl border border-border-subtle p-margin-main sticky top-0 shadow-xs">
          <h2 class="font-headline-sm text-lg text-on-surface font-semibold mb-6 flex items-center gap-2">
            <span class="material-symbols-outlined text-secondary">tune</span>
            Cấu hình nhận dạng OMR
          </h2>

          <form class="space-y-6" @submit.prevent="saveConfig">
            <!-- OMR Engine -->
            <div>
              <label class="block font-label-sm text-xs text-on-surface font-semibold mb-2">OMR Engine</label>
              <select
                v-model="config.omrEngine"
                class="w-full border border-border-subtle rounded-lg bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              >
                <option value="audiveris">Audiveris (Khuyến nghị cho Thánh ca & Piano)</option>
                <option value="oemer">Oemer (Deep Learning)</option>
              </select>
            </div>

            <!-- OCR Language -->
            <div>
              <label class="block font-label-sm text-xs text-on-surface font-semibold mb-2">Ngôn ngữ bóc tách lời (OCR)</label>
              <div class="space-y-2">
                <label class="flex items-center gap-2.5 cursor-pointer">
                  <input
                    v-model="config.langVietnamese"
                    type="checkbox"
                    class="rounded border-border-subtle text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                  />
                  <span class="text-sm text-on-surface font-medium">Tiếng Việt (vie)</span>
                </label>
                <label class="flex items-center gap-2.5 cursor-pointer">
                  <input
                    v-model="config.langEnglish"
                    type="checkbox"
                    class="rounded border-border-subtle text-primary focus:ring-primary w-4 h-4 cursor-pointer"
                  />
                  <span class="text-sm text-on-surface font-medium">English (eng)</span>
                </label>
              </div>
            </div>

            <hr class="border-border-subtle"/>

            <!-- Feature Toggles -->
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <p class="font-label-sm text-sm text-on-surface font-semibold">Nhận dạng lời nhạc (Lyrics)</p>
                  <p class="font-mono-label text-xs text-secondary mt-0.5">Bóc tách lời bài hát dưới nốt</p>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input
                    v-model="config.recognizeLyrics"
                    type="checkbox"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-surface-container-high peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>

              <div class="flex items-center justify-between">
                <div>
                  <p class="font-label-sm text-sm text-on-surface font-semibold">Nhận dạng hợp âm (Chords)</p>
                  <p class="font-mono-label text-xs text-secondary mt-0.5">Phát hiện ký hiệu hợp âm</p>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input
                    v-model="config.recognizeChords"
                    type="checkbox"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-surface-container-high peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>

            <div class="pt-4">
              <button
                type="button"
                @click="saveConfig"
                class="w-full bg-primary-fixed text-on-primary-fixed px-4 py-2.5 rounded-lg font-label-sm text-sm font-semibold hover:bg-primary-fixed-dim transition-colors flex justify-center items-center gap-2 shadow-xs"
              >
                <span class="material-symbols-outlined text-lg">save</span>
                {{ savedNotice ? 'Đã lưu cấu hình ✓' : 'Lưu cấu hình mặc định' }}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { projectStore, type ProjectItem } from '../Services/ProjectStore';

const emit = defineEmits<{
  (e: 'navigate', view: string): void;
  (e: 'open-project', project: ProjectItem): void;
  (e: 'start-conversion', file: File, config: any): void;
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);
const selectedFile = ref<File | null>(null);
const savedNotice = ref(false);

const config = reactive({
  omrEngine: 'audiveris',
  langVietnamese: true,
  langEnglish: true,
  recognizeLyrics: true,
  recognizeChords: true,
});

function triggerFileInput() {
  fileInputRef.value?.click();
}

function onFileSelected(e: Event) {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0];
  }
}

function onDrop(e: DragEvent) {
  isDragging.value = false;
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    selectedFile.value = e.dataTransfer.files[0];
  }
}

function clearFile() {
  selectedFile.value = null;
  if (fileInputRef.value) fileInputRef.value.value = '';
}

function onStartConvert() {
  if (!selectedFile.value) return;
  emit('start-conversion', selectedFile.value, { ...config });
}

function openRecentProject(project: ProjectItem) {
  projectStore.activeProjectId.value = project.id;
  emit('open-project', project);
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

function saveConfig() {
  savedNotice.value = true;
  setTimeout(() => {
    savedNotice.value = false;
  }, 2500);
}
</script>
