<?php

declare(strict_types=1);

namespace App\Services;

require_once dirname(__DIR__) . '/DTOs/HarmonyDto.php';

use App\DTOs\HarmonyDto;

/**
 * Bộ phân tích cú pháp hợp âm chuyên sâu (Full Chord Grammar & Alterations)
 */
class ChordParser
{
    /**
     * Phân tích chuỗi hợp âm tự do thành HarmonyDto chuẩn MusicXML
     */
    public function parse(string $chordStr, string $partId = 'P1', int $measure = 1, float $beatOffset = 0.0): HarmonyDto
    {
        $chordStr = trim($chordStr);
        $parts = explode('/', $chordStr);
        $mainChord = $parts[0];
        $bassPart = $parts[1] ?? null;

        // 1. Phân rã Root và Alter
        $rootStep = strtoupper($mainChord[0] ?? 'C');
        $rootAlter = null;
        $idx = 1;

        if (isset($mainChord[1]) && ($mainChord[1] === '#' || $mainChord[1] === 'b')) {
            $rootAlter = ($mainChord[1] === '#') ? '1' : '-1';
            $idx = 2;
        }

        $qualityStr = substr($mainChord, $idx);
        $kind = 'major';

        // 2. Nhận diện cấu trúc hợp âm mở rộng (Extended Chord Grammar)
        if ($qualityStr === '' || $qualityStr === 'M' || $qualityStr === 'maj') {
            $kind = 'major';
        } elseif ($qualityStr === 'm' || $qualityStr === 'min') {
            $kind = 'minor';
        } elseif ($qualityStr === '7' || $qualityStr === 'dom7') {
            $kind = 'dominant';
        } elseif ($qualityStr === 'maj7' || $qualityStr === 'M7' || $qualityStr === 'Δ') {
            $kind = 'major-seventh';
        } elseif ($qualityStr === 'm7' || $qualityStr === 'min7') {
            $kind = 'minor-seventh';
        } elseif ($qualityStr === 'm7b5' || $qualityStr === 'ø') {
            $kind = 'half-diminished';
        } elseif ($qualityStr === 'dim' || $qualityStr === 'o') {
            $kind = 'diminished';
        } elseif ($qualityStr === 'dim7' || $qualityStr === 'o7') {
            $kind = 'diminished-seventh';
        } elseif ($qualityStr === 'aug' || $qualityStr === '+') {
            $kind = 'augmented';
        } elseif ($qualityStr === 'sus2') {
            $kind = 'suspended-second';
        } elseif ($qualityStr === 'sus4' || $qualityStr === 'sus') {
            $kind = 'suspended-fourth';
        } elseif ($qualityStr === 'add9') {
            $kind = 'major';
        } elseif ($qualityStr === '9') {
            $kind = 'dominant-ninth';
        } elseif ($qualityStr === 'maj9' || $qualityStr === 'M9') {
            $kind = 'major-ninth';
        } elseif ($qualityStr === 'm9') {
            $kind = 'minor-ninth';
        } elseif ($qualityStr === '11') {
            $kind = 'dominant-11th';
        } elseif ($qualityStr === '13') {
            $kind = 'dominant-13th';
        } elseif (str_starts_with($qualityStr, 'm') && str_contains($qualityStr, '7')) {
            $kind = 'minor-seventh';
        }

        // 3. Phân rã Bass (Slash Chord)
        $bassStep = null;
        $bassAlter = null;
        if ($bassPart !== null && $bassPart !== '') {
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
}
