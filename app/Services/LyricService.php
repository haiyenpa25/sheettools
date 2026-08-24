<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';
require_once dirname(__DIR__) . '/Contracts/MusicXmlPatcherInterface.php';
require_once dirname(__DIR__) . '/DTOs/LyricDto.php';
require_once dirname(__DIR__) . '/DTOs/HarmonyDto.php';
require_once dirname(__DIR__) . '/DTOs/NoteEditDto.php';

use App\Services\StorageService;
use App\Contracts\MusicXmlPatcherInterface;
use App\DTOs\LyricDto;
use App\DTOs\HarmonyDto;
use App\DTOs\NoteEditDto;

/**
 * Service xử lý nghiệp vụ chỉnh sửa lời bài hát
 */
class LyricService implements MusicXmlPatcherInterface
{
    protected StorageService $storageService;

    public function __construct(?StorageService $storageService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
    }

    /**
     * Cập nhật một âm tiết/từ lời bài hát trong MusicXML
     */
    public function updateLyric(string $xmlPath, LyricDto $lyric): bool
    {
        $patcherPy = dirname(__DIR__, 2) . '/workers/xml_tools/patcher.py';
        $payload = json_encode([
            'partId' => $lyric->partId,
            'measureNumber' => $lyric->measureNumber,
            'verseNumber' => $lyric->verseNumber,
            'text' => $lyric->text,
            'syllabic' => $lyric->syllabic,
        ]);

        $cmd = sprintf(
            'python %s --xml %s --action patch-lyric --payload %s 2>&1',
            escapeshellarg($patcherPy),
            escapeshellarg($xmlPath),
            escapeshellarg($payload)
        );

        $output = [];
        $exitCode = 0;
        @exec($cmd, $output, $exitCode);

        return $exitCode === 0;
    }

    public function updateHarmony(string $xmlPath, HarmonyDto $harmony): bool
    {
        // Gọi HarmonyService
        return true;
    }

    public function updateNote(string $xmlPath, NoteEditDto $note): bool
    {
        // Gọi NoteService
        return true;
    }

    /**
     * Cập nhật hàng loạt (Bulk lyrics) cho 1 verse
     */
    public function bulkUpdateVerse(string $xmlPath, string $partId, int $verseNum, array $lyricsList): bool
    {
        foreach ($lyricsList as $idx => $text) {
            $dto = new LyricDto(
                id: uniqid('lyr_'),
                partId: $partId,
                staff: 1,
                measureNumber: $idx + 1,
                voice: 1,
                noteId: "n_{$idx}",
                verseNumber: $verseNum,
                text: $text
            );
            $this->updateLyric($xmlPath, $dto);
        }
        return true;
    }
}
