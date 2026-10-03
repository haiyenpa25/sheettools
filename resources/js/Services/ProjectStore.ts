import { reactive, ref } from 'vue';

export interface SongbookCategory {
  slug: string;
  name: string;
  icon: string;
  description: string;
}

export interface ProjectItem {
  id: string;
  uuid?: string;
  title: string;
  composer?: string;
  date: string;
  status: 'READY' | 'NEEDS_REVIEW' | 'PROCESSING' | 'FAILED';
  verses: number;
  keySig?: string;
  timeSig?: string;
  sourceFilename?: string;
  sourceImageUrl?: string;
  sourcePdfUrl?: string;
  xmlContent?: string;
  categorySlug?: string;
  categoryName?: string;
  songNumber?: string;
}

export const defaultCategories: SongbookCategory[] = [
  { slug: 'all', name: 'Tất Cả Tuyển Tập', icon: 'auto_stories', description: 'Toàn bộ bài hát trong thư viện' },
  { slug: 'thanh-ca-ton-vinh', name: 'Thánh Ca Tôn Vinh', icon: 'menu_book', description: 'Tuyển tập thánh ca thờ phượng' },
  { slug: 'nhac-tru-tinh-dan-ca', name: 'Nhạc Trữ Tình & Dân Ca', icon: 'music_note', description: 'Tuyển tập bài hát quê hương & trữ tình' },
  { slug: 'guitar-dem-hat', name: 'Tuyển Tập Đệm Hát', icon: 'queue_music', description: 'Bài hát kèm hợp âm guitar & acoustic' },
  { slug: 'tuyen-tap-ca-nhan', name: 'Tuyển Tập Của Tôi', icon: 'folder', description: 'Các bài hát riêng của bạn' },
];

const STORAGE_KEY = 'sheet_converter_projects_v17';

class ProjectStore {
  public projects = reactive<ProjectItem[]>([]);
  public activeProjectId = ref<string>('p_002');
  public activeCategorySlug = ref<string>('all');
  public categories = reactive<SongbookCategory[]>([...defaultCategories]);
  public deletedProjects = reactive<ProjectItem[]>([]);

  constructor() {
    this.loadFromStorage();
    this.syncWithBackend();
  }

  private loadFromStorage(): void {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw !== null) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          this.projects.splice(0, this.projects.length, ...parsed);
          return;
        }
      }
    } catch (e) {
      console.warn('Failed to load projects from storage, using defaults:', e);
    }
    // The backend library is the sole source of truth. Demo scores must only
    // be imported through an explicit user action, never resurrected here.
    this.projects.splice(0, this.projects.length);
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
      if (res && Array.isArray(res.data)) {
        const backendUuids = new Set(res.data.map((item: any) => item.uuid).filter(Boolean));
        for (let index = this.projects.length - 1; index >= 0; index -= 1) {
          const project = this.projects[index];
          if (project.uuid && !backendUuids.has(project.uuid)) {
            this.projects.splice(index, 1);
          }
        }
        for (const item of res.data) {
          if (!item.uuid) continue;
          const existing = this.projects.find(p => p.id === item.uuid || p.uuid === item.uuid);
          if (existing) {
            existing.status = this.normalizeStatus(item.status);
            existing.title = item.title || existing.title;
            existing.composer = item.composer || '';
            existing.categorySlug = item.category_slug || '';
            existing.categoryName = item.category_name || '';
            existing.songNumber = item.song_number || '';
          } else {
            this.projects.unshift({
              id: item.uuid,
              uuid: item.uuid,
              title: item.title || String(item.source_filename || 'Dự án OMR').replace(/\.[^/.]+$/, ''),
              date: this.formatBackendDate(item.created_at),
              status: this.normalizeStatus(item.status),
              verses: 0,
              sourceFilename: item.source_filename,
              composer: item.composer || '',
              categorySlug: item.category_slug || '',
              categoryName: item.category_name || '',
              songNumber: item.song_number || '',
            });
          }
        }
        this.saveToStorage();
      }
    } catch (e) {
      console.log('Backend sync notice:', e);
    }
  }

  private normalizeStatus(status: string): ProjectItem['status'] {
    if (status === 'READY' || status === 'NEEDS_REVIEW' || status === 'FAILED') return status;
    return 'PROCESSING';
  }

  private formatBackendDate(value?: string): string {
    if (!value) return new Date().toLocaleDateString('vi-VN');
    const parsed = new Date(value.replace(' ', 'T'));
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString('vi-VN');
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
      composer: '',
      date: dateStr,
      status: 'READY',
      verses: 0,
      keySig: undefined,
      timeSig: undefined,
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
      
      if (uuid) {
        const response = await fetch(`/api/conversions/${uuid}`, { method: 'DELETE' });
        const result = await response.json().catch(() => null);
        if (!response.ok || !result?.success) throw new Error(result?.message || 'Không thể xóa dự án');
      }
      this.projects.splice(idx, 1);
      if (this.activeProjectId.value === id) this.activeProjectId.value = this.projects[0]?.id || '';
      this.saveToStorage();
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
        if (updates.title !== undefined || updates.composer !== undefined || updates.status !== undefined ||
            updates.categorySlug !== undefined || updates.categoryName !== undefined || updates.songNumber !== undefined) {
          try {
            await fetch(`/api/conversions/${uuid}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: proj.title,
                composer: proj.composer,
                status: proj.status,
                category_slug: proj.categorySlug || '',
                category_name: proj.categoryName || '',
                song_number: proj.songNumber || '',
              }),
            });
          } catch (err) {
            console.warn('Could not sync metadata update to backend:', err);
          }
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

  public async updateProjectCategory(id: string, categorySlug: string, songNumber?: string): Promise<void> {
    const proj = this.projects.find(p => p.id === id);
    if (proj) {
      const cat = this.categories.find(c => c.slug === categorySlug);
      proj.categorySlug = categorySlug;
      proj.categoryName = cat?.name || categorySlug;
      if (songNumber) proj.songNumber = songNumber;
      this.saveToStorage();
      await this.updateProject(id, {
        categorySlug: proj.categorySlug,
        categoryName: proj.categoryName,
        songNumber: proj.songNumber,
      });
    }
  }

  public getProjectsByCategory(categorySlug: string): ProjectItem[] {
    if (categorySlug === 'all') return this.projects;
    return this.projects.filter(p => p.categorySlug === categorySlug);
  }

  public async loadTrash(): Promise<void> {
    const response = await fetch('/api/trash');
    const result = await response.json().catch(() => null);
    if (!response.ok || !Array.isArray(result?.data)) throw new Error('Không thể tải thùng rác');
    this.deletedProjects.splice(0, this.deletedProjects.length, ...result.data.map((item: any) => ({
      id: item.uuid,
      uuid: item.uuid,
      title: item.title || 'Bản nhạc chưa đặt tên',
      composer: item.composer || '',
      date: this.formatBackendDate(item.updated_at),
      status: this.normalizeStatus(item.status),
      verses: 0,
      categorySlug: item.category_slug || '',
      categoryName: item.category_name || '',
      songNumber: item.song_number || '',
    })));
  }

  public async restoreProject(uuid: string): Promise<void> {
    const response = await fetch(`/api/trash/${uuid}/restore`, { method: 'POST' });
    if (!response.ok) throw new Error('Không thể khôi phục bản nhạc');
    await Promise.all([this.syncWithBackend(), this.loadTrash()]);
  }

  public async purgeProject(uuid: string): Promise<void> {
    const response = await fetch(`/api/trash/${uuid}/purge`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Không thể xóa vĩnh viễn bản nhạc');
    await this.loadTrash();
  }
}

export const projectStore = new ProjectStore();
