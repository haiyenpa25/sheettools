from __future__ import annotations
import json, os, re, tempfile
from pathlib import Path


class BookProfile:
    def __init__(self, directory: str, book: str):
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',book): raise ValueError('Invalid book slug')
        self.path=Path(directory)/f'{book}.json'
        self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.is_file() else {'book':book,'songs_seen':0,'params':{},'ocr_confusions':[]}

    def confirm(self, before: str, after: str, context: str, event: str) -> None:
        """Offline import of explicitly human-confirmed corrections, never OCR output."""
        matches=[v for v in self.data['ocr_confusions'] if (v['from'],v['to'],v['context'])==(before,after,context)]
        if matches: item=matches[0]
        else:
            item={'from':before,'to':after,'context':context,'events':[],'confirmations':0}; self.data['ocr_confusions'].append(item)
        if event not in item['events']: item['events'].append(event)
        item['confirmations']=len(item['events'])
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=self.path.parent,delete=False) as f:
            json.dump(self.data,f,ensure_ascii=False,indent=2); temporary=f.name
        os.replace(temporary,self.path)

    def apply_text(self, text: str) -> dict:
        changes=[]; suggestions=[]
        for pair in self.data.get('ocr_confusions',[]):
            context=pair.get('context','')
            if context.count('_')!=1: continue
            old=context.replace('_',pair['from']); new=context.replace('_',pair['to'])
            if old not in text: continue
            if pair.get('confirmations',0)>=3:
                text=text.replace(old,new); changes.append({'from':old,'to':new,'source':'human_book_profile'})
            else: suggestions.append({'from':old,'to':new,'confirmations':pair.get('confirmations',0)})
        return {'text':text,'changes':changes,'suggestions':suggestions}


def apply_book_profile(decomposition: dict, output_dir: str) -> None:
    project_dir=next((p for p in [Path(output_dir),*Path(output_dir).parents] if (p/'project.json').is_file()),None)
    if project_dir is None: return
    project=json.loads((project_dir/'project.json').read_text(encoding='utf-8')); book=project.get('book_slug','')
    if not book: return
    profile=BookProfile(str(project_dir.parent.parent/'profiles'),book)
    decomposition['book_profile_params']=profile.data.get('params',{})
    header=decomposition.get('header',{}); document=header.get('document_model',{})
    for field in ('title','composer','translator','lyricist'):
        item=document.get(field)
        if not item: continue
        result=profile.apply_text(item.get('text',''))
        item['text']=result['text']; item['profile_changes']=result['changes']; item['profile_suggestions']=result['suggestions']
        if field in header: header[field]=result['text']
    groups={}
    for word in decomposition.get('lyrics',[]):
        groups.setdefault((word.get('section_type','verse'),word.get('verse_number',1)),[]).append(word)
    for words in groups.values():
        result=profile.apply_text(' '.join(w['text'] for w in words)); tokens=result['text'].split()
        if len(tokens)!=len(words): continue
        for word,text in zip(words,tokens):
            if word['text']==text: continue
            word.setdefault('context_changes',[]).append({'from':word['text'],'to':text,'source':'human_book_profile'})
            word['text']=text
