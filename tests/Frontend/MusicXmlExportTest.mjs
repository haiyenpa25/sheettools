import assert from 'node:assert/strict';
import JSZip from 'jszip';
import { readFile, writeFile } from 'node:fs/promises';
import { createScoreDownload } from '../../resources/js/Services/MusicXmlExportService.ts';

const xml = process.argv[2] ? await readFile(process.argv[2], 'utf8') : '<?xml version="1.0" encoding="UTF-8"?><score-partwise><work><work-title>Giữ tiếng Việt</work-title></work><part-list/></score-partwise>';
const plain = await createScoreDownload(xml, 'musicxml');
assert.equal(await plain.text(), xml);
const compressed = await createScoreDownload(xml, 'mxl');
const bytes = new Uint8Array(await compressed.arrayBuffer());
assert.deepEqual(Array.from(bytes.slice(0, 4)), [80, 75, 3, 4], 'MXL must have a ZIP header');
const zip = await JSZip.loadAsync(bytes);
assert.equal(await zip.file('score.xml').async('string'), xml, 'Unicode and editor changes must survive compression');
const container = await zip.file('META-INF/container.xml').async('string');
assert.match(container, /full-path="score.xml"/);
assert.equal(await zip.file('mimetype').async('string'), 'application/vnd.recordare.musicxml');
if (process.argv[3]) await writeFile(process.argv[3], bytes);
await assert.rejects(() => createScoreDownload(xml, 'mscx'), /Unsupported/);
console.log('MusicXmlExportTest: PASS (XML, genuine MXL, Unicode, unsupported format)');
