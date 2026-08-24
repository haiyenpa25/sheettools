<?php

declare(strict_types=1);

namespace App\DTOs;

/**
 * Result DTO returned by OmrEngineInterface implementations.
 */
class OmrResultDto
{
    /**
     * @param bool $success Whether OMR succeeded and valid MusicXML exists
     * @param string|null $musicXmlPath Absolute path to canonical raw.musicxml if created
     * @param string|null $omrPath Absolute path to source.omr if created
     * @param array<string> $generatedArtifacts List of all generated files
     * @param int $exitCode Process exit code
     * @param string $logs Standard output / error logs
     * @param array<string> $warnings Non-fatal warnings encountered
     */
    public function __construct(
        public bool $success,
        public ?string $musicXmlPath = null,
        public ?string $omrPath = null,
        public array $generatedArtifacts = [],
        public int $exitCode = 0,
        public string $logs = '',
        public array $warnings = []
    ) {}
}
