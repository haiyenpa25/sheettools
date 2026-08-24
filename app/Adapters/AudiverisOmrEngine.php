<?php

declare(strict_types=1);

namespace App\Adapters;

require_once dirname(__DIR__) . '/Contracts/OmrEngineInterface.php';
require_once dirname(__DIR__) . '/DTOs/ConversionInputDto.php';
require_once dirname(__DIR__) . '/DTOs/OmrResultDto.php';
require_once dirname(__DIR__) . '/Services/StorageService.php';

use App\Contracts\OmrEngineInterface;
use App\DTOs\ConversionInputDto;
use App\DTOs\OmrResultDto;
use App\Services\StorageService;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use ZipArchive;

/**
 * Adapter thực thi Audiveris CLI cho OMR với cơ chế quét và xác thực artifact thực tế.
 */
class AudiverisOmrEngine implements OmrEngineInterface
{
    protected StorageService $storageService;
    protected array $config;

    public function __construct(?StorageService $storageService = null, ?array $config = null)
    {
        $this->storageService = $storageService ?: new StorageService();
        $this->config = $config ?: (file_exists(dirname(__DIR__, 2) . '/config/omr.php') ? require dirname(__DIR__, 2) . '/config/omr.php' : []);
    }

    /**
     * @param ConversionInputDto $input
     * @return OmrResultDto
     */
    public function transcribe(ConversionInputDto $input): OmrResultDto
    {
        $uuid = $input->projectUuid;
        $this->storageService->initProjectDirs($uuid);

        $logPath = $this->storageService->getLogPath($uuid, 'audiveris');
        $canonicalXmlPath = $this->storageService->getRawMusicXmlPath($uuid);
        $canonicalOmrPath = $this->storageService->getOmrPath($uuid);

        $javaBin = $this->config['java_bin'] ?? 'java';
        $audiverisJar = $this->config['audiveris_jar'] ?? 'audiveris.jar';
        $outDir = $this->storageService->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'omr_out';

        if (!is_dir($outDir)) {
            mkdir($outDir, 0755, true);
        }

        // Xây dựng lệnh gọi Headless Audiveris Batch
        $cmd = sprintf(
            '%s -cp %s org.audiveris.omr.Main -batch -export -output %s %s 2>&1',
            escapeshellarg($javaBin),
            escapeshellarg($audiverisJar),
            escapeshellarg($outDir),
            escapeshellarg($input->sourceFilePath)
        );

        $output = [];
        $exitCode = 0;
        @exec($cmd, $output, $exitCode);

        $logContent = "COMMAND: " . $cmd . "\nEXIT CODE: " . $exitCode . "\n\n" . implode("\n", $output);
        file_put_contents($logPath, $logContent);

        // Quét đệ quy thư mục output để tìm artifact thực tế
        $foundArtifacts = [];
        $foundMusicXml = null;
        $foundOmr = null;
        $warnings = [];

        if (is_dir($outDir)) {
            $iterator = new RecursiveIteratorIterator(
                new RecursiveDirectoryIterator($outDir, RecursiveDirectoryIterator::SKIP_DOTS)
            );

            foreach ($iterator as $file) {
                if ($file->isFile()) {
                    $filePath = $file->getPathname();
                    $ext = strtolower($file->getExtension());
                    $foundArtifacts[] = $filePath;

                    if ($ext === 'omr' && !$foundOmr) {
                        $foundOmr = $filePath;
                    } elseif (in_array($ext, ['mxl', 'musicxml', 'xml'], true) && !$foundMusicXml) {
                        $foundMusicXml = $filePath;
                    }
                }
            }
        }

        // Nếu tìm thấy file OMR thực tế, sao chép về vị trí canonical
        if ($foundOmr && file_exists($foundOmr)) {
            copy($foundOmr, $canonicalOmrPath);
        }

        // Nếu tìm thấy file MusicXML thực tế
        if ($foundMusicXml && file_exists($foundMusicXml) && filesize($foundMusicXml) > 50) {
            $ext = strtolower(pathinfo($foundMusicXml, PATHINFO_EXTENSION));

            if ($ext === 'mxl') {
                // Giải nén MXL lấy MusicXML
                $zip = new ZipArchive();
                if ($zip->open($foundMusicXml) === true) {
                    $xmlExtracted = false;
                    for ($i = 0; $i < $zip->numFiles; $i++) {
                        $filename = $zip->getNameIndex($i);
                        if (!str_starts_with($filename, 'META-INF/') && (str_ends_with($filename, '.xml') || str_ends_with($filename, '.musicxml'))) {
                            $content = $zip->getFromIndex($i);
                            if ($content !== false && strlen($content) > 50) {
                                file_put_contents($canonicalXmlPath, $content);
                                $xmlExtracted = true;
                                break;
                            }
                        }
                    }
                    $zip->close();
                    if (!$xmlExtracted) {
                        $warnings[] = "Could not extract valid score XML from .mxl archive.";
                    }
                } else {
                    $warnings[] = "Failed to open .mxl archive with ZipArchive.";
                }
            } else {
                copy($foundMusicXml, $canonicalXmlPath);
            }
        }

        $hasValidXml = file_exists($canonicalXmlPath) && filesize($canonicalXmlPath) > 50;
        $success = ($exitCode === 0) && $hasValidXml;

        return new OmrResultDto(
            success: $success,
            musicXmlPath: $hasValidXml ? $canonicalXmlPath : null,
            omrPath: file_exists($canonicalOmrPath) ? $canonicalOmrPath : null,
            generatedArtifacts: $foundArtifacts,
            exitCode: $exitCode,
            logs: $logContent,
            warnings: $warnings
        );
    }
}
