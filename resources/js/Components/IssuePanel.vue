<template>
  <div class="issue-panel">
    <div class="panel-header-sub">
      <h4>Danh sách Kiểm tra & Cảnh báo Nhận dạng</h4>
      <span class="badge badge-info">{{ issues.length }} mục cần soát</span>
    </div>

    <div class="issue-list">
      <div v-if="issues.length === 0" class="empty-issue">
        <span class="check-icon">✓</span>
        <span>Không có lỗi cú pháp hoặc xung đột nhịp nào được phát hiện!</span>
      </div>

      <div
        v-for="issue in issues"
        :key="issue.id"
        class="issue-card"
        :class="'severity-' + issue.severity"
        @click="$emit('issue-clicked', issue)"
      >
        <div class="issue-badge">{{ issue.severity.toUpperCase() }}</div>
        <div class="issue-content">
          <div class="issue-msg">{{ issue.message }}</div>
          <div class="issue-meta">Part: {{ issue.partId }} | Measure: M.{{ issue.measureNumber }} | Loại: {{ issue.entityType }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface IssueItem {
  id: string;
  partId: string;
  measureNumber: number;
  entityType: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
}

defineProps<{
  issues: IssueItem[];
}>();

defineEmits<{
  (e: 'issue-clicked', issue: IssueItem): void;
}>();
</script>

<style scoped>
.issue-panel {
  padding: 16px;
  background-color: var(--bg-surface);
  height: 100%;
  overflow-y: auto;
}

.panel-header-sub {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-header-sub h4 {
  font-size: 0.9375rem;
  color: var(--text-primary);
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-issue {
  padding: 24px;
  text-align: center;
  color: var(--status-success);
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.check-icon {
  font-size: 1.25rem;
  font-weight: 700;
}

.issue-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background-color: var(--bg-app);
  border-radius: 6px;
  border-left: 4px solid var(--status-warning);
  cursor: pointer;
  transition: all 0.2s ease;
}

.issue-card:hover {
  background-color: var(--bg-surface-hover);
}

.issue-card.severity-error {
  border-left-color: var(--status-danger);
}

.issue-badge {
  font-size: 0.625rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  background-color: var(--border-default);
  color: var(--text-secondary);
}

.issue-msg {
  font-size: 0.8125rem;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.issue-meta {
  font-size: 0.6875rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}
</style>
