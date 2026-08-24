<template>
  <nav class="h-screen w-64 fixed left-0 top-0 bg-surface-container-lowest border-r border-border-subtle flex flex-col py-margin-main z-50 select-none">
    <!-- Brand Logo -->
    <div class="px-gutter-default mb-8 flex items-center gap-3 cursor-pointer" @click="$emit('navigate', 'dashboard')">
      <div class="w-10 h-10 bg-primary text-on-primary rounded flex items-center justify-center font-bold text-xl shadow-sm">
        S
      </div>
      <div>
        <h1 class="font-display-lg text-lg font-bold text-primary leading-tight">Sheet Converter</h1>
        <p class="font-label-sm text-xs text-secondary mt-0.5">OMR Professional</p>
      </div>
    </div>

    <!-- Navigation Menu -->
    <ul class="flex flex-col gap-1 px-panel-padding">
      <li>
        <button
          @click="$emit('navigate', 'dashboard')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded font-body-md text-sm transition-all text-left"
          :class="currentView === 'dashboard'
            ? 'text-primary font-bold border-r-4 border-primary bg-sync-active-highlight scale-[0.98]'
            : 'text-secondary hover:text-primary hover:bg-surface-container-low'"
        >
          <span
            class="material-symbols-outlined text-xl"
            :class="{ 'filled': currentView === 'dashboard' }"
          >dashboard</span>
          <span>Dashboard</span>
        </button>
      </li>

      <li>
        <button
          @click="$emit('navigate', 'library')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded font-body-md text-sm transition-all text-left"
          :class="currentView === 'library'
            ? 'text-primary font-bold border-r-4 border-primary bg-sync-active-highlight scale-[0.98]'
            : 'text-secondary hover:text-primary hover:bg-surface-container-low'"
        >
          <span
            class="material-symbols-outlined text-xl"
            :class="{ 'filled': currentView === 'library' }"
          >library_music</span>
          <span>Project Library</span>
        </button>
      </li>

      <li v-if="hasActiveProject">
        <button
          @click="$emit('navigate', 'editor')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded font-body-md text-sm transition-all text-left"
          :class="currentView === 'editor'
            ? 'text-primary font-bold border-r-4 border-primary bg-sync-active-highlight scale-[0.98]'
            : 'text-secondary hover:text-primary hover:bg-surface-container-low'"
        >
          <span
            class="material-symbols-outlined text-xl"
            :class="{ 'filled': currentView === 'editor' }"
          >edit_note</span>
          <span>Score Editor</span>
          <span class="ml-auto w-2 h-2 rounded-full bg-success"></span>
        </button>
      </li>

      <li>
        <button
          @click="$emit('navigate', 'settings')"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded font-body-md text-sm transition-all text-left"
          :class="currentView === 'settings'
            ? 'text-primary font-bold border-r-4 border-primary bg-sync-active-highlight scale-[0.98]'
            : 'text-secondary hover:text-primary hover:bg-surface-container-low'"
        >
          <span
            class="material-symbols-outlined text-xl"
            :class="{ 'filled': currentView === 'settings' }"
          >settings</span>
          <span>Settings</span>
        </button>
      </li>
    </ul>

    <!-- Footer Profile -->
    <div class="mt-auto px-gutter-default pt-4 border-t border-border-subtle flex items-center gap-3">
      <div class="w-10 h-10 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-semibold border border-border-subtle">
        AU
      </div>
      <div class="min-w-0">
        <p class="font-label-sm text-sm text-on-surface font-semibold truncate">Admin User</p>
        <p class="font-mono-label text-xs text-secondary">Pro Plan • v2.4.1</p>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
defineProps<{
  currentView: string;
  hasActiveProject: boolean;
}>();

defineEmits<{
  (e: 'navigate', view: string): void;
}>();
</script>
