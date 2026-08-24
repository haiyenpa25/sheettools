<?php

declare(strict_types=1);

namespace App\Services;

use DOMDocument;
use DOMElement;
use DOMXPath;

/**
 * Service quản lý định vị đối tượng âm nhạc ổn định (Stable Music Entity Locator)
 */
class MusicXmlIndexService
{
    /**
     * Tìm DOMElement của Note dựa trên chuỗi locator hoặc các thuộc tính
     */
    public function resolveNoteNode(DOMXPath $xpath, string $locatorOrPartId, ?int $measure = null, ?int $voice = 1, ?int $staff = 1, ?int $noteOrdinal = 1): ?DOMElement
    {
        // Phân rã nếu truyền vào chuỗi locator dạng "P1:M1:S1:V1:N1"
        if (str_contains($locatorOrPartId, ':')) {
            $parts = explode(':', $locatorOrPartId);
            $partId = $parts[0];
            $measure = isset($parts[1]) ? (int)preg_replace('/\D/', '', $parts[1]) : 1;
            $staff = isset($parts[2]) ? (int)preg_replace('/\D/', '', $parts[2]) : 1;
            $voice = isset($parts[3]) ? (int)preg_replace('/\D/', '', $parts[3]) : 1;
            $noteOrdinal = isset($parts[4]) ? (int)preg_replace('/\D/', '', $parts[4]) : 1;
        } else {
            $partId = $locatorOrPartId;
        }

        $cleanPart = ltrim($partId, 'P');
        $query = sprintf(
            "//part[@id='%s' or @id='P%s' or @id='%s']/measure[@number='%d']/note",
            $partId,
            $cleanPart,
            $cleanPart,
            $measure
        );

        $nodes = $xpath->query($query);
        if (!$nodes || $nodes->length === 0) {
            // Fallback: Tìm measure không phân biệt part
            $nodes = $xpath->query("//measure[@number='{$measure}']/note");
        }

        if (!$nodes || $nodes->length === 0) {
            return null;
        }

        // Lọc theo voice và staff nếu có
        $matchedNotes = [];
        for ($i = 0; $i < $nodes->length; $i++) {
            $item = $nodes->item($i);
            if ($item instanceof DOMElement) {
                // Bỏ qua nốt phụ của hợp âm (chord note 2+)
                if ($item->getElementsByTagName('chord')->length > 0) {
                    continue;
                }

                $itemVoice = (int)($item->getElementsByTagName('voice')->item(0)?->nodeValue ?? 1);
                $itemStaff = (int)($item->getElementsByTagName('staff')->item(0)?->nodeValue ?? 1);

                if ($itemVoice === $voice && $itemStaff === $staff) {
                    $matchedNotes[] = $item;
                }
            }
        }

        $targetIndex = max(0, $noteOrdinal - 1);
        if (!empty($matchedNotes) && isset($matchedNotes[$targetIndex])) {
            return $matchedNotes[$targetIndex];
        }

        // Fallback: trả về note thứ targetIndex trong measure
        return $nodes->item(min($targetIndex, $nodes->length - 1)) instanceof DOMElement
            ? $nodes->item(min($targetIndex, $nodes->length - 1))
            : null;
    }

    /**
     * Lấy danh sách toàn bộ nốt có thể gắn lời (Lyric-capable note sequence)
     *
     * @return array<int, array{locator: string, measure: int, voice: int, staff: int, noteIndex: int, pitch: string}>
     */
    public function getLyricCapableNotes(DOMXPath $xpath, string $partId = 'P1'): array
    {
        $cleanPart = ltrim($partId, 'P');
        $measures = $xpath->query("//part[@id='{$partId}' or @id='P{$cleanPart}' or @id='{$cleanPart}']/measure");
        if (!$measures || $measures->length === 0) {
            $measures = $xpath->query("//measure");
        }
        if (!$measures) return [];

        $sequence = [];

        for ($m = 0; $m < $measures->length; $m++) {
            $measureElem = $measures->item($m);
            if (!$measureElem instanceof DOMElement) continue;

            $measureNum = (int)$measureElem->getAttribute('number');
            $notes = $measureElem->getElementsByTagName('note');
            $ordinal = 1;

            for ($n = 0; $n < $notes->length; $n++) {
                $noteElem = $notes->item($n);
                if (!$noteElem instanceof DOMElement) continue;

                // Bỏ qua nốt dấu lặng (rest) và nốt phụ thuộc hợp âm (chord note 2+)
                $isRest = $noteElem->getElementsByTagName('rest')->length > 0;
                $isChord = $noteElem->getElementsByTagName('chord')->length > 0;

                if ($isRest || $isChord) {
                    continue;
                }

                $voice = (int)($noteElem->getElementsByTagName('voice')->item(0)?->nodeValue ?? 1);
                $staff = (int)($noteElem->getElementsByTagName('staff')->item(0)?->nodeValue ?? 1);
                $step = $noteElem->getElementsByTagName('step')->item(0)?->nodeValue ?? 'C';
                $octave = $noteElem->getElementsByTagName('octave')->item(0)?->nodeValue ?? '4';

                $locator = sprintf("%s:M%d:S%d:V%d:N%d", $partId, $measureNum, $staff, $voice, $ordinal);

                $sequence[] = [
                    'locator' => $locator,
                    'measure' => $measureNum,
                    'voice' => $voice,
                    'staff' => $staff,
                    'noteIndex' => $ordinal,
                    'pitch' => "{$step}{$octave}"
                ];

                $ordinal++;
            }
        }

        return $sequence;
    }
}
