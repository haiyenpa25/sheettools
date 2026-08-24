<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';
require_once __DIR__ . '/MusicXmlIndexService.php';
require_once dirname(__DIR__) . '/Contracts/MusicXmlPatcherInterface.php';
require_once dirname(__DIR__) . '/DTOs/LyricDto.php';
require_once dirname(__DIR__) . '/DTOs/HarmonyDto.php';
require_once dirname(__DIR__) . '/DTOs/NoteEditDto.php';

use App\Services\StorageService;
use App\Services\MusicXmlIndexService;
use App\Contracts\MusicXmlPatcherInterface;
use App\DTOs\LyricDto;
use App\DTOs\HarmonyDto;
use App\DTOs\NoteEditDto;
use DOMDocument;
use DOMElement;
use DOMXPath;

/**
 * Service xử lý lời bài hát phân bổ chuẩn xác theo chuỗi nốt âm nhạc
 */
class LyricService implements MusicXmlPatcherInterface
{
    protected StorageService $storageService;
    protected MusicXmlIndexService $indexService;

    public function __construct(?StorageService $storageService = null, ?MusicXmlIndexService $indexService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
        $this->indexService = $indexService ?: new MusicXmlIndexService();
    }

    /**
     * Cập nhật một âm tiết/từ lời bài hát trong MusicXML theo locator
     */
    public function updateLyric(string $xmlPath, LyricDto $lyric): bool
    {
        if (!file_exists($xmlPath)) return false;

        $doc = new DOMDocument();
        $doc->preserveWhiteSpace = false;
        $doc->formatOutput = true;
        if (!@$doc->load($xmlPath)) return false;

        $xpath = new DOMXPath($doc);

        $noteElem = $this->indexService->resolveNoteNode(
            $xpath,
            $lyric->noteId ?: $lyric->partId,
            $lyric->measureNumber,
            $lyric->voice,
            $lyric->staff,
            1
        );

        if (!$noteElem instanceof DOMElement) {
            return false;
        }

        // Tìm hoặc tạo thẻ <lyric number="verseNumber">
        $existingLyrics = $noteElem->getElementsByTagName('lyric');
        $targetLyric = null;

        for ($i = 0; $i < $existingLyrics->length; $i++) {
            $item = $existingLyrics->item($i);
            if ($item instanceof DOMElement && (int)$item->getAttribute('number') === $lyric->verseNumber) {
                $targetLyric = $item;
                break;
            }
        }

        if (!$targetLyric) {
            $targetLyric = $doc->createElement('lyric');
            $targetLyric->setAttribute('number', (string)$lyric->verseNumber);
            $noteElem->appendChild($targetLyric);
        }

        // Cập nhật text
        $textNodes = $targetLyric->getElementsByTagName('text');
        if ($textNodes->length > 0) {
            $textNodes->item(0)->nodeValue = $lyric->text;
        } else {
            $targetLyric->appendChild($doc->createElement('text', $lyric->text));
        }

        // Cập nhật syllabic
        $syllabicNodes = $targetLyric->getElementsByTagName('syllabic');
        if ($syllabicNodes->length > 0) {
            $syllabicNodes->item(0)->nodeValue = $lyric->syllabic;
        } else {
            $targetLyric->insertBefore($doc->createElement('syllabic', $lyric->syllabic), $targetLyric->firstChild);
        }

        // Atomic write
        $tempPath = $xmlPath . '.tmp';
        if ($doc->save($tempPath)) {
            $verify = new DOMDocument();
            if (@$verify->load($tempPath)) {
                rename($tempPath, $xmlPath);
                return true;
            }
            @unlink($tempPath);
        }

        return false;
    }

    public function updateHarmony(string $xmlPath, HarmonyDto $harmony): bool
    {
        return true;
    }

    public function updateNote(string $xmlPath, NoteEditDto $note): bool
    {
        return true;
    }

    /**
     * Phân bổ lời bài hát hàng loạt (Bulk Syllable Distribution) theo chuỗi nốt thực tế
     *
     * @param string $xmlPath
     * @param string $partId
     * @param int $verseNum
     * @param array<string> $syllablesList
     * @return bool
     */
    public function bulkUpdateVerse(string $xmlPath, string $partId, int $verseNum, array $syllablesList): bool
    {
        if (!file_exists($xmlPath) || empty($syllablesList)) return false;

        $doc = new DOMDocument();
        $doc->preserveWhiteSpace = false;
        $doc->formatOutput = true;
        if (!@$doc->load($xmlPath)) return false;

        $xpath = new DOMXPath($doc);
        $noteSequence = $this->indexService->getLyricCapableNotes($xpath, $partId);

        if (empty($noteSequence)) {
            return false;
        }

        $count = min(count($syllablesList), count($noteSequence));

        for ($i = 0; $i < $count; $i++) {
            $token = trim($syllablesList[$i]);
            $noteInfo = $noteSequence[$i];

            $dto = new LyricDto(
                id: uniqid('lyr_'),
                partId: $partId,
                staff: $noteInfo['staff'],
                measureNumber: $noteInfo['measure'],
                voice: $noteInfo['voice'],
                noteId: $noteInfo['locator'],
                verseNumber: $verseNum,
                text: $token,
                syllabic: str_ends_with($token, '-') ? 'begin' : 'single'
            );

            $this->updateLyric($xmlPath, $dto);
        }

        return true;
    }
}
