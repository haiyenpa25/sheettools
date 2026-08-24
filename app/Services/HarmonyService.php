<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';
require_once dirname(__DIR__) . '/DTOs/HarmonyDto.php';

use App\Services\StorageService;
use App\DTOs\HarmonyDto;
use SimpleXMLElement;

/**
 * Service xử lý nghiệp vụ Hợp âm (<harmony>) và Slash Chord
 */
class HarmonyService
{
    protected StorageService $storageService;

    public function __construct(?StorageService $storageService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
    }

    /**
     * Phân rã chuỗi hợp âm tự do (như "G/B", "D7#5", "Am7") thành HarmonyDto
     */
    public function parseChordString(string $chordStr, string $partId = 'P1', int $measure = 1, float $beatOffset = 0.0): HarmonyDto
    {
        $chordStr = trim($chordStr);
        $parts = explode('/', $chordStr);
        $mainChord = $parts[0];
        $bassPart = $parts[1] ?? null;

        // Phân rã Root và Alter
        $rootStep = strtoupper($mainChord[0] ?? 'C');
        $rootAlter = null;
        $idx = 1;

        if (isset($mainChord[1]) && ($mainChord[1] === '#' || $mainChord[1] === 'b')) {
            $rootAlter = ($mainChord[1] === '#') ? '1' : '-1';
            $idx = 2;
        }

        $qualityStr = substr($mainChord, $idx);
        $kind = 'major';

        if (str_starts_with($qualityStr, 'm') && !str_starts_with($qualityStr, 'maj')) {
            $kind = str_contains($qualityStr, '7') ? 'minor-seventh' : 'minor';
        } elseif (str_starts_with($qualityStr, '7')) {
            $kind = 'dominant';
        } elseif (str_starts_with($qualityStr, 'maj7')) {
            $kind = 'major-seventh';
        } elseif (str_starts_with($qualityStr, 'dim')) {
            $kind = 'diminished';
        } elseif (str_starts_with($qualityStr, 'sus4')) {
            $kind = 'suspended-fourth';
        }

        // Bass part
        $bassStep = null;
        $bassAlter = null;
        if ($bassPart) {
            $bassStep = strtoupper($bassPart[0]);
            if (isset($bassPart[1])) {
                $bassAlter = ($bassPart[1] === '#') ? '1' : (($bassPart[1] === 'b') ? '-1' : null);
            }
        }

        return new HarmonyDto(
            id: uniqid('harm_'),
            partId: $partId,
            measureNumber: $measure,
            beatOffset: $beatOffset,
            rootStep: $rootStep,
            rootAlter: $rootAlter,
            kind: $kind,
            bassStep: $bassStep,
            bassAlter: $bassAlter,
            displayText: $chordStr
        );
    }

    /**
     * Thêm hoặc sửa thẻ <harmony> vào ô nhịp trong MusicXML
     */
    public function saveHarmony(string $xmlPath, HarmonyDto $harmony): bool
    {
        if (!file_exists($xmlPath)) return false;

        $doc = new \DOMDocument();
        $doc->preserveWhiteSpace = false;
        $doc->formatOutput = true;
        if (!@$doc->load($xmlPath)) return false;

        $xpath = new \DOMXPath($doc);
        $measures = $xpath->query("//part[@id='{$harmony->partId}']/measure[@number='{$harmony->measureNumber}']");

        if ($measures->length === 0) return false;
        $measureNode = $measures->item(0);

        // Tạo thẻ harmony
        $harmElem = $doc->createElement('harmony');
        
        $rootElem = $doc->createElement('root');
        $rootStepElem = $doc->createElement('root-step', $harmony->rootStep);
        $rootElem->appendChild($rootStepElem);
        if ($harmony->rootAlter !== null) {
            $rootElem->appendChild($doc->createElement('root-alter', $harmony->rootAlter));
        }
        $harmElem->appendChild($rootElem);

        $kindElem = $doc->createElement('kind', $harmony->kind);
        if ($harmony->displayText) {
            $kindElem->setAttribute('text', $harmony->displayText);
        }
        $harmElem->appendChild($kindElem);

        if ($harmony->bassStep) {
            $bassElem = $doc->createElement('bass');
            $bassElem->appendChild($doc->createElement('bass-step', $harmony->bassStep));
            if ($harmony->bassAlter !== null) {
                $bassElem->appendChild($doc->createElement('bass-alter', $harmony->bassAlter));
            }
            $harmElem->appendChild($bassElem);
        }

        if ($harmony->beatOffset > 0) {
            $harmElem->appendChild($doc->createElement('offset', (string)$harmony->beatOffset));
        }

        // Chèn vào trước nốt đầu tiên của measure
        $notes = $measureNode->getElementsByTagName('note');
        if ($notes->length > 0) {
            $measureNode->insertBefore($harmElem, $notes->item(0));
        } else {
            $measureNode->appendChild($harmElem);
        }

        return (bool)$doc->save($xmlPath);
    }
}
