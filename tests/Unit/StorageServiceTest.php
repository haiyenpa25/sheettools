<?php

declare(strict_types=1);

use App\Services\StorageService;

$root = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_storage_' . bin2hex(random_bytes(5));
$storage = new StorageService($root);
$storage->initProjectDirs('p1');
$realSource = $storage->getSourcePath('p1', 'pdf');
file_put_contents($realSource, 'pdf');

try {
    assert(basename($realSource) === 'original.pdf', 'source files must use a canonical server-side name');
    assert($storage->getSourcePath('p1', '../../evil.php') === null, 'unapproved extensions must be rejected');
    assert($storage->resolveSourcePath('p1', '57.pdf', 'pdf') === $realSource);
    assert($storage->resolveSourcePath('p1', '57', 'pdf') === $realSource, 'renaming title must not break retry source resolution');
    assert($storage->resolveSourcePath('p1', '../57.pdf', 'pdf') === $realSource, 'resolver must never traverse outside source directory');
    $storage->saveRawMusicXml('p1', 'first raw version');
    $storage->saveRawMusicXml('p1', 'second raw version');
    assert(file_get_contents($storage->getRawMusicXmlPath('p1')) === 'first raw version', 'raw MusicXML must remain immutable');
    echo "  [Unit] StorageServiceTest: PASS\n";
} finally {
    unlink($realSource);
    @unlink($storage->getRawMusicXmlPath('p1'));
    @unlink($storage->getCurrentMusicXmlPath('p1'));
    foreach (array_reverse(['source', 'pages', 'omr', 'musicxml', 'ocr', 'document', 'logs']) as $dir) {
        @rmdir($storage->getProjectDir('p1') . DIRECTORY_SEPARATOR . $dir);
    }
    @rmdir($storage->getProjectDir('p1'));
    @rmdir($storage->getProjectsRoot());
    @rmdir($root);
}
