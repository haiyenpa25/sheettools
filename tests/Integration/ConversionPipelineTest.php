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

$conversionService = new ConversionService();
$exportService = new ExportService();
$storageService = new StorageService();
$repo = new ConversionProjectRepository();

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

$exportPath = $exportService->export($project->uuid, 'musicxml');
assert($exportPath !== null && file_exists($exportPath), "Exported MusicXML file must exist");
assert(filesize($exportPath) > 100, "Exported MusicXML file must be non-empty");

@unlink($tempFile);

echo "  [Integration] ConversionPipelineTest: PASS\n";
