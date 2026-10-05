<?php
declare(strict_types=1);
/** Prepare existing sample PDFs in separate benchmark folders, outside the user's library. */
require_once dirname(__DIR__,2).'/app/autoload.php';
use App\Services\StorageService;
use App\Services\OmrComparisonService;
$storage=new StorageService(); $service=new OmrComparisonService($storage);
foreach(['002_tu_coi_long','003_tron_ca_tam_long'] as $sample) {
    $uuid='benchmark-'.$sample;
    $storage->initProjectDirs($uuid);
    $source=$storage->getProjectDir($uuid).'/source/original.pdf';
    $sampleRoot=is_dir(dirname(__DIR__,2).'/public/samples')?dirname(__DIR__,2).'/public/samples':dirname(__DIR__,2).'/samples';
    if(!is_file($source)&&!copy($sampleRoot.'/'.$sample.'/source.pdf',$source)) throw new RuntimeException('Sample source unavailable');
    $script=dirname(__DIR__,2).'/workers/preprocessing/extract_pdf.py';
    $command=escapeshellarg(getenv('PYTHON_BIN')?:'python').' '.escapeshellarg($script).' --input '.escapeshellarg($source).' --output-dir '.escapeshellarg($storage->getPagesDir($uuid));
    passthru($command,$exit); if($exit!==0) throw new RuntimeException('Sample render failed');
    foreach(['homr','clarity'] as $engine) echo json_encode($service->enqueue($uuid,$engine))."\n";
}
