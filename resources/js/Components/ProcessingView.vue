<template>
  <main class="w-full max-w-xl mx-auto px-gutter-default flex flex-col items-center justify-center flex-1 py-12">
    <div class="bg-surface-container-lowest rounded-xl border border-border-subtle p-margin-main w-full shadow-xs">
      <!-- Header with Pulsing Icon -->
      <div class="text-center mb-8">
        <div 
          class="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 transition-colors"
          :class="errorMessage ? 'bg-error-container text-error' : 'bg-primary-fixed text-primary pulse-animation'"
        >
          <span class="material-symbols-outlined text-3xl">
            {{ errorMessage ? 'error' : 'memory' }}
          </span>
        </div>
        <h1 class="font-headline-md text-xl font-bold text-on-surface mb-2 truncate">
          {{ errorMessage ? 'Lỗi xử lý tệp' : `Đang nhận diện: ${fileName}` }}
        </h1>
        <p class="font-body-md text-sm" :class="errorMessage ? 'text-error font-medium' : 'text-on-surface-variant'">
          {{ errorMessage || 'Audiveris OMR & Tesseract OCR đang phân tích từng trang nốt nhạc...' }}
        </p>
      </div>

      <!-- Error State Card if failed -->
      <div v-if="errorMessage" class="bg-error/10 border border-error/30 rounded-lg p-4 mb-6 space-y-3">
        <p class="text-xs text-error leading-relaxed">
          {{ errorMessage }}
        </p>
        <div class="flex gap-2 justify-end">
          <button
            @click="$emit('cancel')"
            class="px-3 py-1.5 bg-surface-container text-on-surface text-xs font-semibold rounded hover:bg-surface-container-high transition-colors"
          >
            Quay lại Dashboard
          </button>
        </div>
      </div>

      <!-- Pipeline Steps -->
      <div v-else class="space-y-4">
        <!-- Step 1: Preparing pages -->
        <div class="flex items-start gap-4">
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="currentStep >= 1 ? 'bg-success text-on-primary' : 'border border-outline-variant bg-surface-container-low text-outline-variant'"
          >
            <span v-if="currentStep >= 1" class="material-symbols-outlined text-sm font-bold">check</span>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <p class="font-body-md text-sm font-medium" :class="currentStep >= 1 ? 'text-on-surface' : 'text-on-surface-variant'">
              Chuẩn bị trang & Tiền xử lý ảnh (Deskew & CLAHE)
            </p>
            <p class="font-label-sm text-xs font-semibold" :class="currentStep >= 1 ? 'text-success' : 'text-outline'">
              {{ currentStep >= 1 ? 'Hoàn tất' : 'Chờ' }}
            </p>
          </div>
        </div>

        <!-- Step 2: Recognizing score -->
        <div class="flex items-start gap-4 relative">
          <div class="absolute left-[11px] top-[-16px] bottom-[28px] w-0.5 bg-border-subtle -z-10"></div>
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="[
              currentStep > 2 ? 'bg-success text-on-primary' : '',
              currentStep === 2 ? 'border-2 border-primary bg-surface-container-lowest' : '',
              currentStep < 2 ? 'border border-outline-variant bg-surface-container-low text-outline-variant' : ''
            ]"
          >
            <span v-if="currentStep > 2" class="material-symbols-outlined text-sm font-bold">check</span>
            <div v-else-if="currentStep === 2" class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <div class="flex justify-between items-center mb-1">
              <p class="font-body-md text-sm font-medium" :class="currentStep >= 2 ? 'text-primary' : 'text-on-surface-variant'">
                Nhận diện cấu trúc khuông & nốt nhạc (OMR Engine)
              </p>
              <span v-if="currentStep === 2" class="font-mono-label text-xs text-primary font-semibold">{{ currentProgress }}%</span>
              <span v-else-if="currentStep > 2" class="font-label-sm text-xs text-success font-semibold">Hoàn tất</span>
            </div>
            <div v-if="currentStep === 2" class="h-2 w-full bg-surface-container-high rounded-full overflow-hidden mb-1">
              <div
                class="h-full bg-primary rounded-full progress-bar-stripes transition-all duration-300"
                :style="{ width: currentProgress + '%' }"
              ></div>
            </div>
            <p class="font-label-sm text-xs text-on-surface-variant">
              {{ currentStep === 2 ? 'Đang phân tích cao độ pixel và trường độ nốt...' : (currentStep > 2 ? 'Khuông nhạc đã nhận dạng' : 'Chờ') }}
            </p>
          </div>
        </div>

        <!-- Step 3: Recognizing lyrics -->
        <div class="flex items-start gap-4 relative">
          <div class="absolute left-[11px] top-[-16px] bottom-[28px] w-0.5 bg-border-subtle -z-10"></div>
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="[
              currentStep > 3 ? 'bg-success text-on-primary' : '',
              currentStep === 3 ? 'border-2 border-primary bg-surface-container-lowest' : '',
              currentStep < 3 ? 'border border-outline-variant bg-surface-container-low text-outline-variant' : ''
            ]"
          >
            <span v-if="currentStep > 3" class="material-symbols-outlined text-sm font-bold">check</span>
            <div v-else-if="currentStep === 3" class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <p class="font-body-md text-sm font-medium" :class="currentStep === 3 ? 'text-primary' : (currentStep > 3 ? 'text-on-surface' : 'text-on-surface-variant')">
              Nhận diện Lời tiếng Việt & Hợp âm (OCR vie+eng)
            </p>
            <p class="font-label-sm text-xs" :class="currentStep > 3 ? 'text-success font-semibold' : (currentStep === 3 ? 'text-primary font-semibold' : 'text-outline')">
              {{ currentStep > 3 ? 'Hoàn tất' : (currentStep === 3 ? 'Đang bóc tách âm tiết tiếng Việt...' : 'Chờ') }}
            </p>
          </div>
        </div>

        <!-- Step 4: Creating MusicXML -->
        <div class="flex items-start gap-4 relative">
          <div class="absolute left-[11px] top-[-16px] bottom-[28px] w-0.5 bg-border-subtle -z-10"></div>
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="[
              currentStep > 4 ? 'bg-success text-on-primary' : '',
              currentStep === 4 ? 'border-2 border-primary bg-surface-container-lowest' : '',
              currentStep < 4 ? 'border border-outline-variant bg-surface-container-low text-outline-variant' : ''
            ]"
          >
            <span v-if="currentStep > 4" class="material-symbols-outlined text-sm font-bold">check</span>
            <div v-else-if="currentStep === 4" class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <p class="font-body-md text-sm font-medium" :class="currentStep === 4 ? 'text-primary' : (currentStep > 4 ? 'text-on-surface' : 'text-on-surface-variant')">
              Hợp nhất MusicXML & Cân bằng phách (music21 Auto-Healer)
            </p>
            <p class="font-label-sm text-xs" :class="currentStep > 4 ? 'text-success font-semibold' : (currentStep === 4 ? 'text-primary font-semibold' : 'text-outline')">
              {{ currentStep > 4 ? 'Hoàn tất' : (currentStep === 4 ? 'Đang cân bằng nhịp và quantize...' : 'Chờ') }}
            </p>
          </div>
        </div>

        <!-- Step 5: Validating -->
        <div class="flex items-start gap-4 relative">
          <div class="absolute left-[11px] top-[-16px] bottom-[28px] w-0.5 bg-border-subtle -z-10"></div>
          <div
            class="mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-colors"
            :class="[
              currentStep >= 5 ? 'bg-success text-on-primary' : 'border border-outline-variant bg-surface-container-low text-outline-variant'
            ]"
          >
            <span v-if="currentStep >= 5" class="material-symbols-outlined text-sm font-bold">check</span>
            <span v-else class="material-symbols-outlined text-xs">hourglass_empty</span>
          </div>
          <div class="flex-1">
            <p class="font-body-md text-sm font-medium" :class="currentStep >= 5 ? 'text-on-surface' : 'text-on-surface-variant'">
              Kiểm định cú pháp & Chuẩn bị giao diện
            </p>
            <p class="font-label-sm text-xs" :class="currentStep >= 5 ? 'text-success font-semibold' : 'text-outline'">
              {{ currentStep >= 5 ? 'Sẵn sàng mở Editor' : 'Chờ' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Cancel Action -->
      <div v-if="!errorMessage" class="mt-8 pt-6 border-t border-border-subtle text-center">
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
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  fileName: string;
  step?: number;
  progress?: number;
  errorMessage?: string | null;
}>(), {
  step: 2,
  progress: 40,
  errorMessage: null,
});

defineEmits<{
  (e: 'completed'): void;
  (e: 'cancel'): void;
}>();

const currentStep = computed(() => props.step);
const currentProgress = computed(() => props.progress);
</script>
