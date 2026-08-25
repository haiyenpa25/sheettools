import { reactive, ref } from 'vue';
import { OmrTranscriptionService } from './OmrTranscriptionService';

export interface ProjectItem {
  id: string;
  uuid?: string;
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

const STORAGE_KEY = 'sheet_converter_projects_v12';

// Danh sách các bản nhạc chuẩn mẫu (Chỉ nạp lần đầu tiên khi chưa có dữ liệu)
const initialProjects: ProjectItem[] = [
  {
    id: 'p_001',
    title: 'TỪ CÕI LÒNG SÂU THẲM',
    composer: 'Nguyễn Đình Tiến',
    date: '25/08/2026',
    status: 'READY',
    verses: 1,
    keySig: 'E minor / G Major',
    timeSig: '2/4',
    sourceFilename: '1.pdf',
    sourceImageUrl: '/golden.png',
    sourcePdfUrl: '/samples/002_tu_coi_long/source.pdf',
    xmlContent: OmrTranscriptionService.generateTuCoiLongSauTham(),
  },
  {
    id: 'p_002',
    title: 'TRỌN CẢ TẤM LÒNG',
    composer: 'Tôn Vinh Chúa Hằng Hữu',
    date: '25/08/2026',
    status: 'READY',
    verses: 2,
    keySig: 'G Major',
    timeSig: '4/4',
    sourceFilename: '2.pdf',
    sourcePdfUrl: '/samples/003_tron_ca_tam_long/source.pdf',
    xmlContent: OmrTranscriptionService.generateTronCaTamLong(),
  },
  {
    id: 'p_003',
    title: '001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI',
    composer: 'Felice de Giardini, 1769',
    date: '12/10/2023',
    status: 'READY',
    verses: 4,
    keySig: 'G Major',
    timeSig: '3/4',
    sourceFilename: '001 Hỡi Thánh Vương, Kíp Ngự Lai.pdf',
    sourcePdfUrl: '/samples/001_hoi_thanh_vuong/score.xml',
    xmlContent: OmrTranscriptionService.generateTonVinhChanThan(),
  },
];

class ProjectStore {
  public projects = reactive<ProjectItem[]>([]);
  public activeProjectId = ref<string>('p_001');

  constructor() {
    this.loadFromStorage();
    this.syncWithBackend();
  }

  private loadFromStorage(): void {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw !== null) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          // Nạp đúng danh sách người dùng đã lưu (kể cả khi đã xoá rỗng)
          this.projects.splice(0, this.projects.length, ...parsed);
          return;
        }
      }
    } catch (e) {
      console.warn('Failed to load projects from storage, using defaults:', e);
    }
    // Chỉ nạp initialProjects vào lần đầu tiên mở ứng dụng
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

  /**
   * Đồng bộ trạng thái từ Backend API
   */
  public async syncWithBackend(): Promise<void> {
    try {
      const res = await fetch('/api/conversions').then(r => r.json()).catch(() => null);
      if (res && Array.isArray(res.data) && res.data.length > 0) {
        for (const item of res.data) {
          if (!item.uuid) continue;
          const existing = this.projects.find(p => p.id === item.uuid || p.uuid === item.uuid);
          if (existing) {
            existing.status = item.status === 'NEEDS_REVIEW' ? 'NEEDS_REVIEW' : (item.status === 'READY' ? 'READY' : 'PROCESSING');
          }
        }
        this.saveToStorage();
      }
    } catch (e) {
      console.log('Backend sync notice:', e);
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
    xmlContent?: string,
    uuid?: string
  ): ProjectItem {
    const today = new Date();
    const dateStr = `${String(today.getDate()).padStart(2, '0')}/${String(today.getMonth() + 1).padStart(2, '0')}/${today.getFullYear()}`;

    const newProj: ProjectItem = {
      id: uuid || ('proj_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7)),
      uuid: uuid,
      title: title.trim() || 'Bản nhạc mới',
      composer: 'Tác giả bài hát',
      date: dateStr,
      status: 'READY',
      verses: 2,
      keySig: 'G Major',
      timeSig: '4/4',
      sourceFilename: filename,
      sourceImageUrl,
      sourcePdfUrl,
      xmlContent,
    };

    this.projects.unshift(newProj);
    this.activeProjectId.value = newProj.id;
    this.saveToStorage();

    // Tự động tạo thư mục dự án và tệp MusicXML thật trên ổ đĩa backend
    if (!uuid && xmlContent && xmlContent.length > 50) {
      fetch('/api/conversions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newProj.title,
          filename: newProj.sourceFilename,
          xmlContent: newProj.xmlContent,
        }),
      })
        .then(r => r.json())
        .then(res => {
          if (res?.data?.uuid) {
            newProj.uuid = res.data.uuid;
            this.saveToStorage();
          }
        })
        .catch(err => console.warn('Could not persist new project to backend:', err));
    }

    return newProj;
  }

  public async deleteProject(id: string): Promise<boolean> {
    const idx = this.projects.findIndex(p => p.id === id);
    if (idx !== -1) {
      const proj = this.projects[idx];
      const uuid = proj.uuid || (id.length > 20 ? id : undefined);
      
      // 1. Xóa ngay lập tức khỏi mảng reactive và lưu localStorage
      this.projects.splice(idx, 1);
      if (this.activeProjectId.value === id) {
        this.activeProjectId.value = this.projects.length > 0 ? this.projects[0].id : '';
      }
      this.saveToStorage();

      // 2. Gọi API xóa vĩnh viễn trên ổ đĩa backend
      if (uuid) {
        try {
          await fetch(`/api/conversions/${uuid}`, { method: 'DELETE' });
        } catch (err) {
          console.warn('Could not delete project from backend:', err);
        }
      }
      return true;
    }
    return false;
  }

  public async updateProject(id: string, updates: Partial<ProjectItem>): Promise<void> {
    const proj = this.projects.find(p => p.id === id);
    if (proj) {
      Object.assign(proj, updates);
      this.saveToStorage();

      const uuid = proj.uuid || (id.length > 20 ? id : undefined);
      if (uuid) {
        // Đồng bộ siêu dữ liệu (Metadata: Title, Status)
        if (updates.title || updates.composer || updates.status) {
          fetch(`/api/conversions/${uuid}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title: updates.title || proj.title,
              status: updates.status || proj.status,
            }),
          }).catch(err => console.warn('Could not sync metadata to backend:', err));
        }

        // Đồng bộ MusicXML vào current.musicxml trên ổ đĩa backend
        if (updates.xmlContent) {
          fetch(`/api/conversions/${uuid}/musicxml`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/xml' },
            body: updates.xmlContent,
          }).catch(err => console.warn('Could not sync MusicXML to backend:', err));
        }
      }
    }
  }

  public getProject(id: string): ProjectItem | undefined {
    return this.projects.find(p => p.id === id);
  }
}

export const projectStore = new ProjectStore();
