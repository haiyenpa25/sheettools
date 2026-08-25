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

    // ═════════════════════════════════════════════════════════════════════════
    // ─── SONGBOOKS & CATEGORIES HIERARCHY ───
    // ═════════════════════════════════════════════════════════════════════════

    public function getSongbooksRoot(): string
    {
        $dir = $this->storageRoot . DIRECTORY_SEPARATOR . 'songbooks';
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        return $dir;
    }

    public function getSongbookDir(string $categorySlug): string
    {
        $dir = $this->getSongbooksRoot() . DIRECTORY_SEPARATOR . $categorySlug;
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        return $dir;
    }

    public function saveSongbookItem(string $categorySlug, string $songSlug, array $files, array $metadata = []): string
    {
        $songDir = $this->getSongbookDir($categorySlug) . DIRECTORY_SEPARATOR . $songSlug;
        if (!is_dir($songDir)) {
            mkdir($songDir, 0755, true);
        }

        foreach ($files as $filename => $content) {
            file_put_contents($songDir . DIRECTORY_SEPARATOR . $filename, $content);
        }

        if (!empty($metadata)) {
            file_put_contents(
                $songDir . DIRECTORY_SEPARATOR . 'metadata.json',
                json_encode($metadata, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
            );
        }

        return $songDir;
    }

    public function listSongbooks(): array
    {
        $root = $this->getSongbooksRoot();
        $items = [];
        if (!is_dir($root)) return $items;

        $dirs = scandir($root);
        foreach ($dirs as $d) {
            if ($d === '.' || $d === '..' || !is_dir($root . DIRECTORY_SEPARATOR . $d)) continue;
            $bookDir = $root . DIRECTORY_SEPARATOR . $d;
            $songDirs = array_filter(scandir($bookDir), fn($s) => $s !== '.' && $s !== '..' && is_dir($bookDir . DIRECTORY_SEPARATOR . $s));
            $items[] = [
                'slug' => $d,
                'name' => ucwords(str_replace('-', ' ', $d)),
                'path' => $bookDir,
                'total_songs' => count($songDirs),
            ];
        }

        return $items;
    }
}
