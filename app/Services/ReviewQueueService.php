<?php
declare(strict_types=1);
namespace App\Services;
use App\Models\RecognitionIssue;
use App\Repositories\ConversionProjectRepository;

/** Reads generated evidence; records human decisions against a specific XML revision. */
final class ReviewQueueService
{
    private StorageService $storage;
    public function __construct(?StorageService $storage=null) { $this->storage=$storage??new StorageService(); }
    private function directory(string $uuid): string {
        if(!preg_match('/^[a-zA-Z0-9_-]+$/',$uuid)) throw new \InvalidArgumentException('Invalid project id');
        return $this->storage->getProjectDir($uuid).'/omr_out';
    }
    private function read(string $path): array { return is_file($path)?(json_decode(file_get_contents($path),true)?:[]):[]; }
    public function getQueue(string $uuid,bool $all=false): array {
        $dir=$this->directory($uuid); $queue=$this->read($dir.'/review_queue.json');
        if(!$queue) throw new \RuntimeException('Review artifacts are not ready');
        if($all) {
            $metadata=array_values(array_filter($queue['items']??[],fn($m)=>($m['kind']??'')==='metadata'));
            $queue['items']=array_merge($metadata,$this->read($dir.'/measure_ledger.json')['measures']??array_values(array_filter($queue['items'],fn($m)=>($m['kind']??'')!=='metadata')));
        }
        $state=$this->read($dir.'/review_state.json');
        $hash=is_file($this->storage->getCurrentMusicXmlPath($uuid))?hash_file('sha256',$this->storage->getCurrentMusicXmlPath($uuid)):'';
        $issues=[];
        foreach($queue['items'] as &$item) {
            if(($item['kind']??'')==='metadata') $item['metadata']=$this->read($this->storage->getDocumentArtifactPath($uuid))?:($item['metadata']??[]);
            $decision=$state['decisions'][$item['id']]??[];
            $item['review_status']=($decision['xml_sha256']??'')===$hash?($decision['status']??'open'):'open';
            foreach($item['violations']??[] as $i=>$v) {
                $issue=new RecognitionIssue(['id'=>$item['id'].'-'.$i,'project_uuid'=>$uuid,'part_id'=>$item['part_id']??'P1',
                    'measure_number'=>$item['measure_number']??0,'entity_type'=>$v['rule'],'severity'=>$v['severity'],
                    'message'=>$v['message'],'bounding_coords'=>$item['box']??[],'status'=>$item['review_status']==='accepted'?'resolved':'open']);
                $issues[]=$issue->toArray();
            }
        } unset($item);
        return $queue+['xml_sha256'=>$hash,'issues'=>$issues,'log'=>$state['log']??[]];
    }
    public function record(string $uuid,string $id,array $input): array {
        $dir=$this->directory($uuid); $queue=$this->getQueue($uuid,true);
        $item=null; foreach($queue['items'] as $row) if($row['id']===$id) $item=$row;
        if($item===null) throw new \InvalidArgumentException('Unknown measure id');
        $action=$input['action']??'';
        if(!in_array($action,['accept','skip','reject','metadata','apply','undo','edit'],true)) throw new \InvalidArgumentException('Unsupported review action');
        $seconds=$input['seconds']??0;
        if(!is_numeric($seconds)||$seconds<0||$seconds>3600) throw new \InvalidArgumentException('Invalid review duration');
        $xmlPath=$this->storage->getCurrentMusicXmlPath($uuid);
        $lock=fopen($dir.'/review_state.lock','c+'); flock($lock,LOCK_EX);
        try {
            $before=file_get_contents($xmlPath); $hash=hash('sha256',$before);
            if(($input['xml_sha256']??'')!==$hash) throw new \RuntimeException('XML changed; reload the review queue');
            $state=$this->read($dir.'/review_state.json'); $state+=['decisions'=>[],'log'=>[]];
            $doc=new \DOMDocument(); $previous=libxml_use_internal_errors(true);
            $loaded=$doc->loadXML($before,LIBXML_NONET); libxml_clear_errors(); libxml_use_internal_errors($previous);
            if(!$loaded) throw new \RuntimeException('Current XML is invalid');
            $doc->encoding='UTF-8';
            $oldFields=[];
            $documentPath=$this->storage->getDocumentArtifactPath($uuid);
            $documentBefore=is_file($documentPath)?file_get_contents($documentPath):null;
            $repo=new ConversionProjectRepository($this->storage);
            $projectBefore=$repo->findByUuid($uuid);
            if($action==='metadata') {
                if($id!=='metadata') throw new \InvalidArgumentException('Metadata action requires metadata card');
                $fields=$input['fields']??[];
                foreach($fields as $key=>$value) {
                    if(!in_array($key,['title','composer','translator'],true)||!is_string($value)||mb_strlen($value)>300) throw new \InvalidArgumentException('Invalid metadata field');
                    $xpath=new \DOMXPath($doc);
                    $nodes=$key==='title'?$xpath->query('/*/work/work-title | /*/movement-title'):$xpath->query('/*/identification/creator[@type="'.($key==='translator'?'lyricist':'composer').'"]');
                    $oldFields[$key]=$nodes->item(0)?->textContent??'';
                    if($nodes->length===0) {
                        $parentName=$key==='title'?'work':'identification'; $parent=$doc->getElementsByTagName($parentName)->item(0);
                        if(!$parent) { $parent=$doc->createElement($parentName); $doc->documentElement->insertBefore($parent,$doc->documentElement->firstChild); }
                        $node=$doc->createElement($key==='title'?'work-title':'creator');
                        if($key!=='title') $node->setAttribute('type',$key==='translator'?'lyricist':'composer');
                        $parent->appendChild($node); $node->appendChild($doc->createTextNode($value));
                    } else foreach($nodes as $node) $node->textContent=$value;
                }
                $this->saveXml($xmlPath,$doc->saveXML());
                $metadata=$this->read($this->storage->getDocumentArtifactPath($uuid));
                foreach($fields as $key=>$value) { $metadata[$key]['text']=$value; $metadata[$key]['human_confirmed']=true; }
                file_put_contents($this->storage->getDocumentArtifactPath($uuid),json_encode($metadata,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
                $repo=new ConversionProjectRepository($this->storage); $project=$repo->findByUuid($uuid);
                if($project) {
                    if(isset($fields['title'])) $project->title=$fields['title']; if(isset($fields['composer'])) $project->composer=$fields['composer']; $repo->save($project);
                    if($project->bookSlug!=='') $this->learn($project->bookSlug,$uuid,$oldFields,$fields);
                }
            } elseif($action==='apply') {
                $candidate=null; foreach($item['suggestions']??[] as $s) if($s['id']===($input['suggestion_id']??'')) $candidate=$s;
                if(!$candidate||empty($candidate['verified'])||empty($candidate['measure_xml'])) throw new \InvalidArgumentException('No verified candidate selected');
                if(($candidate['xml_sha256']??'')!==$hash) throw new \RuntimeException('Candidate belongs to another XML revision; reread the measure');
                $fragment=new \DOMDocument(); if(!$fragment->loadXML($candidate['measure_xml'],LIBXML_NONET)||$fragment->documentElement->tagName!=='measure') throw new \InvalidArgumentException('Invalid candidate');
                $xpath=new \DOMXPath($doc); $number=(int)$item['measure_number']; $part=preg_replace('/[^a-zA-Z0-9_-]/','',$item['part_id']);
                $target=$xpath->query('/*/part[@id="'.$part.'"]/measure[@number="'.$number.'"]')->item(0);
                if(!$target) throw new \RuntimeException('Measure no longer exists');
                $replacement=$doc->importNode($fragment->documentElement,true); $replacement->setAttribute('number',(string)$number);
                $target->parentNode->replaceChild($replacement,$target); $this->saveXml($xmlPath,$doc->saveXML());
            } elseif($action==='undo') {
                $snapshot=$dir.'/review_previous.musicxml';
                if(!is_file($snapshot)||($state['last_after_hash']??'')!==$hash) throw new \RuntimeException('No matching review change to undo');
                $this->saveXml($xmlPath,file_get_contents($snapshot)); $state['decisions']=[];
                if(array_key_exists('previous_document',$state)) {
                    file_put_contents($documentPath,$state['previous_document']??'{}');
                    $project=$repo->findByUuid($uuid);
                    if($project) { $project->title=$state['previous_title']??$project->title; $project->composer=$state['previous_composer']??$project->composer; $repo->save($project); }
                    if($project && $project->bookSlug!=='' && ($state['last_action']??'')==='metadata') (new BookProfileService(dirname($this->storage->getProjectsRoot())))->retractCorrections($project->bookSlug,$uuid.':');
                }
                unset($state['last_after_hash']);
            }
            $afterHash=hash_file('sha256',$xmlPath);
            if($afterHash!==$hash&&$action!=='undo') {
                file_put_contents($dir.'/review_previous.musicxml',$before); $state['last_after_hash']=$afterHash;
                $state['previous_document']=$documentBefore; $state['previous_title']=$projectBefore?->title; $state['previous_composer']=$projectBefore?->composer;
                $state['last_action']=$action;
            }
            $status=in_array($action,['accept','metadata','apply'],true)?'accepted':($action==='reject'?'incorrect':(in_array($action,['undo','edit'],true)?'open':'skipped'));
            $state['decisions'][$id]=['status'=>$status,'xml_sha256'=>$afterHash];
            if($action==='accept') {
                $project=(new ConversionProjectRepository($this->storage))->findByUuid($uuid);
                if($project && $project->bookSlug!=='') {
                    (new BookProfileService(dirname($this->storage->getProjectsRoot())))->confirmMeasure($project->bookSlug,$uuid.':'.$id,$item['evidence']['lyric_anchor_samples']??[]);
                    $this->learnLyrics($project->bookSlug,$uuid,$item,$doc);
                }
            }
            $state['log'][]=['measure_id'=>$id,'rule'=>array_column($item['violations']??[],'rule'),'action'=>$action,
                'suggestion_id'=>$input['suggestion_id']??null,'seconds'=>(float)$seconds,'xml_before'=>$hash,'xml_after'=>$afterHash,'at'=>gmdate('c')];
            file_put_contents($dir.'/review_state.json.tmp',json_encode($state,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)); rename($dir.'/review_state.json.tmp',$dir.'/review_state.json');
        } finally { flock($lock,LOCK_UN); fclose($lock); }
        return $this->getQueue($uuid,($input['all']??false)===true);
    }
    public function requestRepair(string $uuid,string $id): array {
        $queue=$this->getQueue($uuid,true); $found=false;
        foreach($queue['items'] as $item) if($item['id']===$id && ($item['kind']??'')!=='metadata') $found=true;
        if(!$found) throw new \InvalidArgumentException('Unknown measure id');
        $python=getenv('PYTHON_BIN')?:'python'; $worker=dirname(__DIR__,2).'/workers/omr_checks/repair.py';
        $command=escapeshellarg($python).' '.escapeshellarg($worker).' --project '.escapeshellarg($this->storage->getProjectDir($uuid)).' --measure-id '.escapeshellarg($id).' 2>&1';
        $output=[]; $exit=0;
        $lock=fopen($this->directory($uuid).'/review_state.lock','c+'); flock($lock,LOCK_EX);
        try { exec($command,$output,$exit); } finally { flock($lock,LOCK_UN); fclose($lock); }
        file_put_contents($this->directory($uuid).'/repair.log',implode("\n",$output));
        if($exit!==0) throw new \RuntimeException('Crop reread failed; see repair log');
        return $this->getQueue($uuid);
    }
    public function buildQueue(string $uuid): array {
        $this->directory($uuid);
        $python=getenv('PYTHON_BIN')?:'python'; $worker=dirname(__DIR__,2).'/workers/omr_checks/backfill.py';
        $command=escapeshellarg($python).' '.escapeshellarg($worker).' --project '.escapeshellarg($this->storage->getProjectDir($uuid)).' 2>&1';
        $output=[]; $exit=0;
        $lock=fopen($this->directory($uuid).'/review_state.lock','c+'); flock($lock,LOCK_EX);
        try { exec($command,$output,$exit); } finally { flock($lock,LOCK_UN); fclose($lock); }
        file_put_contents($this->directory($uuid).'/review_build.log',implode("\n",$output));
        if($exit!==0) throw new \RuntimeException('Review build failed; see review_build.log');
        return $this->getQueue($uuid);
    }
    private function saveXml(string $path,string $xml): void { file_put_contents($path.'.tmp',$xml); rename($path.'.tmp',$path); }
    private function learnLyrics(string $book,string $uuid,array $item,\DOMDocument $current): void {
        if(!isset($item['part_id'],$item['measure_number'],$item['local_measure_number'],$item['page'])) return;
        $base=$this->directory($uuid); $path=$base.'/page_result_'.sprintf('%04d',(int)$item['page']).'/score.musicxml';
        if(!is_file($path)) $path=$base.'/score.musicxml';
        if(!is_file($path)) return;
        $original=new \DOMDocument(); if(!@$original->load($path,LIBXML_NONET)) return;
        $part=preg_replace('/[^a-zA-Z0-9_-]/','',$item['part_id']);
        $before=(new \DOMXPath($original))->query('/*/part[@id="'.$part.'"]/measure[@number="'.(int)$item['local_measure_number'].'"]/note');
        $after=(new \DOMXPath($current))->query('/*/part[@id="'.$part.'"]/measure[@number="'.(int)$item['measure_number'].'"]/note');
        if($before->length!==$after->length) return;
        $rowsBefore=[]; $rowsAfter=[];
        foreach($before as $i=>$note) {
            $new=$after->item($i);
            foreach(['pitch','duration','voice','staff'] as $tag) if(($note->getElementsByTagName($tag)->item(0)?->textContent??'')!==($new->getElementsByTagName($tag)->item(0)?->textContent??'')) return;
            foreach([[$note,&$rowsBefore],[$new,&$rowsAfter]] as &$pair) {
                foreach($pair[0]->getElementsByTagName('lyric') as $lyric) $pair[1][$lyric->getAttribute('number')][]=$lyric->getElementsByTagName('text')->item(0)?->textContent??'';
            } unset($pair);
        }
        $old=[]; $new=[];
        foreach($rowsBefore as $verse=>$words) if(count($words)===count($rowsAfter[$verse]??[])) {
            $key='measure'.$item['measure_number'].'-verse'.$verse; $old[$key]=implode(' ',$words); $new[$key]=implode(' ',$rowsAfter[$verse]);
        }
        $this->learn($book,$uuid,$old,$new);
    }
    private function learn(string $book,string $uuid,array $before,array $after): void {
        $service=new BookProfileService(dirname($this->storage->getProjectsRoot()));
        foreach($after as $key=>$text) {
            $old=preg_split('/\s+/u',trim($before[$key]??'')); $new=preg_split('/\s+/u',trim($text));
            if(count($old)!==count($new)) continue;
            foreach($old as $i=>$word) if($word!==$new[$i]) {
                $context=($old[$i-1]??'').' _ '.($old[$i+1]??'');
                $service->confirmCorrection($book,$uuid.':'.$key.':'.$i,$word,$new[$i],trim($context));
            }
        }
    }
}
