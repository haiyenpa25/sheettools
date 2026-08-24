<template>
  <div class="flex-1 overflow-y-auto p-margin-main">
    <div class="max-w-7xl mx-auto space-y-6">
      <!-- ════════ TOP HEADER & SEARCH/FILTER BAR ════════ -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 class="font-headline-md text-2xl font-bold text-primary flex items-center gap-2">
            <span>Thư viện dự án</span>
            <span class="text-xs bg-primary/10 text-primary border border-primary/20 px-2.5 py-0.5 rounded-full font-mono-label font-bold">
              {{ projectStore.projects.length }} bản nhạc
            </span>
          </h2>
          <p class="font-label-sm text-sm text-secondary mt-0.5">Quản lý, thêm, sửa, xóa và mở các bản nhạc đã chuyển đổi</p>
        </div>

        <div class="flex items-center gap-3 w-full sm:w-auto">
          <!-- Live Search Input -->
          <div class="relative flex-1 sm:w-64">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-secondary text-lg">search</span>
            <input
              v-model="searchTerm"
              type="text"
              placeholder="Tìm kiếm theo tên bài, tác giả..."
              class="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-border-subtle rounded-lg text-sm text-on-surface focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <!-- + Tạo mới Button -->
          <label class="bg-primary text-on-primary px-4 py-2 rounded-lg font-label-sm text-sm font-semibold hover:bg-primary-container transition-colors flex items-center gap-1.5 shadow-sm whitespace-nowrap cursor-pointer">
            <span class="material-symbols-outlined text-lg">add</span>
            <span>+ Tạo mới</span>
            <input type="file" accept=".pdf,.png,.jpg,.jpeg,.xml,.musicxml" class="hidden" @change="onQuickUploadNewFile" />
          </label>
        </div>
      </div>

      <!-- ════════ FILTER STATUS PILLS ════════ -->
      <div class="flex items-center gap-2 border-b border-border-subtle pb-3">
        <button
          @click="statusFilter = 'ALL'"
          class="px-3 py-1 rounded-full text-xs font-semibold transition-colors"
          :class="statusFilter === 'ALL' ? 'bg-primary text-on-primary' : 'bg-surface-container-low text-secondary hover:text-on-surface'"
        >
          Tất cả ({{ projectStore.projects.length }})
        </button>
        <button
          @click="statusFilter = 'READY'"
          class="px-3 py-1 rounded-full text-xs font-semibold transition-colors flex items-center gap-1"
          :class="statusFilter === 'READY' ? 'bg-success text-on-primary' : 'bg-surface-container-low text-secondary hover:text-on-surface'"
        >
          <span class="w-1.5 h-1.5 bg-success rounded-full" :class="{ 'bg-white': statusFilter === 'READY' }"></span>
          Đã xong (READY)
        </button>
        <button
          @click="statusFilter = 'NEEDS_REVIEW'"
          class="px-3 py-1 rounded-full text-xs font-semibold transition-colors flex items-center gap-1"
          :class="statusFilter === 'NEEDS_REVIEW' ? 'bg-warning text-on-background' : 'bg-surface-container-low text-secondary hover:text-on-surface'"
        >
          <span class="w-1.5 h-1.5 bg-warning rounded-full"></span>
          Cần soát lỗi (NEEDS REVIEW)
        </button>
      </div>

      <!-- ════════ EMPTY STATE ════════ -->
      <div v-if="filteredProjects.length === 0" class="text-center py-16 bg-surface-container-lowest rounded-xl border border-border-subtle">
        <span class="material-symbols-outlined text-5xl text-secondary mb-3">library_music</span>
        <h3 class="font-headline-sm text-base font-bold text-on-surface mb-1">Không tìm thấy bản nhạc nào</h3>
        <p class="text-xs text-secondary mb-4">Hãy tải lên một bản nhạc PDF hoặc hình ảnh mới để bắt đầu.</p>
        <label class="bg-primary text-on-primary px-4 py-2 rounded font-label-sm text-xs font-semibold hover:bg-primary-container transition-colors inline-flex items-center gap-1.5 cursor-pointer">
          <span class="material-symbols-outlined text-base">upload_file</span>
          <span>Tải lên bản nhạc mới</span>
          <input type="file" accept=".pdf,.png,.jpg,.jpeg,.xml,.musicxml" class="hidden" @change="onQuickUploadNewFile" />
        </label>
      </div>

      <!-- ════════ PROJECT GRID CARDS ════════ -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <div
          v-for="project in filteredProjects"
          :key="project.id"
          class="bg-surface-container-lowest border border-border-subtle rounded-xl overflow-hidden flex flex-col hover:shadow-md hover:border-primary/50 transition-all group relative cursor-pointer"
          @click="openProject(project)"
        >
          <!-- Card Thumbnail with dynamic preview -->
          <div class="h-40 bg-surface-container-low border-b border-border-subtle relative overflow-hidden flex items-center justify-center">
            <!-- If user has actual image preview -->
            <img
              v-if="project.sourceImageUrl"
              :src="project.sourceImageUrl"
              alt="Preview"
              class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
            <!-- Simulated Sheet music paper background -->
            <div v-else class="w-full h-full bg-white p-4 flex flex-col justify-center gap-2 opacity-90 group-hover:opacity-100 transition-opacity">
              <div class="text-[11px] font-bold text-center text-slate-800 truncate mb-1">{{ project.title }}</div>
              <div v-for="s in 3" :key="s" class="flex flex-col gap-1 border-b border-slate-200 pb-1">
                <div v-for="l in 4" :key="l" class="h-px bg-slate-400 w-full"></div>
              </div>
            </div>

            <!-- Status Badge -->
            <div
              v-if="project.status === 'READY'"
              class="absolute top-2.5 right-2.5 bg-success text-on-primary px-2.5 py-1 rounded-md font-mono-label text-[10px] font-bold flex items-center gap-1 shadow-sm"
            >
              <span class="material-symbols-outlined text-xs">check_circle</span> READY
            </div>
            <div
              v-else-if="project.status === 'NEEDS_REVIEW'"
              class="absolute top-2.5 right-2.5 bg-warning text-on-background px-2.5 py-1 rounded-md font-mono-label text-[10px] font-bold flex items-center gap-1 shadow-sm"
            >
              <span class="material-symbols-outlined text-xs">error_outline</span> NEEDS REVIEW
            </div>
            <div
              v-else
              class="absolute top-2.5 right-2.5 bg-primary text-on-primary px-2.5 py-1 rounded-md font-mono-label text-[10px] font-bold flex items-center gap-1 shadow-sm"
            >
              <span class="material-symbols-outlined text-xs animate-spin">sync</span> PROCESSING
            </div>
          </div>

          <!-- Card Details -->
          <div class="p-4 flex-1 flex flex-col justify-between">
            <div>
              <div class="flex items-start justify-between gap-2 mb-1">
                <h3 class="font-headline-sm text-sm font-bold text-on-surface truncate group-hover:text-primary transition-colors flex-1" :title="project.title">
                  {{ project.title }}
                </h3>
                <button
                  @click.stop="openRenameModal(project)"
                  class="text-secondary hover:text-primary p-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Đổi tên bản nhạc"
                >
                  <span class="material-symbols-outlined text-sm">edit</span>
                </button>
              </div>

              <p class="font-label-sm text-xs text-secondary mb-3 flex items-center gap-2">
                <span>{{ project.composer || 'Felice de Giardini' }}</span>
                <span>•</span>
                <span>{{ project.date }}</span>
              </p>
            </div>

            <!-- Card Bottom Actions -->
            <div class="flex justify-between items-center border-t border-border-subtle pt-3 mt-2">
              <button
                @click.stop="openProject(project)"
                class="text-primary hover:text-primary-container font-label-sm text-xs font-bold transition-colors uppercase tracking-wider flex items-center gap-1"
              >
                {{ project.status === 'NEEDS_REVIEW' ? 'REVIEW' : 'OPEN' }} →
              </button>

              <div class="flex items-center gap-1">
                <!-- Quick Export MusicXML -->
                <button
                  @click.stop="quickDownloadXml(project)"
                  class="p-1.5 text-secondary hover:text-primary hover:bg-surface-container-low rounded-md transition-colors"
                  title="Tải về file MusicXML"
                >
                  <span class="material-symbols-outlined text-base">download</span>
                </button>

                <!-- Delete Project Button -->
                <button
                  @click.stop="confirmDelete(project)"
                  class="p-1.5 text-secondary hover:text-error hover:bg-error/10 rounded-md transition-colors"
                  title="Xóa bản nhạc này"
                >
                  <span class="material-symbols-outlined text-base">delete</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════ RENAME PROJECT MODAL ════════ -->
    <Teleport to="body">
      <div v-if="showRenameModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4" @click.self="showRenameModal = false">
        <div class="bg-surface-container-lowest border border-border-subtle rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
          <div class="flex justify-between items-center pb-2 border-b border-border-subtle">
            <h3 class="font-headline-sm text-base font-bold text-on-surface">Đổi Tên Bản Nhạc</h3>
            <button @click="showRenameModal = false" class="p-1 text-secondary hover:text-on-surface">✕</button>
          </div>

          <div class="space-y-3 text-xs">
            <div>
              <label class="block font-semibold text-on-surface mb-1">Tiêu đề bài hát</label>
              <input
                v-model="editProjectTitle"
                type="text"
                class="w-full p-2.5 border border-border-subtle rounded-lg bg-surface-container-lowest text-sm focus:border-primary outline-none"
              />
            </div>
            <div>
              <label class="block font-semibold text-on-surface mb-1">Nhạc sĩ / Tác giả</label>
              <input
                v-model="editProjectComposer"
                type="text"
                class="w-full p-2.5 border border-border-subtle rounded-lg bg-surface-container-lowest text-sm focus:border-primary outline-none"
              />
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-2 border-t border-border-subtle">
            <button @click="showRenameModal = false" class="px-3.5 py-1.5 border border-border-subtle text-secondary rounded-lg text-xs font-semibold">Hủy</button>
            <button @click="saveRename" class="px-4 py-1.5 bg-primary text-on-primary rounded-lg text-xs font-semibold hover:bg-primary-container">Lưu thay đổi</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { projectStore, type ProjectItem } from '../Services/ProjectStore';

const emit = defineEmits<{
  (e: 'open-project', project: ProjectItem): void;
  (e: 'start-conversion', file: File, config: any): void;
}>();

const searchTerm = ref('');
const statusFilter = ref<'ALL' | 'READY' | 'NEEDS_REVIEW'>('ALL');

const showRenameModal = ref(false);
const editingProjectId = ref('');
const editProjectTitle = ref('');
const editProjectComposer = ref('');

const filteredProjects = computed(() => {
  let list = projectStore.projects;

  if (statusFilter.value !== 'ALL') {
    list = list.filter(p => p.status === statusFilter.value);
  }

  if (searchTerm.value.trim()) {
    const q = searchTerm.value.toLowerCase();
    list = list.filter(
      p => p.title.toLowerCase().includes(q) || (p.composer && p.composer.toLowerCase().includes(q))
    );
  }

  return list;
});

function openProject(project: ProjectItem) {
  projectStore.activeProjectId.value = project.id;
  emit('open-project', project);
}

function openRenameModal(project: ProjectItem) {
  editingProjectId.value = project.id;
  editProjectTitle.value = project.title;
  editProjectComposer.value = project.composer || '';
  showRenameModal.value = true;
}

function saveRename() {
  if (editingProjectId.value && editProjectTitle.value.trim()) {
    projectStore.updateProject(editingProjectId.value, {
      title: editProjectTitle.value.trim(),
      composer: editProjectComposer.value.trim(),
    });
  }
  showRenameModal.value = false;
}

function confirmDelete(project: ProjectItem) {
  if (confirm(`Bạn có chắc chắn muốn xóa bản nhạc "${project.title}" khỏi thư viện?`)) {
    projectStore.deleteProject(project.id);
  }
}

function quickDownloadXml(project: ProjectItem) {
  const xml = project.xmlContent || '';
  const blob = new Blob([xml], { type: 'application/vnd.recordare.musicxml+xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${project.title}.musicxml`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function onQuickUploadNewFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;

  emit('start-conversion', file, {
    omrEngine: 'audiveris',
    langVietnamese: true,
    langEnglish: true,
    recognizeLyrics: true,
    recognizeChords: true,
  });
}
</script>
