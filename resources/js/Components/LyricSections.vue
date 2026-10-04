<template>
  <div v-if="sections.length" class="space-y-2 text-xs">
    <details v-for="section in sections" :key="section.id" class="border border-border-subtle rounded p-2">
      <summary class="cursor-pointer text-on-surface font-medium">
        {{ labels[section.type] || section.type }} · {{ section.verse_count }} lời
        <span class="text-secondary"> · {{ section.alignment_summary?.accepted || 0 }} đã gắn / {{ section.alignment_summary?.review || 0 }} cần soát</span>
        <span v-if="section.needs_review" class="text-warning"> · Phân đoạn suy luận</span>
      </summary>
      <div v-for="verse in section.verses || []" :key="verse.number" class="mt-2">
        <span class="font-medium text-secondary">Lời {{ verse.number }}: </span>
        <p v-for="(line, index) in verse.lines" :key="index" class="mt-1">
          <span v-for="(word, wordIndex) in line.syllables" :key="wordIndex"
            :class="word.alignment?.status === 'accepted' ? 'text-on-surface' : 'text-warning'"
            :title="word.alignment?.status === 'accepted' ? 'Đã gắn vào nốt' : 'Cần soát tay'">{{ word.text }} </span>
        </p>
      </div>
    </details>
  </div>
  <p v-if="error" class="text-xs text-warning">{{ error }}</p>
</template>

<script setup lang="ts">
import { ref, watch, onBeforeUnmount } from 'vue';
import { loadLyricSections, type LyricSection } from '../Services/LyricStructureService';
const props = defineProps<{ projectUuid?: string | null }>();
const sections = ref<LyricSection[]>([]);
const error = ref('');
const labels: Record<string, string> = { verse: 'Đoạn lời', chorus: 'Điệp khúc', coda: 'Coda', intro: 'Dạo đầu' };
let request: AbortController | null = null;
watch(() => props.projectUuid, async uuid => {
  request?.abort();
  sections.value = [];
  error.value = '';
  if (!uuid) return;
  const controller = new AbortController();
  request = controller;
  try {
    const loaded = await loadLyricSections(uuid, controller.signal);
    if (!controller.signal.aborted) sections.value = loaded;
  } catch (reason) {
    if (!controller.signal.aborted) error.value = reason instanceof Error ? reason.message : 'Không tải được cấu trúc lời';
  }
}, { immediate: true });
onBeforeUnmount(() => request?.abort());
</script>
