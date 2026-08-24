<?php

declare(strict_types=1);

namespace App\Services;

require_once dirname(__DIR__) . '/DTOs/HarmonyDto.php';

use App\DTOs\HarmonyDto;
use DOMDocument;
use DOMElement;
use DOMXPath;

/**
 * Ghi và chuẩn hóa thẻ <harmony> vào MusicXML Document
 */
class HarmonyXmlWriter
{
    public function writeHarmony(string $xmlPath, HarmonyDto $harmony): bool
    {
        if (!file_exists($xmlPath)) return false;

        $doc = new DOMDocument();
        $doc->preserveWhiteSpace = false;
        $doc->formatOutput = true;
        if (!@$doc->load($xmlPath)) return false;

        $xpath = new DOMXPath($doc);
        $measures = $xpath->query("//part[@id='{$harmony->partId}']/measure[@number='{$harmony->measureNumber}']");

        if (!$measures || $measures->length === 0) return false;
        $measureNode = $measures->item(0);
        if (!$measureNode instanceof DOMElement) return false;

        // Tạo thẻ harmony
        $harmElem = $doc->createElement('harmony');
        
        $rootElem = $doc->createElement('root');
        $rootStepElem = $doc->createElement('root-step', $harmony->rootStep);
        $rootElem->appendChild($rootStepElem);
        if ($harmony->rootAlter !== null) {
            $rootElem->appendChild($doc->createElement('root-alter', $harmony->rootAlter));
        }
        $harmElem->appendChild($rootElem);

        $kindElem = $doc->createElement('kind', $harmony->kind);
        if ($harmony->displayText) {
            $kindElem->setAttribute('text', $harmony->displayText);
        }
        $harmElem->appendChild($kindElem);

        if ($harmony->bassStep) {
            $bassElem = $doc->createElement('bass');
            $bassElem->appendChild($doc->createElement('bass-step', $harmony->bassStep));
            if ($harmony->bassAlter !== null) {
                $bassElem->appendChild($doc->createElement('bass-alter', $harmony->bassAlter));
            }
            $harmElem->appendChild($bassElem);
        }

        if ($harmony->beatOffset > 0) {
            $harmElem->appendChild($doc->createElement('offset', (string)$harmony->beatOffset));
        }

        // Chèn vào trước nốt đầu tiên của measure
        $notes = $measureNode->getElementsByTagName('note');
        if ($notes->length > 0) {
            $measureNode->insertBefore($harmElem, $notes->item(0));
        } else {
            $measureNode->appendChild($harmElem);
        }

        // Atomic write
        $tempPath = $xmlPath . '.tmp';
        if ($doc->save($tempPath)) {
            $verify = new DOMDocument();
            if (@$verify->load($tempPath)) {
                rename($tempPath, $xmlPath);
                return true;
            }
            @unlink($tempPath);
        }

        return false;
    }
}
