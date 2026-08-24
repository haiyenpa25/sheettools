import { reactive, ref } from 'vue';
import { OmrTranscriptionService } from './OmrTranscriptionService';

export interface ProjectItem {
  id: string;
  title: string;
  composer?: string;
  date: string;
  status: 'READY' | 'NEEDS_REVIEW' | 'PROCESSING';
  verses: number;
  keySig?: string;
  timeSig?: string;
  sourceFilename?: string;
  sourceImageUrl?: string;
  sourcePdfUrl?: string;
  xmlContent?: string;
}

const STORAGE_KEY = 'sheet_converter_projects_v4';

// Default initial projects with accurate MusicXML content
const initialProjects: ProjectItem[] = [
  {
    id: 'p_001',
    title: '001 Hỡi Thánh Vương, Kíp Ngự Lai',
    composer: 'Felice de Giardini, 1769',
    date: '12/10/2023',
    status: 'READY',
    verses: 4,
    keySig: 'G Major',
    timeSig: '3/4',
    sourceFilename: '001 Hỡi Thánh Vương, Kíp Ngự Lai.pdf',
  },
  {
    id: 'p_045',
    title: '045 Chúa Chăn Nuôi Tôi',
    composer: 'T. Koschat',
    date: '11/10/2023',
    status: 'NEEDS_REVIEW',
    verses: 3,
    keySig: 'F Major',
    timeSig: '4/4',
    sourceFilename: '045_Chua_Chan_Nuoi_Toi.png',
    xmlContent: OmrTranscriptionService.generateChuaChanNuoiToi(),
  },
  {
    id: 'p_089',
    title: '089 Tâm Hồn Chúc Tụng',
    composer: 'Jonas Myrin & Matt Redman',
    date: '12/10/2023',
    status: 'READY',
    verses: 4,
    keySig: 'G Major',
    timeSig: '4/4',
    sourceFilename: '089_Tam_Hon_Chuc_Tung.jpg',
    xmlContent: OmrTranscriptionService.generateTamHonChucTung(),
  },
  {
    id: 'p_112',
    title: '112 Nguyện Danh Chúa Cả Sáng',
    composer: 'Lowell Mason',
    date: '10/10/2023',
    status: 'READY',
    verses: 5,
    keySig: 'D Major',
    timeSig: '3/4',
    sourceFilename: '112_Nguyen_Danh_Chua.pdf',
    xmlContent: OmrTranscriptionService.generateDynamicHymnStructure('112 Nguyện Danh Chúa Cả Sáng', 3, 4, 2, 16),
  },
];

class ProjectStore {
  public projects = reactive<ProjectItem[]>([]);
  public activeProjectId = ref<string>('p_001');

  constructor() {
    this.loadFromStorage();
  }

  private loadFromStorage(): void {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          this.projects.splice(0, this.projects.length, ...parsed);
          return;
        }
      }
    } catch (e) {
      console.warn('Failed to load projects from storage, using defaults:', e);
    }
    this.projects.splice(0, this.projects.length, ...initialProjects);
    this.saveToStorage();
  }

  public saveToStorage(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.projects));
    } catch (e) {
      console.warn('Failed to save projects to storage:', e);
    }
  }

  public get activeProject(): ProjectItem | undefined {
    return this.projects.find(p => p.id === this.activeProjectId.value) || this.projects[0];
  }

  public createProject(
    title: string,
    filename: string,
    sourceImageUrl?: string,
    sourcePdfUrl?: string,
    xmlContent?: string
  ): ProjectItem {
    const today = new Date();
    const dateStr = `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()}`;

    const newProj: ProjectItem = {
      id: 'proj_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
      title: title.trim() || 'Bản nhạc mới',
      composer: 'Tác giả bài hát',
      date: dateStr,
      status: 'READY',
      verses: 4,
      keySig: 'G Major',
      timeSig: '3/4',
      sourceFilename: filename,
      sourceImageUrl,
      sourcePdfUrl,
      xmlContent,
    };

    this.projects.unshift(newProj);
    this.activeProjectId.value = newProj.id;
    this.saveToStorage();
    return newProj;
  }

  public deleteProject(id: string): boolean {
    const idx = this.projects.findIndex(p => p.id === id);
    if (idx !== -1) {
      this.projects.splice(idx, 1);
      if (this.activeProjectId.value === id && this.projects.length > 0) {
        this.activeProjectId.value = this.projects[0].id;
      }
      this.saveToStorage();
      return true;
    }
    return false;
  }

  public updateProject(id: string, updates: Partial<ProjectItem>): void {
    const proj = this.projects.find(p => p.id === id);
    if (proj) {
      Object.assign(proj, updates);
      this.saveToStorage();
    }
  }

  public getProject(id: string): ProjectItem | undefined {
    return this.projects.find(p => p.id === id);
  }
}

export const projectStore = new ProjectStore();
