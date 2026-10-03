<?php

declare(strict_types=1);

namespace App\Services;

/** Durable filesystem queue shared by the web and OMR worker containers. */
final class JobQueueService
{
    public function __construct(private readonly ?string $storageRoot = null)
    {
    }

    public function enqueue(string $projectUuid, ?int $pageIndex = null): string
    {
        if ($pageIndex !== null && $pageIndex < 0) {
            throw new \InvalidArgumentException('Page index must be non-negative.');
        }
        $this->ensureDirectories();
        $jobId = date('YmdHis') . '-' . bin2hex(random_bytes(6));
        $payload = [
            'job_id' => $jobId,
            'project_uuid' => $projectUuid,
            'created_at' => date(DATE_ATOM),
            'attempts' => 0,
        ];
        if ($pageIndex !== null) {
            $payload['page_index'] = $pageIndex;
        }
        $temporary = $this->pendingDir() . DIRECTORY_SEPARATOR . ".{$jobId}.tmp";
        $target = $this->pendingDir() . DIRECTORY_SEPARATOR . "{$jobId}.json";
        file_put_contents($temporary, json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
        if (!rename($temporary, $target)) {
            @unlink($temporary);
            throw new \RuntimeException('Could not publish OMR job');
        }
        return $jobId;
    }

    public function claimNext(): ?array
    {
        $this->ensureDirectories();
        $jobs = glob($this->pendingDir() . DIRECTORY_SEPARATOR . '*.json') ?: [];
        sort($jobs, SORT_STRING);
        foreach ($jobs as $pendingPath) {
            $processingPath = $this->processingDir() . DIRECTORY_SEPARATOR . basename($pendingPath);
            if (!@rename($pendingPath, $processingPath)) continue;
            $payload = json_decode((string) file_get_contents($processingPath), true);
            if (!is_array($payload) || empty($payload['project_uuid'])) {
                $this->finish($processingPath, false, 'Invalid job payload');
                continue;
            }
            $payload['attempts'] = (int) ($payload['attempts'] ?? 0) + 1;
            $payload['processing_path'] = $processingPath;
            $payload['started_at'] = date(DATE_ATOM);
            file_put_contents($processingPath, json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
            return $payload;
        }
        return null;
    }

    public function complete(array $job): void
    {
        $this->finish((string) ($job['processing_path'] ?? ''), true);
    }

    public function fail(array $job, string $error): void
    {
        $this->finish((string) ($job['processing_path'] ?? ''), false, $error);
    }

    /** Recover jobs interrupted by a container restart. Page checkpoints make reprocessing resumable. */
    public function recoverInterrupted(): int
    {
        $this->ensureDirectories();
        $count = 0;
        foreach (glob($this->processingDir() . DIRECTORY_SEPARATOR . '*.json') ?: [] as $path) {
            $target = $this->pendingDir() . DIRECTORY_SEPARATOR . basename($path);
            if (@rename($path, $target)) $count++;
        }
        return $count;
    }

    /** Remove queued work for a project. Processing workers are stopped from
     * resurrecting it by the repository's trash tombstone. */
    public function cancelProject(string $projectUuid): int
    {
        $this->ensureDirectories();
        $cancelled = 0;
        foreach (glob($this->pendingDir() . DIRECTORY_SEPARATOR . '*.json') ?: [] as $path) {
            $payload = json_decode((string) file_get_contents($path), true);
            if (($payload['project_uuid'] ?? '') !== $projectUuid) continue;
            if (unlink($path)) $cancelled++;
        }
        return $cancelled;
    }

    private function finish(string $processingPath, bool $success, ?string $error = null): void
    {
        if ($processingPath === '' || !is_file($processingPath)) return;
        $payload = json_decode((string) file_get_contents($processingPath), true) ?: [];
        $payload['finished_at'] = date(DATE_ATOM);
        $payload['status'] = $success ? 'COMPLETED' : 'FAILED';
        if ($error !== null) $payload['error'] = $error;
        file_put_contents($processingPath, json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
        $destination = ($success ? $this->completedDir() : $this->failedDir()) . DIRECTORY_SEPARATOR . basename($processingPath);
        rename($processingPath, $destination);
    }

    private function root(): string
    {
        return ($this->storageRoot ?: dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'storage') . DIRECTORY_SEPARATOR . 'jobs';
    }

    private function pendingDir(): string { return $this->root() . DIRECTORY_SEPARATOR . 'pending'; }
    private function processingDir(): string { return $this->root() . DIRECTORY_SEPARATOR . 'processing'; }
    private function completedDir(): string { return $this->root() . DIRECTORY_SEPARATOR . 'completed'; }
    private function failedDir(): string { return $this->root() . DIRECTORY_SEPARATOR . 'failed'; }

    private function ensureDirectories(): void
    {
        foreach ([$this->pendingDir(), $this->processingDir(), $this->completedDir(), $this->failedDir()] as $directory) {
            if (!is_dir($directory) && !mkdir($directory, 0775, true) && !is_dir($directory)) {
                throw new \RuntimeException("Could not create queue directory: {$directory}");
            }
        }
    }
}
