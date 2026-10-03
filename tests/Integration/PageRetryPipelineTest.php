<?php

declare(strict_types=1);

use App\Contracts\OmrEngineInterface;
use App\DTOs\ConversionInputDto;
use App\DTOs\OmrResultDto;
use App\Repositories\ConversionProjectRepository;
use App\Services\ConversionService;
use App\Services\ImagePreprocessService;
use App\Services\StorageService;

$root = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_page_retry_' . bin2hex(random_bytes(5));
$storage = new StorageService($root);
$repository = new ConversionProjectRepository($storage);
$engine = new class($storage) implements OmrEngineInterface {
    public ?ConversionInputDto $input = null;

    public function __construct(private StorageService $storage) {}

    public function transcribe(ConversionInputDto $input): OmrResultDto
    {
        $this->input = $input;
        $raw = $this->storage->getRawMusicXmlPath($input->projectUuid);
        copy(dirname(__DIR__) . '/fixtures/golden_hymn.musicxml', $raw);
        return new OmrResultDto(true, $raw);
    }
};
$service = new ConversionService($repository, $storage, new ImagePreprocessService($storage), $engine);
$source = tempnam(sys_get_temp_dir(), 'sheettools_pdf_');
file_put_contents($source, 'PDF source fixture');

try {
    $project = $service->createProject('two-pages.pdf', $source);
    $savedSource = $storage->getSourcePath($project->uuid, 'pdf');
    $pages = $storage->getPagesDir($project->uuid);
    file_put_contents($pages . DIRECTORY_SEPARATOR . 'page-001.png', 'first page');
    file_put_contents($pages . DIRECTORY_SEPARATOR . 'page-002.png', 'second page');
    file_put_contents($pages . DIRECTORY_SEPARATOR . 'page-manifest.json', json_encode([
        'source_sha256' => hash_file('sha256', $savedSource),
        'page_count' => 2,
        'dpi' => 300,
    ]));

    assert($service->processProject($project->uuid, 1));
    assert($engine->input?->retryPageIndex === 1);
    assert($repository->findByUuid($project->uuid)?->status === 'NEEDS_REVIEW');
    assert(is_file($storage->getCurrentMusicXmlPath($project->uuid)));
    echo "  [Integration] PageRetryPipelineTest: PASS\n";
} finally {
    unlink($source);
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ($iterator as $item) {
        $item->isDir() ? rmdir($item->getPathname()) : unlink($item->getPathname());
    }
    rmdir($root);
}
