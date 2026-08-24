<?php

declare(strict_types=1);

namespace App\Models;

/**
 * Model quản lý phiên bản MusicXML của một dự án (RAW, CURRENT, FINAL)
 */
class ScoreVersion
{
    public string $id;
    public string $projectUuid;
    public string $type; // RAW, CURRENT, FINAL
    public string $path;
    public string $createdAt;

    public function __construct(array $attributes = [])
    {
        $this->id = $attributes['id'] ?? uniqid('ver_');
        $this->projectUuid = $attributes['project_uuid'] ?? '';
        $this->type = $attributes['type'] ?? 'CURRENT';
        $this->path = $attributes['path'] ?? '';
        $this->createdAt = $attributes['created_at'] ?? date('Y-m-d H:i:s');
    }

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'project_uuid' => $this->projectUuid,
            'type' => $this->type,
            'path' => $this->path,
            'created_at' => $this->createdAt,
        ];
    }
}
