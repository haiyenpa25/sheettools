<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';

use App\Services\StorageService;

/**
 * Service tiền xử lý hình ảnh và tách trang từ PDF phục vụ OMR
 */
class ImagePreprocessService
{
    protected StorageService $storageService;
    protected int $maxPages;
    protected string $pythonBin;

    public function __construct(?StorageService $storageService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
        $config = require dirname(__DIR__, 2) . '/config/omr.php';
        $this->maxPages = max(1, (int)($config['max_pages'] ?? 50));
        $this->pythonBin = (string)($config['python_bin'] ?? 'python');
    }

    /**
     * Tách trang PDF hoặc xử lý ảnh đơn và tiền xử lý qua pipeline
     *
     * @param string $uuid
     * @param string $sourceFilePath
     * @param string $sourceType 'pdf' | 'png' | 'jpg' | 'jpeg'
     * @return array<int, string> Danh sách đường dẫn tuyệt đối các trang ảnh
     */
    public function processSource(string $uuid, string $sourceFilePath, string $sourceType, bool $reuseExisting = false): array
    {
        $pagesDir = $this->storageService->getPagesDir($uuid);
        if (!is_dir($pagesDir)) {
            mkdir($pagesDir, 0755, true);
        }

        $sourceType = strtolower($sourceType);

        if ($sourceType === 'pdf') {
            if ($reuseExisting) {
                $existing = $this->reusablePages($uuid, $sourceFilePath);
                if ($existing !== []) {
                    return $existing;
                }
            }
            $pages = $this->extractPdfPages($sourceFilePath, $pagesDir);
            $this->writePageManifest($pagesDir, $sourceFilePath, count($pages));
            return $pages;
        }

        // Ảnh đơn (PNG/JPG): Lưu vào trang 1
        $targetPage1 = $pagesDir . DIRECTORY_SEPARATOR . 'page-001.png';
        if (!$this->runOpenCvPipeline($sourceFilePath, $targetPage1)) {
            throw new \RuntimeException('Image preprocessing failed; no valid page PNG was produced.');
        }
        
        return [$targetPage1];
    }

    /** @return array<int, string> Complete pages from the same immutable source, or none. */
    public function reusablePages(string $uuid, string $sourceFilePath): array
    {
        $pagesDir = $this->storageService->getPagesDir($uuid);
        $manifestPath = $pagesDir . DIRECTORY_SEPARATOR . 'page-manifest.json';
        if (!is_file($manifestPath) || !is_file($sourceFilePath)) {
            return [];
        }
        $manifest = json_decode((string) file_get_contents($manifestPath), true);
        $sourceHash = hash_file('sha256', $sourceFilePath);
        $count = (int) ($manifest['page_count'] ?? 0);
        if (!is_array($manifest) || $sourceHash === false ||
            ($manifest['source_sha256'] ?? null) !== $sourceHash ||
            $count < 1 || $count > $this->maxPages || ($manifest['dpi'] ?? null) !== 300) {
            return [];
        }
        $pages = [];
        for ($index = 1; $index <= $count; $index++) {
            $path = $pagesDir . DIRECTORY_SEPARATOR . sprintf('page-%03d.png', $index);
            if (!is_file($path) || filesize($path) === 0) {
                return [];
            }
            $pages[] = $path;
        }
        return $pages;
    }

    private function writePageManifest(string $pagesDir, string $sourceFilePath, int $pageCount): void
    {
        $payload = json_encode([
            'source_sha256' => hash_file('sha256', $sourceFilePath),
            'page_count' => $pageCount,
            'dpi' => 300,
        ], JSON_PRETTY_PRINT);
        $temporary = $pagesDir . DIRECTORY_SEPARATOR . 'page-manifest.json.tmp';
        $target = $pagesDir . DIRECTORY_SEPARATOR . 'page-manifest.json';
        if ($payload === false || file_put_contents($temporary, $payload, LOCK_EX) === false || !rename($temporary, $target)) {
            throw new \RuntimeException('Could not persist rendered page manifest.');
        }
    }

    protected function runOpenCvPipeline(string $inputPath, string $outputPath): bool
    {
        $pipelineScript = dirname(__DIR__, 2) . '/workers/preprocessing/pipeline.py';
        $reportPath = $outputPath . '.quality.json';
        $cmd = sprintf(
            '%s %s --input %s --output %s --report %s --debug-dir %s 2>&1',
            escapeshellarg($this->pythonBin),
            escapeshellarg($pipelineScript),
            escapeshellarg($inputPath),
            escapeshellarg($outputPath),
            escapeshellarg($reportPath),
            escapeshellarg(dirname($outputPath) . DIRECTORY_SEPARATOR . 'preprocess_debug')
        );

        $output = [];
        $exitCode = 0;
        @exec($cmd, $output, $exitCode);

        return $exitCode === 0 && is_file($outputPath) && filesize($outputPath) > 0;
    }

    /**
     * Trích xuất toàn bộ các trang PDF thành ảnh PNG 300 DPI bằng Python worker
     *
     * @param string $pdfPath
     * @param string $pagesDir
     * @return array<int, string>
     * @throws \RuntimeException Khi không thể trích xuất PDF
     */
    protected function extractPdfPages(string $pdfPath, string $pagesDir): array
    {
        $scriptPath = dirname(__DIR__, 2) . '/workers/preprocessing/extract_pdf.py';
        
        $cmd = sprintf(
            '%s %s --input %s --output-dir %s --dpi 300 --max-pages %d 2>&1',
            escapeshellarg($this->pythonBin),
            escapeshellarg($scriptPath),
            escapeshellarg($pdfPath),
            escapeshellarg($pagesDir),
            $this->maxPages
        );

        $output = [];
        $exitCode = 0;
        @exec($cmd, $output, $exitCode);

        $rawOutput = implode("\n", $output);
        $json = json_decode($rawOutput, true);

        if ($exitCode === 0 && is_array($json) && !empty($json['success']) && !empty($json['pages'])) {
            if (count($json['pages']) > $this->maxPages) {
                throw new \RuntimeException("PDF exceeds the configured {$this->maxPages}-page limit.");
            }
            return $json['pages'];
        }

        // Nếu có lỗi, fail loudly không dùng ảnh trắng giả
        $errorDetail = is_array($json) && isset($json['error']) ? $json['error'] : $rawOutput;
        throw new \RuntimeException("Failed to extract pages from PDF '{$pdfPath}': {$errorDetail}");
    }
}
