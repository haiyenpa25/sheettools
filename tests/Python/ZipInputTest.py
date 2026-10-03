#!/usr/bin/env python3
import sys
import tempfile
import zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'workers'))
from audiveris_runner import extract_zip_pages

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for name in ('page-10.png', 'page-2.png'):
        Image.new('L', (20, 20), 255).save(root / name)
    archive = root / 'pages.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.write(root / 'page-10.png', 'nested/page-10.png')
        bundle.write(root / 'page-2.png', '../page-2.png')
        bundle.writestr('ignore.txt', 'not an image')
    pages = extract_zip_pages(str(archive), str(root / 'out'))
    assert [Path(path).name for path in pages] == ['page-001.png', 'page-002.png']

print('  [Python] ZipInputTest: PASS')
