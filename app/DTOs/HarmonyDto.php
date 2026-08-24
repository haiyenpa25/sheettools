<?php

declare(strict_types=1);

namespace App\DTOs;

/**
 * Data Transfer Object cho Hợp âm (<harmony>)
 */
final readonly class HarmonyDto
{
    public function __construct(
        public string $id,
        public string $partId,
        public int $measureNumber,
        public float $beatOffset,
        public string $rootStep,       // C, D, E, F, G, A, B
        public ?string $rootAlter,     // #, b, or null
        public string $kind,           // major, minor, dominant, diminished, etc.
        public ?string $bassStep = null, // C, D, E... for slash chords
        public ?string $bassAlter = null,
        public ?string $displayText = null, // e.g. "G/B", "Am7"
    ) {}
}
