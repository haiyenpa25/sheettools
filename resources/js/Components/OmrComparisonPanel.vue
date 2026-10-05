<template>
  <section class="border border-border-subtle rounded p-4 space-y-2 text-sm" aria-label="Đối chiếu nhận dạng">
    <h3 class="font-semibold">Đối chiếu nhận dạng nốt và khuông</h3>
    <p class="text-secondary">Chạy trên trang gốc. Kết quả thử nghiệm cần được kiểm tra trước khi sử dụng.</p>
    <div class="flex flex-wrap gap-2">
      <button v-for="engine in engines" :key="engine" :disabled="busy || active(engine)" @click="enqueue(engine)" class="p-2 border border-border-subtle rounded disabled:opacity-50">Chạy {{ engine === 'homr' ? 'Homr' : 'Clarity' }}</button>
    </div>
    <p v-if="error" class="text-warning" role="alert">{{ error }}</p>
    <article v-for="run in runs.slice(0, 6)" :key="run.id" class="border border-border-subtle rounded p-2 space-y-2">
      <p>{{ run.engine }} · {{ labels[run.status] || run.status }} · {{ run.pages?.length || 0 }}/{{ run.total_pages || '—' }} trang</p>
      <p v-if="run.status === 'queued' && !availability[run.engine]?.online" class="text-warning">Worker chưa sẵn sàng hoặc đang bận. Yêu cầu đang chờ.</p>
      <p v-if="run.error" class="text-warning">{{ run.error }}</p>
      <a v-if="run.status === 'running'" :href="artifact(run, (run.pages?.length || 0) + 1, 'engine.log')" target="_blank" rel="noopener" class="text-primary underline">Xem tiến trình đọc trang hiện tại</a>
      <p v-if="run.analysis" class="text-secondary">Phân tích lời: {{ labels[run.analysis.status] || run.analysis.status }} {{ run.analysis.error || '' }}</p>
      <div v-for="page in run.pages" :key="page.page" class="flex flex-wrap items-center gap-2">
        <span>Trang {{ page.page }}: {{ page.staff_regions }} khuông · {{ page.summary.pitched_notes }} nốt</span>
        <a :href="artifact(run, page.page, page.xml)" target="_blank" rel="noopener" class="text-primary underline">MusicXML</a>
        <button @click="preview(run, page.page)" class="text-primary underline">Xem bản nhạc</button>
        <a v-if="run.analysis?.status === 'completed'" :href="artifact(run, page.page, 'aligned.musicxml')" target="_blank" rel="noopener" class="text-primary underline">Bản ghép lời cần soát</a>
        <button @click="overlay = artifact(run, page.page, 'regions.png')" class="text-primary underline">Xem vùng nhận dạng</button>
        <a :href="artifact(run, page.page, 'engine.log')" target="_blank" rel="noopener" class="text-primary underline">Nhật ký</a>
      </div>
      <a v-if="run.status === 'failed'" :href="artifact(run, (run.pages?.length || 0) + 1, 'engine.log')" target="_blank" rel="noopener" class="text-primary underline">Nhật ký trang lỗi</a>
    </article>
    <div v-if="overlay || previewOpen" class="space-y-2">
      <button @click="closePreview" class="underline">Đóng đối chiếu</button>
      <div class="grid md:grid-cols-2 gap-4">
        <img v-if="overlay" :src="overlay" alt="Khuông và vùng chữ được phát hiện trên ảnh gốc" class="max-w-full bg-white" />
        <div v-show="previewOpen" ref="scoreElement" class="bg-white overflow-auto rounded p-2" aria-label="Bản nhận dạng thử nghiệm" />
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
type Engine = 'homr' | 'clarity';
interface Run { id: string; engine: Engine; status: string; total_pages?: number; error?: string; analysis?: { status: string; error?: string }; pages?: { page: number; xml: string; staff_regions: number; summary: { pitched_notes: number } }[] }
const props = defineProps<{ uuid: string }>();
const engines: Engine[] = ['homr', 'clarity'];
const runs = ref<Run[]>([]); const availability = ref<Partial<Record<Engine, { online: boolean }>>>({});
const busy = ref(false); const error = ref(''); const overlay = ref('');
const previewOpen = ref(false); const scoreElement = ref<HTMLElement>(); let renderGeneration = 0;
const labels: Record<string, string> = { queued: 'Đang chờ', running: 'Đang đọc', completed: 'Hoàn thành', failed: 'Không hoàn thành' };
const base = `/api/conversions/${encodeURIComponent(props.uuid)}/omr-comparisons`;
const active = (engine: Engine) => runs.value.some(run => run.engine === engine && ['queued', 'running'].includes(run.status));
const artifact = (run: Run, page: number, name: string) => `${base}/${run.id}/pages/${page}/${encodeURIComponent(name)}`;
let timer: ReturnType<typeof setTimeout> | undefined; let disposed = false;
async function load() {
  try { const response = await fetch(base, { cache: 'no-store' }); const data = await response.json(); if (!response.ok) throw new Error(data.message); if (!disposed) { runs.value = data.runs; availability.value = data.engines; } }
  catch (e) { if (!disposed) error.value = String(e); }
  finally { if (!disposed) timer = setTimeout(load, 5000); }
}
async function enqueue(engine: Engine) {
  if (busy.value || active(engine)) return; busy.value = true; error.value = '';
  try { const response = await fetch(base, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ engine }) }); const data = await response.json(); if (!response.ok) throw new Error(data.message); runs.value.unshift(data); }
  catch (e) { error.value = String(e); } finally { busy.value = false; }
}
function closePreview() { renderGeneration++; overlay.value = ''; previewOpen.value = false; }
async function preview(run: Run, page: number) {
  const generation = ++renderGeneration; previewOpen.value = true; error.value = '';
  overlay.value = artifact(run, page, 'regions.png'); await nextTick();
  try {
    const name = run.analysis?.status === 'completed' ? 'aligned.musicxml' : run.pages?.find(p => p.page === page)?.xml;
    if (!name || !scoreElement.value) return;
    const response = await fetch(artifact(run, page, name), { cache: 'no-store' }); if (!response.ok) throw new Error('Không tải được bản nhạc.');
    const xml = await response.text(); if (generation !== renderGeneration || disposed) return;
    scoreElement.value.innerHTML = '';
    const osmd = new OpenSheetMusicDisplay(scoreElement.value, { backend: 'svg', autoResize: false, drawTitle: false, drawComposer: false });
    await osmd.load(xml); if (generation === renderGeneration && !disposed) osmd.render();
  } catch (e) { if (!disposed && generation === renderGeneration) error.value = String(e); }
}
onMounted(load); onUnmounted(() => { disposed = true; renderGeneration++; clearTimeout(timer); });
</script>
