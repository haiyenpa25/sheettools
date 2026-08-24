<template>
  <header class="bg-surface-container-lowest docked full-width top-0 sticky z-40 border-b border-border-subtle flex justify-between items-center h-16 px-gutter-default shrink-0">
    <!-- Left Section -->
    <div class="flex items-center gap-6 flex-1 min-w-0">
      <span class="font-headline-sm text-lg text-on-surface font-semibold truncate">{{ title }}</span>

      <!-- Search bar (when in library or dashboard) -->
      <div v-if="showSearch" class="relative hidden sm:block flex-1 max-w-md">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-secondary text-lg">search</span>
        <input
          :value="searchQuery"
          @input="$emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
          type="text"
          placeholder="Tìm kiếm bản nhạc, dự án..."
          class="w-full pl-9 pr-4 py-1.5 bg-surface-container-low border border-border-subtle rounded text-sm text-on-surface focus:outline-none focus:border-primary transition-colors"
        />
      </div>
    </div>

    <!-- Right Actions -->
    <div class="flex items-center gap-3">
      <button
        class="p-2 text-on-surface-variant hover:text-primary hover:bg-surface-container-low rounded transition-colors relative"
        title="Thông báo"
      >
        <span class="material-symbols-outlined text-xl">notifications</span>
        <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-error rounded-full"></span>
      </button>

      <button
        class="p-2 text-on-surface-variant hover:text-primary hover:bg-surface-container-low rounded transition-colors"
        title="Trợ giúp & Tài liệu"
      >
        <span class="material-symbols-outlined text-xl">help_outline</span>
      </button>

      <!-- Primary Action Button -->
      <button
        v-if="actionLabel"
        @click="$emit('action')"
        class="bg-primary text-on-primary px-4 py-2 rounded font-label-sm text-sm font-semibold hover:bg-primary-container transition-colors flex items-center gap-1.5 shadow-sm"
      >
        <span class="material-symbols-outlined text-lg" v-if="actionIcon">{{ actionIcon }}</span>
        <span>{{ actionLabel }}</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  showSearch?: boolean;
  searchQuery?: string;
  actionLabel?: string;
  actionIcon?: string;
}>();

defineEmits<{
  (e: 'action'): void;
  (e: 'update:searchQuery', val: string): void;
}>();
</script>
