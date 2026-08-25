<?php

declare(strict_types=1);

namespace App\Repositories;

require_once dirname(__DIR__) . '/Models/ConversionProject.php';
require_once dirname(__DIR__) . '/Services/StorageService.php';

use App\Models\ConversionProject;
use App\Services\StorageService;

/**
 * Repository quản lý lưu trữ và truy vấn thông tin dự án chuyển đổi
 */
class ConversionProjectRepository
{
    protected StorageService $storageService;

    public function __construct(?StorageService $storageService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
    }

    public function findByUuid(string $uuid): ?ConversionProject
    {
        $metaPath = $this->getMetaPath($uuid);
        if (!file_exists($metaPath)) {
            return null;
        }

        $json = file_get_contents($metaPath);
        $data = json_decode($json, true);
        if (!is_array($data)) {
            return null;
        }

        return new ConversionProject($data);
    }

    public function save(ConversionProject $project): void
    {
        $this->storageService->initProjectDirs($project->uuid);
        $metaPath = $this->getMetaPath($project->uuid);

        $project->updatedAt = date('Y-m-d H:i:s');
        file_put_contents($metaPath, json_encode($project->toArray(), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    }

    public function listAll(): array
    {
        $root = $this->storageService->getProjectsRoot();
        if (!is_dir($root)) {
            return [];
        }

        $projects = [];
        $entries = scandir($root);
        foreach ($entries as $entry) {
            if ($entry === '.' || $entry === '..') continue;
            $project = $this->findByUuid($entry);
            if ($project) {
                $projects[] = $project;
            }
        }

        usort($projects, fn($a, $b) => strcmp($b->createdAt, $a->createdAt));
        return $projects;
    }

    public function delete(string $uuid): bool
    {
        $dir = $this->storageService->getProjectDir($uuid);
        if (!is_dir($dir)) {
            return false;
        }

        $this->deleteDirectoryRecursively($dir);
        return !is_dir($dir);
    }

    protected function deleteDirectoryRecursively(string $dir): void
    {
        if (!is_dir($dir)) return;
        $files = array_diff(scandir($dir) ?: [], ['.', '..']);
        foreach ($files as $file) {
            $path = $dir . DIRECTORY_SEPARATOR . $file;
            is_dir($path) ? $this->deleteDirectoryRecursively($path) : @unlink($path);
        }
        @rmdir($dir);
    }

    protected function getMetaPath(string $uuid): string
    {
        return $this->storageService->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'project.json';
    }
}
