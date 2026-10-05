<?php
declare(strict_types=1);
use App\Services\StorageService;
use App\Services\OmrComparisonService;

$comparisonRoot=sys_get_temp_dir().'/sheettools_comparison_'.bin2hex(random_bytes(5));
$comparisonStorage=new StorageService($comparisonRoot);
$comparisonStorage->initProjectDirs('song');
file_put_contents($comparisonStorage->getPagesDir('song').'/page_0001.png','image');
$comparisonService=new OmrComparisonService($comparisonStorage);
$queued=$comparisonService->enqueue('song','homr');
assert($queued['status']==='queued');
assert($comparisonService->enqueue('song','homr')['id']===$queued['id'],'Deduplicate active job');
assert(count($comparisonService->list('song')['runs'])===1);
foreach(['../homr','audiveris',''] as $engine) {
    $rejected=false; try { $comparisonService->enqueue('song',$engine); } catch(InvalidArgumentException) { $rejected=true; }
    assert($rejected,'Unknown engine rejected');
}
$rejected=false; try { $comparisonService->list('../song'); } catch(InvalidArgumentException) { $rejected=true; }
assert($rejected);
echo "OmrComparisonServiceTest passed\n";
