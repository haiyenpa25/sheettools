<?php

declare(strict_types=1);

namespace Tests\Failure;

require_once dirname(__DIR__, 2) . '/app/Services/ConversionService.php';
require_once dirname(__DIR__, 2) . '/app/Repositories/ConversionProjectRepository.php';

use App\Services\ConversionService;
use App\Repositories\ConversionProjectRepository;
use App\Services\StorageService;
use App\Services\ImagePreprocessService;
use App\Adapters\AudiverisOmrEngine;

$testRoot = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_failure_' . bin2hex(random_bytes(5));
$storage = new StorageService($testRoot);
$repo = new ConversionProjectRepository($storage);
$service = new ConversionService(
    $repo,
    $storage,
    new ImagePreprocessService($storage),
    new AudiverisOmrEngine($storage)
);

// 1. Create a project with invalid/corrupt content
$tempFile = tempnam(sys_get_temp_dir(), 'invalid_sheet_');
file_put_contents($tempFile, 'Corrupted binary data that cannot be recognized as sheet music');

$project = $service->createProject('invalid_corrupt.pdf', $tempFile);
assert($project->status === 'UPLOADED', "Initial status must be UPLOADED");

// 2. Process project without mocking
$success = $service->processProject($project->uuid);
$fresh = $repo->findByUuid($project->uuid);

// 3. Must fail honestly without producing fake READY status
assert($success === false, "Processing corrupt PDF must return false");
assert($fresh->status === 'FAILED', "Status of corrupt PDF must be FAILED, got: {$fresh->status}");
assert(!empty($fresh->errorMessage), "Error message must be set upon failure");

@unlink($tempFile);
function removeFailureTree(string $dir): void {
    if (!is_dir($dir)) return;
    foreach (array_diff(scandir($dir) ?: [], ['.', '..']) as $entry) {
        $path = $dir . DIRECTORY_SEPARATOR . $entry;
        is_dir($path) ? removeFailureTree($path) : unlink($path);
    }
    rmdir($dir);
}
removeFailureTree($testRoot);

echo "  [Failure] FailureHandlingTest: PASS (Truthful failure reporting verified)\n";
