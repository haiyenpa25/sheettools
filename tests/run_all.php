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
        __DIR__ . '/Unit/JobQueueServiceTest.php',
        __DIR__ . '/Unit/PageArtifactServiceTest.php',
        __DIR__ . '/Unit/ImagePreprocessServiceTest.php',
        __DIR__ . '/Unit/StorageServiceTest.php',
        __DIR__ . '/Unit/ChorusExportTest.php',
        __DIR__ . '/Unit/ReviewQueueServiceTest.php',
        __DIR__ . '/Unit/OmrComparisonServiceTest.php',
        __DIR__ . '/Unit/SecurityBoundaryTest.php',
        __DIR__ . '/Unit/ProjectLibraryTest.php',
    ],
    'Golden Reference Tests' => [
        __DIR__ . '/Golden/GoldenHymnExtractionTest.php',
    ],
    'Failure & Robustness Tests' => [
        __DIR__ . '/Failure/FailureHandlingTest.php',
    ],
    'Integration Lifecycle Tests' => [
        __DIR__ . '/Integration/ConversionPipelineTest.php',
        __DIR__ . '/Integration/PageRetryPipelineTest.php',
    ],
];

$totalSuites = 0;
$passedSuites = 0;

if ((int) ini_get('zend.assertions') !== 1) {
    fwrite(STDERR, "ERROR: Tests require zend.assertions=1. Run php -d zend.assertions=1 tests/run_all.php\n");
    exit(2);
}

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

foreach (['HomrRepairTest.py', 'ExternalOmrTest.py', 'TextRolesTest.py', 'DiacriticFusionTest.py', 'PageModelTest.py', 'OmrAnchorsTest.py', 'ChordAnchoringTest.py', 'LyricStructureTest.py', 'LyricAssemblyTest.py', 'RoadmapBenchmarkTest.py', 'PdfExtractionTest.py', 'PageSourceTest.py', 'PageProgressTest.py', 'PageWorkerRetryTest.py', 'PageLayoutTest.py', 'PreprocessDebugTest.py', 'ImageQualityTest.py', 'ZipInputTest.py', 'NotationLayerTest.py', 'SemanticMergeTest.py', 'StaffAndLyricSegmentationTest.py', 'HeaderSemanticsTest.py', 'VietnameseContextTest.py', 'NotationOnlyModeTest.py', 'LyricsArtifactTest.py', 'LyricsAlignmentTest.py', 'MultiPartLyricsAlignmentTest.py', 'ValidatorDurationTest.py', 'ValidatorStructureTest.py', 'AccuracyReportTest.py', 'MultiPageMergerTest.py', 'OmrChecksTest.py', 'SectionContinuityTest.py', 'RepairEvidenceTest.py', 'ReviewBenchmarkTest.py'] as $pythonTestName) {
    $totalSuites++;
    $pythonTest = __DIR__ . '/Python/' . $pythonTestName;
    $pythonOutput = [];
    $pythonExit = 0;
    $pythonBin = getenv('PYTHON_BIN') ?: 'python';
    exec(escapeshellarg($pythonBin) . ' ' . escapeshellarg($pythonTest) . ' 2>&1', $pythonOutput, $pythonExit);
    echo implode("\n", $pythonOutput) . "\n\n";
    if ($pythonExit === 0) {
        $passedSuites++;
    } else {
        echo "  [FAIL] {$pythonTestName} exited with {$pythonExit}\n\n";
    }
}

echo "=================================================================\n";
$percent = $totalSuites > 0 ? (int) round(($passedSuites / $totalSuites) * 100) : 0;
echo "   TEST SUMMARY: {$passedSuites} / {$totalSuites} TEST SUITES PASSED ({$percent}%)\n";
echo "=================================================================\n\n";

if ($passedSuites !== $totalSuites) {
    exit(1);
}
