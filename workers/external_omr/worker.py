"""Filesystem job worker for Homr and Clarity, without a Docker socket in the app."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

REVISIONS = {'homr': '560ca5ce254db129b1b2167598bdc7a20ac5d6b0',
             'clarity': 'c6bb8a4d2a5b52842a9c41bd0f761f58d02f6f82'}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def score_root(path: Path, comments: bool = False) -> ET.Element:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=comments))
    root = ET.parse(path, parser=parser).getroot()
    for node in root.iter():
        if isinstance(node.tag, str): node.tag = node.tag.rsplit('}', 1)[-1]
    if root.tag != 'score-partwise' or root.find('part/measure/note') is None:
        raise ValueError('Engine did not produce a nonempty partwise MusicXML score')
    return root


def summarize_xml(path: Path) -> dict:
    root = score_root(path)
    notes = root.findall('part/measure/note')
    return {'parts': len(root.findall('part')), 'measures': len(root.findall('part/measure')),
            'pitched_notes': sum(n.find('pitch') is not None for n in notes),
            'rests': sum(n.find('rest') is not None for n in notes),
            'tuplets': sum(n.find('time-modification') is not None for n in notes),
            'accuracy_available': False}


def homr_positions(path: Path, page: int) -> list[dict]:
    """Retain upstream attention coordinates as approximate, never pixel ground truth."""
    root = score_root(path, comments=True)
    positions = []
    for part in root.findall('part'):
        for measure in part.findall('measure'):
            for index, note in enumerate(measure.findall('note'), 1):
                if note.find('pitch') is None or note.find('chord') is not None or note.find('grace') is not None: continue
                if any(t.get('type')=='stop' for t in note.findall('tie')): continue
                for child in note:
                    if child.tag is ET.Comment:
                        match = re.search(r'imgpos:\s*([\d.-]+),\s*([\d.-]+)', child.text or '')
                        if match:
                            positions.append({'id': f"{part.get('id')}:{measure.get('number')}:{index}",
                                'page': page, 'position': list(map(float, match.groups())),
                                'approximate': True, 'source': 'homr_attention'})
    return positions


class ComparisonWorker:
    def __init__(self, storage: Path, engine: str, timeout: int = 1800) -> None:
        if engine not in REVISIONS: raise ValueError('Unknown comparison engine')
        self.storage = storage.resolve()
        self.engine = engine
        self.timeout = timeout

    def validate(self, job: dict) -> None:
        if job.get('engine') != self.engine: raise ValueError('Engine mismatch')
        for key in ('id', 'project_uuid'):
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', str(job.get(key, ''))):
                raise ValueError(f'Invalid {key}')

    def run_page(self, image: Path, directory: Path, page: int) -> dict:
        from PIL import Image
        directory.mkdir(parents=True, exist_ok=False)
        copied = directory / 'page.png'
        shutil.copyfile(image, copied)
        if self.engine == 'homr':
            command = ['homr', '--no-title', '--debug', '--write-staff-positions', str(copied)]
            xml = copied.with_suffix('.musicxml')
        else:
            pdf = directory / 'page.pdf'
            # Embed PNG losslessly; Pillow PDF export would recompress the source as JPEG.
            import fitz
            with Image.open(copied) as opened: width, height = opened.size
            with fitz.open() as document:
                pdf_page=document.new_page(width=width*72/300,height=height*72/300)
                pdf_page.insert_image(pdf_page.rect,filename=str(copied)); document.save(pdf)
            xml = directory / 'score.musicxml'
            command = [sys.executable, '/opt/clarity/omr.py', str(pdf), '-o', str(xml),
                       '--device', 'cpu', '--work-dir', str(directory / 'debug')]
        with (directory / 'engine.log').open('w', encoding='utf-8') as log:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                       timeout=self.timeout, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f'{self.engine} exited {completed.returncode}; see page {page} engine.log')
        summary = summarize_xml(xml)
        with Image.open(copied) as opened: width, height = opened.size
        regions = []
        if self.engine == 'homr':
            positions = homr_positions(xml, page)
            write_json(directory / 'note_positions.json', {'positions': positions})
            staff_file = copied.with_suffix('.txt')
            if staff_file.exists():
                for line in staff_file.read_text().splitlines():
                    cls, cx, cy, w, h = map(float, line.split())
                    regions.append({'type': 'staff', 'box': [max(0, (cx-w/2)*width),
                        max(0, (cy-h/2)*height), min(width, (cx+w/2)*width), min(height, (cy+h/2)*height)],
                        'source': 'homr_segmentation', 'grand_staff': bool(cls)})
        else:
            metadata = directory / 'debug/stage_a_crops_all.jsonl'
            if metadata.exists():
                for line in metadata.read_text().splitlines():
                    row = json.loads(line)
                    box = row.get('bbox', {})
                    if all(k in box for k in ('x_min', 'y_min', 'x_max', 'y_max')):
                        regions.append({'type': 'staff', 'box': [box[k] for k in ('x_min','y_min','x_max','y_max')], 'source': 'clarity_yolo'})
        write_json(directory / 'regions.json', {'page': page, 'width': width, 'height': height,
            'regions': regions, 'coordinate_system': 'pixels', 'requires_review': True})
        overlay = Image.open(copied).convert('RGB')
        from PIL import ImageDraw
        draw = ImageDraw.Draw(overlay)
        for index, region in enumerate(regions):
            draw.rectangle(region['box'], outline='#38bdf8', width=3)
            draw.text(tuple(region['box'][:2]), f'staff {index+1}', fill='#0284c7')
        overlay.save(directory / 'regions.png'); overlay.close()
        return {'page': page, 'summary': summary, 'xml': str(xml.relative_to(directory)),
                'staff_regions': len(regions), 'source_sha256': hashlib.sha256(image.read_bytes()).hexdigest()}

    def process(self, job: dict) -> dict:
        self.validate(job)
        project = self.storage / 'projects' / job['project_uuid']
        if not project.is_dir() or project.is_symlink(): raise ValueError('Project not available')
        directory = project / 'omr_comparisons' / job['id']
        directory.mkdir(parents=True, exist_ok=True)
        status_path = directory / 'status.json'
        result = {**job, 'status': 'running', 'revision': REVISIONS[self.engine], 'pages': [],
                  'started_at': time.time(), 'accuracy_available': False}
        write_json(status_path, result)
        try:
            pages = sorted(p for p in (project / 'pages').glob('*.png') if re.fullmatch(r'page[-_]\d+\.png', p.name))
            if not pages: raise RuntimeError('No rendered source pages')
            result['total_pages'] = len(pages)
            write_json(status_path, result)
            for page, path in enumerate(pages, 1):
                if not project.is_dir(): raise RuntimeError('Project removed during comparison')
                output = self.run_page(path, directory / f'page_{page:04d}', page)
                result['pages'].append(output)
                write_json(status_path, result)
            result['status'] = 'completed'
        except Exception as error:
            result['status'] = 'failed'; result['error'] = str(error)
            (directory / 'worker.log').write_text(traceback.format_exc(), encoding='utf-8')
        result['finished_at'] = time.time()
        write_json(status_path, result)
        return result

    def watch(self) -> None:
        queue = self.storage / 'omr_jobs' / self.engine
        queue.mkdir(parents=True, exist_ok=True)
        # A stopped container leaves its claim behind; expose that failure instead of hanging forever.
        for claimed in queue.glob('*.running'):
            try:
                job = json.loads(claimed.read_text()); self.validate(job)
                path = self.storage / 'projects' / job['project_uuid'] / 'omr_comparisons' / job['id'] / 'status.json'
                if path.exists():
                    status = json.loads(path.read_text()); status.update(status='failed', error='Worker restarted; submit a new run')
                    write_json(path, status)
                claimed.rename(claimed.with_suffix('.failed'))
            except Exception: traceback.print_exc()
        while True:
            write_json(queue / 'heartbeat.json', {'engine': self.engine, 'at': time.time(), 'revision': REVISIONS[self.engine]})
            for path in sorted(queue.glob('*.json')):
                if path.name == 'heartbeat.json': continue
                claimed = path.with_suffix('.running')
                try: path.rename(claimed)
                except FileNotFoundError: continue
                try:
                    result = self.process(json.loads(claimed.read_text()))
                    claimed.rename(claimed.with_suffix('.done' if result['status'] == 'completed' else '.failed'))
                except Exception:
                    traceback.print_exc(); claimed.rename(claimed.with_suffix('.failed'))
            time.sleep(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage', type=Path, default=Path('/var/www/html/storage'))
    parser.add_argument('--engine', choices=REVISIONS, required=True)
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--job', type=Path)
    args = parser.parse_args()
    worker = ComparisonWorker(args.storage, args.engine, args.timeout)
    if args.job:
        result=worker.process(json.loads(args.job.read_text())); print(json.dumps(result,ensure_ascii=False))
        sys.exit(0 if result['status']=='completed' else 1)
    else: worker.watch()
