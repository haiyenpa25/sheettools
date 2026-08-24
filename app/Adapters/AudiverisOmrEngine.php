<?php

declare(strict_types=1);

namespace App\Adapters;

require_once dirname(__DIR__) . '/Contracts/OmrEngineInterface.php';
require_once dirname(__DIR__) . '/DTOs/ConversionInputDto.php';
require_once dirname(__DIR__) . '/Services/StorageService.php';

use App\Contracts\OmrEngineInterface;
use App\DTOs\ConversionInputDto;
use App\Services\StorageService;

/**
 * Adapter thực thi Audiveris CLI cho OMR
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
     * @return array{success: bool, rawMusicXmlPath: string, omrFilePath: string, logs: string}
     */
    public function transcribe(ConversionInputDto $input): array
    {
        $uuid = $input->projectUuid;
        $this->storageService->initProjectDirs($uuid);

        $logPath = $this->storageService->getLogPath($uuid, 'audiveris');
        $rawXmlPath = $this->storageService->getRawMusicXmlPath($uuid);
        $omrPath = $this->storageService->getOmrPath($uuid);

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

        $success = ($exitCode === 0);

        return [
            'success' => $success,
            'rawMusicXmlPath' => $rawXmlPath,
            'omrFilePath' => $omrPath,
            'logs' => $logContent,
        ];
    }
}
