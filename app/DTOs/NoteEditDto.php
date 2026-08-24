<?php

declare(strict_types=1);

namespace App\DTOs;

/**
 * Data Transfer Object cho việc chỉnh sửa nốt theo Entity Locator & Thuộc tính âm nhạc
 */
final readonly class NoteEditDto
{
    public function __construct(
        public string $partId = 'P1',
        public int $measureNumber = 1,
        public string $step = 'C',             // C, D, E, F, G, A, B
        public int $octave = 4,              // 1..8
        public ?string $accidental = null,   // sharp, flat, natural, etc.
        public string $duration = 'quarter', // whole, half, quarter, eighth, 16th
        public bool $isRest = false,
        public bool $isDotted = false,
        public int $voice = 1,
        public int $staff = 1,
        public int $noteIndex = 1,
        public ?string $noteId = null
    ) {}
}
