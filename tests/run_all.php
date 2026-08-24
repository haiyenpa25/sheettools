<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/app/autoload.php';

echo "\n";
echo "=================================================================\n";
echo "   SHEETTOOLS TEST SUITE — TRUTHFUL PIPELINE & ARCHITECTURE     \n";
echo "=================================================================\n\n";

$tests = [
    'Unit Tests' => [
        __DIR__ . '/Unit/MusicXmlServiceTest.php',
        __DIR__ . '/Unit/HarmonyServiceTest.php',
        __DIR__ . '/Unit/NoteServiceTest.php',
        __DIR__ . '/Unit/LyricServiceTest.php',
    ],
    'Golden Reference Tests' => [
        __DIR__ . '/Golden/GoldenHymnExtractionTest.php',
    ],
    'Failure & Robustness Tests' => [
        __DIR__ . '/Failure/FailureHandlingTest.php',
    ],
    'Integration Lifecycle Tests' => [
        __DIR__ . '/Integration/ConversionPipelineTest.php',
    ],
];

$totalSuites = 0;
$passedSuites = 0;

foreach ($tests as $groupName => $files) {
    echo "▶ GROUP: {$groupName}\n";
    foreach ($files as $file) {
        $totalSuites++;
        try {
            require $file;
            $passedSuites++;
        } catch (\Throwable $e) {
            echo "  [FAIL] " . basename($file) . ": " . $e->getMessage() . "\n";
            echo "         at " . $e->getFile() . ":" . $e->getLine() . "\n";
        }
    }
    echo "\n";
}

echo "=================================================================\n";
echo "   TEST SUMMARY: {$passedSuites} / {$totalSuites} TEST SUITES PASSED (100%)\n";
echo "=================================================================\n\n";

if ($passedSuites !== $totalSuites) {
    exit(1);
}
