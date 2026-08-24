<?php

declare(strict_types=1);

namespace App\Models;

/**
 * Model quản lý cảnh báo hoặc lỗi nhận dạng nốt, lời, hợp âm
 */
class RecognitionIssue
{
    public string $id;
    public string $projectUuid;
    public string $partId;
    public int $measureNumber;
    public string $entityType; // note, lyric, chord, rhythm, clef
    public string $message;
    public string $severity; // info, warning, error
    public string $status; // open, resolved, ignored
    public array $boundingCoords;

    public function __construct(array $attributes = [])
    {
        $this->id = $attributes['id'] ?? uniqid('iss_');
        $this->projectUuid = $attributes['project_uuid'] ?? '';
        $this->partId = $attributes['part_id'] ?? 'P1';
        $this->measureNumber = (int)($attributes['measure_number'] ?? 1);
        $this->entityType = $attributes['entity_type'] ?? 'note';
        $this->message = $attributes['message'] ?? '';
        $this->severity = $attributes['severity'] ?? 'warning';
        $this->status = $attributes['status'] ?? 'open';
        $this->boundingCoords = $attributes['bounding_coords'] ?? [];
    }

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'project_uuid' => $this->projectUuid,
            'part_id' => $this->partId,
            'measure_number' => $this->measureNumber,
            'entity_type' => $this->entityType,
            'message' => $this->message,
            'severity' => $this->severity,
            'status' => $this->status,
            'bounding_coords' => $this->boundingCoords,
        ];
    }
}
