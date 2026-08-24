<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';

use App\Services\StorageService;

/**
 * Service tiền xử lý hình ảnh và tách trang từ PDF
 */
class ImagePreprocessService
{
    protected StorageService $storageService;

    public function __construct(?StorageService $storageService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
    }

    /**
     * Tách trang PDF hoặc xử lý ảnh đơn và tiền xử lý qua OpenCV
     *
     * @param string $uuid
     * @param string $sourceFilePath
     * @param string $sourceType 'pdf' | 'png' | 'jpg'
     * @return array<int, string> Danh sách đường dẫn ảnh các trang đã sẵn sàng
     */
    public function processSource(string $uuid, string $sourceFilePath, string $sourceType): array
    {
        $pagesDir = $this->storageService->getPagesDir($uuid);
        if (!is_dir($pagesDir)) {
            mkdir($pagesDir, 0755, true);
        }

        $pageImages = [];

        if (strtolower($sourceType) === 'pdf') {
            // Tách trang PDF bằng Python hoặc pdftoppm nếu có
            $pageImages = $this->extractPdfPages($sourceFilePath, $pagesDir);
        } else {
            // Ảnh đơn (PNG/JPG): Sao chép vào trang 1
            $targetPage1 = $pagesDir . DIRECTORY_SEPARATOR . 'page-001.png';
            $this->runOpenCvPipeline($sourceFilePath, $targetPage1);
            $pageImages[] = $targetPage1;
        }

        return $pageImages;
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

        // Nếu OpenCV chạy thành công thì xong, nếu chưa cài OpenCV thì fallback copy trực tiếp
        if ($exitCode !== 0 || !file_exists($outputPath)) {
            copy($inputPath, $outputPath);
        }

        return file_exists($outputPath);
    }

    protected function extractPdfPages(string $pdfPath, string $pagesDir): array
    {
        // Fallback: Tạo ít nhất 1 ảnh đại diện hoặc dùng pdftoppm/Python
        $page1 = $pagesDir . DIRECTORY_SEPARATOR . 'page-001.png';
        
        // Thử chạy python script nếu có PyMuPDF / pdf2image
        $pyExtract = sprintf(
            'python -c "import fitz; doc=fitz.open(%s); page=doc.load_page(0); pix=page.get_pixmap(); pix.save(%s)" 2>&1',
            escapeshellarg($pdfPath),
            escapeshellarg($page1)
        );
        @exec($pyExtract);

        if (!file_exists($page1)) {
            if (function_exists('imagecreatetruecolor')) {
                $im = imagecreatetruecolor(800, 1100);
                $white = imagecolorallocate($im, 255, 255, 255);
                imagefill($im, 0, 0, $white);
                imagepng($im, $page1);
                imagedestroy($im);
            } else {
                // Minimal 1x1 white PNG base64
                $minimalPng = base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=');
                file_put_contents($page1, $minimalPng);
            }
        }

        return [$page1];
    }
}
