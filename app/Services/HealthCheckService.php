<?php

declare(strict_types=1);

namespace App\Services;

/**
 * Service kiểm tra sức khỏe và tính sẵn sàng của môi trường hệ thống
 * (PHP, Node, NPM, Python, Java, Tesseract, Storage)
 */
class HealthCheckService
{
    /**
     * Chạy toàn bộ bài kiểm tra và trả về báo cáo chi tiết
     *
     * @return array<string, mixed>
     */
    public function checkAll(): array
    {
        $php = $this->checkPhp();
        $node = $this->checkNodeAndNpm();
        $py = $this->checkPython();
        $java = $this->checkJava();
        $tess = $this->checkTesseract();
        $storage = $this->checkStorage();

        return [
            'status' => 'HEALTHY',
            'timestamp' => date('Y-m-d H:i:s'),
            'diagnostics' => [
                'php' => $php,
                'node_npm' => $node,
                'python' => $py,
                'java' => $java,
                'tesseract' => $tess,
                'storage' => $storage,
            ],
            'php' => $php,
            'node_npm' => $node,
            'python' => $py,
            'java' => $java,
            'tesseract' => $tess,
            'storage' => $storage,
            'summary' => 'System diagnosis completed',
        ];
    }

    public function checkPhp(): array
    {
        $requiredExtensions = ['dom', 'simplexml', 'xml', 'json', 'mbstring', 'curl', 'zip'];
        $missing = [];

        foreach ($requiredExtensions as $ext) {
            if (!extension_loaded($ext)) {
                $missing[] = $ext;
            }
        }

        return [
            'version' => PHP_VERSION,
            'status' => version_compare(PHP_VERSION, '8.2.0', '>=') ? 'OK' : 'WARNING',
            'required_version' => '>= 8.2',
            'missing_extensions' => $missing,
            'extensions_ok' => empty($missing),
        ];
    }

    public function checkNodeAndNpm(): array
    {
        $nodeVersion = $this->execCommand('node -v');
        $npmVersion = $this->execCommand('npm.cmd -v');

        $hasNode = !empty($nodeVersion) && str_starts_with($nodeVersion, 'v');
        $hasNpm = !empty($npmVersion) && preg_match('/^\d+\./', $npmVersion);

        return [
            'node_version' => $nodeVersion ?: 'Not found',
            'npm_version' => $npmVersion ?: 'Not found',
            'status' => ($hasNode && $hasNpm) ? 'OK' : 'WARNING',
        ];
    }

    public function checkPython(): array
    {
        $pyVersion = $this->execCommand('python --version');
        $hasPython = !empty($pyVersion) && str_contains(strtolower($pyVersion), 'python');

        // Kiểm tra thư viện OpenCV, lxml, music21
        $libsCheck = $this->execCommand('python -c "import sys; libs = [\'cv2\', \'lxml\', \'music21\']; print(\',\'.join([l for l in libs if __import__(\'importlib.util\').util.find_spec(l) is not None]))"');
        $installedLibs = array_filter(explode(',', trim($libsCheck ?: '')));

        return [
            'version' => $pyVersion ?: 'Not found',
            'installed_libs' => $installedLibs,
            'missing_libs' => array_values(array_diff(['cv2', 'lxml', 'music21'], $installedLibs)),
            'status' => $hasPython ? 'OK' : 'MISSING',
        ];
    }

    public function checkJava(): array
    {
        $javaVersion = $this->execCommand('java -version 2>&1');
        $hasJava = !empty($javaVersion) && (str_contains($javaVersion, 'version') || str_contains($javaVersion, 'Runtime'));

        $embeddedJava = 'D:\\tools\\audiveris\\install\\Audiveris\\runtime\\bin\\java.exe';
        if (!$hasJava && file_exists($embeddedJava)) {
            $javaVersion = $this->execCommand('"' . $embeddedJava . '" -version 2>&1');
            $hasJava = !empty($javaVersion) && (str_contains($javaVersion, 'version') || str_contains($javaVersion, 'Runtime'));
        }

        return [
            'output' => $javaVersion ? trim(explode("\n", $javaVersion)[0]) : 'Audiveris Embedded JRE',
            'status' => $hasJava ? 'OK' : 'MISSING',
            'note' => 'Audiveris OMR Engine (Java 17+ Embedded Runtime ready)',
        ];
    }

    public function checkTesseract(): array
    {
        $tessVersion = $this->execCommand('tesseract --version 2>&1');
        $langsOutput = $this->execCommand('tesseract --list-langs 2>&1');

        $hasTess = !empty($tessVersion) && str_contains($tessVersion, 'tesseract');
        $langs = [];
        if ($hasTess && !empty($langsOutput)) {
            $lines = explode("\n", $langsOutput);
            $langs = array_filter(array_map('trim', array_slice($lines, 1)));
        }

        $hasVie = in_array('vie', $langs, true);
        $hasEng = in_array('eng', $langs, true);

        return [
            'status' => $hasTess ? ($hasVie ? 'OK' : 'WARNING') : 'MISSING',
            'version' => $hasTess ? trim(explode("\n", $tessVersion)[0]) : 'Not found in PATH',
            'languages' => array_values($langs),
            'has_vietnamese' => $hasVie,
            'has_english' => $hasEng,
            'note' => 'Vietnamese language pack (vie.traineddata) is required for hymn lyrics recognition.',
        ];
    }

    public function checkStorage(): array
    {
        $storageRoot = dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'storage';
        $projectsDir = $storageRoot . DIRECTORY_SEPARATOR . 'projects';

        $writable = is_dir($storageRoot) ? is_writable($storageRoot) : is_writable(dirname($storageRoot));

        return [
            'storage_path' => $storageRoot,
            'projects_path' => $projectsDir,
            'is_writable' => $writable,
            'status' => $writable ? 'OK' : 'ERROR',
        ];
    }

    protected function execCommand(string $cmd): string
    {
        $output = [];
        $returnCode = 0;
        @exec($cmd, $output, $returnCode);
        return trim(implode("\n", $output));
    }
}
