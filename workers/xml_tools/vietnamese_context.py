#!/usr/bin/env python3
"""Conservative context-based Vietnamese diacritic restoration for hymn text."""
from __future__ import annotations

import re
import unicodedata


PHRASES = {
    # Prefer long, domain-specific phrases so ambiguous single words such as
    # "chua" are restored only when their surrounding hymn context supports it.
    ("hat", "khen", "ngoi", "chua", "tren", "troi"): ("hát", "khen", "ngợi", "chúa", "trên", "trời"),
    ("ngoi", "ca"): ("ngợi", "ca"),
    ("tinh", "yeu"): ("tình", "yêu"),
    ("thien", "chua"): ("thiên", "chúa"),
    ("muon", "doi"): ("muôn", "đời"),
    ("hat", "khen", "ngoi"): ("hát", "khen", "ngợi"),
    ("tren", "troi"): ("trên", "trời"),
    ("su", "thanh", "tin"): ("sự", "thành", "tín"),
    ("tu", "long", "toi"): ("từ", "lòng", "tôi"),
    ("cung", "nhau"): ("cùng", "nhau"),
}


def _fold(text: str) -> str:
    normalized = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    return ''.join(char for char in normalized if unicodedata.category(char) != 'Mn' and char.isalpha())


def _case_like(replacement: str, source: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement.capitalize()
    return replacement


def restore_liturgical_diacritics(text: str) -> tuple[str, list[str]]:
    tokens = text.split()
    cores = [re.sub(r'^\W+|\W+$', '', token, flags=re.UNICODE) for token in tokens]
    changes = []
    for source_phrase, target_phrase in sorted(PHRASES.items(), key=lambda item: len(item[0]), reverse=True):
        width = len(source_phrase)
        for start in range(0, len(tokens) - width + 1):
            if tuple(_fold(core) for core in cores[start:start + width]) != source_phrase:
                continue
            before = ' '.join(tokens[start:start + width])
            for offset, replacement in enumerate(target_phrase):
                index = start + offset
                source_core = cores[index]
                prefix = tokens[index][:tokens[index].find(source_core)] if source_core and source_core in tokens[index] else ''
                suffix_start = tokens[index].find(source_core) + len(source_core) if source_core and source_core in tokens[index] else len(tokens[index])
                suffix = tokens[index][suffix_start:]
                new_core = _case_like(replacement, source_core)
                tokens[index] = prefix + new_core + suffix
                cores[index] = new_core
            after = ' '.join(tokens[start:start + width])
            if before != after:
                changes.append(f"{before} -> {after}")
    return ' '.join(tokens), changes


def restore_liturgical_items(items: list[dict]) -> list[dict]:
    """Restore phrases across token boxes while retaining every token's geometry/provenance."""
    if not items:
        return items
    cores = [re.sub(r'^\W+|\W+$', '', str(item.get('text', '')), flags=re.UNICODE) for item in items]
    for source_phrase, target_phrase in sorted(PHRASES.items(), key=lambda entry: len(entry[0]), reverse=True):
        width = len(source_phrase)
        for start in range(0, len(items) - width + 1):
            if tuple(_fold(core) for core in cores[start:start + width]) != source_phrase:
                continue
            before = ' '.join(str(item.get('text', '')) for item in items[start:start + width])
            replacements = []
            for offset, replacement in enumerate(target_phrase):
                index = start + offset
                source_token = str(items[index].get('text', ''))
                source_core = cores[index]
                core_at = source_token.find(source_core) if source_core else -1
                prefix = source_token[:core_at] if core_at >= 0 else ''
                suffix = source_token[core_at + len(source_core):] if core_at >= 0 else ''
                new_core = _case_like(replacement, source_core)
                replacements.append(prefix + new_core + suffix)
            after = ' '.join(replacements)
            if before == after:
                continue
            change = f"{before} -> {after}"
            for offset, restored_token in enumerate(replacements):
                item = items[start + offset]
                item['text'] = restored_token
                item.setdefault('context_changes', []).append(change)
                engine = str(item.get('ocr_engine') or 'unknown')
                if not engine.endswith('+context'):
                    item['ocr_engine'] = engine + '+context'
                cores[start + offset] = re.sub(r'^\W+|\W+$', '', restored_token, flags=re.UNICODE)
    return items
