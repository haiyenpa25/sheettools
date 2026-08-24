<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <div class="export-card">
      <div class="export-header">
        <h3>Xuất Bản & Tải Về MusicXML</h3>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <!-- Compatibility Checklist -->
      <div class="compat-box">
        <div class="compat-title">✓ Trạng thái Tương thích Hệ sinh thái:</div>
        <ul class="compat-list">
          <li><span>✓</span> Chuẩn MusicXML 3.1 & 4.0 Partwise</li>
          <li><span>✓</span> Tương thích 100% với OpenSheetMusicDisplay (OSMD)</li>
          <li><span>✓</span> Tương thích với SheetApp & MuseScore / Finale / Sibelius</li>
          <li><span>✓</span> Bảo toàn 4 Verse lời Tiếng Việt & Hợp âm</li>
        </ul>
      </div>

      <!-- Download Options -->
      <div class="download-options">
        <div class="option-card" @click="downloadFile('musicxml')">
          <div class="opt-icon">🎼</div>
          <div class="opt-info">
            <div class="opt-title">MusicXML 4.0 (.musicxml)</div>
            <div class="opt-sub">Định dạng khuyên dùng cho các ứng dụng hiện đại</div>
          </div>
          <button class="btn btn-primary btn-sm">Tải về</button>
        </div>

        <div class="option-card" @click="downloadFile('xml')">
          <div class="opt-icon">📄</div>
          <div class="opt-info">
            <div class="opt-title">Standard XML (.xml)</div>
            <div class="opt-sub">Tương thích với Finale, Sibelius và các DAW cũ</div>
          </div>
          <button class="btn btn-secondary btn-sm">Tải về</button>
        </div>

        <div class="option-card" @click="downloadFile('mxl')">
          <div class="opt-icon">📦</div>
          <div class="opt-info">
            <div class="opt-title">Compressed MusicXML (.mxl)</div>
            <div class="opt-sub">Đóng gói ZIP nén chuẩn kèm metadata container</div>
          </div>
          <button class="btn btn-secondary btn-sm">Tải về</button>
        </div>
      </div>

      <div class="export-footer">
        <button class="btn btn-secondary" @click="$emit('close')">Đóng</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  projectUuid: string;
}>();

defineEmits<{
  (e: 'close'): void;
}>();

function downloadFile(format: string) {
  const url = `/api/conversions/${props.projectUuid}/export?format=${format}`;
  window.open(url, '_blank');
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.export-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 24px;
  max-width: 550px;
  width: 90%;
}

.export-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.export-header h3 {
  color: var(--text-primary);
  font-size: 1.125rem;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 20px;
  cursor: pointer;
}

.compat-box {
  background-color: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 20px;
}

.compat-title {
  color: var(--status-success);
  font-weight: 600;
  font-size: 0.8125rem;
  margin-bottom: 6px;
}

.compat-list {
  list-style: none;
  font-size: 0.75rem;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.compat-list span {
  color: var(--status-success);
  font-weight: 700;
  margin-right: 4px;
}

.download-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.option-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--bg-app);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.option-card:hover {
  border-color: var(--accent-primary);
  background-color: var(--bg-surface-hover);
}

.opt-icon {
  font-size: 24px;
}

.opt-info {
  flex: 1;
}

.opt-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.opt-sub {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.export-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
