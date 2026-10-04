import JSZip from 'jszip';

/** Serialize the current editor XML into the format named by the download. */
export async function createScoreDownload(xml: string, format: string): Promise<Blob> {
  if (format === 'musicxml' || format === 'xml') {
    return new Blob([xml], { type: 'application/vnd.recordare.musicxml+xml;charset=utf-8' });
  }
  if (format !== 'mxl') throw new Error(`Unsupported score format: ${format}`);
  const zip = new JSZip();
  zip.file('mimetype', 'application/vnd.recordare.musicxml', { compression: 'STORE' });
  zip.file('META-INF/container.xml', '<?xml version="1.0" encoding="UTF-8"?><container><rootfiles><rootfile full-path="score.xml" media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>');
  zip.file('score.xml', xml);
  const bytes = await zip.generateAsync({ type: 'arraybuffer', compression: 'DEFLATE' });
  return new Blob([bytes], { type: 'application/vnd.recordare.musicxml' });
}
