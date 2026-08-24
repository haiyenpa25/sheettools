<?php

declare(strict_types=1);

namespace App\DTOs;

/**
 * Data Transfer Object cho tham số đầu vào chuyển đổi
 */
final readonly class ConversionInputDto
{
    public function __construct(
        public string $projectUuid,
        public string $sourceFilePath,
        public string $sourceFileName,
        public string $sourceType, // 'pdf', 'png', 'jpg'
        public string $language = 'vie+eng',
        public bool $detectLyrics = true,
        public bool $detectChords = true,
    ) {}
}
