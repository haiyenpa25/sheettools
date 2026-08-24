<?php

declare(strict_types=1);

namespace App\Services;

require_once dirname(__DIR__) . '/DTOs/LyricDto.php';
require_once dirname(__DIR__) . '/DTOs/HarmonyDto.php';

use App\DTOs\LyricDto;
use App\DTOs\HarmonyDto;
use SimpleXMLElement;

/**
 * Service phân tích cú pháp và trích xuất cấu trúc MusicXML
 */
class MusicXmlService
{
    /**
     * Trích xuất danh sách tất cả các lời (lyrics) phân theo từng Verse
     *
     * @param string $xmlContent
     * @return array<int, array<int, LyricDto>> Danh sách verse => [LyricDto]
     */
    public function extractLyrics(string $xmlContent): array
    {
        $xml = @simplexml_load_string($xmlContent);
        if (!$xml) return [];

        $verses = [];

        foreach ($xml->part as $part) {
            $partId = (string)$part['id'];
            foreach ($part->measure as $measure) {
                $measureNum = (int)$measure['number'];
                $noteIndex = 0;

                foreach ($measure->note as $note) {
                    $noteId = (string)($note['id'] ?? "n_{$measureNum}_{$noteIndex}");
                    $voice = (int)($note->voice ?? 1);
                    $staff = (int)($note->staff ?? 1);

                    if (isset($note->lyric)) {
                        foreach ($note->lyric as $lyric) {
                            $verseNum = (int)($lyric['number'] ?? 1);
                            $text = (string)($lyric->text ?? '');
                            $syllabic = (string)($lyric->syllabic ?? 'single');

                            $dto = new LyricDto(
                                id: uniqid("lyr_"),
                                partId: $partId,
                                staff: $staff,
                                measureNumber: $measureNum,
                                voice: $voice,
                                noteId: $noteId,
                                verseNumber: $verseNum,
                                text: $text,
                                syllabic: $syllabic
                            );

                            $verses[$verseNum][] = $dto;
                        }
                    }
                    $noteIndex++;
                }
            }
        }

        ksort($verses);
        return $verses;
    }

    /**
     * Trích xuất danh sách tất cả các hợp âm (<harmony>)
     *
     * @param string $xmlContent
     * @return array<int, HarmonyDto>
     */
    public function extractHarmonies(string $xmlContent): array
    {
        $xml = @simplexml_load_string($xmlContent);
        if (!$xml) return [];

        $harmonies = [];

        foreach ($xml->part as $part) {
            $partId = (string)$part['id'];
            foreach ($part->measure as $measure) {
                $measureNum = (int)$measure['number'];

                foreach ($measure->harmony as $harmony) {
                    $rootStep = (string)($harmony->root->{'root-step'} ?? 'C');
                    $rootAlter = isset($harmony->root->{'root-alter'}) ? (string)$harmony->root->{'root-alter'} : null;
                    $kind = (string)($harmony->kind ?? 'major');
                    $kindText = (string)($harmony->kind['text'] ?? $kind);

                    $bassStep = isset($harmony->bass) ? (string)($harmony->bass->{'bass-step'} ?? '') : null;
                    $bassAlter = isset($harmony->bass->{'bass-alter'}) ? (string)$harmony->bass->{'bass-alter'} : null;

                    $offset = isset($harmony->offset) ? (float)$harmony->offset : 0.0;

                    // Xây dựng displayText
                    $display = $rootStep;
                    if ($rootAlter === '1') $display .= '#';
                    $harmonies[] = new HarmonyDto(
                        id: uniqid('harm_'),
                        partId: $partId,
                        measureNumber: $measureNum,
                        beatOffset: $offset,
                        rootStep: $rootStep,
                        rootAlter: $rootAlter,
                        kind: $kind,
                        bassStep: $bassStep,
                        bassAlter: $bassAlter,
                        displayText: $display
                    );
                }
            }
        }

        return $harmonies;
    }

    /**
     * Trích xuất thông tin tiêu đề, tác giả từ MusicXML
     */
    public function extractMetadata(string $xmlContent): array
    {
        $xml = @simplexml_load_string($xmlContent);
        if (!$xml) {
            return [
                'title' => '',
                'composer' => '',
                'lyricist' => '',
                'tempo' => 100,
            ];
        }

        $title = (string)($xml->{'movement-title'} ?? ($xml->work->{'work-title'} ?? ''));
        $composer = '';
        $lyricist = '';

        if (isset($xml->identification->creator)) {
            foreach ($xml->identification->creator as $creator) {
                $type = (string)($creator['type'] ?? '');
                if ($type === 'composer') {
                    $composer = (string)$creator;
                } elseif ($type === 'lyricist' || $type === 'poet') {
                    $lyricist = (string)$creator;
                }
            }
        }

        return [
            'title' => trim($title),
            'composer' => trim($composer),
            'lyricist' => trim($lyricist),
            'tempo' => 100,
        ];
    }
}
