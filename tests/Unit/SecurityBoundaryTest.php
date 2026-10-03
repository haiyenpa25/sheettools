<?php

declare(strict_types=1);

use App\Models\ConversionProject;
use App\Services\MusicXmlIndexService;

$uuid = ConversionProject::generateUuid();
assert(preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/', $uuid) === 1);

$doc = new DOMDocument();
$doc->loadXML('<score-partwise><part id="P1"><measure number="1"><note><pitch><step>C</step><octave>4</octave></pitch><voice>1</voice><staff>1</staff></note></measure></part></score-partwise>');
$index = new MusicXmlIndexService();
$xpath = new DOMXPath($doc);
assert($index->resolveNoteNode($xpath, "P1' or '1'='1", 1, 1, 1, 1) === null, 'part id must not allow XPath injection');
assert($index->resolveNoteNode($xpath, 'P1', 0, 1, 1, 1) === null, 'measure locator must be positive');

echo "  [Unit] SecurityBoundaryTest: PASS\n";
