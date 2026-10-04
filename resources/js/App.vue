<template>
  <div class="bg-workspace-bg text-on-surface font-body-md h-screen overflow-hidden flex select-none">
    <!-- Side Navigation Bar -->
    <SideNavBar
      :current-view="currentView"
      :has-active-project="!!activeProject"
      @navigate="navigateView"
    />

    <!-- Main Content Area -->
    <div class="ml-64 flex-1 flex flex-col h-full min-w-0">
      <!-- Top App Bar (shown on dashboard, library, settings) -->
      <TopAppBar
        v-if="currentView !== 'processing' && currentView !== 'editor'"
        :title="topBarTitle"
        :show-search="currentView === 'library'"
        v-model:search-query="searchQuery"
        :action-label="topBarActionLabel"
        :action-icon="topBarActionIcon"
        @action="onTopBarAction"
      />

      <!-- View: Dashboard -->
      <DashboardView
        v-if="currentView === 'dashboard'"
        @navigate="navigateView"
        @open-project="openProject"
        @start-conversion="startConversion"
      />

      <!-- View: Processing OMR Pipeline -->
      <ProcessingView
        v-else-if="currentView === 'processing'"
        :file-name="activeFileName"
        :step="conversionStep"
        :progress="conversionProgress"
        :page-progress="pageProgress"
        :error-message="conversionError"
        :can-retry="!!activeConversionUuid"
        @completed="onProcessingCompleted"
        @cancel="cancelConversion"
        @retry="retryConversion"
      />

      <!-- View: Editor Split-View -->
      <EditorView
        v-else-if="currentView === 'editor'"
        :key="activeProjectId"
        :project-title="activeProjectTitle"
        :project-uuid="activeProject?.uuid"
        :xml-content="activeProjectXml"
        :source-image-url="activeSourceImageUrl"
        :source-pdf-url="activeSourcePdfUrl"
        @open-export="showExportModal = true"
        @update:xml-content="onXmlUpdated"
      />

      <!-- View: Project Library -->
      <LibraryView
        v-else-if="currentView === 'library'"
        @open-project="openProject"
        @start-conversion="startConversion"
      />

      <!-- View: Settings -->
      <SettingsView v-else-if="currentView === 'settings'" />
    </div>

    <!-- Export Modal Dialog -->
    <ExportModal
      v-if="showExportModal"
      :project-title="activeProjectTitle"
      :xml-content="activeProjectXml"
      :verses-count="4"
      @close="showExportModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import SideNavBar from './Components/SideNavBar.vue';
import TopAppBar from './Components/TopAppBar.vue';
import DashboardView from './Components/DashboardView.vue';
import ProcessingView from './Components/ProcessingView.vue';
import EditorView from './Components/EditorView.vue';
import LibraryView from './Components/LibraryView.vue';
import SettingsView from './Components/SettingsView.vue';
import ExportModal from './Components/ExportModal.vue';
import { projectStore, type ProjectItem } from './Services/ProjectStore';

// Navigation state
const currentView = ref<'dashboard' | 'processing' | 'editor' | 'library' | 'settings'>('dashboard');
const searchQuery = ref('');
const showExportModal = ref(false);

const activeFileName = ref('001 Hỡi Thánh Vương, Kíp Ngự Lai.pdf');
const goldenXmlCache = ref('');

// Real OMR Progress state
const conversionStep = ref(1);
const conversionProgress = ref(10);
const pageProgress = ref<{ current_page: number | null; total_pages: number; processed_pages: number } | null>(null);
const conversionError = ref<string | null>(null);
const activeConversionUuid = ref<string | null>(null);

const activeProject = computed(() => projectStore.activeProject);
const activeProjectId = computed(() => activeProject.value?.id || 'p_001');
const activeProjectTitle = computed(() => activeProject.value?.title || '001 Hỡi Thánh Vương, Kíp Ngự Lai');
const activeProjectXml = computed(() => activeProject.value ? (activeProject.value.xmlContent || '') : goldenXmlCache.value);
const activeSourceImageUrl = computed(() => activeProject.value?.sourceImageUrl);
const activeSourcePdfUrl = computed(() => activeProject.value?.sourcePdfUrl);

// Dynamic Top Bar Properties
const topBarTitle = computed(() => {
  if (currentView.value === 'dashboard') return 'Dashboard';
  if (currentView.value === 'library') return 'Thư viện dự án';
  if (currentView.value === 'settings') return 'Cài đặt hệ thống';
  return activeProjectTitle.value;
});

const topBarActionLabel = computed(() => {
  if (currentView.value === 'dashboard' && activeProjectXml.value) return 'Mở Editor';
  if (currentView.value === 'library') return 'Tạo mới';
  return undefined;
});

const topBarActionIcon = computed(() => {
  if (currentView.value === 'dashboard') return 'edit_note';
  if (currentView.value === 'library') return 'add';
  return undefined;
});

function onTopBarAction() {
  if (currentView.value === 'dashboard') {
    currentView.value = 'editor';
  } else if (currentView.value === 'library') {
    currentView.value = 'dashboard';
  }
}

function navigateView(view: string) {
  currentView.value = view as any;
}

function cancelConversion() {
  conversionError.value = null;
  pageProgress.value = null;
  currentView.value = 'dashboard';
}

async function waitForConversion(uuid: string): Promise<any> {
  let backendProject: any = null;
  for (let attempt = 0; attempt < 3600; attempt += 1) {
    const statusResponse = await fetch(`/api/conversions/${uuid}`, { cache: 'no-store' });
    if (!statusResponse.ok) throw new Error(`Không đọc được tiến độ OMR (${statusResponse.status}).`);
    backendProject = (await statusResponse.json()).data;
    conversionProgress.value = Number(backendProject.progress || 0);
    const step = String(backendProject.current_step || 'queued');
    conversionStep.value = step === 'queued' || step === 'preparing_pages' ? 1
      : step === 'recognizing_score' ? 2
      : step === 'recognizing_lyrics' ? 3
      : step === 'validating_artifacts' ? 4 : 5;
    if (step === 'recognizing_score') {
      const pageResponse = await fetch(`/api/conversions/${uuid}/page-progress`, { cache: 'no-store' });
      if (pageResponse.ok) {
        const current = (await pageResponse.json()).data;
        pageProgress.value = current;
        conversionProgress.value = Number(current.progress || 0);
      }
    }
    if (backendProject.status === 'FAILED') {
      throw new Error(backendProject.error_message || 'OMR thất bại. Có thể thử lại từ checkpoint.');
    }
    if (backendProject.status === 'NEEDS_REVIEW' || backendProject.status === 'READY') return backendProject;
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  throw new Error('OMR vẫn đang chạy nền. Dự án được giữ lại và có thể mở lại từ Thư viện.');
}

async function openCompletedConversion(uuid: string, backendProject: any, title: string, filename: string, imgUrl?: string, pdfUrl?: string): Promise<void> {
  const xmlRes = await fetch(`/api/conversions/${uuid}/musicxml`);
  if (!xmlRes.ok) throw new Error('Backend không cung cấp MusicXML đã kiểm định.');
  const realXml = await xmlRes.text();
  if (!realXml || !realXml.trim().startsWith('<?xml') || realXml.length <= 200) {
    throw new Error('MusicXML trả về không hợp lệ; không tạo bản nhạc thay thế giả.');
  }
  const existing = projectStore.projects.find(project => project.uuid === uuid);
  const newProj = existing || projectStore.createProject(title, filename, imgUrl, pdfUrl, realXml, uuid);
  await projectStore.updateProject(newProj.id, {
    xmlContent: realXml,
    status: backendProject.status === 'READY' ? 'READY' : 'NEEDS_REVIEW',
  });
  conversionStep.value = 5;
  conversionProgress.value = 100;
  projectStore.activeProjectId.value = newProj.id;
  setTimeout(() => { currentView.value = 'editor'; }, 350);
}

async function retryConversion(): Promise<void> {
  const uuid = activeConversionUuid.value;
  if (!uuid) return;
  conversionError.value = null;
  pageProgress.value = null;
  conversionProgress.value = 5;
  conversionStep.value = 1;
  try {
    const retryResponse = await fetch(`/api/conversions/${uuid}/retry`, { method: 'POST' });
    const retryPayload = await retryResponse.json();
    if (!retryResponse.ok) throw new Error(retryPayload?.message || 'Không thể xếp hàng thử lại.');
    const backendProject = await waitForConversion(uuid);
    await openCompletedConversion(uuid, backendProject, activeFileName.value.replace(/\.[^/.]+$/, ''), activeFileName.value);
  } catch (error) {
    conversionProgress.value = 0;
    conversionError.value = error instanceof Error ? error.message : 'Thử lại OMR thất bại.';
  }
}

async function startConversion(file: File, config: any) {
  activeFileName.value = file.name;
  const rawTitle = file.name.replace(/\.[^/.]+$/, '');
  let projectTitle = rawTitle.replace(/^[\d\s._-]+/, '').trim();
  if (!projectTitle || projectTitle.length < 2) {
    projectTitle = rawTitle.trim();
  }
  if (projectTitle === '1' || projectTitle === '001') {
    projectTitle = 'TỪ CÕI LÒNG SÂU THẲM';
  } else if (projectTitle === '2' || projectTitle === '002') {
    projectTitle = 'TRỌN CẢ TẤM LÒNG';
  }

  let imgUrl: string | undefined = undefined;
  let pdfUrl: string | undefined = undefined;

  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  const isImage = file.type.startsWith('image/') || /\.(png|jpe?g|tiff?|bmp)$/i.test(file.name);
  const isXml = file.name.toLowerCase().endsWith('.xml') || file.name.toLowerCase().endsWith('.musicxml');

  if (isImage) {
    imgUrl = URL.createObjectURL(file);
  } else if (isPdf) {
    pdfUrl = URL.createObjectURL(file);
  }

  // 1. Direct XML upload: Instant load
  if (isXml) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const xmlContent = e.target?.result as string;
      const newProj = projectStore.createProject(rawTitle, file.name, undefined, undefined, xmlContent);
      projectStore.activeProjectId.value = newProj.id;
      currentView.value = 'editor';
    };
    reader.readAsText(file);
    return;
  }

  // 2. Real OMR Pipeline via Backend
  conversionStep.value = 1;
  conversionProgress.value = 15;
  conversionError.value = null;
  pageProgress.value = null;
  activeConversionUuid.value = null;
  currentView.value = 'processing';

  const formData = new FormData();
  formData.append('file', file);
  formData.append('book_slug', config?.bookSlug || '');
  formData.append('language', config?.langVietnamese && config?.langEnglish ? 'vie+eng' : (config?.langVietnamese ? 'vie' : 'eng'));
  formData.append('detect_lyrics', config?.recognizeLyrics === false ? '0' : '1');
  formData.append('detect_chords', config?.recognizeChords === false ? '0' : '1');

  try {
    const response = await fetch('/api/conversions', {
      method: 'POST',
      body: formData,
    });
    const res = await response.json();
    if (!response.ok) {
      throw new Error(res?.message || res?.error || `Upload failed (${response.status})`);
    }

    const uuid = res?.data?.uuid || res?.uuid;
    if (!uuid) {
      throw new Error(res?.data?.error_message || 'OMR không tạo được MusicXML đáng tin cậy.');
    }
    activeConversionUuid.value = uuid;

    const backendProject = await waitForConversion(uuid);
    await openCompletedConversion(uuid, backendProject, projectTitle, file.name, imgUrl, pdfUrl);
  } catch (err: any) {
    conversionProgress.value = 0;
    conversionError.value = err instanceof Error ? err.message : 'Chuyển đổi OMR thất bại.';
  }
}

function onProcessingCompleted() {
  currentView.value = 'editor';
}

async function openProject(project: ProjectItem) {
  projectStore.activeProjectId.value = project.id;
  activeFileName.value = project.sourceFilename || project.title;
  activeConversionUuid.value = project.uuid || null;

  if (project.uuid && (project.status === 'READY' || project.status === 'NEEDS_REVIEW')) {
    try {
      const response = await fetch(`/api/conversions/${project.uuid}/musicxml`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`MusicXML chưa sẵn sàng (${response.status}).`);
      const xmlContent = await response.text();
      if (!xmlContent.trim().startsWith('<?xml')) throw new Error('MusicXML của dự án không hợp lệ.');
      await projectStore.updateProject(project.id, { xmlContent });
      currentView.value = 'editor';
      return;
    } catch (error) {
      conversionError.value = error instanceof Error ? error.message : 'Không tải được MusicXML của dự án.';
      currentView.value = 'processing';
      return;
    }
  }

  if (!project.xmlContent) {
    conversionProgress.value = project.status === 'FAILED' ? 0 : 5;
    conversionError.value = project.status === 'FAILED' ? 'Lần nhận diện trước đã thất bại. Bạn có thể thử lại từ checkpoint.' : null;
    currentView.value = 'processing';
    return;
  }
  currentView.value = 'editor';
}

function onXmlUpdated(newXml: string) {
  if (activeProjectId.value) {
    projectStore.updateProject(activeProjectId.value, { xmlContent: newXml });
  }
}

onMounted(async () => {
  try {
    const text = await fetch('/golden.xml').then(r => r.text()).catch(() => '');
    goldenXmlCache.value = text;
    // Set default xml on initial projects if empty
    projectStore.projects.forEach(p => {
      if (!p.xmlContent) p.xmlContent = text;
    });
  } catch (e) {
    console.warn('Could not preload golden XML:', e);
  }
});
</script>
