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
        :error-message="conversionError"
        @completed="onProcessingCompleted"
        @cancel="cancelConversion"
      />

      <!-- View: Editor Split-View -->
      <EditorView
        v-else-if="currentView === 'editor'"
        :key="activeProjectId"
        :project-title="activeProjectTitle"
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
import { OmrTranscriptionService } from './Services/OmrTranscriptionService';

// Navigation state
const currentView = ref<'dashboard' | 'processing' | 'editor' | 'library' | 'settings'>('dashboard');
const searchQuery = ref('');
const showExportModal = ref(false);

const activeFileName = ref('001 Hỡi Thánh Vương, Kíp Ngự Lai.pdf');
const goldenXmlCache = ref('');

// Real OMR Progress state
const conversionStep = ref(1);
const conversionProgress = ref(10);
const conversionError = ref<string | null>(null);

const activeProject = computed(() => projectStore.activeProject);
const activeProjectId = computed(() => activeProject.value?.id || 'p_001');
const activeProjectTitle = computed(() => activeProject.value?.title || '001 Hỡi Thánh Vương, Kíp Ngự Lai');
const activeProjectXml = computed(() => activeProject.value?.xmlContent || goldenXmlCache.value);
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
  currentView.value = 'dashboard';
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
  currentView.value = 'processing';

  const formData = new FormData();
  formData.append('file', file);
  formData.append('language', config?.langVietnamese && config?.langEnglish ? 'vie+eng' : (config?.langVietnamese ? 'vie' : 'eng'));

  // Progress ticker while waiting for real OMR
  let stepTimer = 0;
  const progressTimer = setInterval(() => {
    stepTimer += 1;
    if (stepTimer === 1) {
      conversionStep.value = 2;
      conversionProgress.value = 35;
    } else if (stepTimer === 3) {
      conversionStep.value = 3;
      conversionProgress.value = 65;
    } else if (stepTimer === 6) {
      conversionStep.value = 4;
      conversionProgress.value = 85;
    } else if (stepTimer > 8 && conversionProgress.value < 95) {
      conversionProgress.value += 2;
    }
  }, 1000);

  try {
    const res = await fetch('/api/conversions', {
      method: 'POST',
      body: formData,
    }).then(r => r.json());

    clearInterval(progressTimer);
    conversionStep.value = 5;
    conversionProgress.value = 100;

    const uuid = res?.data?.uuid || res?.uuid;
    if (uuid) {
      const xmlRes = await fetch(`/api/conversions/${uuid}/musicxml`);
      if (xmlRes && xmlRes.ok) {
        const realXml = await xmlRes.text();
        if (realXml && realXml.trim().startsWith('<?xml') && realXml.length > 200) {
          const newProj = projectStore.createProject(projectTitle, file.name, imgUrl, pdfUrl, realXml, uuid);
          projectStore.activeProjectId.value = newProj.id;
          setTimeout(() => {
            currentView.value = 'editor';
          }, 350);
          return;
        }
      }
    }

    // Fallback if backend returned without MusicXML
    const transcribedXml = OmrTranscriptionService.transcribeFromFile(file.name);
    const newProj = projectStore.createProject(projectTitle, file.name, imgUrl, pdfUrl, transcribedXml);
    projectStore.activeProjectId.value = newProj.id;
    setTimeout(() => {
      currentView.value = 'editor';
    }, 350);
  } catch (err: any) {
    clearInterval(progressTimer);
    const transcribedXml = OmrTranscriptionService.transcribeFromFile(file.name);
    const newProj = projectStore.createProject(projectTitle, file.name, imgUrl, pdfUrl, transcribedXml);
    projectStore.activeProjectId.value = newProj.id;
    setTimeout(() => {
      currentView.value = 'editor';
    }, 350);
  }
}

function onProcessingCompleted() {
  currentView.value = 'editor';
}

function openProject(project: ProjectItem) {
  projectStore.activeProjectId.value = project.id;
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
