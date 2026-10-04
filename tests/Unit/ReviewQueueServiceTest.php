<?php
declare(strict_types=1);
use App\Services\StorageService;
use App\Services\ReviewQueueService;
use App\Services\BookProfileService;

$reviewRoot=sys_get_temp_dir().'/sheettools_review_'.bin2hex(random_bytes(5));
$reviewStorage=new StorageService($reviewRoot); $reviewStorage->initProjectDirs('song');
$reviewXml='<score-partwise><work><work-title>ĐẤNG NĂM GIỮ</work-title></work><identification/><part-list/><part id="P1"><measure number="0"><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note></measure></part></score-partwise>';
$reviewStorage->saveCurrentMusicXml('song',$reviewXml); $reviewStorage->saveRawMusicXml('song',$reviewXml);
$reviewDir=$reviewStorage->getProjectDir('song').'/omr_out'; mkdir($reviewDir);
file_put_contents($reviewDir.'/review_queue.json',json_encode(['items'=>[['id'=>'metadata','kind'=>'metadata','box'=>[]],['id'=>'p1_P1_s1_m0','measure_number'=>0,'part_id'=>'P1','box'=>[0,0,10,10],'violations'=>[['rule'=>'C2','severity'=>'error','message'=>'missing head']],'suggestions'=>[]]],'total_measures'=>1]));
$reviewService=new ReviewQueueService($reviewStorage);
$reviewQueue=$reviewService->getQueue('song'); assert(count($reviewQueue['items'])===2);
$reviewService->record('song','p1_P1_s1_m0',['action'=>'accept','seconds'=>2.5,'xml_sha256'=>$reviewQueue['xml_sha256']]);
assert($reviewService->getQueue('song')['items'][1]['review_status']==='accepted');
assert(file_get_contents($reviewStorage->getRawMusicXmlPath('song'))===$reviewXml);
$reviewService->record('song','metadata',['action'=>'metadata','seconds'=>3,'xml_sha256'=>$reviewQueue['xml_sha256'],'fields'=>['title'=>'ĐẤNG NẮM GIỮ']]);
assert(str_contains(file_get_contents($reviewStorage->getCurrentMusicXmlPath('song')),'ĐẤNG NẮM GIỮ'));
assert(file_get_contents($reviewStorage->getRawMusicXmlPath('song'))===$reviewXml);
$staleRejected=false;
try { $reviewService->record('song','p1_P1_s1_m0',['action'=>'accept','seconds'=>1,'xml_sha256'=>$reviewQueue['xml_sha256']]); }
catch (RuntimeException $e) { $staleRejected=true; }
assert($staleRejected,'Stale XML must not be reviewed against another version');
$updatedQueue=$reviewService->getQueue('song');
assert($updatedQueue['items'][0]['metadata']['title']['text']==='ĐẤNG NẮM GIỮ');
$reviewService->record('song','metadata',['action'=>'undo','xml_sha256'=>$updatedQueue['xml_sha256']]);
assert(file_get_contents($reviewStorage->getCurrentMusicXmlPath('song'))===$reviewXml);
assert(!isset($reviewService->getQueue('song')['items'][0]['metadata']['title']['human_confirmed']));
$unknownRejected=false;
try { $reviewService->record('song','../raw.musicxml',['action'=>'accept']); }
catch (InvalidArgumentException $e) { $unknownRejected=true; }
assert($unknownRejected);
$profileService=new BookProfileService($reviewRoot);
for ($i=1;$i<=3;$i++) $profileService->confirmCorrection('book','song'.$i,'NĂM','NẮM','ĐẤNG _ GIỮ');
assert($profileService->get('book')['ocr_confusions'][0]['confirmations']===3);
$profileService->confirmCorrection('book','song3','NĂM','NẮM','ĐẤNG _ GIỮ');
assert($profileService->get('book')['ocr_confusions'][0]['confirmations']===3,'Duplicate confirmation must not train a profile');
$profileService->confirmMeasure('book','human-measure',[.4,.5,.6]);
assert($profileService->get('book')['params']['lyric_anchor_fraction']===.5);
$profileService->reset('book'); assert($profileService->get('book')['ocr_confusions']===[]);
$learningXml='<score-partwise><part id="P1"><measure number="0">';
foreach(['ĐẤNG','NĂM','GIỮ'] as $word) $learningXml.='<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><lyric number="1"><text>'.$word.'</text></lyric></note>';
$learningXml.='</measure></part></score-partwise>';
file_put_contents($reviewDir.'/score.musicxml',$learningXml);
$reviewStorage->saveCurrentMusicXml('song',str_replace('NĂM','NẮM',$learningXml));
$repo=new App\Repositories\ConversionProjectRepository($reviewStorage);
$repo->save(new App\Models\ConversionProject(['uuid'=>'song','book_slug'=>'book']));
$learningQueue=json_decode(file_get_contents($reviewDir.'/review_queue.json'),true);
$learningQueue['items'][1]+=['local_measure_number'=>'0','page'=>1];
file_put_contents($reviewDir.'/review_queue.json',json_encode($learningQueue));
$reviewService->record('song','p1_P1_s1_m0',['action'=>'accept','xml_sha256'=>$reviewService->getQueue('song')['xml_sha256']]);
assert(($profileService->get('book')['ocr_confusions'][0]['confirmations']??0)===1,'Learn lyric corrections only after human ACCEPT with unchanged note structure');
echo "  [Unit] ReviewQueueServiceTest: PASS\n";
// Cleanup stays in a randomly created test directory.
$reviewIterator=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($reviewRoot,FilesystemIterator::SKIP_DOTS),RecursiveIteratorIterator::CHILD_FIRST);
foreach($reviewIterator as $file) { $file->isDir()?rmdir($file->getPathname()):unlink($file->getPathname()); } rmdir($reviewRoot);
