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

require_once __DIR__ . '/app/Services/HealthCheckService.php';
require_once __DIR__ . '/app/Services/StorageService.php';
require_once __DIR__ . '/app/Services/ConversionService.php';
require_once __DIR__ . '/app/Services/MusicXmlService.php';
require_once __DIR__ . '/app/Services/LyricService.php';
require_once __DIR__ . '/app/Services/HarmonyService.php';
require_once __DIR__ . '/app/Services/NoteService.php';
require_once __DIR__ . '/app/Services/ExportService.php';
require_once __DIR__ . '/app/DTOs/LyricDto.php';
require_once __DIR__ . '/app/DTOs/NoteEditDto.php';

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
    if ($method === 'GET') {
        $repo = new \App\Repositories\ConversionProjectRepository();
        $projects = array_map(fn($p) => $p->toArray(), $repo->listAll());
        jsonResponse(['data' => $projects]);
    }

    if ($method === 'POST') {
        if (!isset($_FILES['file'])) {
            jsonResponse(['error' => 'No file uploaded'], 400);
        }

        $file = $_FILES['file'];
        $language = $_POST['language'] ?? 'vie+eng';

        $project = $conversionService->createProject($file['name'], $file['tmp_name'], ['language' => $language]);
        // Bắt đầu xử lý (Sync hoặc Dispatch Queue)
        $conversionService->processProject($project->uuid);

        jsonResponse(['data' => $project->toArray()], 201);
    }
}

// 3. Match /api/conversions/{uuid}/...
if (preg_match('#^/api/conversions/([a-zA-Z0-9_\-]+)(/.*)?$#', $uri, $matches)) {
    $uuid = $matches[1];
    $subPath = $matches[2] ?? '';

    $repo = new \App\Repositories\ConversionProjectRepository();
    $project = $repo->findByUuid($uuid);

    if (!$project) {
        // Nếu không có trong DB thì tạo mock/fallback project cho preview nếu cần
        $project = new \App\Models\ConversionProject([
            'uuid' => $uuid,
            'title' => 'HỠI THÁNH VƯƠNG, KÍP NGỰ LAI',
            'status' => 'READY',
            'progress' => 100,
        ]);
    }

    // GET /api/conversions/{uuid}
    if ($subPath === '' || $subPath === '/') {
        jsonResponse(['data' => $project->toArray()]);
    }

    // GET /api/conversions/{uuid}/musicxml
    if ($subPath === '/musicxml' && $method === 'GET') {
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);
        if (!file_exists($xmlPath)) {
            $fixture = dirname(__DIR__) . '/001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml';
            $xmlContent = file_exists($fixture) ? file_get_contents($fixture) : '';
        } else {
            $xmlContent = file_get_contents($xmlPath);
        }

        header('Content-Type: application/xml; charset=utf-8');
        echo $xmlContent;
        exit;
    }

    // GET /api/conversions/{uuid}/lyrics
    if ($subPath === '/lyrics' && $method === 'GET') {
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);
        $xmlContent = file_exists($xmlPath) ? file_get_contents($xmlPath) : file_get_contents(__DIR__ . '/001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml');
        $lyrics = $musicXmlService->extractLyrics($xmlContent);
        jsonResponse(['data' => $lyrics]);
    }

    // PATCH /api/conversions/{uuid}/lyrics
    if (str_starts_with($subPath, '/lyrics') && $method === 'PATCH') {
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);
        
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
        $xmlContent = file_exists($xmlPath) ? file_get_contents($xmlPath) : file_get_contents(__DIR__ . '/001 HỠI THÁNH VƯƠNG, KÍP NGỰ LAI.xml');
        $harmonies = $musicXmlService->extractHarmonies($xmlContent);
        jsonResponse(['data' => $harmonies]);
    }

    // POST /api/conversions/{uuid}/harmonies
    if ($subPath === '/harmonies' && ($method === 'POST' || $method === 'PATCH')) {
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);

        $chordText = $input['chord'] ?? 'G';
        $measure = (int)($input['measureNumber'] ?? 1);
        $offset = (float)($input['beatOffset'] ?? 0.0);

        $harmonyDto = $harmonyService->parseChordString($chordText, 'P1', $measure, $offset);
        $ok = $harmonyService->saveHarmony($xmlPath, $harmonyDto);

        jsonResponse(['success' => $ok, 'data' => $harmonyDto]);
    }

    // PATCH /api/conversions/{uuid}/notes
    if (str_starts_with($subPath, '/notes') && $method === 'PATCH') {
        $input = json_decode(file_get_contents('php://input'), true) ?: [];
        $xmlPath = $storageService->getCurrentMusicXmlPath($uuid);

        $noteDto = new NoteEditDto(
            noteId: $input['noteId'] ?? 'n_0',
            partId: $input['partId'] ?? 'P1',
            measureNumber: (int)($input['measureNumber'] ?? 1),
            step: $input['step'] ?? 'G',
            octave: (int)($input['octave'] ?? 4),
            accidental: $input['accidental'] ?? null,
            duration: $input['duration'] ?? 'quarter'
        );

        $ok = $noteService->updateNote($xmlPath, $noteDto);
        jsonResponse(['success' => $ok, 'data' => $noteDto]);
    }

    // GET /api/conversions/{uuid}/validate
    if ($subPath === '/validate') {
        jsonResponse($exportService->validateProject($uuid));
    }

    // POST /api/conversions/{uuid}/export
    if ($subPath === '/export') {
        $format = $_GET['format'] ?? 'musicxml';
        $filePath = $exportService->export($uuid, $format);
        if ($filePath && file_exists($filePath)) {
            header('Content-Type: application/octet-stream');
            header('Content-Disposition: attachment; filename="' . basename($filePath) . '"');
            readfile($filePath);
            exit;
        }
        jsonResponse(['error' => 'Export failed'], 500);
    }
}

// Fallback 404
jsonResponse(['error' => 'API Route not found', 'path' => $uri], 404);
