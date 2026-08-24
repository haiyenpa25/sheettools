<?php

declare(strict_types=1);

namespace App\Contracts;

use App\DTOs\ConversionInputDto;
use App\DTOs\OmrResultDto;

/**
 * Interface cho các OMR Engine (Audiveris, Oemer, etc.)
 */
interface OmrEngineInterface
{
    /**
     * Nhận dạng bản nhạc từ file đầu vào và trả về kết quả quét artifact thực tế.
     *
     * @param ConversionInputDto $input
     * @return OmrResultDto
     */
    public function transcribe(ConversionInputDto $input): OmrResultDto;
}
