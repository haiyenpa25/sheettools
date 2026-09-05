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

        $logPath        = $this->storageService->getLogPath($uuid, 'audiveris');
        $canonicalXmlPath = $this->storageService->getRawMusicXmlPath($uuid);
        $canonicalOmrPath = $this->storageService->getOmrPath($uuid);

        $outDir = $this->storageService->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'omr_out';
        if (!is_dir($outDir)) {
            mkdir($outDir, 0755, true);
        }

        // Tìm đường dẫn Python worker
        $workerScript = dirname(__DIR__, 2) . '/workers/audiveris_runner.py';

        // Tìm Audiveris exe từ config hoặc vị trí mặc định
        $audiverisExe = $this->config['audiveris_exe']
            ?? 'D:\\tools\\audiveris\\install\\Audiveris\\Audiveris.exe';

        // Tìm Python binary
        $pythonBin = $this->config['python_bin'] ?? 'python';

        // Xây dựng lệnh gọi Python worker
        $cmd = sprintf(
            '%s %s --input %s --output %s --audiveris %s 2>&1',
            escapeshellarg($pythonBin),
            escapeshellarg($workerScript),
            escapeshellarg($input->sourceFilePath),
            escapeshellarg($outDir),
            escapeshellarg($audiverisExe)
        );

        $output   = [];
        $exitCode = 0;
        @exec($cmd, $output, $exitCode);

        $rawOutput  = implode("\n", $output);
        $logContent = "COMMAND: {$cmd}\nEXIT CODE: {$exitCode}\n\n{$rawOutput}";
        file_put_contents($logPath, $logContent);

        // Parse JSON result từ Python worker
        $jsonResult = null;
        if (preg_match('/__OMR_JSON_RESULT__\s*(\{[\s\S]*?\})\s*$/', $rawOutput, $m)) {
            $jsonResult = json_decode($m[1], true);
        } elseif (preg_match('/(\{[\s\S]*"success"[\s\S]*\})\s*$/', $rawOutput, $m)) {
            $jsonResult = json_decode($m[1], true);
        }

        // Tìm dòng JSON (bắt đầu bằng {) từ cuối output nếu regex chưa bắt
        if (!$jsonResult) {
            foreach (array_reverse($output) as $line) {
                $line = trim($line);
                if (str_starts_with($line, '{') || str_starts_with($line, '[')) {
                    $res = json_decode($line, true);
                    if ($res && is_array($res) && isset($res['success'])) {
                        $jsonResult = $res;
                        break;
                    }
                }
            }
        }
        if (!$jsonResult) {
            $jsonResult = json_decode($rawOutput, true);
        }

        $warnings      = [];
        $foundArtifacts = [];
        $foundMusicXml  = null;
        $foundOmr       = null;

        if ($jsonResult && !empty($jsonResult['xml_path']) && file_exists($jsonResult['xml_path'])) {
            $foundMusicXml = $jsonResult['xml_path'];
        }
        if ($jsonResult && !($jsonResult['success'] ?? false)) {
            $warnings[] = $jsonResult['error'] ?? 'Unknown OMR error';
        }

        // Ưu tiên 1: Tệp đã được phục hồi hoàn chỉnh và inject lời tiếng Việt (score_healed.xml)
        $healedCandidate = $outDir . DIRECTORY_SEPARATOR . 'score_healed.xml';
        if (file_exists($healedCandidate) && filesize($healedCandidate) > 50) {
            $foundMusicXml = $healedCandidate;
        }

        // Ưu tiên 2: Quét thư mục output nếu chưa tìm thấy, ưu tiên .xml/.musicxml trước .mxl
        if (!$foundMusicXml && is_dir($outDir)) {
            $candidatesXml = [];
            $candidatesMxl = [];
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
                    } elseif (in_array($ext, ['xml', 'musicxml'], true)) {
                        $candidatesXml[] = $filePath;
                    } elseif ($ext === 'mxl') {
                        $candidatesMxl[] = $filePath;
                    }
                }
            }
            if (!empty($candidatesXml)) {
                $foundMusicXml = $candidatesXml[0];
            } elseif (!empty($candidatesMxl)) {
                $foundMusicXml = $candidatesMxl[0];
            }
        }

        if ($foundOmr && file_exists($foundOmr)) {
            copy($foundOmr, $canonicalOmrPath);
        }

        if ($foundMusicXml && file_exists($foundMusicXml) && filesize($foundMusicXml) > 50) {
            $ext = strtolower(pathinfo($foundMusicXml, PATHINFO_EXTENSION));
            if ($ext === 'mxl') {
                $xmlExtracted = false;
                if (class_exists('ZipArchive')) {
                    $zip = new ZipArchive();
                    if ($zip->open($foundMusicXml) === true) {
                        for ($i = 0; $i < $zip->numFiles; $i++) {
                            $filename = $zip->getNameIndex($i);
                            if (!str_starts_with($filename, 'META-INF/') &&
                                (str_ends_with($filename, '.xml') || str_ends_with($filename, '.musicxml'))) {
                                $content = $zip->getFromIndex($i);
                                if ($content !== false && strlen($content) > 50) {
                                    file_put_contents($canonicalXmlPath, $content);
                                    $xmlExtracted = true;
                                    break;
                                }
                            }
                        }
                        $zip->close();
                    }
                }

                // Fallback giải nén qua Python zipfile nếu ZipArchive không khả dụng
                if (!$xmlExtracted || !file_exists($canonicalXmlPath) || filesize($canonicalXmlPath) < 50) {
                    $pyCmd = sprintf(
                        'python -c "import zipfile, os; z=zipfile.ZipFile(r\'%s\'); [open(r\'%s\', \'wb\').write(z.read(n)) for n in z.namelist() if n.endswith(\'.xml\') and \'META-INF\' not in n]" 2>&1',
                        $foundMusicXml,
                        $canonicalXmlPath
                    );
                    @exec($pyCmd);
                }
            } else {
                copy($foundMusicXml, $canonicalXmlPath);
            }
        }

        $hasValidXml = file_exists($canonicalXmlPath) && filesize($canonicalXmlPath) > 50;
        $success     = $hasValidXml;

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

