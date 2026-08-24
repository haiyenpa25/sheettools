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

    public function __construct(?StorageService $storageService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
    }

    /**
     * Tách trang PDF hoặc xử lý ảnh đơn và tiền xử lý qua pipeline
     *
     * @param string $uuid
     * @param string $sourceFilePath
     * @param string $sourceType 'pdf' | 'png' | 'jpg' | 'jpeg'
     * @return array<int, string> Danh sách đường dẫn tuyệt đối các trang ảnh
     */
    public function processSource(string $uuid, string $sourceFilePath, string $sourceType): array
    {
        $pagesDir = $this->storageService->getPagesDir($uuid);
        if (!is_dir($pagesDir)) {
            mkdir($pagesDir, 0755, true);
        }

        $sourceType = strtolower($sourceType);

        if ($sourceType === 'pdf') {
            return $this->extractPdfPages($sourceFilePath, $pagesDir);
        }

        // Ảnh đơn (PNG/JPG): Lưu vào trang 1
        $targetPage1 = $pagesDir . DIRECTORY_SEPARATOR . 'page-001.png';
        $this->runOpenCvPipeline($sourceFilePath, $targetPage1);
        
        return [$targetPage1];
    }

    protected function runOpenCvPipeline(string $inputPath, string $outputPath): bool
    {
        $pipelineScript = dirname(__DIR__, 2) . '/workers/preprocessing/pipeline.py';
        $cmd = sprintf(
            'python %s --input %s --output %s 2>&1',
            escapeshellarg($pipelineScript),
            escapeshellarg($inputPath),
            escapeshellarg($outputPath)
        );

        $output = [];
        $exitCode = 0;
        @exec($cmd, $output, $exitCode);

        // Nếu OpenCV pipeline không khả dụng, sao chép nguyên bản
        if ($exitCode !== 0 || !file_exists($outputPath)) {
            copy($inputPath, $outputPath);
        }

        return file_exists($outputPath);
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
            'python %s --input %s --output-dir %s --dpi 300 2>&1',
            escapeshellarg($scriptPath),
            escapeshellarg($pdfPath),
            escapeshellarg($pagesDir)
        );

        $output = [];
        $exitCode = 0;
        @exec($cmd, $output, $exitCode);

        $rawOutput = implode("\n", $output);
        $json = json_decode($rawOutput, true);

        if ($exitCode === 0 && is_array($json) && !empty($json['success']) && !empty($json['pages'])) {
            return $json['pages'];
        }

        // Nếu có lỗi, fail loudly không dùng ảnh trắng giả
        $errorDetail = is_array($json) && isset($json['error']) ? $json['error'] : $rawOutput;
        throw new \RuntimeException("Failed to extract pages from PDF '{$pdfPath}': {$errorDetail}");
    }
}
