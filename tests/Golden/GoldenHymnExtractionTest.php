<?php

declare(strict_types=1);

namespace Tests\Golden;

require_once dirname(__DIR__, 2) . '/app/Services/MusicXmlService.php';

use App\Services\MusicXmlService;

$fixturePath = dirname(__DIR__) . '/fixtures/golden_hymn.musicxml';
assert(file_exists($fixturePath), "Golden fixture must exist at: {$fixturePath}");

$xmlContent = file_get_contents($fixturePath);
$service = new MusicXmlService();

// 1. Verify lyrics extraction
$lyrics = $service->extractLyrics($xmlContent);
$versesCount = count($lyrics);
assert($versesCount >= 4, "Should extract at least 4 verses from golden hymn");
assert(count($lyrics[1]) >= 30, "Verse 1 should have >= 30 syllables");

// 2. Verify harmonies extraction
$harmonies = $service->extractHarmonies($xmlContent);
assert(count($harmonies) >= 10, "Should extract >= 10 harmonies from golden hymn");

// 3. Verify Vietnamese diacritics in extracted lyrics
$firstVerseText = array_map(fn($l) => $l->text, $lyrics[1]);
$joined = implode(' ', $firstVerseText);
assert(str_contains($joined, 'Thánh') || str_contains($joined, 'Vương') || str_contains($joined, 'ngự'), "Vietnamese diacritics must be preserved in golden extraction");

echo "  [Golden] GoldenHymnExtractionTest: PASS\n";
