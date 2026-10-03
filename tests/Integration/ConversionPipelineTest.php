<?php

declare(strict_types=1);

namespace Tests\Integration;

require_once dirname(__DIR__, 2) . '/app/Services/ConversionService.php';
require_once dirname(__DIR__, 2) . '/app/Services/ExportService.php';
require_once dirname(__DIR__, 2) . '/app/Services/StorageService.php';
require_once dirname(__DIR__, 2) . '/app/Repositories/ConversionProjectRepository.php';

use App\Services\ConversionService;
use App\Services\ExportService;
use App\Services\StorageService;
use App\Repositories\ConversionProjectRepository;
use App\Services\ImagePreprocessService;
use App\Adapters\AudiverisOmrEngine;

$testRoot = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_integration_' . bin2hex(random_bytes(5));
$storageService = new StorageService($testRoot);
$repo = new ConversionProjectRepository($storageService);
$conversionService = new ConversionService(
    $repo,
    $storageService,
    new ImagePreprocessService($storageService),
    new AudiverisOmrEngine($storageService)
);
$exportService = new ExportService($storageService);

// 1. Create a project
$fixturePath = dirname(__DIR__) . '/fixtures/golden_hymn.musicxml';
$tempFile = tempnam(sys_get_temp_dir(), 'test_proj_');
copy($fixturePath, $tempFile);

$project = $conversionService->createProject('integration_test_hymn.musicxml', $tempFile);
assert($project->status === 'UPLOADED', "Status must be UPLOADED");

// 2. Simulate raw MusicXML placement and current.musicxml generation
$storageService->saveRawMusicXml($project->uuid, file_get_contents($fixturePath));
$storageService->saveCurrentMusicXml($project->uuid, file_get_contents($fixturePath));

$project->status = 'NEEDS_REVIEW';
$project->progress = 100;
$repo->save($project);

// 3. Validate & Export
$validation = $exportService->validateProject($project->uuid);
assert($validation['isValid'] === true, "Project validation must succeed for valid XML");

$exportPath = $exportService->export($project->uuid, 'musicxml', 'full');
assert($exportPath !== null && file_exists($exportPath), "Exported MusicXML file must exist");
assert(filesize($exportPath) > 100, "Exported MusicXML file must be non-empty");

$notationPath = $exportService->export($project->uuid, 'musicxml', 'notation');
assert($notationPath !== null && file_exists($notationPath), "Notation-only MusicXML must exist");
$fullDoc = new \DOMDocument();
$notationDoc = new \DOMDocument();
$fullDoc->load($exportPath);
$notationDoc->load($notationPath);
$fullXpath = new \DOMXPath($fullDoc);
$notationXpath = new \DOMXPath($notationDoc);
assert($notationXpath->query('//*[local-name()="lyric"]')->length === 0, "Notation-only export must contain no lyric elements");
assert(
    $notationXpath->query('//*[local-name()="note"]')->length === $fullXpath->query('//*[local-name()="note"]')->length,
    "Removing lyrics must preserve every recognized note"
);

$lyricsPath = $exportService->export($project->uuid, 'txt', 'lyrics');
assert($lyricsPath !== null && file_exists($lyricsPath), "Lyrics-only text must exist");
$lyricsText = file_get_contents($lyricsPath);
assert(str_contains($lyricsText, 'VERSE 1'), "Lyrics-only text must identify verses");
assert(str_contains($lyricsText, 'Cúi'), "Lyrics-only text must preserve Vietnamese diacritics");

@unlink($tempFile);
function removeIntegrationTree(string $dir): void {
    if (!is_dir($dir)) return;
    foreach (array_diff(scandir($dir) ?: [], ['.', '..']) as $entry) {
        $path = $dir . DIRECTORY_SEPARATOR . $entry;
        is_dir($path) ? removeIntegrationTree($path) : unlink($path);
    }
    rmdir($dir);
}
removeIntegrationTree($testRoot);

echo "  [Integration] ConversionPipelineTest: PASS\n";
