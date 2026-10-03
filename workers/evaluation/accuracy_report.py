#!/usr/bin/env python3
"""Ground-truth metrics for SheetTools recognition quality.

Accuracy is never inferred from OCR confidence.  It is calculated only when a
human-verified reference MusicXML is supplied.
"""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from typing import Sequence

from lxml import etree


def _edit_distance(reference: Sequence[object], prediction: Sequence[object]) -> int:
    previous = list(range(len(prediction) + 1))
    for row, expected in enumerate(reference, start=1):
        current = [row]
        for column, actual in enumerate(prediction, start=1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (expected != actual),
            ))
        previous = current
    return previous[-1]


def _accuracy(reference: Sequence[object], prediction: Sequence[object]) -> float:
    denominator = max(len(reference), len(prediction), 1)
    return max(0.0, 1.0 - (_edit_distance(reference, prediction) / denominator))


def _note_tokens(path: str | Path) -> list[tuple[str, str, str, str]]:
    root = etree.parse(str(path)).getroot()
    tokens: list[tuple[str, str, str, str]] = []
    for note in root.xpath("//*[local-name()='note'][not(*[local-name()='grace'])]"):
        voice = note.xpath("string(*[local-name()='voice'])") or "1"
        duration = note.xpath("string(*[local-name()='duration'])") or "0"
        if note.xpath("./*[local-name()='rest']"):
            pitch = "REST"
        else:
            step = note.xpath("string(*[local-name()='pitch']/*[local-name()='step'])")
            alter = note.xpath("string(*[local-name()='pitch']/*[local-name()='alter'])") or "0"
            octave = note.xpath("string(*[local-name()='pitch']/*[local-name()='octave'])")
            pitch = f"{step}:{alter}:{octave}"
        chord = "chord" if note.xpath("./*[local-name()='chord']") else "onset"
        tokens.append((voice, pitch, duration, chord))
    return tokens


def _lyrics(path: str | Path) -> str:
    root = etree.parse(str(path)).getroot()
    values = root.xpath("//*[local-name()='lyric']/*[local-name()='text']/text()")
    normalized = " ".join(" ".join(values).split())
    return unicodedata.normalize("NFC", normalized).casefold()


def compare_musicxml(reference_path: str | Path, prediction_path: str | Path) -> dict:
    reference_notes = _note_tokens(reference_path)
    prediction_notes = _note_tokens(prediction_path)
    reference_lyrics = _lyrics(reference_path)
    prediction_lyrics = _lyrics(prediction_path)

    char_error_rate = _edit_distance(reference_lyrics, prediction_lyrics) / max(len(reference_lyrics), 1)
    reference_words = reference_lyrics.split()
    prediction_words = prediction_lyrics.split()
    word_error_rate = _edit_distance(reference_words, prediction_words) / max(len(reference_words), 1)

    return {
        "ground_truth_used": True,
        "note_sequence_accuracy": round(_accuracy(reference_notes, prediction_notes), 6),
        "reference_note_count": len(reference_notes),
        "prediction_note_count": len(prediction_notes),
        "lyric_character_accuracy": round(max(0.0, 1.0 - char_error_rate), 6),
        "lyric_word_accuracy": round(max(0.0, 1.0 - word_error_rate), 6),
        "character_error_rate": round(char_error_rate, 6),
        "word_error_rate": round(word_error_rate, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare recognized MusicXML with verified ground truth")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--prediction", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = compare_musicxml(args.reference, args.prediction)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
