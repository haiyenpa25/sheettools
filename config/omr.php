<?php

declare(strict_types=1);

if (!function_exists('env')) {
    function env(string $key, mixed $default = null): mixed {
        $val = getenv($key);
        if ($val === false) {
            return $_ENV[$key] ?? $_SERVER[$key] ?? $default;
        }
        return $val;
    }
}

return [
    /*
    |--------------------------------------------------------------------------
    | OMR Runtime & Binary Configurations
    |--------------------------------------------------------------------------
    | Cấu hình đường dẫn cho Java, Audiveris JAR, Tesseract OCR và Python.
    */

    'java_bin' => env('JAVA_BIN', 'java'),
    'audiveris_jar' => env('AUDIVERIS_JAR', 'C:\\Program Files\\Audiveris\\app\\audiveris.jar'),
    'tessdata_path' => env('TESSDATA_PREFIX', 'C:\\Program Files\\Tesseract-OCR\\tessdata'),
    'tesseract_bin' => env('TESSERACT_BIN', 'tesseract'),
    'python_bin' => env('PYTHON_BIN', 'python'),
    'timeout_seconds' => (int) env('OMR_TIMEOUT_SECONDS', 180),

    'default_languages' => 'vie+eng',

    /*
    |--------------------------------------------------------------------------
    | Quality & Security Boundaries
    |--------------------------------------------------------------------------
    */
    'max_file_size_mb' => 25,
    'max_pages' => 20,
    'allowed_extensions' => ['pdf', 'png', 'jpg', 'jpeg', 'tif', 'tiff'],
];
