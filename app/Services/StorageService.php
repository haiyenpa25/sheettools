<?php

declare(strict_types=1);

namespace App\Services;

/**
 * Service quản lý cấu trúc lưu trữ phân tầng bất biến của dự án chuyển đổi
 * storage/projects/{uuid}/...
 */
class StorageService
{
    protected string $storageRoot;

    public function __construct(?string $storageRoot = null)
    {
        $this->storageRoot = $storageRoot ?: dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'storage';
    }

    public function getProjectsRoot(): string
    {
        return $this->storageRoot . DIRECTORY_SEPARATOR . 'projects';
    }

    public function getProjectDir(string $uuid): string
    {
        return $this->getProjectsRoot() . DIRECTORY_SEPARATOR . $uuid;
    }

    /**
     * Khởi tạo toàn bộ cấu trúc thư mục con cho 1 project UUID
     *
     * @param string $uuid
     * @return array<string, string>
     */
    public function initProjectDirs(string $uuid): array
    {
        $base = $this->getProjectDir($uuid);
        $dirs = [
            'base' => $base,
            'source' => $base . DIRECTORY_SEPARATOR . 'source',
            'pages' => $base . DIRECTORY_SEPARATOR . 'pages',
            'omr' => $base . DIRECTORY_SEPARATOR . 'omr',
            'musicxml' => $base . DIRECTORY_SEPARATOR . 'musicxml',
            'logs' => $base . DIRECTORY_SEPARATOR . 'logs',
        ];

        foreach ($dirs as $dir) {
            if (!is_dir($dir)) {
                mkdir($dir, 0755, true);
            }
        }

        return $dirs;
    }

    public function getSourcePath(string $uuid, string $filename): string
    {
        return $this->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'source' . DIRECTORY_SEPARATOR . $filename;
    }

    public function getPagesDir(string $uuid): string
    {
        return $this->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'pages';
    }

    public function getOmrPath(string $uuid): string
    {
        return $this->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'omr' . DIRECTORY_SEPARATOR . 'source.omr';
    }

    public function getRawMusicXmlPath(string $uuid): string
    {
        return $this->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'musicxml' . DIRECTORY_SEPARATOR . 'raw.musicxml';
    }

    public function getCurrentMusicXmlPath(string $uuid): string
    {
        return $this->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'musicxml' . DIRECTORY_SEPARATOR . 'current.musicxml';
    }

    public function getFinalMusicXmlPath(string $uuid): string
    {
        return $this->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'musicxml' . DIRECTORY_SEPARATOR . 'final.musicxml';
    }

    public function getLogPath(string $uuid, string $logName = 'audiveris'): string
    {
        return $this->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'logs' . DIRECTORY_SEPARATOR . $logName . '.log';
    }

    /**
     * Lưu raw.musicxml và tự động nhân bản sang current.musicxml cho lần đầu nhận dạng
     */
    public function saveRawMusicXml(string $uuid, string $content): void
    {
        $this->initProjectDirs($uuid);
        $rawPath = $this->getRawMusicXmlPath($uuid);
        $curPath = $this->getCurrentMusicXmlPath($uuid);

        file_put_contents($rawPath, $content);
        if (!file_exists($curPath)) {
            file_put_contents($curPath, $content);
        }
    }

    /**
     * Cập nhật bản current.musicxml sau khi người dùng sửa lời/hợp âm/nốt
     */
    public function saveCurrentMusicXml(string $uuid, string $content): void
    {
        $this->initProjectDirs($uuid);
        $curPath = $this->getCurrentMusicXmlPath($uuid);
        file_put_contents($curPath, $content);
    }
}
