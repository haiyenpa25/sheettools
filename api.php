<?php

declare(strict_types=1);

// CORS Headers
$corsOrigin = getenv('CORS_ORIGIN') ?: 'http://localhost:5173';
header('Access-Control-Allow-Origin: ' . $corsOrigin);
header('Vary: Origin');
header('Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once __DIR__ . '/app/autoload.php';

use App\Services\HealthCheckService;
use App\Services\StorageService;
use App\Services\ConversionService;
use App\Services\MusicXmlService;
use App\Services\LyricService;
use App\Services\HarmonyService;
use App\Services\NoteService;
use App\Services\ExportService;
use App\Services\JobQueueService;
use App\Services\PageArtifactService;
use App\DTOs\LyricDto;
use App\DTOs\NoteEditDto;
use App\Repositories\ConversionProjectRepository;

$storageService = new StorageService();
$conversionService = new ConversionService();
$musicXmlService = new MusicXmlService();
$lyricService = new LyricService();
$harmonyService = new HarmonyService();
$noteService = new NoteService();
$exportService = new ExportService();
$healthService = new HealthCheckService();
$jobQueue = new JobQueueService();
$pageArtifacts = new PageArtifactService();

$rawUri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$uri = preg_replace('#^/SheetTools(?:/api\.php)?#', '', $rawUri);
$method = $_SERVER['REQUEST_METHOD'];

// Helper JSON response
function jsonResponse(mixed $data, int $status = 200): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

// 1. Public liveness endpoint
if ($uri === '/api/health') {
    jsonResponse(['ok' => true]);
}

$apiToken = getenv('SHEETTOOLS_API_TOKEN') ?: '';
if ($apiToken !== '') {
    $authorization = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    $providedToken = str_starts_with($authorization, 'Bearer ') ? substr($authorization, 7) : '';
    if (!hash_equals($apiToken, $providedToken)) {
        jsonResponse(['error' => 'UNAUTHORIZED', 'message' => 'A valid bearer token is required.'], 401);
    }
}

if ($uri === '/api/health/full' && $method === 'GET') {
    jsonResponse($healthService->checkAll());
}

// 2. List or Create Conversions
if ($uri === '/api/conversions') {
    $repo = new ConversionProjectRepository();

    if ($method === 'GET') {
        $projects = array_map(fn($p) => $p->toArray(), $repo->listAll());
        jsonResponse(['data' => $projects]);
    }

    if ($method === 'POST') {
        $language = $_POST['language'] ?? 'vie+eng';
        $detectLyrics = filter_var($_POST['detect_lyrics'] ?? true, FILTER_VALIDATE_BOOLEAN);
        $detectChords = filter_var($_POST['detect_chords'] ?? true, FILTER_VALIDATE_BOOLEAN);

        // 1. Tạo từ tệp tải lên (PDF, PNG, JPG, XML)
        if (isset($_FILES['file'])) {
            $file = $_FILES['file'];
            $config = require __DIR__ . '/config/omr.php';
            $extension = strtolower(pathinfo((string)($file['name'] ?? ''), PATHINFO_EXTENSION));
            $allowedMimeTypes = [
                'pdf' => ['application/pdf'],
                'png' => ['image/png'],
                'jpg' => ['image/jpeg'],
                'jpeg' => ['image/jpeg'],
            ];
            $error = (int)($file['error'] ?? UPLOAD_ERR_NO_FILE);
            $size = (int)($file['size'] ?? 0);
            $maxBytes = (int)$config['max_file_size_mb'] * 1024 * 1024;
            $isHttpUpload = PHP_SAPI === 'cli' || is_uploaded_file((string)($file['tmp_name'] ?? ''));
            $mime = $isHttpUpload && is_file((string)$file['tmp_name'])
                ? (new finfo(FILEINFO_MIME_TYPE))->file((string)$file['tmp_name'])
                : false;
            if ($error !== UPLOAD_ERR_OK || !$isHttpUpload || $size < 1 || $size > $maxBytes || !isset($allowedMimeTypes[$extension]) || !in_array($mime, $allowedMimeTypes[$extension], true)) {
                jsonResponse(['error' => 'INVALID_UPLOAD', 'message' => 'Upload must be a valid PDF, PNG, or JPEG within the configured size limit.'], 422);
            }
            try {
                $project = $conversionService->createProject((string)$file['name'], (string)$file['tmp_name'], [
                'language' => $language,
                'detect_lyrics' => $detectLyrics,
                'detect_chords' => $detectChords,
                ]);
            } catch (InvalidArgumentException $e) {
                jsonResponse(['error' => 'INVALID_UPLOAD', 'message' => $e->getMessage()], 422);
            }
            $project->status = 'QUEUED';
            $project->currentStep = 'queued';
            $project->progress = 5;
            $repo->save($project);
            $jobId = $jobQueue->enqueue($project->uuid);
            jsonResponse(['data' => $project->toArray(), 'job_id' => $jobId], 202);
        }

        // 2. Tạo trực tiếp từ JSON payload (VD: nhập XML, cấu trúc mới từ Wizard)
        $rawInput = file_get_contents('php://input');
        if (!empty($rawInput) && str_starts_with(trim($rawInput), '{')) {
            $json = json_decode($rawInput, true);
            $title = $json['title'] ?? 'Bản nhạc mới';
            $xmlContent = $json['xmlContent'] ?? $json['xml'] ?? '';
            $filename = $json['filename'] ?? ($title . '.musicxml');

            $tempFile = tempnam(sys_get_temp_dir(), 'proj_init_');
            file_put_contents($tempFile, $xmlContent);

            try {
                $project = $conversionService->createProject($filename, $tempFile, ['language' => $language]);
            } catch (InvalidArgumentException $e) {
                @unlink($tempFile);
                jsonResponse(['error' => 'INVALID_SOURCE', 'message' => $e->getMessage()], 422);
            }
            if (!empty($xmlContent) && strlen($xmlContent) > 50) {
                $rawXmlPath = $storageService->getRawMusicXmlPath($project->uuid);
                $curXmlPath = $storageService->getCurrentMusicXmlPath($project->uuid);
                file_put_contents($rawXmlPath, $xmlContent);
                file_put_contents($curXmlPath, $xmlContent);
                $project->status = 'READY';
                $project->progress = 100;
                $project->currentStep = 'ready';
                $repo->save($project);
            }
            @unlink($tempFile);
            jsonResponse(['data' => $project->toArray()], 201);
        }

        jsonResponse(['error' => 'NO_FILE_OR_DATA', 'message' => 'Vui lòng cung cấp tệp upload hoặc dữ liệu JSON.'], 400);
    }
}

// Library trash endpoints are resolved before active-project lookup.
if ($uri === '/api/trash' && $method === 'GET') {
    $repo = new ConversionProjectRepository();
    jsonResponse(['data' => array_map(fn($p) => $p->toArray(), $repo->listDeleted())]);
}

if (preg_match('#^/api/trash/([a-zA-Z0-9_\-]+)/(restore|purge)$#', $uri, $trashMatch)) {
    $repo = new ConversionProjectRepository();
    $uuid = $trashMatch[1];
    $action = $trashMatch[2];
    if ($action === 'restore' && $method === 'POST') {
        $ok = $repo->restore($uuid);
        jsonResponse(['success' => $ok], $ok ? 200 : 404);
    }
    if ($action === 'purge' && $method === 'DELETE') {
        $ok = $repo->purge($uuid);
        jsonResponse(['success' => $ok], $ok ? 200 : 404);
    }
}

// 3. Match /api/conversions/{uuid}/...
if (preg_match('#^/api/conversions/([a-zA-Z0-9_\-]+)(/.*)?$#', $uri, $matches)) {
    $uuid = $matches[1];
    $subPath = $matches[2] ?? '';

    $repo = new ConversionProjectRepository();
    $project = $repo->findByUuid($uuid);

    if (!$project) {
        jsonResponse(['error' => 'PROJECT_NOT_FOUND', 'message' => "Project with UUID '{$uuid}' does not exist."], 404);
    }

    // GET /api/conversions/{uuid}
    if ($subPath === '' || $subPath === '/') {
        if ($method === 'GET') {
            jsonResponse(['data' => $project->toArray()]);
        }
        if ($method === 'DELETE') {
            $cancelledJobs = $jobQueue->cancelProject($uuid);
            $ok = $repo->delete($uuid);
            jsonResponse(['success' => $ok, 'cancelled_jobs' => $cancelledJobs, 'message' => 'Project moved to trash.'], $ok ? 200 : 500);
        }
        if ($method === 'PATCH') {
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            if (isset($input['title'])) $project->title = trim((string)$input['title']);
            if (isset($input['composer'])) $project->composer = trim((string)$input['composer']);
            if (isset($input['category_slug'])) $project->categorySlug = trim((string)$input['category_slug']);
            if (isset($input['category_name'])) $project->categoryName = trim((string)$input['category_name']);
            if (isset($input['song_number'])) $project->songNumber = trim((string)$input['song_number']);
            if (isset($input['status'])) {
                $allowedTransitions = [
                    'UPLOADED' => ['QUEUED'], 'QUEUED' => ['FAILED'], 'PROCESSING' => ['FAILED'],
                    'NEEDS_REVIEW' => ['READY', 'FAILED'], 'READY' => ['NEEDS_REVIEW'], 'FAILED' => ['QUEUED'],
                ];
                $nextStatus = (string)$input['status'];
                if (!in_array($nextStatus, $allowedTransitions[$project->status] ?? [], true)) {
                    jsonResponse(['error' => 'INVALID_STATUS_TRANSITION'], 422);
                }
                $project->status = $nextStatus;
            }
            $repo->save($project);
            jsonResponse(['success' => true, 'data' => $project->toArray()]);
        }
    }

    // GET, PUT, PATCH /api/conversions/{uuid}/musicxml
    if ($subPath === '/musicxml') {
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);

        if ($method === 'GET') {
            if (!file_exists($xmlPath) || filesize($xmlPath) < 50) {
                $rawPath = $storageService->getRawMusicXmlPath($uuid);
                if (file_exists($rawPath) && filesize($rawPath) >= 50) {
                    $xmlPath = $rawPath;
                } else {
                    jsonResponse(['error' => 'MUSICXML_NOT_READY', 'message' => 'MusicXML artifact is not yet available for this project.'], 409);
                }
            }

            header('Content-Type: application/xml; charset=utf-8');
            readfile($xmlPath);
            exit;
        }

        if (in_array($method, ['PUT', 'PATCH'], true)) {
            $rawInput = file_get_contents('php://input');
            $xmlData = '';
            if (str_starts_with(trim($rawInput), '{')) {
                $json = json_decode($rawInput, true);
                $xmlData = $json['xml'] ?? $json['xmlContent'] ?? '';
            } else {
                $xmlData = $rawInput;
            }

            $xmlDoc = new DOMDocument();
            $previous = libxml_use_internal_errors(true);
            $validXml = $xmlData !== '' && $xmlDoc->loadXML($xmlData, LIBXML_NONET) && $xmlDoc->documentElement?->localName === 'score-partwise';
            libxml_clear_errors();
            libxml_use_internal_errors($previous);
            if (!$validXml) {
                jsonResponse(['error' => 'INVALID_XML', 'message' => 'A valid score-partwise MusicXML document is required.'], 422);
            }

            file_put_contents($xmlPath, $xmlData);
            jsonResponse(['success' => true, 'message' => 'MusicXML updated successfully.', 'bytes' => strlen($xmlData)]);
        }
    }

    // GET /api/conversions/{uuid}/lyrics
    if ($subPath === '/lyrics-artifact' && $method === 'GET') {
        $artifactPath = $storageService->getLyricsArtifactPath($uuid);
        if (!file_exists($artifactPath)) {
            jsonResponse(['error' => 'LYRICS_ARTIFACT_NOT_READY', 'message' => 'Independent OCR lyrics artifact is unavailable.'], 404);
        }
        header('Content-Type: application/json; charset=utf-8');
        readfile($artifactPath);
        exit;
    }

    if ($subPath === '/document-artifact' && $method === 'GET') {
        $artifactPath = $storageService->getDocumentArtifactPath($uuid);
        if (!file_exists($artifactPath)) {
            jsonResponse(['error' => 'DOCUMENT_ARTIFACT_NOT_READY', 'message' => 'Semantic page document is unavailable.'], 404);
        }
        header('Content-Type: application/json; charset=utf-8');
        readfile($artifactPath);
        exit;
    }

    // GET /api/conversions/{uuid}/lyrics
    if ($subPath === '/lyrics' && $method === 'GET') {
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);
        if (!file_exists($xmlPath)) {
            $xmlPath = $storageService->getRawMusicXmlPath($uuid);
        }
        if (!file_exists($xmlPath)) {
            jsonResponse(['error' => 'MUSICXML_NOT_READY', 'message' => 'MusicXML not available.'], 409);
        }

        $xmlContent = file_get_contents($xmlPath);
        $lyrics = $musicXmlService->extractLyrics($xmlContent);
        jsonResponse(['data' => $lyrics]);
    }

    // PATCH /api/conversions/{uuid}/lyrics
    if (str_starts_with($subPath, '/lyrics') && $method === 'PATCH') {
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);

        if (!file_exists($xmlPath)) {
            jsonResponse(['error' => 'MUSICXML_NOT_READY', 'message' => 'Current MusicXML not ready for editing.'], 409);
        }
        
        $lyricDto = new LyricDto(
            id: $input['id'] ?? uniqid('lyr_'),
            partId: $input['partId'] ?? 'P1',
            staff: 1,
            measureNumber: (int)($input['measureNumber'] ?? 1),
            voice: 1,
            noteId: $input['noteId'] ?? 'n_0',
            verseNumber: (int)($input['verseNumber'] ?? 1),
            text: $input['text'] ?? '',
            syllabic: $input['syllabic'] ?? 'single'
        );

        $ok = $lyricService->updateLyric($xmlPath, $lyricDto);
        jsonResponse(['success' => $ok, 'data' => $lyricDto]);
    }

    // GET /api/conversions/{uuid}/harmonies
    if ($subPath === '/harmonies' && $method === 'GET') {
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);
        if (!file_exists($xmlPath)) {
            $xmlPath = $storageService->getRawMusicXmlPath($uuid);
        }
        if (!file_exists($xmlPath)) {
            jsonResponse(['error' => 'MUSICXML_NOT_READY', 'message' => 'MusicXML not available.'], 409);
        }

        $xmlContent = file_get_contents($xmlPath);
        $harmonies = $musicXmlService->extractHarmonies($xmlContent);
        jsonResponse(['data' => $harmonies]);
    }

    // PATCH /api/conversions/{uuid}/harmonies
    if (str_starts_with($subPath, '/harmonies') && $method === 'PATCH') {
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);

        if (!file_exists($xmlPath)) {
            jsonResponse(['error' => 'MUSICXML_NOT_READY', 'message' => 'Current MusicXML not ready for editing.'], 409);
        }

        $harmonyDto = $harmonyService->parseChordString(
            $input['chordText'] ?? 'C',
            $input['partId'] ?? 'P1',
            (int)($input['measureNumber'] ?? 1)
        );

        $ok = $harmonyService->addOrUpdateHarmony($xmlPath, $harmonyDto);
        jsonResponse(['success' => $ok, 'data' => $harmonyDto]);
    }

    // PATCH /api/conversions/{uuid}/notes
    if (str_starts_with($subPath, '/notes') && $method === 'PATCH') {
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);

        if (!file_exists($xmlPath)) {
            jsonResponse(['error' => 'MUSICXML_NOT_READY', 'message' => 'Current MusicXML not ready for editing.'], 409);
        }

        $noteDto = new NoteEditDto(
            partId: $input['partId'] ?? 'P1',
            staff: 1,
            measureNumber: (int)($input['measureNumber'] ?? 1),
            voice: 1,
            noteIndex: (int)($input['noteIndex'] ?? 1),
            step: $input['step'] ?? 'C',
            octave: (int)($input['octave'] ?? 4),
            accidental: $input['accidental'] ?? null,
            duration: $input['duration'] ?? 'quarter',
            isDotted: (bool)($input['isDotted'] ?? false),
            isRest: (bool)($input['isRest'] ?? false)
        );

        $ok = $noteService->updateNoteDetail($xmlPath, $noteDto);
        jsonResponse(['success' => $ok, 'data' => $noteDto]);
    }

    // GET /api/conversions/{uuid}/validate
    if ($subPath === '/validate' && $method === 'GET') {
        $res = $exportService->validateProject($uuid);
        jsonResponse($res);
    }

    // GET /api/conversions/{uuid}/pages and /pages/{zero-based-index}
    if ($subPath === '/pages' && $method === 'GET') {
        $pages = array_map(
            static fn(array $page): array => $page + [
                'url' => '/api/conversions/' . $uuid . '/pages/' . $page['index'],
            ],
            $pageArtifacts->list($uuid)
        );
        jsonResponse(['data' => $pages, 'page_count' => count($pages)]);
    }

    if ($subPath === '/page-progress' && $method === 'GET') {
        $path = $storageService->getPageProgressPath($uuid);
        $progress = is_file($path) ? json_decode((string) file_get_contents($path), true) : null;
        if (!is_array($progress)) {
            jsonResponse(['error' => 'PAGE_PROGRESS_NOT_READY'], 404);
        }
        jsonResponse(['data' => $progress]);
    }

    if (preg_match('#^/pages/(\d+)$#', $subPath, $pageMatch) && $method === 'GET') {
        $page = $pageArtifacts->resolve($uuid, (int) $pageMatch[1]);
        if ($page === null) {
            jsonResponse(['error' => 'PAGE_NOT_FOUND', 'message' => 'Rendered source page is unavailable.'], 404);
        }
        header('Content-Type: ' . $page['mime_type']);
        header('Content-Length: ' . filesize($page['path']));
        header('Cache-Control: private, max-age=3600');
        readfile($page['path']);
        exit;
    }

    if (preg_match('#^/pages/(\d+)/(regions|regions-debug)$#', $subPath, $pageMatch) && $method === 'GET') {
        $artifact = $pageArtifacts->resolveLayout($uuid, (int) $pageMatch[1], $pageMatch[2] === 'regions-debug');
        if ($artifact === null) {
            jsonResponse(['error' => 'PAGE_LAYOUT_NOT_READY'], 404);
        }
        header('Content-Type: ' . $artifact['mime_type']);
        header('Cache-Control: private, no-store');
        readfile($artifact['path']);
        exit;
    }

    // POST /api/conversions/{uuid}/pages/{zero-based-index}/retry
    if (preg_match('#^/pages/(\d+)/retry$#', $subPath, $pageMatch) && $method === 'POST') {
        $pageIndex = (int) $pageMatch[1];
        if ($pageArtifacts->resolve($uuid, $pageIndex) === null) {
            jsonResponse(['error' => 'PAGE_NOT_FOUND', 'message' => 'Rendered source page is unavailable.'], 404);
        }
        if (in_array($project->status, ['QUEUED', 'PROCESSING'], true)) {
            jsonResponse(['error' => 'ALREADY_RUNNING', 'message' => 'Project is already queued or processing.'], 409);
        }
        $project->status = 'QUEUED';
        $project->currentStep = 'queued';
        $project->progress = 5;
        $project->errorMessage = null;
        @unlink($storageService->getPageProgressPath($uuid));
        $repo->save($project);
        $jobId = $jobQueue->enqueue($uuid, $pageIndex);
        jsonResponse(['success' => true, 'job_id' => $jobId, 'page_index' => $pageIndex, 'data' => $project->toArray()], 202);
    }

    // POST /api/conversions/{uuid}/retry — resume from durable per-page checkpoints.
    if ($subPath === '/retry' && $method === 'POST') {
        if (in_array($project->status, ['QUEUED', 'PROCESSING'], true)) {
            jsonResponse(['error' => 'ALREADY_RUNNING', 'message' => 'Project is already queued or processing.'], 409);
        }
        $project->status = 'QUEUED';
        $project->currentStep = 'queued';
        $project->progress = 5;
        $project->errorMessage = null;
        @unlink($storageService->getPageProgressPath($uuid));
        $repo->save($project);
        $jobId = $jobQueue->enqueue($uuid);
        jsonResponse(['success' => true, 'job_id' => $jobId, 'data' => $project->toArray()], 202);
    }

    // POST /api/conversions/{uuid}/export
    if ($subPath === '/export' && $method === 'POST') {
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $format = $input['format'] ?? 'musicxml';
        $variant = $input['variant'] ?? 'full';
        $duplicateChorus = ($input['duplicate_chorus'] ?? false) === true;
        $exportPath = $exportService->export($uuid, $format, $variant, $duplicateChorus);

        if (!$exportPath || !file_exists($exportPath)) {
            jsonResponse(['error' => 'EXPORT_FAILED', 'message' => 'Failed to export score file.'], 500);
        }

        jsonResponse([
            'success' => true,
            'format' => $format,
            'variant' => $variant,
            'download_url' => '/api/conversions/' . $uuid . '/download?format=' . $format . '&variant=' . $variant . ($duplicateChorus ? '&duplicate_chorus=1' : ''),
            'file_name' => basename($exportPath),
        ]);
    }

    // GET /api/conversions/{uuid}/download
    if ($subPath === '/download' && $method === 'GET') {
        $format = $_GET['format'] ?? 'musicxml';
        $variant = $_GET['variant'] ?? 'full';
        if (!in_array($format, ['xml', 'musicxml', 'mxl'], true) || !in_array($variant, ['full', 'notation', 'lyrics'], true)) {
            jsonResponse(['error' => 'INVALID_EXPORT_OPTIONS', 'message' => 'Unsupported export format or variant.'], 400);
        }
        $baseName = $variant === 'lyrics' ? 'lyrics_only' : ($variant === 'notation' ? 'score_notation_only' : 'score_full');
        $duplicateChorus = ($_GET['duplicate_chorus'] ?? '') === '1';
        if ($variant === 'full' && $duplicateChorus) $baseName = 'score_full_chorus_all_verses';
        $extension = $variant === 'lyrics' ? 'txt' : $format;
        $exportPath = $storageService->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'export' . DIRECTORY_SEPARATOR . $baseName . '.' . $extension;
        if (!file_exists($exportPath)) {
            $exportPath = $exportService->export($uuid, $format, $variant, $duplicateChorus);
        }

        if (!$exportPath || !file_exists($exportPath)) {
            jsonResponse(['error' => 'FILE_NOT_FOUND', 'message' => 'Export file not found.'], 404);
        }

        header('Content-Description: File Transfer');
        header('Content-Type: application/octet-stream');
        header('Content-Disposition: attachment; filename="' . basename($exportPath) . '"');
        header('Expires: 0');
        header('Cache-Control: must-revalidate');
        header('Pragma: public');
        header('Content-Length: ' . filesize($exportPath));
        readfile($exportPath);
        exit;
    }
}

// 404 Default
jsonResponse(['error' => 'NOT_FOUND', 'message' => 'Route not found: ' . $uri], 404);
