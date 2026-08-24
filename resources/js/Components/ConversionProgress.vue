<template>
  <div class="progress-card">
    <div class="progress-header">
      <h3>Đang xử lý chuyển đổi bản nhạc...</h3>
      <span class="progress-pct">{{ progress }}%</span>
    </div>

    <!-- Main Progress Bar -->
    <div class="bar-container">
      <div class="bar-fill" :style="{ width: progress + '%' }"></div>
    </div>

    <!-- Step List -->
    <div class="steps-list">
      <div
        v-for="(step, idx) in steps"
        :key="idx"
        class="step-item"
        :class="{
          'step-done': step.status === 'done',
          'step-active': step.status === 'active',
          'step-waiting': step.status === 'waiting'
        }"
      >
        <div class="step-icon">
          <span v-if="step.status === 'done'">✓</span>
          <span v-else-if="step.status === 'active'" class="spinner">⏳</span>
          <span v-else>○</span>
        </div>
        <div class="step-name">{{ step.name }}</div>
        <div class="step-status">{{ step.statusText }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  progress: number;
  currentStep: string;
}>();

const steps = computed(() => [
  {
    name: '1. Chuẩn bị trang & Tiền xử lý (OpenCV Deskew)',
    status: props.progress >= 20 ? (props.progress > 20 ? 'done' : 'active') : 'waiting',
    statusText: props.progress > 20 ? 'Hoàn thành' : (props.progress === 20 ? 'Đang chạy' : 'Chờ')
  },
  {
    name: '2. Nhận dạng khuôn & nốt nhạc (Audiveris OMR)',
    status: props.progress >= 50 ? (props.progress > 50 ? 'done' : 'active') : 'waiting',
    statusText: props.progress > 50 ? 'Hoàn thành' : (props.progress === 50 ? 'Đang chạy' : 'Chờ')
  },
  {
    name: '3. Nhận dạng lời tiếng Việt (Tesseract vie+eng)',
    status: props.progress >= 70 ? (props.progress > 70 ? 'done' : 'active') : 'waiting',
    statusText: props.progress > 70 ? 'Hoàn thành' : (props.progress === 70 ? 'Đang chạy' : 'Chờ')
  },
  {
    name: '4. Khởi tạo cấu trúc MusicXML 3.1/4.0',
    status: props.progress >= 85 ? (props.progress > 85 ? 'done' : 'active') : 'waiting',
    statusText: props.progress > 85 ? 'Hoàn thành' : (props.progress === 85 ? 'Đang chạy' : 'Chờ')
  },
  {
    name: '5. Kiểm định nhạc lý & Nạp vào OSMD Canvas',
    status: props.progress >= 100 ? 'done' : (props.progress >= 85 ? 'active' : 'waiting'),
    statusText: props.progress >= 100 ? 'Sẵn sàng' : 'Chờ'
  }
]);
</script>

<style scoped>
.progress-card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 32px;
  max-width: 600px;
  width: 100%;
  margin: 60px auto;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.progress-header h3 {
  font-size: 1.125rem;
  color: var(--text-primary);
}

.progress-pct {
  font-family: var(--font-mono);
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--accent-primary);
}

.bar-container {
  height: 8px;
  background-color: var(--bg-app);
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: 28px;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--status-success));
  transition: width 0.4s ease;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  background-color: rgba(15, 23, 42, 0.5);
  font-size: 0.875rem;
}

.step-done {
  color: var(--status-success);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.step-active {
  color: var(--accent-primary);
  border: 1px solid rgba(56, 189, 248, 0.4);
  background-color: rgba(56, 189, 248, 0.05);
}

.step-waiting {
  color: var(--text-muted);
}

.step-icon {
  width: 20px;
  font-weight: 700;
  display: flex;
  justify-content: center;
}

.step-name {
  flex: 1;
}

.step-status {
  font-size: 0.75rem;
  font-family: var(--font-mono);
}
</style>
