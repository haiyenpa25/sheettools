"""Safely materialize numbered image pages from a ZIP without extracting paths."""
from __future__ import annotations

import io
import os
import re
import zipfile
from pathlib import Path

from PIL import Image


def _natural_key(name: str) -> list[int | str]:
    return [int(piece) if piece.isdigit() else piece.lower()
            for piece in re.split(r"(\d+)", Path(name).name)]


def extract_zip_pages(archive_path: str, output_dir: str, max_pages: int = 50) -> list[str]:
    """Read image members in memory and publish sequential PNGs atomically."""
    with zipfile.ZipFile(archive_path) as archive:
        members = [item for item in archive.infolist()
                   if not item.is_dir() and Path(item.filename).suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff'}]
        members.sort(key=lambda item: _natural_key(item.filename))
        if not members or len(members) > max_pages:
            raise ValueError(f"Expected 1-{max_pages} image pages in archive; found {len(members)}.")
        if any(item.file_size > 50 * 1024 * 1024 for item in members):
            raise ValueError("Archive contains an oversized image page.")
        os.makedirs(output_dir, exist_ok=True)
        pages = []
        for index, member in enumerate(members, start=1):
            # Never join member.filename to output_dir. Archive names can contain ../.
            with archive.open(member) as stream:
                data = stream.read(50 * 1024 * 1024 + 1)
            if len(data) > 50 * 1024 * 1024:
                raise ValueError("Archive contains an oversized image page.")
            target = os.path.join(output_dir, f"page-{index:03d}.png")
            temporary = target + ".tmp"
            try:
                with Image.open(io.BytesIO(data)) as image:
                    image.convert('RGB').save(temporary, 'PNG')
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            pages.append(os.path.abspath(target))
        return pages
