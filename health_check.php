<?php

declare(strict_types=1);

require_once __DIR__ . '/app/Services/HealthCheckService.php';

use App\Services\HealthCheckService;

echo "========================================================\n";
echo "   SHEET CONVERTER — ENVIRONMENT HEALTH CHECK (PHASE 0)  \n";
echo "========================================================\n\n";

$checker = new HealthCheckService();
$results = $checker->checkAll();

// 1. PHP
echo "[1] PHP RUNTIME:\n";
echo "    - Version: " . $results['php']['version'] . " (" . $results['php']['status'] . ")\n";
echo "    - Extensions: " . ($results['php']['extensions_ok'] ? 'All required extensions loaded (DOM, XML, SimpleXML, JSON, MBString, cURL, Zip)' : 'Missing: ' . implode(', ', $results['php']['missing_extensions'])) . "\n\n";

// 2. Node & NPM
echo "[2] NODE & NPM:\n";
echo "    - Node: " . $results['node_npm']['node_version'] . "\n";
echo "    - NPM:  " . $results['node_npm']['npm_version'] . " (" . $results['node_npm']['status'] . ")\n\n";

// 3. Python & Libs
echo "[3] PYTHON & OMR LIBRARIES:\n";
echo "    - Python: " . $results['python']['version'] . " (" . $results['python']['status'] . ")\n";
echo "    - Installed Libs: " . (empty($results['python']['installed_libs']) ? 'None' : implode(', ', $results['python']['installed_libs'])) . "\n";
if (!empty($results['python']['missing_libs'])) {
    echo "    - [Notice] Missing optional/worker libs: " . implode(', ', $results['python']['missing_libs']) . "\n";
    echo "      (Tip: pip install opencv-python lxml music21)\n";
}
echo "\n";

// 4. Java
echo "[4] JAVA (FOR AUDIVERIS OMR):\n";
echo "    - Output: " . $results['java']['output'] . " (" . $results['java']['status'] . ")\n";
if ($results['java']['status'] !== 'OK') {
    echo "    - [Notice] " . $results['java']['note'] . "\n";
}
echo "\n";

// 5. Tesseract OCR
echo "[5] TESSERACT OCR:\n";
echo "    - Version: " . $results['tesseract']['version'] . " (" . $results['tesseract']['status'] . ")\n";
if ($results['tesseract']['status'] === 'OK') {
    echo "    - Languages: " . implode(', ', $results['tesseract']['languages']) . "\n";
    echo "    - Vietnamese (vie): " . ($results['tesseract']['has_vietnamese'] ? 'YES' : 'NO') . "\n";
    echo "    - English (eng):    " . ($results['tesseract']['has_english'] ? 'YES' : 'NO') . "\n";
} else {
    echo "    - [Notice] " . $results['tesseract']['note'] . "\n";
}
echo "\n";

// 6. Storage
echo "[6] STORAGE SYSTEM:\n";
echo "    - Storage Path: " . $results['storage']['storage_path'] . "\n";
echo "    - Writable: " . ($results['storage']['is_writable'] ? 'YES (Ready)' : 'NO') . "\n\n";

echo "========================================================\n";
echo " Health check complete at: " . $results['timestamp'] . "\n";
echo "========================================================\n";
