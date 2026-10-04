export interface StructuredSyllable {
  text: string;
  alignment?: { status?: string } | null;
}
export interface LyricSection {
  id: string;
  type: string;
  verse_count: number;
  needs_review?: boolean;
  verses?: { number: number; lines: { syllables: StructuredSyllable[] }[] }[];
  alignment_summary?: { accepted: number; review: number };
}

export async function loadLyricSections(uuid: string, signal: AbortSignal): Promise<LyricSection[]> {
  const response = await fetch(`/api/conversions/${encodeURIComponent(uuid)}/lyrics-artifact`, { signal, cache: 'no-store' });
  if (response.status === 404) return [];
  if (!response.ok) throw new Error('Không tải được cấu trúc lời');
  const payload = await response.json();
  const artifact = payload.data || payload;
  return Array.isArray(artifact.sections) ? artifact.sections : [];
}
