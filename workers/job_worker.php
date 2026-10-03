<?php

declare(strict_types=1);

require_once dirname(__DIR__) . '/app/autoload.php';

use App\Repositories\ConversionProjectRepository;
use App\Services\ConversionService;
use App\Services\JobQueueService;

$queue = new JobQueueService();
$conversion = new ConversionService();
$projects = new ConversionProjectRepository();
$runOnce = in_array('--once', $argv, true);
$pollSeconds = max(1, (int) (getenv('JOB_POLL_SECONDS') ?: 2));

$recovered = $queue->recoverInterrupted();
if ($recovered > 0) fwrite(STDOUT, "Recovered {$recovered} interrupted OMR job(s).\n");

do {
    $job = $queue->claimNext();
    if ($job === null) {
        if ($runOnce) break;
        sleep($pollSeconds);
        continue;
    }

    $uuid = (string) $job['project_uuid'];
    fwrite(STDOUT, "Processing OMR job {$job['job_id']} for {$uuid}.\n");
    try {
        if (!$projects->findByUuid($uuid)) throw new RuntimeException("Project {$uuid} no longer exists");
        $retryPageIndex = isset($job['page_index']) && is_int($job['page_index']) ? $job['page_index'] : null;
        if (!$conversion->processProject($uuid, $retryPageIndex)) {
            $project = $projects->findByUuid($uuid);
            throw new RuntimeException($project?->errorMessage ?: 'OMR processing failed');
        }
        $queue->complete($job);
        fwrite(STDOUT, "Completed OMR job {$job['job_id']}.\n");
    } catch (Throwable $error) {
        $queue->fail($job, $error->getMessage());
        fwrite(STDERR, "Failed OMR job {$job['job_id']}: {$error->getMessage()}\n");
    }
} while (true);
