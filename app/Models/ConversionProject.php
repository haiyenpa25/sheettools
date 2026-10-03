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
    public string $composer;
    public string $categorySlug;
    public string $categoryName;
    public string $songNumber;
    public string $status; // UPLOADED, QUEUED, PROCESSING, NEEDS_REVIEW, READY, FAILED
    public string $sourceFilename;
    public string $sourceType; // pdf, png, jpg
    public string $language; // vie+eng
    public bool $detectLyrics;
    public bool $detectChords;
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
        $this->composer = $attributes['composer'] ?? '';
        $this->categorySlug = $attributes['category_slug'] ?? '';
        $this->categoryName = $attributes['category_name'] ?? '';
        $this->songNumber = $attributes['song_number'] ?? '';
        $this->status = $attributes['status'] ?? 'UPLOADED';
        $this->sourceFilename = $attributes['source_filename'] ?? 'unknown.pdf';
        $this->sourceType = $attributes['source_type'] ?? 'pdf';
        $this->language = $attributes['language'] ?? 'vie+eng';
        $this->detectLyrics = (bool)($attributes['detect_lyrics'] ?? true);
        $this->detectChords = (bool)($attributes['detect_chords'] ?? true);
        $this->progress = (int)($attributes['progress'] ?? 0);
        $this->currentStep = $attributes['current_step'] ?? 'uploaded';
        $this->errorMessage = $attributes['error_message'] ?? null;
        $this->createdAt = $attributes['created_at'] ?? date('Y-m-d H:i:s');
        $this->updatedAt = $attributes['updated_at'] ?? date('Y-m-d H:i:s');
    }

    public static function generateUuid(): string
    {
        $bytes = random_bytes(16);
        $bytes[6] = chr((ord($bytes[6]) & 0x0f) | 0x40);
        $bytes[8] = chr((ord($bytes[8]) & 0x3f) | 0x80);
        $hex = bin2hex($bytes);
        return substr($hex, 0, 8) . '-' . substr($hex, 8, 4) . '-' . substr($hex, 12, 4)
            . '-' . substr($hex, 16, 4) . '-' . substr($hex, 20, 12);
    }

    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'uuid' => $this->uuid,
            'title' => $this->title,
            'composer' => $this->composer,
            'category_slug' => $this->categorySlug,
            'category_name' => $this->categoryName,
            'song_number' => $this->songNumber,
            'status' => $this->status,
            'source_filename' => $this->sourceFilename,
            'source_type' => $this->sourceType,
            'language' => $this->language,
            'detect_lyrics' => $this->detectLyrics,
            'detect_chords' => $this->detectChords,
            'progress' => $this->progress,
            'current_step' => $this->currentStep,
            'error_message' => $this->errorMessage,
            'created_at' => $this->createdAt,
            'updated_at' => $this->updatedAt,
        ];
    }
}
