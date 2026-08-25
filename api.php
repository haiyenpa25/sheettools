<?php

declare(strict_types=1);

// CORS Headers
header('Access-Control-Allow-Origin: *');
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

// 1. Health Check Endpoint
if ($uri === '/api/health') {
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
        if (!isset($_FILES['file'])) {
            jsonResponse(['error' => 'NO_FILE_UPLOADED', 'message' => 'No file uploaded in form field "file"'], 400);
        }

        $file = $_FILES['file'];
        $language = $_POST['language'] ?? 'vie+eng';

        $project = $conversionService->createProject($file['name'], $file['tmp_name'], ['language' => $language]);
        // Process project via truthful OMR pipeline
        $conversionService->processProject($project->uuid);

        // Fetch refreshed status after processing
        $fresh = $repo->findByUuid($project->uuid);
        jsonResponse(['data' => $fresh ? $fresh->toArray() : $project->toArray()], 201);
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
            $ok = $repo->delete($uuid);
            jsonResponse(['success' => $ok, 'message' => 'Project deleted successfully.']);
        }
        if ($method === 'PATCH') {
            $input = json_decode(file_get_contents('php://input'), true) ?: [];
            if (isset($input['title'])) $project->sourceFilename = $input['title'];
            if (isset($input['status'])) $project->status = $input['status'];
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

            if (empty($xmlData) || strlen($xmlData) < 50) {
                jsonResponse(['error' => 'INVALID_XML', 'message' => 'MusicXML data is invalid or empty.'], 400);
            }

            file_put_contents($xmlPath, $xmlData);
            jsonResponse(['success' => true, 'message' => 'MusicXML updated successfully.', 'bytes' => strlen($xmlData)]);
        }
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

    // POST /api/conversions/{uuid}/export
    if ($subPath === '/export' && $method === 'POST') {
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $format = $input['format'] ?? 'musicxml';
        $exportPath = $exportService->export($uuid, $format);

        if (!$exportPath || !file_exists($exportPath)) {
            jsonResponse(['error' => 'EXPORT_FAILED', 'message' => 'Failed to export score file.'], 500);
        }

        jsonResponse([
            'success' => true,
            'format' => $format,
            'download_url' => '/api/conversions/' . $uuid . '/download?format=' . $format,
            'file_name' => basename($exportPath),
        ]);
    }

    // GET /api/conversions/{uuid}/download
    if ($subPath === '/download' && $method === 'GET') {
        $format = $_GET['format'] ?? 'musicxml';
        $exportPath = $storageService->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'exports' . DIRECTORY_SEPARATOR . 'score_export.' . $format;
        if (!file_exists($exportPath)) {
            $exportPath = $exportService->export($uuid, $format);
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
