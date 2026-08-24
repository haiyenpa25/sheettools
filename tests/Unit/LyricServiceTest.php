<?php

declare(strict_types=1);

namespace Tests\Unit;

require_once dirname(__DIR__, 2) . '/app/autoload.php';

use App\Services\LyricService;
use App\DTOs\LyricDto;

$service = new LyricService();

// Create temporary MusicXML file
$sampleXml = '<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part id="P1">
    <measure number="1">
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>';

$tempFile = tempnam(sys_get_temp_dir(), 'test_lyric_') . '.xml';
file_put_contents($tempFile, $sampleXml);

// 1. Bulk distribute 2 syllables
$ok = $service->bulkUpdateVerse($tempFile, 'P1', 1, ['Tôn', 'vinh']);
assert($ok === true, "bulkUpdateVerse should return true");

// Verify XML content
$updated = file_get_contents($tempFile);
assert(str_contains($updated, '<text>Tôn</text>'), "First syllable 'Tôn' must be present");
assert(str_contains($updated, '<text>vinh</text>'), "Second syllable 'vinh' must be present");

@unlink($tempFile);

echo "  [Unit] LyricServiceTest: PASS (Syllable distribution sequence verified)\n";
