<template>
  <main class="w-full max-w-xl mx-auto px-gutter-default flex flex-col items-center justify-center flex-1 py-12">
    <div class="bg-surface-container-lowest rounded-xl border border-border-subtle p-margin-main w-full shadow-xs">
      <!-- Header with Pulsing Icon -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-fixed mb-4 pulse-animation">
          <span class="material-symbols-outlined text-primary text-3xl">memory</span>
        </div>
        <h1 class="font-headline-md text-xl font-bold text-on-surface mb-2 truncate">
          Đang xử lý: {{ fileName }}
        </h1>
        <p class="font-body-md text-sm text-on-surface-variant">
          Audiveris OMR đang làm việc, vui lòng không đóng trình duyệt.
        </p>
      </div>

      <!-- Pipeline Steps -->
      <div class="space-y-4">
        <!-- Step 1: Preparing pages -->
        <div class="flex items-start gap-4">
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="step >= 1 ? 'bg-success text-on-primary' : 'border border-outline-variant bg-surface-container-low text-outline-variant'"
          >
            <span v-if="step >= 1" class="material-symbols-outlined text-sm font-bold">check</span>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <p class="font-body-md text-sm font-medium" :class="step >= 1 ? 'text-on-surface' : 'text-on-surface-variant'">
              Preparing pages
            </p>
            <p class="font-label-sm text-xs font-semibold" :class="step >= 1 ? 'text-success' : 'text-outline'">
              {{ step >= 1 ? 'Hoàn tất' : 'Chờ' }}
            </p>
          </div>
        </div>

        <!-- Step 2: Recognizing score -->
        <div class="flex items-start gap-4 relative">
          <div class="absolute left-[11px] top-[-16px] bottom-[28px] w-0.5 bg-border-subtle -z-10"></div>
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="[
              step > 2 ? 'bg-success text-on-primary' : '',
              step === 2 ? 'border-2 border-primary bg-surface-container-lowest' : '',
              step < 2 ? 'border border-outline-variant bg-surface-container-low text-outline-variant' : ''
            ]"
          >
            <span v-if="step > 2" class="material-symbols-outlined text-sm font-bold">check</span>
            <div v-else-if="step === 2" class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <div class="flex justify-between items-center mb-1">
              <p class="font-body-md text-sm font-medium" :class="step >= 2 ? 'text-primary' : 'text-on-surface-variant'">
                Recognizing score
              </p>
              <span v-if="step === 2" class="font-mono-label text-xs text-primary font-semibold">{{ scoreProgress }}%</span>
              <span v-else-if="step > 2" class="font-label-sm text-xs text-success font-semibold">Hoàn tất</span>
            </div>
            <div v-if="step === 2" class="h-2 w-full bg-surface-container-high rounded-full overflow-hidden mb-1">
              <div
                class="h-full bg-primary rounded-full progress-bar-stripes transition-all duration-300"
                :style="{ width: scoreProgress + '%' }"
              ></div>
            </div>
            <p class="font-label-sm text-xs text-on-surface-variant">
              {{ step === 2 ? 'Đang phân tích cấu trúc khuông nhạc...' : (step > 2 ? 'Khuôn nhạc đã nhận dạng' : 'Chờ') }}
            </p>
          </div>
        </div>

        <!-- Step 3: Recognizing lyrics -->
        <div class="flex items-start gap-4 relative">
          <div class="absolute left-[11px] top-[-16px] bottom-[28px] w-0.5 bg-border-subtle -z-10"></div>
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="[
              step > 3 ? 'bg-success text-on-primary' : '',
              step === 3 ? 'border-2 border-primary bg-surface-container-lowest' : '',
              step < 3 ? 'border border-outline-variant bg-surface-container-low text-outline-variant' : ''
            ]"
          >
            <span v-if="step > 3" class="material-symbols-outlined text-sm font-bold">check</span>
            <div v-else-if="step === 3" class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <p class="font-body-md text-sm font-medium" :class="step === 3 ? 'text-primary' : (step > 3 ? 'text-on-surface' : 'text-on-surface-variant')">
              Recognizing lyrics (OCR vie+eng)
            </p>
            <p class="font-label-sm text-xs" :class="step > 3 ? 'text-success font-semibold' : (step === 3 ? 'text-primary font-semibold' : 'text-outline')">
              {{ step > 3 ? 'Hoàn tất' : (step === 3 ? 'Đang bóc tách lời bài hát...' : 'Chờ') }}
            </p>
          </div>
        </div>

        <!-- Step 4: Creating MusicXML -->
        <div class="flex items-start gap-4 relative">
          <div class="absolute left-[11px] top-[-16px] bottom-[28px] w-0.5 bg-border-subtle -z-10"></div>
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="[
              step > 4 ? 'bg-success text-on-primary' : '',
              step === 4 ? 'border-2 border-primary bg-surface-container-lowest' : '',
              step < 4 ? 'border border-outline-variant bg-surface-container-low text-outline-variant' : ''
            ]"
          >
            <span v-if="step > 4" class="material-symbols-outlined text-sm font-bold">check</span>
            <div v-else-if="step === 4" class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <p class="font-body-md text-sm font-medium" :class="step === 4 ? 'text-primary' : (step > 4 ? 'text-on-surface' : 'text-on-surface-variant')">
              Creating MusicXML
            </p>
            <p class="font-label-sm text-xs" :class="step > 4 ? 'text-success font-semibold' : (step === 4 ? 'text-primary font-semibold' : 'text-outline')">
              {{ step > 4 ? 'Hoàn tất' : (step === 4 ? 'Đang hợp nhất DOM MusicXML...' : 'Chờ') }}
            </p>
          </div>
        </div>

        <!-- Step 5: Validating -->
        <div class="flex items-start gap-4 relative">
          <div class="absolute left-[11px] top-[-16px] bottom-[28px] w-0.5 bg-border-subtle -z-10"></div>
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="[
              step >= 5 ? 'bg-success text-on-primary' : 'border border-outline-variant bg-surface-container-low text-outline-variant'
            ]"
          >
            <span v-if="step >= 5" class="material-symbols-outlined text-sm font-bold">check</span>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <p class="font-body-md text-sm font-medium" :class="step >= 5 ? 'text-on-surface' : 'text-on-surface-variant'">
              Validating & Finalizing
            </p>
            <p class="font-label-sm text-xs" :class="step >= 5 ? 'text-success font-semibold' : 'text-outline'">
              {{ step >= 5 ? 'Sẵn sàng mở Editor' : 'Chờ' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Cancel Action -->
      <div class="mt-8 pt-6 border-t border-border-subtle text-center">
        <button
          @click="$emit('cancel')"
          class="font-label-sm text-sm text-secondary hover:text-error hover:bg-error-container/20 transition-colors px-4 py-2 rounded-md"
        >
          Hủy quá trình
        </button>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const props = defineProps<{
  fileName: string;
}>();

const emit = defineEmits<{
  (e: 'completed'): void;
  (e: 'cancel'): void;
}>();

const step = ref(1);
const scoreProgress = ref(20);

onMounted(() => {
  // Simulate dynamic pipeline progress
  setTimeout(() => {
    step.value = 2;
    const interval = setInterval(() => {
      if (scoreProgress.value < 90) {
        scoreProgress.value += Math.floor(Math.random() * 15) + 5;
        if (scoreProgress.value > 90) scoreProgress.value = 90;
      } else {
        clearInterval(interval);
        step.value = 3;
        setTimeout(() => {
          step.value = 4;
          setTimeout(() => {
            step.value = 5;
            setTimeout(() => {
              emit('completed');
            }, 600);
          }, 700);
        }, 700);
      }
    }, 300);
  }, 500);
});
</script>
