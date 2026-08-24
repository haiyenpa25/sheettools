<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';
require_once __DIR__ . '/ChordParser.php';
require_once __DIR__ . '/HarmonyXmlWriter.php';
require_once dirname(__DIR__) . '/DTOs/HarmonyDto.php';

use App\Services\StorageService;
use App\Services\ChordParser;
use App\Services\HarmonyXmlWriter;
use App\DTOs\HarmonyDto;

/**
 * Service xử lý nghiệp vụ Hợp âm (<harmony>) và Slash Chord
 */
class HarmonyService
{
    protected StorageService $storageService;
    protected ChordParser $chordParser;
    protected HarmonyXmlWriter $harmonyWriter;

    public function __construct(
        ?StorageService $storageService = null,
        ?ChordParser $chordParser = null,
        ?HarmonyXmlWriter $harmonyWriter = null
    ) {
        $this->storageService = $storageService ?: new StorageService();
        $this->chordParser = $chordParser ?: new ChordParser();
        $this->harmonyWriter = $harmonyWriter ?: new HarmonyXmlWriter();
    }

    /**
     * Phân rã chuỗi hợp âm tự do thành HarmonyDto
     */
    public function parseChordString(string $chordStr, string $partId = 'P1', int $measure = 1, float $beatOffset = 0.0): HarmonyDto
    {
        return $this->chordParser->parse($chordStr, $partId, $measure, $beatOffset);
    }

    /**
     * Thêm hoặc sửa thẻ <harmony> vào ô nhịp trong MusicXML
     */
    public function saveHarmony(string $xmlPath, HarmonyDto $harmony): bool
    {
        return $this->harmonyWriter->writeHarmony($xmlPath, $harmony);
    }

    /**
     * Alias method for addOrUpdateHarmony
     */
    public function addOrUpdateHarmony(string $xmlPath, HarmonyDto $harmony): bool
    {
        return $this->saveHarmony($xmlPath, $harmony);
    }
}
