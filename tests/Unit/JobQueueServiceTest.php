<?php

declare(strict_types=1);

use App\Services\JobQueueService;

$root = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'sheettools_queue_' . bin2hex(random_bytes(4));
$queue = new JobQueueService($root);
$jobId = $queue->enqueue('project-123');
assert($jobId !== '', 'Queue must return a durable job id');
$job = $queue->claimNext();
assert(is_array($job) && $job['project_uuid'] === 'project-123', 'Worker must claim queued project');
assert($queue->claimNext() === null, 'Claim must be atomic and remove pending job');
$queue->complete($job);
assert(count(glob($root . '/jobs/completed/*.json') ?: []) === 1, 'Completed job must be archived');

$queue->enqueue('project-456');
$interrupted = $queue->claimNext();
assert(is_array($interrupted), 'Second job must be claimable');
assert($queue->recoverInterrupted() === 1, 'Interrupted processing job must be recoverable');
assert(($queue->claimNext()['project_uuid'] ?? '') === 'project-456', 'Recovered job must return to pending queue');

$queue->enqueue('project-789', 2);
$pageJob = $queue->claimNext();
assert(($pageJob['page_index'] ?? null) === 2, 'Page retry must retain its zero-based page index');
try {
    $queue->enqueue('project-789', -1);
    assert(false, 'Negative page index must be rejected');
} catch (InvalidArgumentException) {
    // Expected.
}

echo "  [Unit] JobQueueServiceTest: PASS\n";
