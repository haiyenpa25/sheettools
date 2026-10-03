<?php

declare(strict_types=1);

use App\Services\ImagePreprocessService;
use App\Services\StorageService;

$root = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_preprocess_' . bin2hex(random_bytes(5));
$storage = new StorageService($root);
$uuid = 'test-project';
$storage->initProjectDirs($uuid);
$source = $storage->getSourcePath($uuid, 'pdf');
file_put_contents($source, 'immutable source');
$pagesDir = $storage->getPagesDir($uuid);
file_put_contents($pagesDir . DIRECTORY_SEPARATOR . 'page-001.png', 'page one');
file_put_contents($pagesDir . DIRECTORY_SEPARATOR . 'page-002.png', 'page two');
$manifest = $pagesDir . DIRECTORY_SEPARATOR . 'page-manifest.json';
file_put_contents($manifest, json_encode([
    'source_sha256' => hash_file('sha256', $source),
    'page_count' => 2,
    'dpi' => 300,
]));

try {
    $service = new ImagePreprocessService($storage);
    assert(count($service->reusablePages($uuid, $source)) === 2);
    file_put_contents($source, 'changed source');
    assert($service->reusablePages($uuid, $source) === []);
    file_put_contents($source, 'immutable source');
    unlink($pagesDir . DIRECTORY_SEPARATOR . 'page-002.png');
    assert($service->reusablePages($uuid, $source) === []);
    $failedPipeline = new class($storage) extends ImagePreprocessService {
        protected function runOpenCvPipeline(string $inputPath, string $outputPath): bool
        {
            return false;
        }
    };
    try {
        $failedPipeline->processSource($uuid, $source, 'jpg');
        assert(false, 'Failed image normalization must stop conversion.');
    } catch (RuntimeException) {
        // Expected.
    }
    echo "  [Unit] ImagePreprocessServiceTest: PASS\n";
} finally {
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ($iterator as $item) {
        $item->isDir() ? rmdir($item->getPathname()) : unlink($item->getPathname());
    }
    rmdir($root);
}
