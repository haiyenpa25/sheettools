export interface ReviewViolation { rule: string; severity: string; message: string }
export interface ReviewSuggestion { id: string; source: string; summary: string; verified?: boolean }
export interface ReviewItem {
  id: string; kind?: string; page: number; part_id?: string; measure_number: number | null;
  box: number[]; review_status?: string; violations: ReviewViolation[]; suggestions: ReviewSuggestion[];
  metadata?: Record<string, { text?: string }>;
}
export interface ReviewQueue { items: ReviewItem[]; xml_sha256: string; total_measures: number; review_measures?: number }

export async function loadReviewQueue(uuid: string, all = false): Promise<ReviewQueue> {
  const r = await fetch(`/api/conversions/${encodeURIComponent(uuid)}/review-queue${all ? '?all=1' : ''}`, { cache: 'no-store' });
  const data = await r.json();
  if (!r.ok) throw new Error(data.message || 'Chưa có dữ liệu soát; hãy Retry để tạo sổ ô nhịp.');
  return data;
}
export async function recordReview(uuid: string, item: ReviewItem, input: Record<string, unknown>): Promise<ReviewQueue> {
  const r = await fetch(`/api/conversions/${encodeURIComponent(uuid)}/review/${encodeURIComponent(item.id)}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input),
  });
  const data = await r.json(); if (!r.ok) throw new Error(data.message || 'Không ghi được quyết định.'); return data;
}

/** Clone with inherited attributes so OSMD can render a measure in isolation. */
export function measureXml(xml: string, number: number): string {
  const doc = new DOMParser().parseFromString(xml, 'application/xml');
  if (doc.querySelector('parsererror')) throw new Error('MusicXML không hợp lệ.');
  for (const part of Array.from(doc.querySelectorAll('score-partwise > part'))) {
    const measures = Array.from(part.querySelectorAll(':scope > measure'));
    const target = measures.find(m => Number(m.getAttribute('number')) === number);
    if (!target) { part.remove(); continue; }
    const inherited = new Map<string, Element>();
    for (const m of measures) {
      for (const attr of Array.from(m.querySelector(':scope > attributes')?.children || [])) inherited.set(attr.tagName + (attr.getAttribute('number') || ''), attr.cloneNode(true) as Element);
      if (m === target) break;
    }
    const attrs = target.querySelector(':scope > attributes') || doc.createElement('attributes');
    if (!attrs.parentNode) target.insertBefore(attrs, target.firstChild);
    for (const attr of inherited.values()) if (!Array.from(attrs.children).some(a => a.tagName === attr.tagName && a.getAttribute('number') === attr.getAttribute('number'))) attrs.appendChild(attr);
    for (const m of measures) if (m !== target) m.remove();
    target.querySelectorAll('print').forEach(n => n.remove());
  }
  return new XMLSerializer().serializeToString(doc);
}
