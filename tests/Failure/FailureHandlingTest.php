<?php

declare(strict_types=1);

namespace Tests\Failure;

require_once dirname(__DIR__, 2) . '/app/Services/ConversionService.php';
require_once dirname(__DIR__, 2) . '/app/Repositories/ConversionProjectRepository.php';

use App\Services\ConversionService;
use App\Repositories\ConversionProjectRepository;

$service = new ConversionService();
$repo = new ConversionProjectRepository();

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

echo "  [Failure] FailureHandlingTest: PASS (Truthful failure reporting verified)\n";
