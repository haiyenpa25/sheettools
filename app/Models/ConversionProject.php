<?php

declare(strict_types=1);

namespace App\Models;

/**
 * Model quản lý thông tin và trạng thái dự án chuyển đổi bản nhạc
 */
class ConversionProject
{
    public string $id;
    public string $uuid;
    public string $title;
    public string $status; // UPLOADED, PROCESSING, NEEDS_REVIEW, READY, FAILED
    public string $sourceFilename;
    public string $sourceType; // pdf, png, jpg
    public string $language; // vie+eng
    public int $progress; // 0..100
    public string $currentStep; // preparing, recognizing_score, recognizing_lyrics, creating_xml, validating, ready
    public ?string $errorMessage;
    public string $createdAt;
    public string $updatedAt;

    public function __construct(array $attributes = [])
    {
        $this->id = $attributes['id'] ?? uniqid('proj_');
        $this->uuid = $attributes['uuid'] ?? $this->generateUuid();
        $this->title = $attributes['title'] ?? 'Bản nhạc chưa đặt tên';
        $this->status = $attributes['status'] ?? 'UPLOADED';
        $this->sourceFilename = $attributes['source_filename'] ?? 'unknown.pdf';
        $this->sourceType = $attributes['source_type'] ?? 'pdf';
        $this->language = $attributes['language'] ?? 'vie+eng';
        $this->progress = (int)($attributes['progress'] ?? 0);
        $this->currentStep = $attributes['current_step'] ?? 'uploaded';
        $this->errorMessage = $attributes['error_message'] ?? null;
        $this->createdAt = $attributes['created_at'] ?? date('Y-m-d H:i:s');
        $this->updatedAt = $attributes['updated_at'] ?? date('Y-m-d H:i:s');
    }

    public static function generateUuid(): string
    {
        return sprintf(
            '%04x%04x-%04x-%04x-%04x-%04x%04x%04x',
            mt_rand(0, 0xffff), mt_rand(0, 0xffff),
            mt_rand(0, 0xffff),
            mt_rand(0, 0x0fff) | 0x4000,
            mt_rand(0, 0x3fff) | 0x8000,
            mt_rand(0, 0xffff), mt_rand(0, 0xffff), mt_rand(0, 0xffff)
        );
    }

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'uuid' => $this->uuid,
            'title' => $this->title,
            'status' => $this->status,
            'source_filename' => $this->sourceFilename,
            'source_type' => $this->sourceType,
            'language' => $this->language,
            'progress' => $this->progress,
            'current_step' => $this->currentStep,
            'error_message' => $this->errorMessage,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
