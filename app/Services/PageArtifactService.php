<?php

declare(strict_types=1);

namespace App\Services;

/** Provides a safe, naturally ordered view of immutable rendered source pages. */
final class PageArtifactService
{
    private StorageService $storage;

    public function __construct(?string $storageRoot = null)
    {
        $this->storage = new StorageService($storageRoot);
    }

    /** @return array<int, array{index:int, filename:string, mime_type:string}> */
    public function list(string $uuid): array
    {
        $directory = $this->storage->getPagesDir($uuid);
        if (!is_dir($directory)) {
            return [];
        }

        $files = array_merge(
            glob($directory . DIRECTORY_SEPARATOR . 'page-*.png') ?: [],
            glob($directory . DIRECTORY_SEPARATOR . 'page-*.jpg') ?: [],
            glob($directory . DIRECTORY_SEPARATOR . 'page-*.jpeg') ?: []
        );
        natsort($files);

        $items = [];
        foreach (array_values($files) as $index => $path) {
            $extension = strtolower((string) pathinfo($path, PATHINFO_EXTENSION));
            $items[] = [
                'index' => $index,
                'filename' => basename($path),
                'mime_type' => $extension === 'png' ? 'image/png' : 'image/jpeg',
            ];
        }
        return $items;
    }

    /** @return array{path:string, filename:string, mime_type:string}|null */
    public function resolve(string $uuid, int $index): ?array
    {
        if ($index < 0) {
            return null;
        }
        $items = $this->list($uuid);
        if (!isset($items[$index])) {
            return null;
        }

        $item = $items[$index];
        $path = $this->storage->getPagesDir($uuid) . DIRECTORY_SEPARATOR . $item['filename'];
        if (!is_file($path)) {
            return null;
        }
        return ['path' => $path] + $item;
    }

    /** @return array{path:string, mime_type:string}|null */
    public function resolveLayout(string $uuid, int $index, bool $overlay = false): ?array
    {
        if ($this->resolve($uuid, $index) === null) {
            return null;
        }
        $number = $index + 1;
        $base = $this->storage->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'omr_out';
        $filename = sprintf('page_%03d_regions%s', $number, $overlay ? '_debug.png' : '.json');
        $candidates = [
            $base . DIRECTORY_SEPARATOR . sprintf('page_result_%04d', $number) . DIRECTORY_SEPARATOR . $filename,
            $base . DIRECTORY_SEPARATOR . $filename,
        ];
        foreach ($candidates as $path) {
            if (is_file($path)) {
                return ['path' => $path, 'mime_type' => $overlay ? 'image/png' : 'application/json'];
            }
        }
        return null;
    }
}
