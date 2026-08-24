<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';
require_once __DIR__ . '/MusicXmlIndexService.php';
require_once dirname(__DIR__) . '/DTOs/NoteEditDto.php';

use App\Services\StorageService;
use App\Services\MusicXmlIndexService;
use App\DTOs\NoteEditDto;
use DOMDocument;
use DOMElement;
use DOMXPath;

/**
 * Service xử lý sửa nốt nhạc chính xác theo Stable Locator và quy chuẩn MusicXML 4.0
 */
class NoteService
{
    protected StorageService $storageService;
    protected MusicXmlIndexService $indexService;

    public function __construct(?StorageService $storageService = null, ?MusicXmlIndexService $indexService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
        $this->indexService = $indexService ?: new MusicXmlIndexService();
    }

    /**
     * Cập nhật thông tin nốt nhạc chính xác và lưu nguyên tử (Atomic Write)
     */
    public function updateNote(string $xmlPath, NoteEditDto $noteDto): bool
    {
        if (!file_exists($xmlPath)) return false;

        $doc = new DOMDocument();
        $doc->preserveWhiteSpace = false;
        $doc->formatOutput = true;
        if (!@$doc->load($xmlPath)) return false;

        $xpath = new DOMXPath($doc);

        // 1. Định vị nốt chính xác bằng Locator System
        $locator = sprintf(
            "%s:M%d:S%d:V%d:N%d",
            $noteDto->partId,
            $noteDto->measureNumber,
            $noteDto->staff,
            $noteDto->voice,
            $noteDto->noteIndex
        );

        $targetNote = $this->indexService->resolveNoteNode(
            $xpath,
            $locator,
            $noteDto->measureNumber,
            $noteDto->voice,
            $noteDto->staff,
            $noteDto->noteIndex
        );

        if (!$targetNote instanceof DOMElement) {
            return false;
        }

        // 2. Lấy divisions của ô nhịp hoặc part
        $divisions = 1;
        $divNodes = $xpath->query("//part[@id='{$noteDto->partId}']/measure/attributes/divisions");
        if ($divNodes && $divNodes->length > 0) {
            $divisions = max(1, (int)$divNodes->item(0)->nodeValue);
        }

        // 3. Cập nhật Pitch & Alter
        if (!$noteDto->isRest) {
            // Đảm bảo không có thẻ rest
            $rests = $targetNote->getElementsByTagName('rest');
            while ($rests->length > 0) {
                $targetNote->removeChild($rests->item(0));
            }

            $pitchNodes = $targetNote->getElementsByTagName('pitch');
            if ($pitchNodes->length > 0) {
                $pitchElem = $pitchNodes->item(0);
            } else {
                $pitchElem = $doc->createElement('pitch');
                $targetNote->insertBefore($pitchElem, $targetNote->firstChild);
            }

            // Step
            $stepNodes = $pitchElem->getElementsByTagName('step');
            if ($stepNodes->length > 0) {
                $stepNodes->item(0)->nodeValue = strtoupper($noteDto->step);
            } else {
                $pitchElem->appendChild($doc->createElement('step', strtoupper($noteDto->step)));
            }

            // Octave
            $octNodes = $pitchElem->getElementsByTagName('octave');
            if ($octNodes->length > 0) {
                $octNodes->item(0)->nodeValue = (string)$noteDto->octave;
            } else {
                $pitchElem->appendChild($doc->createElement('octave', (string)$noteDto->octave));
            }

            // Alter (<alter>1</alter> cho sharp, <alter>-1</alter> cho flat)
            $alterNodes = $pitchElem->getElementsByTagName('root-alter');
            if ($alterNodes->length === 0) {
                $alterNodes = $pitchElem->getElementsByTagName('alter');
            }

            $alterValue = null;
            if ($noteDto->accidental === 'sharp' || $noteDto->accidental === '#') {
                $alterValue = '1';
            } elseif ($noteDto->accidental === 'flat' || $noteDto->accidental === 'b') {
                $alterValue = '-1';
            }

            if ($alterValue !== null) {
                if ($alterNodes->length > 0) {
                    $alterNodes->item(0)->nodeValue = $alterValue;
                } else {
                    $pitchElem->appendChild($doc->createElement('alter', $alterValue));
                }
            } else {
                // Xóa alter nếu là nốt bình thường (natural)
                while ($alterNodes->length > 0) {
                    $pitchElem->removeChild($alterNodes->item(0));
                }
            }

            // Cập nhật thẻ <accidental>
            $accNodes = $targetNote->getElementsByTagName('accidental');
            if ($noteDto->accidental) {
                $accName = ($noteDto->accidental === '#') ? 'sharp' : (($noteDto->accidental === 'b') ? 'flat' : $noteDto->accidental);
                if ($accNodes->length > 0) {
                    $accNodes->item(0)->nodeValue = $accName;
                } else {
                    $targetNote->appendChild($doc->createElement('accidental', $accName));
                }
            } else {
                while ($accNodes->length > 0) {
                    $targetNote->removeChild($accNodes->item(0));
                }
            }
        } else {
            // Nốt lặng (Rest)
            $pitches = $targetNote->getElementsByTagName('pitch');
            while ($pitches->length > 0) {
                $targetNote->removeChild($pitches->item(0));
            }
            if ($targetNote->getElementsByTagName('rest')->length === 0) {
                $targetNote->insertBefore($doc->createElement('rest'), $targetNote->firstChild);
            }
        }

        // 4. Cập nhật Type & Duration
        $durationMultiplier = match (strtolower($noteDto->duration)) {
            'whole' => 4.0,
            'half' => 2.0,
            'quarter' => 1.0,
            'eighth' => 0.5,
            '16th' => 0.25,
            '32nd' => 0.125,
            default => 1.0,
        };

        if ($noteDto->isDotted) {
            $durationMultiplier *= 1.5;
            if ($targetNote->getElementsByTagName('dot')->length === 0) {
                $targetNote->appendChild($doc->createElement('dot'));
            }
        } else {
            $dots = $targetNote->getElementsByTagName('dot');
            while ($dots->length > 0) {
                $targetNote->removeChild($dots->item(0));
            }
        }

        $calcDuration = (int)round($divisions * $durationMultiplier);
        $durNodes = $targetNote->getElementsByTagName('duration');
        if ($durNodes->length > 0) {
            $durNodes->item(0)->nodeValue = (string)max(1, $calcDuration);
        }

        $typeNodes = $targetNote->getElementsByTagName('type');
        if ($typeNodes->length > 0) {
            $typeNodes->item(0)->nodeValue = strtolower($noteDto->duration);
        }

        // 5. Lưu nguyên tử (Atomic Write)
        $tempPath = $xmlPath . '.tmp';
        $saved = $doc->save($tempPath);
        if ($saved === false) {
            return false;
        }

        // Kiểm tra parse lại được trước khi ghi đè
        $verifyDoc = new DOMDocument();
        if (@$verifyDoc->load($tempPath)) {
            rename($tempPath, $xmlPath);
            return true;
        }

        @unlink($tempPath);
        return false;
    }

    /**
     * Alias method for updateNoteDetail
     */
    public function updateNoteDetail(string $xmlPath, NoteEditDto $noteDto): bool
    {
        return $this->updateNote($xmlPath, $noteDto);
    }
}
