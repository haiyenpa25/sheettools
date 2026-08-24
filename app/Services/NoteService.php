<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';
require_once dirname(__DIR__) . '/DTOs/NoteEditDto.php';

use App\Services\StorageService;
use App\DTOs\NoteEditDto;
use DOMDocument;
use DOMXPath;

/**
 * Service xử lý sửa nhanh nốt nhạc (pitch, octave, duration, accidental, voice)
 */
class NoteService
{
    protected StorageService $storageService;

    public function __construct(?StorageService $storageService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
    }

    public function updateNote(string $xmlPath, NoteEditDto $noteDto): bool
    {
        if (!file_exists($xmlPath)) return false;

        $doc = new DOMDocument();
        $doc->preserveWhiteSpace = false;
        $doc->formatOutput = true;
        if (!@$doc->load($xmlPath)) return false;

        $xpath = new DOMXPath($doc);
        $measures = $xpath->query("//part[@id='{$noteDto->partId}']/measure[@number='{$noteDto->measureNumber}']");
        if ($measures->length === 0) return false;

        $measure = $measures->item(0);
        $notes = $measure->getElementsByTagName('note');
        if ($notes->length === 0) return false;

        // Chọn nốt mục tiêu
        $targetNote = $notes->item(0);

        // Cập nhật Pitch
        $pitchNodes = $targetNote->getElementsByTagName('pitch');
        if ($pitchNodes->length > 0) {
            $pitchNode = $pitchNodes->item(0);
            $stepNodes = $pitchNode->getElementsByTagName('step');
            if ($stepNodes->length > 0) {
                $stepNodes->item(0)->nodeValue = $noteDto->step;
            }
            $octaveNodes = $pitchNode->getElementsByTagName('octave');
            if ($octaveNodes->length > 0) {
                $octaveNodes->item(0)->nodeValue = (string)$noteDto->octave;
            }
        }

        // Cập nhật Type/Duration
        $typeNodes = $targetNote->getElementsByTagName('type');
        if ($typeNodes->length > 0) {
            $typeNodes->item(0)->nodeValue = $noteDto->duration;
        }

        // Cập nhật Dấu hóa Accidental
        if ($noteDto->accidental) {
            $accNodes = $targetNote->getElementsByTagName('accidental');
            if ($accNodes->length > 0) {
                $accNodes->item(0)->nodeValue = $noteDto->accidental;
            } else {
                $accElem = $doc->createElement('accidental', $noteDto->accidental);
                $targetNote->appendChild($accElem);
            }
        }

        return (bool)$doc->save($xmlPath);
    }
}
