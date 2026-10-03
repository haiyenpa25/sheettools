<?php

declare(strict_types=1);

use App\Models\ConversionProject;
use App\Repositories\ConversionProjectRepository;
use App\Services\StorageService;

$root = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_library_' . bin2hex(random_bytes(5));
$storage = new StorageService($root);
$repo = new ConversionProjectRepository($storage);
$project = new ConversionProject([
    'uuid' => 'library-test-uuid',
    'title' => 'Bài thử',
    'composer' => 'Tác giả',
    'category_slug' => 'thanh-ca',
    'category_name' => 'Thánh ca',
    'song_number' => '057',
]);

$repo->save($project);
$loaded = $repo->findByUuid($project->uuid);
assert($loaded?->composer === 'Tác giả');
assert($loaded?->categorySlug === 'thanh-ca');
assert($loaded?->songNumber === '057');

file_put_contents($storage->getSourcePath($project->uuid, 'pdf'), 'source');
assert($repo->delete($project->uuid), 'delete must atomically move a project to trash');
assert($repo->findByUuid($project->uuid) === null);
assert(count($repo->listDeleted()) === 1);
$repo->save($project);
assert($repo->findByUuid($project->uuid) === null, 'a running worker must not recreate a trashed project');
assert($repo->restore($project->uuid));
assert($repo->findByUuid($project->uuid)?->title === 'Bài thử');
assert($repo->delete($project->uuid));
assert($repo->purge($project->uuid));
assert($repo->listDeleted() === []);

@rmdir($storage->getProjectsRoot());
@rmdir($storage->getTrashRoot());
@rmdir($root);
echo "  [Unit] ProjectLibraryTest: PASS\n";
