<?php

declare(strict_types=1);

use App\Services\PageArtifactService;

$root = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_pages_' . bin2hex(random_bytes(5));
$pages = $root . DIRECTORY_SEPARATOR . 'projects' . DIRECTORY_SEPARATOR . 'p1' . DIRECTORY_SEPARATOR . 'pages';
mkdir($pages, 0755, true);
file_put_contents($pages . DIRECTORY_SEPARATOR . 'page-10.png', 'ten');
file_put_contents($pages . DIRECTORY_SEPARATOR . 'page-2.png', 'two');
file_put_contents($pages . DIRECTORY_SEPARATOR . 'page-1.jpg', 'one');
file_put_contents($pages . DIRECTORY_SEPARATOR . 'notes.txt', 'ignore');
$layoutDir = dirname($pages) . DIRECTORY_SEPARATOR . 'omr_out' . DIRECTORY_SEPARATOR . 'page_result_0002';
mkdir($layoutDir, 0755, true);
file_put_contents($layoutDir . DIRECTORY_SEPARATOR . 'page_002_regions.json', '{"systems":[]}');

try {
    $service = new PageArtifactService($root);
    $items = $service->list('p1');

    assert(count($items) === 3);
    assert($items[0]['index'] === 0 && $items[0]['filename'] === 'page-1.jpg');
    assert($items[1]['index'] === 1 && $items[1]['filename'] === 'page-2.png');
    assert($items[2]['index'] === 2 && $items[2]['filename'] === 'page-10.png');
    assert($service->resolve('p1', 1)['mime_type'] === 'image/png');
    assert($service->resolve('p1', -1) === null);
    assert($service->resolve('p1', 99) === null);
    assert($service->resolveLayout('p1', 1)['mime_type'] === 'application/json');
    assert($service->resolveLayout('p1', 0) === null);
    echo "  [PASS] PageArtifactServiceTest\n";
} finally {
    foreach (glob($pages . DIRECTORY_SEPARATOR . '*') ?: [] as $file) {
        unlink($file);
    }
    rmdir($pages);
    unlink($layoutDir . DIRECTORY_SEPARATOR . 'page_002_regions.json');
    rmdir($layoutDir);
    rmdir(dirname($layoutDir));
    rmdir(dirname($pages));
    rmdir(dirname(dirname($pages)));
    rmdir($root);
}
