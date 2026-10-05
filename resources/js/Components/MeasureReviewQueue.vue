<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 bg-background-app/95 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Soát theo ô nhịp">
      <section class="bg-surface-container-lowest border border-border-subtle rounded-xl w-full max-w-6xl max-h-[95vh] overflow-auto p-4 space-y-4">
        <header class="flex items-center justify-between gap-4">
          <h2 class="text-lg font-bold">{{ current?.kind === 'metadata' ? 'Thông tin bài' : `Ô ${current?.measure_number ?? '—'}` }} · {{ index + 1 }}/{{ queue?.items.length || 0 }} · Trang {{ current?.page || 1 }}</h2>
          <label class="text-sm"><input v-model="all" type="checkbox" @change="load" /> Soát toàn bộ để gán nhãn</label>
          <button class="p-2 border border-border-subtle rounded" @click="$emit('close')">Đóng</button>
        </header>
        <p v-if="error" class="text-warning" role="alert">{{ error }} <button @click="load" class="underline">Tải lại</button> · <button :disabled="busy" @click="buildQueue" class="underline">Tạo dữ liệu soát từ kết quả có sẵn</button></p>
        <p v-if="busy" class="text-secondary">Đang tải…</p>
        <OmrComparisonPanel :uuid="props.uuid" />
        <template v-if="current">
          <p class="text-sm text-secondary">Trạng thái: {{ current.review_status || 'open' }} · Phần máy đánh dấu cần được người xác nhận.</p>
          <div class="grid md:grid-cols-2 gap-4">
            <div class="bg-white rounded p-2 overflow-auto"><h3 class="text-slate-900 text-sm font-semibold mb-2">Ảnh gốc</h3><canvas ref="sourceCanvas" class="max-w-full" aria-label="Ảnh cắt ô nhịp gốc" /></div>
            <div class="bg-white rounded p-2 overflow-auto"><h3 class="text-slate-900 text-sm font-semibold mb-2">Bản nhận dạng</h3><div ref="score" /></div>
          </div>
          <div v-if="current.kind === 'metadata'" class="grid md:grid-cols-3 gap-4">
            <label v-for="(label, key) in fieldLabels" :key="key" class="text-sm">{{ label }}<input v-model="fields[key]" class="mt-2 w-full p-2 bg-surface-container border border-border-subtle rounded" /></label>
          </div>
          <ul class="space-y-2 text-sm"><li v-for="v in current.violations" :key="v.rule + v.message" :class="v.severity === 'error' ? 'text-error' : 'text-warning'">{{ v.rule }} · {{ v.message }}</li></ul>
          <div v-for="(suggestion, i) in current.suggestions" :key="suggestion.id" class="border border-border-subtle rounded p-2 text-sm">
            <button :disabled="!suggestion.verified || busy" @click="act('apply', suggestion.id)" class="text-primary disabled:text-secondary">[{{ i + 1 }}] {{ suggestion.summary }} {{ suggestion.verified ? '' : '(cần thêm bằng chứng)' }}</button>
          </div>
          <footer class="flex flex-wrap gap-2 text-sm">
            <button @click="move(-1)" class="p-2 border border-border-subtle rounded">← Trước</button>
            <button :disabled="busy" @click="act(current.kind === 'metadata' ? 'metadata' : 'accept')" class="p-2 bg-primary text-on-primary rounded">Enter · {{ current.kind === 'metadata' ? 'Lưu thông tin' : 'Xác nhận đúng' }}</button>
            <button :disabled="busy || current.kind === 'metadata'" @click="edit" class="p-2 border border-border-subtle rounded">E · Sửa tay</button>
            <button :disabled="busy || current.kind === 'metadata'" @click="repair('audiveris')" class="p-2 border border-border-subtle rounded">Đọc lại hệ 2×</button>
            <button :disabled="busy || current.kind === 'metadata'" @click="repair('homr')" class="p-2 border border-border-subtle rounded">Phương án Homr</button>
            <button :disabled="busy" @click="act('skip')" class="p-2 border border-border-subtle rounded">N · Để sau</button>
            <button :disabled="busy" @click="act('reject')" class="p-2 border border-error text-error rounded">Đánh dấu sai</button>
            <button :disabled="busy" @click="act('undo')" class="p-2 border border-border-subtle rounded">Hoàn tác sửa gần nhất</button>
            <button @click="move(1)" class="p-2 border border-border-subtle rounded">Sau →</button>
          </footer>
        </template>
      </section>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay';
import OmrComparisonPanel from './OmrComparisonPanel.vue';
import { loadReviewQueue, recordReview, measureXml, type ReviewQueue } from '../Services/MeasureReviewService';
const props = defineProps<{ uuid: string; xml: string }>();
const emit = defineEmits<{ (e:'close'):void; (e:'edit',number:number):void; (e:'updated',xml:string):void }>();
const queue=ref<ReviewQueue>(); const index=ref(0); const busy=ref(false); const error=ref(''); const all=ref(false);
const current=computed(()=>queue.value?.items[index.value]); const score=ref<HTMLElement>(); const sourceCanvas=ref<HTMLCanvasElement>();
const fields=ref({title:'',composer:'',translator:''}); const fieldLabels={title:'Tựa bài',composer:'Nhạc sĩ',translator:'Lời Việt'};
let started=performance.now(); let renderGeneration=0;
async function load() { busy.value=true; error.value=''; try { queue.value=await loadReviewQueue(props.uuid,all.value); index.value=0; } catch(e) { error.value=String(e); } finally { busy.value=false; await render(); } }
async function buildQueue() {
  if(busy.value) return; busy.value=true; error.value='';
  try { const response=await fetch(`/api/conversions/${props.uuid}/review-queue/build`,{method:'POST'}); const data=await response.json(); if(!response.ok) throw new Error(data.message); queue.value=data; index.value=0; const xml=await fetch(`/api/conversions/${props.uuid}/musicxml`,{cache:'no-store'}); emit('updated',await xml.text()); }
  catch(e) { error.value=String(e); } finally { busy.value=false; await render(); }
}
async function render() {
  const generation=++renderGeneration; const item=current.value; if(!item) return;
  fields.value={title:item.metadata?.title?.text||'',composer:item.metadata?.composer?.text||'',translator:item.metadata?.translator?.text||''};
  await nextTick();
  try {
    if(score.value) {
      score.value.innerHTML='';
      if(item.measure_number!==null) { const osmd=new OpenSheetMusicDisplay(score.value,{backend:'svg',autoResize:false,drawTitle:false,drawComposer:false,drawPartNames:false}); await osmd.load(measureXml(props.xml,item.measure_number)); if(generation!==renderGeneration) return; osmd.render(); }
      else score.value.textContent=fields.value.title;
    }
    const img=new Image(); img.src=`/api/conversions/${encodeURIComponent(props.uuid)}/pages/${item.page-1}`;
    await img.decode(); if(generation!==renderGeneration) return;
    const canvas=sourceCanvas.value; const ctx=canvas?.getContext('2d'); if(!canvas||!ctx) return;
    const [x1,y1,x2,y2]=item.box.length===4?item.box:[0,0,img.naturalWidth,img.naturalHeight];
    const x=Math.max(0,x1),y=Math.max(0,y1),w=Math.max(1,Math.min(img.naturalWidth,x2)-x),h=Math.max(1,Math.min(img.naturalHeight,y2)-y);
    const scale=Math.min(1,600/w); canvas.width=Math.round(w*scale); canvas.height=Math.round(h*scale); ctx.drawImage(img,x,y,w,h,0,0,canvas.width,canvas.height);
  } catch(e) { error.value=String(e); } finally { if(generation===renderGeneration) started=performance.now(); }
}
function move(delta:number) { if(!queue.value||busy.value) return; index.value=Math.max(0,Math.min(queue.value.items.length-1,index.value+delta)); }
async function edit() {
  const number=current.value?.measure_number;
  if(number===null||number===undefined||!queue.value||!current.value||busy.value) return;
  busy.value=true;
  try { await recordReview(props.uuid,current.value,{action:'edit',seconds:(performance.now()-started)/1000,xml_sha256:queue.value.xml_sha256,all:all.value}); emit('edit',number); emit('close'); }
  catch(e) { error.value=String(e); } finally { busy.value=false; }
}
async function act(action:string,suggestion_id?:string) {
  if(!current.value||!queue.value||busy.value) return; busy.value=true; error.value='';
  try {
    queue.value=await recordReview(props.uuid,current.value,{action,suggestion_id,seconds:(performance.now()-started)/1000,xml_sha256:queue.value.xml_sha256,all:all.value,...(action==='metadata'?{fields:fields.value}:{})});
    if(['metadata','apply','undo'].includes(action)) { const r=await fetch(`/api/conversions/${props.uuid}/musicxml`,{cache:'no-store'}); emit('updated',await r.text()); }
    if(action!=='undo') index.value=Math.min(queue.value.items.length-1,index.value+1);
  } catch(e) { error.value=String(e); } finally { busy.value=false; await render(); }
}
async function repair(engine = 'audiveris') {
  if(!current.value||busy.value) return; busy.value=true; error.value='';
  try { const r=await fetch(`/api/conversions/${props.uuid}/review/${current.value.id}/repair?engine=${engine}`,{method:'POST'}); const data=await r.json(); if(!r.ok) throw new Error(data.message); queue.value=data; }
  catch(e) { error.value=String(e); } finally { busy.value=false; started=performance.now(); }
}
function keyboard(e:KeyboardEvent) {
  if((e.target as HTMLElement)?.closest('input,textarea,select')||busy.value) return;
  if(e.key==='ArrowLeft') move(-1); else if(e.key==='ArrowRight') move(1); else if(e.key==='Enter') void act(current.value?.kind==='metadata'?'metadata':'accept');
  else if(e.key.toLowerCase()==='e') edit(); else if(e.key.toLowerCase()==='n') void act('skip'); else if(/^[1-9]$/.test(e.key)) { const s=current.value?.suggestions[Number(e.key)-1]; if(s?.verified) void act('apply',s.id); }
  else return; e.preventDefault();
}
watch(index,render); watch(()=>props.xml,render); onMounted(()=>{ void load(); window.addEventListener('keydown',keyboard); }); onUnmounted(()=>{ renderGeneration++; window.removeEventListener('keydown',keyboard); });
</script>
