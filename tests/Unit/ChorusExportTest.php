<?php
declare(strict_types=1);

use App\Services\StorageService;
use App\Services\ExportService;

$chorusRoot = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_chorus_' . bin2hex(random_bytes(5));
$chorusStorage = new StorageService($chorusRoot);
$chorusStorage->initProjectDirs('song');
$chorusXml = '<score-partwise version="4.0"><part-list/><part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><lyric number="3" name="Lời 3"><text>Xin</text></lyric></note><note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><lyric number="1" name="ĐK"><text>Chúa</text></lyric></note></measure></part></score-partwise>';
$chorusStorage->saveCurrentMusicXml('song', $chorusXml);
$chorusExporter = new ExportService($chorusStorage);
$chorusDefault = $chorusExporter->export('song', 'musicxml');
$chorusExpanded = $chorusExporter->export('song', 'musicxml', 'full', true);
$chorusDoc = new DOMDocument();
$chorusDoc->load($chorusExpanded);
$chorusXpath = new DOMXPath($chorusDoc);
assert($chorusXpath->query('//lyric[@name="ĐK"]')->length === 3, 'Chorus must be duplicated into all three verses');
assert(file_get_contents($chorusStorage->getCurrentMusicXmlPath('song')) === $chorusXml, 'Current score must remain unchanged');
assert($chorusDefault !== $chorusExpanded, 'Export options require distinct artifact paths');
assert(substr_count(file_get_contents($chorusDefault), 'name="ĐK"') === 1, 'Default export retains one chorus row');
foreach (glob($chorusStorage->getProjectDir('song') . '/export/*') ?: [] as $chorusFile) unlink($chorusFile);
unlink($chorusStorage->getCurrentMusicXmlPath('song'));
foreach (['export', 'source', 'pages', 'omr', 'musicxml', 'ocr', 'document', 'logs'] as $chorusDir) @rmdir($chorusStorage->getProjectDir('song') . '/' . $chorusDir);
@rmdir($chorusStorage->getProjectDir('song'));
@rmdir($chorusStorage->getProjectsRoot());
@rmdir($chorusRoot);
echo "  [Unit] ChorusExportTest: PASS\n";
