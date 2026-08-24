<?php

declare(strict_types=1);

namespace App\Contracts;

use App\DTOs\ConversionInputDto;

/**
 * Interface cho các OMR Engine (Audiveris, etc.)
 */
interface OmrEngineInterface
{
    /**
     * Nhận dạng bản nhạc từ file đầu vào
     *
     * @param ConversionInputDto $input
     * @return array{success: bool, rawMusicXmlPath: string, omrFilePath: string, logs: string}
     */
    public function transcribe(ConversionInputDto $input): array;
}
