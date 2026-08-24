<?php

declare(strict_types=1);

/**
 * Standard PSR-4 Autoloader for SheetTools
 * Tự động nạp các class thuộc App\ và Tests\ theo chuẩn PSR-4
 */
spl_autoload_register(function (string $class): void {
    $prefixes = [
        'App\\' => dirname(__DIR__) . '/app/',
        'Tests\\' => dirname(__DIR__) . '/tests/',
    ];

    foreach ($prefixes as $prefix => $baseDir) {
        $len = strlen($prefix);
        if (strncmp($prefix, $class, $len) !== 0) {
            continue;
        }

        $relativeClass = substr($class, $len);
        $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';

        if (file_exists($file)) {
            require_once $file;
            return;
        }
    }
});
