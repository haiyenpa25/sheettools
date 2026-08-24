<?php

declare(strict_types=1);

namespace Tests\Unit;

require_once dirname(__DIR__, 2) . '/app/Services/MusicXmlService.php';

use App\Services\MusicXmlService;

$service = new MusicXmlService();

// Sample valid MusicXML fragment
$xml = '<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <movement-title>Unit Test Hymn</movement-title>
  <identification>
    <creator type="composer">Test Composer</creator>
  </identification>
  <part id="P1">
    <measure number="1">
      <harmony>
        <root><root-step>G</root-step></root>
        <kind text="major">major</kind>
      </harmony>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
        <lyric number="1">
          <syllabic>single</syllabic>
          <text>Hỡi</text>
        </lyric>
        <lyric number="2">
          <syllabic>single</syllabic>
          <text>Chúa</text>
        </lyric>
      </note>
    </measure>
  </part>
</score-partwise>';

// 1. Extract metadata
$meta = $service->extractMetadata($xml);
assert($meta['title'] === 'Unit Test Hymn', "Metadata title mismatch: {$meta['title']}");
assert($meta['composer'] === 'Test Composer', "Metadata composer mismatch");

// 2. Extract lyrics
$lyrics = $service->extractLyrics($xml);
assert(isset($lyrics[1]) && count($lyrics[1]) === 1, "Verse 1 lyric missing");
assert($lyrics[1][0]->text === 'Hỡi', "Verse 1 text mismatch: '{$lyrics[1][0]->text}'");
assert(isset($lyrics[2]) && count($lyrics[2]) === 1, "Verse 2 lyric missing");
assert($lyrics[2][0]->text === 'Chúa', "Verse 2 text mismatch: '{$lyrics[2][0]->text}'");

// 3. Extract harmonies
$harmonies = $service->extractHarmonies($xml);
assert(count($harmonies) === 1, "Harmonies count mismatch");
assert($harmonies[0]->rootStep === 'G', "Harmony root mismatch");

echo "  [Unit] MusicXmlServiceTest: PASS\n";
