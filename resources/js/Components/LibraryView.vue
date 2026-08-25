<template>
  <div class="flex-1 overflow-y-auto p-margin-main">
    <div class="max-w-7xl mx-auto space-y-6">
      <!-- ════════ TOP HEADER & SEARCH/FILTER BAR ════════ -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 class="font-headline-md text-2xl font-bold text-primary flex items-center gap-2">
            <span>Thư Viện Tuyển Tập & Bản Nhạc</span>
            <span class="text-xs bg-primary/10 text-primary border border-primary/20 px-2.5 py-0.5 rounded-full font-mono-label font-bold">
              {{ projectStore.projects.length }} bản nhạc
            </span>
          </h2>
          <p class="font-label-sm text-sm text-secondary mt-0.5">Quản lý, phân loại theo Cuốn Tuyển Tập, sửa và xuất bản các bài hát</p>
        </div>

        <div class="flex items-center gap-3 w-full sm:w-auto">
          <!-- Live Search Input -->
          <div class="relative flex-1 sm:w-64">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-secondary text-lg">search</span>
            <input
              v-model="searchTerm"
              type="text"
              placeholder="Tìm theo tên bài, tác giả, số bài..."
              class="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-border-subtle rounded-xl text-sm text-on-surface focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <!-- + Tạo mới Button -->
          <label class="bg-primary text-on-primary px-4 py-2 rounded-xl font-label-sm text-sm font-semibold hover:bg-primary-container transition-colors flex items-center gap-1.5 shadow-sm whitespace-nowrap cursor-pointer">
            <span class="material-symbols-outlined text-lg">add</span>
            <span>+ Tải Lên Mới</span>
            <input type="file" accept=".pdf,.png,.jpg,.jpeg,.xml,.musicxml" class="hidden" @change="onQuickUploadNewFile" />
          </label>
        </div>
      </div>

      <!-- ════════ SONGBOOKS & CATEGORIES TABS ════════ -->
      <div class="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none border-b border-border-subtle">
        <button
          v-for="cat in projectStore.categories"
          :key="cat.slug"
          @click="projectStore.activeCategorySlug.value = cat.slug"
          class="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap"
          :class="projectStore.activeCategorySlug.value === cat.slug ? 'bg-primary text-on-primary shadow-sm' : 'bg-surface-container-low text-secondary hover:text-on-surface hover:bg-surface-container'"
        >
          <span class="material-symbols-outlined text-sm">{{ cat.icon }}</span>
          <span>{{ cat.name }}</span>
          <span class="text-[10px] opacity-80 font-mono">({{ getCategoryCount(cat.slug) }})</span>
        </button>
      </div>

      <!-- ════════ FILTER STATUS PILLS ════════ -->
      <div class="flex items-center gap-2">
        <button
          @click="statusFilter = 'ALL'"
          class="px-3 py-1 rounded-full text-xs font-semibold transition-colors"
          :class="statusFilter === 'ALL' ? 'bg-surface-container-high text-on-surface font-bold' : 'bg-surface-container-low text-secondary hover:text-on-surface'"
        >
          Tất cả trạng thái
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
      <div v-if="filteredProjects.length === 0" class="text-center py-16 bg-surface-container-lowest rounded-2xl border border-border-subtle">
        <span class="material-symbols-outlined text-5xl text-secondary mb-3">auto_stories</span>
        <h3 class="font-headline-sm text-base font-bold text-on-surface mb-1">Chưa có bài hát trong tuyển tập này</h3>
        <p class="text-xs text-secondary mb-4">Hãy tải lên một bản nhạc PDF hoặc hình ảnh mới để lưu vào cuốn tuyển tập.</p>
        <label class="bg-primary text-on-primary px-4 py-2 rounded-xl font-label-sm text-xs font-semibold hover:bg-primary-container transition-colors inline-flex items-center gap-1.5 cursor-pointer">
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
          class="bg-surface-container-lowest border border-border-subtle rounded-2xl overflow-hidden flex flex-col hover:shadow-lg hover:border-primary/50 transition-all group relative cursor-pointer"
          @click="openProject(project)"
        >
          <!-- Card Thumbnail with dynamic preview -->
          <div class="h-44 bg-surface-container-low border-b border-border-subtle relative overflow-hidden flex items-center justify-center">
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

            <!-- Category Badge (Top-Left) -->
            <div
              v-if="project.categoryName"
              class="absolute top-2.5 left-2.5 bg-slate-900/80 backdrop-blur-xs text-white px-2.5 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 shadow-sm"
            >
              <span class="material-symbols-outlined text-xs text-primary">bookmark</span>
              <span>{{ project.categoryName }} {{ project.songNumber ? `#${project.songNumber}` : '' }}</span>
            </div>

            <!-- Status Badge (Top-Right) -->
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

          <!-- Card Content -->
          <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
            <div>
              <h3 class="font-headline-sm text-sm font-bold text-on-surface truncate group-hover:text-primary transition-colors">
                {{ project.title }}
              </h3>
              <p class="font-label-sm text-xs text-secondary truncate mt-0.5">
                {{ project.composer || 'Chưa rõ tác giả' }}
              </p>
            </div>

            <!-- Meta details row -->
            <div class="flex items-center justify-between text-[11px] text-secondary border-t border-border-subtle pt-2">
              <div class="flex items-center gap-2 font-mono">
                <span>{{ project.keySig || 'C Major' }}</span>
                <span>•</span>
                <span>{{ project.timeSig || '4/4' }}</span>
              </div>
              <div class="flex items-center gap-1">
                <span class="material-symbols-outlined text-xs">lyrics</span>
                <span>{{ project.verses }} Verse</span>
              </div>
            </div>

            <!-- Card Actions -->
            <div class="flex items-center justify-between pt-1" @click.stop>
              <!-- Chuyển Category Selector -->
              <select
                :value="project.categorySlug || 'thanh-ca-ton-vinh'"
                @change="onCategoryChange(project.id, ($event.target as HTMLSelectElement).value)"
                class="text-[10px] bg-surface-container-low border border-border-subtle rounded-lg px-2 py-1 text-secondary font-medium hover:border-primary transition-colors"
                title="Đổi Tuyển tập / Danh mục"
              >
                <option value="thanh-ca-ton-vinh">📖 Thánh Ca</option>
                <option value="nhac-tru-tinh-dan-ca">🎼 Nhạc Trữ Tình</option>
                <option value="guitar-dem-hat">🎸 Đệm Hát</option>
                <option value="tuyen-tap-ca-nhan">📁 Tuyển Tập Riêng</option>
              </select>

              <div class="flex items-center gap-1">
                <button
                  @click.stop="openProject(project)"
                  class="p-1.5 text-secondary hover:text-primary hover:bg-surface-container-low rounded-lg transition-colors"
                  title="Mở chỉnh sửa bản nhạc"
                >
                  <span class="material-symbols-outlined text-base">edit</span>
                </button>
                <button
                  @click.stop="confirmDeleteProject(project.id, project.title)"
                  class="p-1.5 text-secondary hover:text-error hover:bg-surface-container-low rounded-lg transition-colors"
                  title="Xóa vĩnh viễn"
                >
                  <span class="material-symbols-outlined text-base">delete</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { projectStore, ProjectItem } from '../Services/ProjectStore';

const emit = defineEmits<{
  (e: 'open-project', project: ProjectItem): void;
  (e: 'start-conversion', file: File): void;
}>();

const searchTerm = ref<string>('');
const statusFilter = ref<'ALL' | 'READY' | 'NEEDS_REVIEW'>('ALL');

function getCategoryCount(slug: string): number {
  if (slug === 'all') return projectStore.projects.length;
  return projectStore.projects.filter(p => (p.categorySlug || 'thanh-ca-ton-vinh') === slug).length;
}

const filteredProjects = computed(() => {
  return projectStore.projects.filter(p => {
    // 1. Lọc theo Category / Songbook Tab
    const currentCat = projectStore.activeCategorySlug.value;
    if (currentCat !== 'all') {
      const pCat = p.categorySlug || 'thanh-ca-ton-vinh';
      if (pCat !== currentCat) return false;
    }

    // 2. Lọc theo Status
    if (statusFilter.value !== 'ALL' && p.status !== statusFilter.value) {
      return false;
    }

    // 3. Lọc theo Search Term
    if (searchTerm.value.trim() !== '') {
      const term = searchTerm.value.toLowerCase().trim();
      const matchTitle = p.title.toLowerCase().includes(term);
      const matchComposer = (p.composer || '').toLowerCase().includes(term);
      const matchNumber = (p.songNumber || '').includes(term);
      return matchTitle || matchComposer || matchNumber;
    }

    return true;
  });
});

function openProject(project: ProjectItem) {
  projectStore.activeProjectId.value = project.id;
  emit('open-project', project);
}

function onCategoryChange(projectId: string, newSlug: string) {
  projectStore.updateProjectCategory(projectId, newSlug);
}

async function confirmDeleteProject(id: string, title: string) {
  if (confirm(`Bạn có chắc chắn muốn xóa bản nhạc "${title}" không? Hành động này không thể hoàn tác.`)) {
    await projectStore.deleteProject(id);
  }
}

function onQuickUploadNewFile(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files[0]) {
    emit('start-conversion', input.files[0]);
  }
}
</script>
