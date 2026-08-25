<?php

declare(strict_types=1);

namespace App\Services;

require_once __DIR__ . '/StorageService.php';

use App\Services\StorageService;
use ZipArchive;

/**
 * Service kiểm định và xuất bản file MusicXML / MXL chuẩn
 */
class ExportService
{
    protected StorageService $storageService;

    public function __construct(?StorageService $storageService = null)
    {
        $this->storageService = $storageService ?: new StorageService();
    }

    /**
     * Xác thực tệp MusicXML hiện tại của dự án
     */
    public function validateProject(string $uuid): array
    {
        $xmlPath = $this->storageService->getCurrentMusicXmlPath($uuid);
        if (!file_exists($xmlPath)) {
            return [
                'isValid' => false,
                'errors' => ['MusicXML file does not exist'],
                'warnings' => [],
            ];
        }

        $validatorPy = dirname(__DIR__, 2) . '/workers/xml_tools/validator.py';
        $cmd = sprintf('python %s --xml %s 2>&1', escapeshellarg($validatorPy), escapeshellarg($xmlPath));
        
        $output = [];
        $exitCode = 0;
        @exec($cmd, $output, $exitCode);

        $jsonStr = implode("\n", $output);
        $res = json_decode($jsonStr, true);

        return is_array($res) ? $res : ['isValid' => ($exitCode === 0), 'errors' => [], 'warnings' => []];
    }

    /**
     * Xuất tệp MusicXML theo định dạng yêu cầu (.xml, .musicxml, .mxl)
     */
    public function export(string $uuid, string $format = 'musicxml'): ?string
    {
        $curPath = $this->storageService->getCurrentMusicXmlPath($uuid);
        if (!file_exists($curPath)) {
            $curPath = $this->storageService->getRawMusicXmlPath($uuid);
        }
        if (!file_exists($curPath) || filesize($curPath) < 50) return null;

        // Kiểm tra tính hợp lệ của XML trước khi xuất
        $doc = new \DOMDocument();
        if (!@$doc->load($curPath)) {
            return null;
        }

        $exportDir = $this->storageService->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'export';
        if (!is_dir($exportDir)) {
            mkdir($exportDir, 0755, true);
        }

        $baseName = 'score_export';

        switch (strtolower($format)) {
            case 'xml':
                $target = $exportDir . DIRECTORY_SEPARATOR . "{$baseName}.xml";
                copy($curPath, $target);
                return $target;

            case 'musicxml':
                $target = $exportDir . DIRECTORY_SEPARATOR . "{$baseName}.musicxml";
                copy($curPath, $target);
                return $target;

            case 'mxl':
                $targetMxl = $exportDir . DIRECTORY_SEPARATOR . "{$baseName}.mxl";
                if ($this->packageMxl($curPath, $targetMxl)) {
                    return $targetMxl;
                }
                return null;

            case 'mscx':
                $targetMscx = $exportDir . DIRECTORY_SEPARATOR . "{$baseName}.mscx";
                $exporterPy = dirname(__DIR__, 2) . '/workers/xml_tools/musescore_exporter.py';
                $cmd = sprintf('python %s --input %s --output %s --format mscx 2>&1', escapeshellarg($exporterPy), escapeshellarg($curPath), escapeshellarg($targetMscx));
                @exec($cmd);
                if (file_exists($targetMscx) && filesize($targetMscx) > 50) {
                    return $targetMscx;
                }
                copy($curPath, $targetMscx);
                return $targetMscx;

            default:
                return $curPath;
        }
    }

    /**
     * Đóng gói MusicXML thành file nén .mxl kèm META-INF/container.xml
     */
    protected function packageMxl(string $sourceXmlPath, string $targetMxlPath): bool
    {
        if (!class_exists('ZipArchive')) {
            // Nếu không có Zip extension, fallback copy sang .musicxml
            copy($sourceXmlPath, str_replace('.mxl', '.musicxml', $targetMxlPath));
            return false;
        }

        $zip = new ZipArchive();
        if ($zip->open($targetMxlPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
            return false;
        }

        // 1. Thêm container.xml
        $containerXml = '<?xml version="1.0" encoding="UTF-8"?>
<container>
  <rootfiles>
    <rootfile full-path="score.xml"/>
  </rootfiles>
</container>';
        $zip->addEmptyDir('META-INF');
        $zip->addFromString('META-INF/container.xml', $containerXml);

        // 2. Thêm file score.xml
        $zip->addFile($sourceXmlPath, 'score.xml');
        $zip->close();

        return file_exists($targetMxlPath);
    }
}
