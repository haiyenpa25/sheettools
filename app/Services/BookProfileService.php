<?php
declare(strict_types=1);
namespace App\Services;

final class BookProfileService
{
    public function __construct(private ?string $root=null) { $this->root ??= dirname(__DIR__,2).'/storage'; }
    private function path(string $book): string {
        if (!preg_match('/^[a-z0-9][a-z0-9-]{0,79}$/',$book)) throw new \InvalidArgumentException('Invalid book slug');
        $dir=$this->root.'/profiles'; if(!is_dir($dir)) mkdir($dir,0755,true);
        return $dir.'/'.$book.'.json';
    }
    public function get(string $book): array {
        $path=$this->path($book);
        return is_file($path)?(json_decode(file_get_contents($path),true)?:[]):['book'=>$book,'songs_seen'=>0,'params'=>[],'ocr_confusions'=>[]];
    }
    public function list(): array {
        $profiles=[];
        foreach(glob($this->root.'/profiles/*.json')?:[] as $path) {
            $slug=basename($path,'.json'); if(!preg_match('/^[a-z0-9][a-z0-9-]{0,79}$/',$slug)) continue;
            $profile=$this->get($slug); $profiles[]=['slug'=>$slug,'songs_seen'=>$profile['songs_seen']??0];
        }
        return $profiles;
    }
    public function reset(string $book): void {
        $path=$this->path($book); $lock=fopen($path.'.lock','c+'); flock($lock,LOCK_EX);
        try { if(is_file($path)) unlink($path); } finally { flock($lock,LOCK_UN); fclose($lock); }
    }
    public function confirmCorrection(string $book,string $event,string $from,string $to,string $context): void {
        if($from===''||$to===''||$from===$to||strlen($context)>500) return;
        $path=$this->path($book); $lock=fopen($path.'.lock','c+'); flock($lock,LOCK_EX);
        try {
            $p=$this->get($book); $key=hash('sha256',$from.'|'.$to.'|'.$context);
            $index=null; foreach($p['ocr_confusions'] as $i=>$c) if(($c['key']??'')===$key) $index=$i;
            if($index===null) { $index=count($p['ocr_confusions']); $p['ocr_confusions'][]=['key'=>$key,'from'=>$from,'to'=>$to,'context'=>$context,'confirmations'=>0,'events'=>[]]; }
            $c=&$p['ocr_confusions'][$index];
            if(!in_array($event,$c['events'],true)) { $c['events'][]=$event; $c['confirmations']=count($c['events']); }
            $p['confirmed_songs']=array_values(array_unique(array_merge($p['confirmed_songs']??[],[explode(':',$event)[0]])));
            $p['songs_seen']=count($p['confirmed_songs']);
            file_put_contents($path.'.tmp',json_encode($p,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)); rename($path.'.tmp',$path);
        } finally { flock($lock,LOCK_UN); fclose($lock); }
    }
    public function confirmMeasure(string $book,string $event,array $samples): void {
        $path=$this->path($book); $lock=fopen($path.'.lock','c+'); flock($lock,LOCK_EX);
        try {
            $p=$this->get($book); $p['anchor_events']??=[];
            if(isset($p['anchor_events'][$event])) return;
            $p['anchor_events'][$event]=array_values(array_filter($samples,fn($v)=>is_numeric($v)&&$v>=0&&$v<=1));
            $values=[]; foreach($p['anchor_events'] as $row) $values=array_merge($values,$row);
            sort($values,SORT_NUMERIC); $n=count($values);
            if($n) $p['params']['lyric_anchor_fraction']=$n%2?$values[intdiv($n,2)]:($values[$n/2-1]+$values[$n/2])/2;
            file_put_contents($path.'.tmp',json_encode($p,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)); rename($path.'.tmp',$path);
        } finally { flock($lock,LOCK_UN); fclose($lock); }
    }
    public function retractCorrections(string $book,string $prefix): void {
        $path=$this->path($book); $lock=fopen($path.'.lock','c+'); flock($lock,LOCK_EX);
        try {
            $p=$this->get($book);
            foreach($p['ocr_confusions'] as &$pair) {
                $pair['events']=array_values(array_filter($pair['events']??[],fn($event)=>!str_starts_with($event,$prefix)));
                $pair['confirmations']=count($pair['events']);
            } unset($pair);
            file_put_contents($path.'.tmp',json_encode($p,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE)); rename($path.'.tmp',$path);
        } finally { flock($lock,LOCK_UN); fclose($lock); }
    }
}
