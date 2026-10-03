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

        if (is_array($res)) {
            return $res;
        }

        $doc = new \DOMDocument();
        $previous = libxml_use_internal_errors(true);
        $loaded = $doc->load($xmlPath, LIBXML_NONET);
        $errors = array_map(static fn(\LibXMLError $error): string => trim($error->message), libxml_get_errors());
        libxml_clear_errors();
        libxml_use_internal_errors($previous);
        $isScore = $loaded && $doc->documentElement?->localName === 'score-partwise';
        return [
            'isValid' => $isScore,
            'errors' => $isScore ? [] : ($errors ?: ['Root element must be score-partwise']),
            'warnings' => ['MusicXML schema validator unavailable; structural validation only.'],
        ];
    }

    /**
     * Xuất tệp MusicXML theo định dạng yêu cầu (.xml, .musicxml, .mxl)
     */
    public function export(string $uuid, string $format = 'musicxml', string $variant = 'full'): ?string
    {
        $curPath = $this->storageService->getCurrentMusicXmlPath($uuid);
        if (!file_exists($curPath)) {
            $curPath = $this->storageService->getRawMusicXmlPath($uuid);
        }
        if (!file_exists($curPath) || filesize($curPath) < 50) return null;

        $variant = strtolower($variant);
        if (!in_array($variant, ['full', 'notation', 'lyrics'], true)) {
            return null;
        }

        // Kiểm tra tính hợp lệ của XML trước khi xuất
        $doc = new \DOMDocument();
        if (!@$doc->load($curPath)) {
            return null;
        }

        $exportDir = $this->storageService->getProjectDir($uuid) . DIRECTORY_SEPARATOR . 'export';
        if (!is_dir($exportDir)) {
            mkdir($exportDir, 0755, true);
        }

        if ($variant === 'lyrics') {
            if (!in_array(strtolower($format), ['txt', 'text'], true)) {
                return null;
            }
            $target = $exportDir . DIRECTORY_SEPARATOR . 'lyrics_only.txt';
            $content = $this->extractLyricsText($doc);
            return file_put_contents($target, $content) !== false ? $target : null;
        }

        if ($variant === 'notation') {
            $xpath = new \DOMXPath($doc);
            $lyrics = $xpath->query('//*[local-name()="lyric"]');
            if ($lyrics !== false) {
                foreach (iterator_to_array($lyrics) as $lyric) {
                    $lyric->parentNode?->removeChild($lyric);
                }
            }
        }

        $sourcePath = $curPath;
        $baseName = $variant === 'notation' ? 'score_notation_only' : 'score_full';
        if ($variant === 'notation') {
            $sourcePath = $exportDir . DIRECTORY_SEPARATOR . '_notation_source.musicxml';
            if ($doc->save($sourcePath) === false) {
                return null;
            }
        }

        switch (strtolower($format)) {
            case 'xml':
                $target = $exportDir . DIRECTORY_SEPARATOR . "{$baseName}.xml";
                copy($sourcePath, $target);
                return $target;

            case 'musicxml':
                $target = $exportDir . DIRECTORY_SEPARATOR . "{$baseName}.musicxml";
                copy($sourcePath, $target);
                return $target;

            case 'mxl':
                $targetMxl = $exportDir . DIRECTORY_SEPARATOR . "{$baseName}.mxl";
                if ($this->packageMxl($sourcePath, $targetMxl)) {
                    return $targetMxl;
                }
                return null;

            default:
                return null;
        }
    }

    /** Tạo bản lời thuần văn bản, tách rõ từng verse theo thứ tự nốt. */
    private function extractLyricsText(\DOMDocument $doc): string
    {
        $xpath = new \DOMXPath($doc);
        $verses = [];
        $lyrics = $xpath->query('//*[local-name()="lyric"]');
        if ($lyrics !== false) {
            foreach ($lyrics as $lyric) {
                if (!$lyric instanceof \DOMElement) continue;
                $number = trim($lyric->getAttribute('number')) ?: '1';
                $textNode = $xpath->query('./*[local-name()="text"]', $lyric)?->item(0);
                $text = trim($textNode?->textContent ?? '');
                if ($text !== '') $verses[$number][] = $text;
            }
        }
        uksort($verses, 'strnatcasecmp');
        $sections = [];
        foreach ($verses as $number => $syllables) {
            $sections[] = "VERSE {$number}\n" . implode(' ', $syllables);
        }
        return implode("\n\n", $sections) . "\n";
    }

    /**
     * Đóng gói MusicXML thành file nén .mxl kèm META-INF/container.xml
     */
    protected function packageMxl(string $sourceXmlPath, string $targetMxlPath): bool
    {
        if (!class_exists('ZipArchive')) {
            $exporterPy = dirname(__DIR__, 2) . '/workers/xml_tools/musescore_exporter.py';
            $cmd = sprintf('python %s --input %s --output %s --format mxl 2>&1', escapeshellarg($exporterPy), escapeshellarg($sourceXmlPath), escapeshellarg($targetMxlPath));
            @exec($cmd);
            return file_exists($targetMxlPath) && filesize($targetMxlPath) > 50;
        }

        $zip = new ZipArchive();
        if ($zip->open($targetMxlPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
            return false;
        }

        // 1. Thêm container.xml
        $containerXml = '<?xml version="1.0" encoding="UTF-8"?>
<container>
  <rootfiles>
    <rootfile full-path="score.xml" media-type="application/vnd.recordare.musicxml+xml"/>
  </rootfiles>
</container>';
        $zip->addFromString('mimetype', 'application/vnd.recordare.musicxml');
        $zip->setCompressionName('mimetype', ZipArchive::CM_STORE);
        $zip->addEmptyDir('META-INF');
        $zip->addFromString('META-INF/container.xml', $containerXml);

        // 2. Thêm file score.xml
        $zip->addFile($sourceXmlPath, 'score.xml');
        $zip->close();

        return file_exists($targetMxlPath);
    }
}
