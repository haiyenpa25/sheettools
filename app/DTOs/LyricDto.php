<?php

declare(strict_types=1);

namespace App\DTOs;

/**
 * Data Transfer Object cho một âm tiết/lời bài hát
 */
final readonly class LyricDto
{
    public function __construct(
        public string $id,
        public string $partId,
        public int $staff,
        public int $measureNumber,
        public int $voice,
        public string $noteId,
        public int $verseNumber,
        public string $text,
        public string $syllabic = 'single', // single, begin, middle, end
        public float $confidence = 1.0,
    ) {}
}
