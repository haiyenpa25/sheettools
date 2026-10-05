<?php
declare(strict_types=1);
namespace App\Services;

/** Queue independent OMR runs without exposing the container runtime to HTTP. */
final class OmrComparisonService
{
    public function __construct(private ?StorageService $storage=null) { $this->storage ??= new StorageService(); }
    private function project(string $uuid): string {
        if(!preg_match('/^[a-zA-Z0-9_-]{1,100}$/',$uuid)) throw new \InvalidArgumentException('Invalid project id');
        $path=$this->storage->getProjectDir($uuid);
        if(!is_dir($path)||is_link($path)) throw new \RuntimeException('Project not found');
        return $path;
    }
    public function list(string $uuid): array {
        $project=$this->project($uuid); $runs=[]; $engines=[];
        foreach(glob($project.'/omr_comparisons/*/status.json')?:[] as $path) {
            $run=json_decode(file_get_contents($path),true);
            if(is_array($run)) {
                $analysis=dirname($path).'/analysis.json';
                if(is_file($analysis)) $run['analysis']=json_decode(file_get_contents($analysis),true);
                $runs[]=$run;
            }
        }
        usort($runs,fn($a,$b)=>($b['queued_at']??0)<=>($a['queued_at']??0));
        foreach(['homr','clarity'] as $engine) {
            $path=dirname($this->storage->getProjectsRoot()).'/omr_jobs/'.$engine.'/heartbeat.json';
            $heartbeat=is_file($path)?json_decode(file_get_contents($path),true):[];
            $engines[$engine]=['online'=>time()-($heartbeat['at']??0)<30,'revision'=>$heartbeat['revision']??null];
        }
        return ['runs'=>$runs,'engines'=>$engines];
    }
    public function enqueue(string $uuid,string $engine): array {
        if(!in_array($engine,['homr','clarity'],true)) throw new \InvalidArgumentException('Unsupported comparison engine');
        $project=$this->project($uuid);
        if(!(glob($project.'/pages/page-*.png')?:glob($project.'/pages/page_*.png'))) throw new \RuntimeException('Render source pages first');
        $root=$project.'/omr_comparisons'; if(!is_dir($root)) mkdir($root,0755,true);
        $lock=fopen($root.'/queue.lock','c+'); flock($lock,LOCK_EX);
        try {
            foreach($this->list($uuid)['runs'] as $run) if($run['engine']===$engine&&in_array($run['status'],['queued','running'],true)) return $run;
            $job=['id'=>bin2hex(random_bytes(12)),'project_uuid'=>$uuid,'engine'=>$engine,'status'=>'queued','queued_at'=>microtime(true)];
            $directory=$root.'/'.$job['id']; mkdir($directory,0755,true);
            $json=json_encode($job,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
            file_put_contents($directory.'/status.json',$json);
            $queue=dirname($this->storage->getProjectsRoot()).'/omr_jobs/'.$engine;
            if(!is_dir($queue)) mkdir($queue,0755,true);
            $path=$queue.'/'.$job['id'].'.json';
            if(file_put_contents($path.'.tmp',$json)===false || !rename($path.'.tmp',$path)) {
                $job['status']='failed'; $job['error']='Unable to publish comparison job';
                file_put_contents($directory.'/status.json',json_encode($job));
                throw new \RuntimeException('Unable to publish comparison job');
            }
            return $job;
        } finally { flock($lock,LOCK_UN); fclose($lock); }
    }
    public function artifact(string $uuid,string $run,int $page,string $name): string {
        $project=$this->project($uuid);
        if(!preg_match('/^[a-f0-9]{24}$/',$run)||$page<1||$page>50) throw new \InvalidArgumentException('Invalid comparison artifact');
        if(!in_array($name,['page.musicxml','score.musicxml','regions.json','analysis_regions.json','regions.png','note_positions.json','aligned.musicxml','lyrics.json','engine.log'],true)) throw new \InvalidArgumentException('Unsupported artifact');
        $directory=$project.'/omr_comparisons/'.$run.'/page_'.sprintf('%04d',$page);
        $path=$directory.'/'.$name;
        if(!is_file($path)||is_link($path)||realpath(dirname($path))!==realpath($directory)) throw new \RuntimeException('Artifact not ready');
        return $path;
    }
}
