<?php

declare(strict_types=1);

namespace App\Services;

require_once dirname(__DIR__) . '/Models/ConversionProject.php';
require_once dirname(__DIR__) . '/Repositories/ConversionProjectRepository.php';
require_once dirname(__DIR__) . '/Services/StorageService.php';
require_once dirname(__DIR__) . '/Services/ImagePreprocessService.php';
require_once dirname(__DIR__) . '/Contracts/OmrEngineInterface.php';
require_once dirname(__DIR__) . '/Adapters/AudiverisOmrEngine.php';
require_once dirname(__DIR__) . '/DTOs/ConversionInputDto.php';
require_once dirname(__DIR__) . '/DTOs/OmrResultDto.php';

use App\Models\ConversionProject;
use App\Repositories\ConversionProjectRepository;
use App\Services\StorageService;
use App\Services\ImagePreprocessService;
use App\Contracts\OmrEngineInterface;
use App\Adapters\AudiverisOmrEngine;
use App\DTOs\ConversionInputDto;
use App\DTOs\OmrResultDto;

/**
 * Service điều phối quy trình OMR trung thực (Truthful Conversion Pipeline)
 */
class ConversionService
{
    protected ConversionProjectRepository $projectRepo;
    protected StorageService $storageService;
    protected ImagePreprocessService $preprocessService;
    protected OmrEngineInterface $omrEngine;

    public function __construct(
        ?ConversionProjectRepository $projectRepo = null,
        ?StorageService $storageService = null,
        ?ImagePreprocessService $preprocessService = null,
        ?OmrEngineInterface $omrEngine = null
    ) {
        $this->projectRepo = $projectRepo ?: new ConversionProjectRepository();
        $this->storageService = $storageService ?: new StorageService();
        $this->preprocessService = $preprocessService ?: new ImagePreprocessService();
        $this->omrEngine = $omrEngine ?: new AudiverisOmrEngine($this->storageService);
    }

    /**
     * Khởi tạo dự án từ file upload
     */
    public function createProject(string $originalFilename, string $tempFilePath, array $options = []): ConversionProject
    {
        $ext = strtolower(pathinfo($originalFilename, PATHINFO_EXTENSION));
        $title = pathinfo($originalFilename, PATHINFO_FILENAME);

        $project = new ConversionProject([
            'title' => $title,
            'source_filename' => $originalFilename,
            'source_type' => $ext,
            'language' => $options['language'] ?? 'vie+eng',
            'status' => 'UPLOADED',
            'progress' => 0,
            'current_step' => 'uploaded',
        ]);

        $this->storageService->initProjectDirs($project->uuid);
        $savedSourcePath = $this->storageService->getSourcePath($project->uuid, $originalFilename);
        copy($tempFilePath, $savedSourcePath);

        $this->projectRepo->save($project);
        return $project;
    }

    /**
     * Thực thi quy trình OMR trung thực cho dự án
     */
    public function processProject(string $uuid): bool
    {
        $project = $this->projectRepo->findByUuid($uuid);
        if (!$project) return false;

        try {
            // Bước 1: Chuẩn bị & Tiền xử lý ảnh (OpenCV / PyMuPDF)
            $project->status = 'PROCESSING';
            $project->currentStep = 'preparing_pages';
            $project->progress = 20;
            $this->projectRepo->save($project);

            $sourcePath = $this->storageService->getSourcePath($uuid, $project->sourceFilename);
            if (!file_exists($sourcePath)) {
                throw new \RuntimeException("Source file missing at: {$sourcePath}");
            }

            $pages = $this->preprocessService->processSource($uuid, $sourcePath, $project->sourceType);

            // Bước 2: Chạy OMR Engine
            $project->currentStep = 'recognizing_score';
            $project->progress = 50;
            $this->projectRepo->save($project);

            $dto = new ConversionInputDto(
                projectUuid: $uuid,
                sourceFilePath: !empty($pages) ? $pages[0] : $sourcePath,
                sourceFileName: $project->sourceFilename,
                sourceType: $project->sourceType,
                language: $project->language
            );

            /** @var OmrResultDto $result */
            $result = $this->omrEngine->transcribe($dto);

            // Bước 3: Kiểm tra tính xác thực của Artifact MusicXML
            $project->currentStep = 'validating_artifacts';
            $project->progress = 85;
            $this->projectRepo->save($project);

            $rawXmlPath = $this->storageService->getRawMusicXmlPath($uuid);

            if (!$result->success || !file_exists($rawXmlPath) || filesize($rawXmlPath) < 50) {
                $errorMsg = !empty($result->warnings) 
                    ? implode('; ', $result->warnings) 
                    : "OMR engine did not produce a valid MusicXML artifact (Exit code: {$result->exitCode}).";
                throw new \RuntimeException($errorMsg);
            }

            // Sao chép raw.musicxml sang current.musicxml phục vụ chỉnh sửa (Immutable Raw -> Mutable Current)
            $currentXmlPath = $this->storageService->getCurrentMusicXmlPath($uuid);
            copy($rawXmlPath, $currentXmlPath);

            // Bước 4: Hoàn thành & Chuyển sang chế độ Sẵn sàng Soát lỗi (NEEDS_REVIEW)
            $project->status = 'NEEDS_REVIEW';
            $project->currentStep = 'needs_review';
            $project->progress = 100;
            $project->errorMessage = null;
            $this->projectRepo->save($project);

            return true;
        } catch (\Throwable $e) {
            $project->status = 'FAILED';
            $project->currentStep = 'failed';
            $project->errorMessage = $e->getMessage();
            $this->projectRepo->save($project);
            return false;
        }
    }
}
