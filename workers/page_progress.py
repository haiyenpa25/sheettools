"""Durable per-page OMR progress artifact for polling and diagnosis."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone


class PageProgress:
    def __init__(self, path: str, total_pages: int) -> None:
        if total_pages < 1:
            raise ValueError("total_pages must be positive")
        self.path = path
        self.total_pages = total_pages
        self.completed_pages: set[int] = set()
        self.failed_pages: dict[int, str] = {}
        self.current_page: int | None = None
        self._write()

    def start_page(self, page: int) -> None:
        self.current_page = page
        self._write()

    def complete_page(self, page: int) -> None:
        self.completed_pages.add(page)
        self.failed_pages.pop(page, None)
        self.current_page = None
        self._write()

    def fail_page(self, page: int, error: str) -> None:
        self.failed_pages[page] = error
        self.current_page = None
        self._write()

    def _write(self) -> None:
        processed = len(self.completed_pages)
        if self.failed_pages:
            status = "partial"
        elif processed == self.total_pages:
            status = "completed"
        else:
            status = "processing"
        payload = {
            "status": status,
            "total_pages": self.total_pages,
            "processed_pages": processed,
            "completed_pages": sorted(self.completed_pages),
            "failed_pages": [
                {"page": page, "error": error}
                for page, error in sorted(self.failed_pages.items())
            ],
            "current_page": self.current_page,
            "progress": round(processed / self.total_pages * 100),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as target:
            json.dump(payload, target, ensure_ascii=False, indent=2)
        os.replace(temporary, self.path)
