<?php

declare(strict_types=1);

namespace Tests\Unit;

require_once dirname(__DIR__, 2) . '/app/Services/HarmonyService.php';

use App\Services\HarmonyService;

$service = new HarmonyService();

// 1. Simple major chord
$cChord = $service->parseChordString('C', 'P1', 1);
assert($cChord->rootStep === 'C', "Root step should be C");
assert($cChord->rootAlter === null, "Root alter should be null for natural");
assert($cChord->bassStep === null, "Bass step should be null");

// 2. Minor chord with sharp
$fSharpM = $service->parseChordString('F#m', 'P1', 2);
assert($fSharpM->rootStep === 'F', "Root step should be F");
assert($fSharpM->rootAlter === '1', "Root alter should be '1'");
assert($fSharpM->kind === 'minor', "Kind should be minor");

// 3. Slash Chord: D/F#
$dSlashF = $service->parseChordString('D/F#', 'P1', 3);
assert($dSlashF->rootStep === 'D', "Root step should be D");
assert($dSlashF->bassStep === 'F', "Bass step should be F");
assert($dSlashF->bassAlter === '1', "Bass alter should be '1'");
assert($dSlashF->displayText === 'D/F#', "Display text should be D/F#");

// 4. Dominant 7th: B7
$b7 = $service->parseChordString('B7', 'P1', 4);
assert($b7->rootStep === 'B', "Root step should be B");
assert($b7->kind === 'dominant', "Kind should be dominant");

echo "  [Unit] HarmonyServiceTest: PASS\n";
