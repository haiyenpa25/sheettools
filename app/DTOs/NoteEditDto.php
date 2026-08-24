<?php

declare(strict_types=1);

namespace App\DTOs;

/**
 * Data Transfer Object cho việc chỉnh sửa nốt nhanh
 */
final readonly class NoteEditDto
{
    public function __construct(
        public string $noteId,
        public string $partId,
        public int $measureNumber,
        public string $step,         // C, D, E, F, G, A, B
        public int $octave,          // 1..8
        public ?string $accidental = null, // sharp, flat, natural, etc.
        public string $duration = 'quarter', // whole, half, quarter, eighth, 16th
        public bool $isRest = false,
        public bool $isDotted = false,
        public int $voice = 1,
    ) {}
}
