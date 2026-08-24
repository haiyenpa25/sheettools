<?php

declare(strict_types=1);

namespace App\Contracts;

/**
 * Interface cho việc kiểm định chất lượng và cú pháp nhạc lý của MusicXML
 */
interface MusicXmlValidatorInterface
{
    /**
     * @param string $xmlPath
     * @return array{isValid: bool, errors: array<string>, warnings: array<string>}
     */
    public function validate(string $xmlPath): array;
}
