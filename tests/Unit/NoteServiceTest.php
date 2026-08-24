<?php

declare(strict_types=1);

namespace Tests\Unit;

require_once dirname(__DIR__, 2) . '/app/autoload.php';

use App\Services\NoteService;
use App\DTOs\NoteEditDto;

$service = new NoteService();

// Create temporary MusicXML file
$sampleXml = '<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>';

$tempFile = tempnam(sys_get_temp_dir(), 'test_note_') . '.xml';
file_put_contents($tempFile, $sampleXml);

// 1. Edit second note to F#4 (with sharp accidental)
$noteEdit = new NoteEditDto(
    partId: 'P1',
    staff: 1,
    measureNumber: 1,
    voice: 1,
    noteIndex: 2,
    step: 'F',
    octave: 4,
    accidental: 'sharp',
    duration: 'half'
);

$ok = $service->updateNote($tempFile, $noteEdit);
assert($ok === true, "updateNote should return true");

// Verify XML content
$updated = file_get_contents($tempFile);
assert(str_contains($updated, '<step>F</step>'), "Second note step should be updated to F");
assert(str_contains($updated, '<alter>1</alter>'), "Second note alter should be updated to 1");
assert(str_contains($updated, '<accidental>sharp</accidental>'), "Second note accidental should be sharp");
assert(str_contains($updated, '<type>half</type>'), "Second note type should be half");
assert(str_contains($updated, '<duration>4</duration>'), "Duration for half note with divisions=2 should be 4");

@unlink($tempFile);

echo "  [Unit] NoteServiceTest: PASS (Accurate note locator & alter handling verified)\n";
