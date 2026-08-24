<?php

declare(strict_types=1);

namespace App\Contracts;

use App\DTOs\LyricDto;
use App\DTOs\HarmonyDto;
use App\DTOs\NoteEditDto;

/**
 * Interface cho dịch vụ can thiệp nhanh (patch) MusicXML
 */
interface MusicXmlPatcherInterface
{
    public function updateLyric(string $xmlPath, LyricDto $lyric): bool;

    public function updateHarmony(string $xmlPath, HarmonyDto $harmony): bool;

    public function updateNote(string $xmlPath, NoteEditDto $note): bool;
}
