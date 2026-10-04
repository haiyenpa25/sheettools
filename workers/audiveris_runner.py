#!/usr/bin/env python3
"""
workers/audiveris_runner.py
Điều phối notation-first OMR pipeline:
PDF → PNG → OpenCV preprocessing → notation/text separation → Audiveris → derived lyrics MusicXML
Usage: python audiveris_runner.py --input <file.pdf|file.png> --output <out_dir> [--audiveris <path_to_audiveris_cli>]
"""
import argparse
import copy
import hashlib
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from statistics import mean
from pathlib import Path

# Thêm đường dẫn root vào sys.path để import auto_healer & vietnamese_universal_ocr
sys.path.insert(0, os.path.dirname(__file__))


def confidence_summary(items: list[dict]) -> dict:
    values = [float(item.get("confidence", 0.0)) for item in items]
    if not values:
        return {"count": 0, "mean": 0.0, "minimum": 0.0, "below_0_80": 0}
    return {
        "count": len(values),
        "mean": round(mean(values), 6),
        "minimum": round(min(values), 6),
        "below_0_80": sum(value < 0.80 for value in values),
    }


def write_notation_only(source_path: str, destination_path: str, score_title: str | None = None) -> str:
    """Create strict notation MusicXML without OCR-derived text or expressive noise."""
    tree = ET.parse(source_path)
    root = tree.getroot()
    removable = {
        'lyric', 'lyric-font', 'lyric-language', 'direction', 'harmony', 'figured-bass',
        'ornaments', 'articulations', 'technical', 'fermata',
    }
    for parent in root.iter():
        for child in list(parent):
            if child.tag.rsplit('}', 1)[-1] in removable:
                parent.remove(child)
        # Remove empty <notations> containers after expressive markings are stripped.
        for child in list(parent):
            if child.tag.rsplit('}', 1)[-1] == 'notations' and len(child) == 0:
                parent.remove(child)

    if score_title:
        namespace = root.tag.split('}', 1)[0] + '}' if root.tag.startswith('{') else ''
        work = next((node for node in root if node.tag.rsplit('}', 1)[-1] == 'work'), None)
        if work is None:
            work = ET.Element(namespace + 'work')
            root.insert(0, work)
        title = next((node for node in work if node.tag.rsplit('}', 1)[-1] == 'work-title'), None)
        if title is None:
            title = ET.SubElement(work, namespace + 'work-title')
        if not (title.text or '').strip():
            title.text = score_title
    tree.write(destination_path, encoding='utf-8', xml_declaration=True)
    return destination_path


def write_without_chords(source_path: str, destination_path: str) -> str:
    """Create a derived MusicXML artifact without chord-symbol harmony nodes."""
    tree = ET.parse(source_path)
    root = tree.getroot()
    for parent in root.iter():
        for child in list(parent):
            if child.tag.rsplit('}', 1)[-1] == 'harmony':
                parent.remove(child)
    tree.write(destination_path, encoding='utf-8', xml_declaration=True)
    return destination_path


def merge_semantic_elements(primary_path: str, auxiliary_path: str, destination_path: str, include_harmony: bool = True) -> str:
    """Copy directions/harmonies from full grayscale OMR without touching primary notes."""
    primary_tree = ET.parse(primary_path)
    auxiliary_tree = ET.parse(auxiliary_path)
    primary_root, auxiliary_root = primary_tree.getroot(), auxiliary_tree.getroot()
    allowed = {'direction', 'harmony'} if include_harmony else {'direction'}
    primary_parts = [node for node in primary_root if node.tag.rsplit('}', 1)[-1] == 'part']
    auxiliary_parts = {node.get('id'): node for node in auxiliary_root if node.tag.rsplit('}', 1)[-1] == 'part'}
    for primary_part in primary_parts:
        auxiliary_part = auxiliary_parts.get(primary_part.get('id'))
        if auxiliary_part is None:
            continue
        primary_measures = [node for node in primary_part if node.tag.rsplit('}', 1)[-1] == 'measure']
        auxiliary_measures = [node for node in auxiliary_part if node.tag.rsplit('}', 1)[-1] == 'measure']
        for primary_measure, auxiliary_measure in zip(primary_measures, auxiliary_measures):
            existing = {ET.tostring(node, encoding='unicode') for node in primary_measure
                        if node.tag.rsplit('}', 1)[-1] in {'direction', 'harmony'}}
            first_note_index = next((index for index, node in enumerate(primary_measure)
                                     if node.tag.rsplit('}', 1)[-1] == 'note'), len(primary_measure))
            for node in auxiliary_measure:
                if node.tag.rsplit('}', 1)[-1] not in allowed:
                    continue
                serialized = ET.tostring(node, encoding='unicode')
                if serialized not in existing:
                    primary_measure.insert(first_note_index, copy.deepcopy(node))
                    first_note_index += 1
                    existing.add(serialized)
    primary_tree.write(destination_path, encoding='utf-8', xml_declaration=True)
    return destination_path


def write_lyrics_artifact(decomp_meta: dict, destination_path: str, page_number: int = 1) -> str:
    """Persist OCR lyrics independently from MusicXML so note recognition stays immutable."""
    words = []
    for sequence, item in enumerate(decomp_meta.get("lyrics", []), start=1):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        words.append({
            "id": f"p{page_number}-w{sequence}",
            "page": page_number,
            "staff_index": int(item.get("staff_index", 0)),
            "verse_number": int(item.get("verse_number", 1)),
            "sequence": sequence,
            "text": text,
            "x": float(item.get("x", 0.0)),
            "y": float(item.get("y", 0.0)),
            "box": list(item.get("box", [])),
            "confidence": float(item.get("confidence", 0.0)),
            "ocr_engine": item.get("ocr_engine"),
            "raw_ocr": item.get("raw_ocr"),
            "ocr_candidates": item.get("ocr_candidates", []),
            "context_changes": item.get("context_changes", []),
            "diacritic_fusion": item.get("diacritic_fusion"),
            **{key: item[key] for key in ('system_id', 'section_id', 'section_type', 'lyric_name', 'row_offset',
                                         'box_source', 'geometry_needs_review', 'poem_stanza') if key in item},
            "alignment": None,
        })
    verses: dict[str, list[dict]] = {}
    for word in words:
        verses.setdefault(str(word["verse_number"]), []).append(word)
    artifact = {
        "schema_version": 2 if decomp_meta.get('sections') else 1,
        "artifact_type": "lyrics_ocr",
        "alignment_status": "unreviewed",
        "page_count": 1,
        "word_count": len(words),
        "words": words,
        "verses": verses,
        "sections": decomp_meta.get('sections', []),
        "stanzas": [{**stanza, 'words': [word for word in words if word.get('poem_stanza') == stanza['id']]}
                    for stanza in decomp_meta.get('stanzas', [])],
    }
    temporary = destination_path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as output:
        json.dump(artifact, output, ensure_ascii=False, indent=2)
    os.replace(temporary, destination_path)
    return destination_path


def merge_lyrics_artifacts(source_paths: list[str], destination_path: str) -> str:
    """Merge page-level lyric artifacts without losing page/staff/verse coordinates."""
    words, sections, stanzas = [], [], []
    for page_index, source_path in enumerate(source_paths, 1):
        with open(source_path, "r", encoding="utf-8") as source:
            page_artifact = json.load(source)
        page_words = page_artifact.get('words', [])
        for section in page_artifact.get('sections', []):
            old_id = section['id']
            section['id'] = f'p{page_index}-{old_id}'
            section['page'] = page_index
            section['measure_scope'] = 'page_original'
            for word in page_words:
                if word.get('section_id') == old_id:
                    word['section_id'] = section['id']
            sections.append(section)
        for stanza in page_artifact.get('stanzas', []):
            stanza['page'] = page_index
            stanzas.append(stanza)
        words.extend(page_words)
    words.sort(key=lambda item: (
        int(item.get("page", 1)), int(item.get("staff_index", 0)),
        int(item.get("verse_number", 1)), float(item.get("y", 0)), float(item.get("x", 0)),
    ))
    verses: dict[str, list[dict]] = {}
    for word in words:
        verses.setdefault(str(word.get("verse_number", 1)), []).append(word)
    review_count = sum(1 for word in words if (word.get("alignment") or {}).get("status") != "accepted")
    artifact = {
        "schema_version": 2 if sections else 1,
        "artifact_type": "lyrics_ocr",
        "alignment_status": "aligned" if words and review_count == 0 else "needs_review",
        "page_count": len(source_paths),
        "word_count": len(words),
        "words": words,
        "verses": verses,
        "sections": sections,
        "stanzas": stanzas,
        "alignment_summary": {
            "accepted": len(words) - review_count,
            "review": review_count,
            "algorithm": "monotonic_spatial_dp_v1",
        },
    }
    if sections:
        from xml_tools.lyric_structure import structure_tree
        artifact['sections'] = structure_tree(words, sections)
    temporary = destination_path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as output:
        json.dump(artifact, output, ensure_ascii=False, indent=2)
    os.replace(temporary, destination_path)
    return destination_path


def _load_page_checkpoint(path: str, require_lyrics: bool = False, source_sha256: str | None = None) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as checkpoint_file:
            result = json.load(checkpoint_file)
        required = [result.get("raw_xml_path"), result.get("xml_path")]
        if require_lyrics:
            required.append(result.get("lyrics_artifact_path"))
        if source_sha256 is not None and result.get("source_sha256") != source_sha256:
            return None
        if result.get('pipeline_version') != 'roadmap1_v2':
            return None
        return result if result.get("success") and all(p and os.path.isfile(p) for p in required) else None
    except (OSError, ValueError, TypeError):
        return None


def _save_page_checkpoint(path: str, result: dict) -> None:
    checkpoint = {key: value for key, value in result.items() if key != "log"}
    checkpoint['pipeline_version'] = 'roadmap1_v2'
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as checkpoint_file:
        json.dump(checkpoint, checkpoint_file, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

# ───────── pypdfium2 trích ảnh PNG từ PDF ─────────
def pdf_to_png_pages(pdf_path: str, output_dir: str, dpi: int = 300) -> list:
    """Chuyển mỗi trang PDF thành file PNG 300 DPI."""
    from preprocessing.extract_pdf import extract_pdf_pages
    result = extract_pdf_pages(pdf_path, output_dir, dpi=dpi, max_pages=50)
    if not result["success"]:
        raise RuntimeError(result["error"])
    return result["pages"]


def extract_zip_pages(archive_path: str, output_dir: str) -> list[str]:
    from preprocessing.extract_zip import extract_zip_pages as extract_pages
    return extract_pages(archive_path, output_dir)


# ───────── Tiền xử lý ảnh nâng cao (OpenCV Deskew, CLAHE & Denoising) ─────────
def preprocess_image(png_path: str, out_path: str) -> str:
    """Tăng tương phản thông minh, khử đổ bóng và chỉnh góc nghiêng (Deskew) trước khi đưa vào OMR."""
    try:
        from preprocessing.pipeline import preprocess_image as adv_preprocess
        if adv_preprocess(png_path, out_path, enable_deskew=True, enable_shadow_removal=None,
                          report_path=out_path + '.quality.json',
                          debug_dir=os.path.join(os.path.dirname(out_path), 'preprocess_debug')):
            return out_path
    except Exception as e:
        print(f"[AudiverisRunner] Preprocessing notice: {e}")
    return png_path


# ───────── Tìm Audiveris CLI ─────────
def find_audiveris_cli(hint=None):
    """Tìm Audiveris CLI từ các vị trí thông thường trên Windows."""
    candidates = []
    if hint:
        candidates.append(hint)

    candidates += [
        r"D:\tools\audiveris\install\Audiveris\Audiveris.exe",
        r"D:\tools\audiveris\bin\Audiveris.bat",
        r"C:\Program Files\Audiveris\bin\Audiveris.bat",
        r"D:\audiveris\bin\Audiveris.bat",
        r"C:\tools\audiveris\bin\Audiveris.bat",
    ]
    import shutil
    path_result = shutil.which("Audiveris") or shutil.which("audiveris")
    if path_result:
        candidates.insert(0, path_result)

    for c in candidates:
        if os.path.isfile(c):
            return c

    for search_root in [r"D:\tools", r"C:\Program Files"]:
        if os.path.isdir(search_root):
            matches = glob.glob(os.path.join(search_root, "**", "Audiveris.exe"), recursive=True) + \
                      glob.glob(os.path.join(search_root, "**", "Audiveris.bat"), recursive=True)
            if matches:
                return matches[0]
    return None


# ───────── Gọi Audiveris CLI ─────────
def run_audiveris(input_path: str, output_dir: str, audiveris_cli: str) -> dict:
    """Gọi Audiveris CLI và trả về dict chứa đường dẫn MusicXML + log."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        audiveris_cli,
        "-batch",
        "-save",
        "-export",
        "-output", output_dir,
        input_path
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=int(os.getenv("OMR_TIMEOUT_SECONDS", "180")),
            encoding='utf-8', errors='replace'
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Audiveris exceeded the configured timeout", "xml_path": None}
    except FileNotFoundError:
        return {"success": False, "error": f"Audiveris CLI không tìm thấy: {audiveris_cli}", "xml_path": None}

    log = f"CMD: {' '.join(cmd)}\nEXIT: {exit_code}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"

    # Tìm file MusicXML output (có thể là .xml hoặc .mxl)
    xml_files = sorted(glob.glob(os.path.join(output_dir, "**", "*.xml"), recursive=True))
    mxl_files = sorted(glob.glob(os.path.join(output_dir, "**", "*.mxl"), recursive=True))
    omr_files = sorted(glob.glob(os.path.join(output_dir, "**", "*.omr"), recursive=True))

    xml_path = None

    if xml_files:
        xml_path = xml_files[0]
    elif mxl_files:
        mxl_path = mxl_files[0]
        try:
            with zipfile.ZipFile(mxl_path, 'r') as z:
                for name in z.namelist():
                    if name.endswith('.xml') and 'META-INF' not in name:
                        archive_path = Path(name)
                        if archive_path.is_absolute() or '..' in archive_path.parts:
                            raise ValueError(f"Unsafe MXL entry: {name}")
                        extract_path = Path(output_dir) / archive_path.name
                        with z.open(name) as source, open(extract_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        xml_path = str(extract_path)
                        break
        except Exception as e:
            log += f"\nLỗi giải nén MXL: {e}"

    # Preserve the byte-for-byte Audiveris export before any lyric enrichment.
    if xml_path and os.path.isfile(xml_path):
        raw_xml_path = os.path.join(output_dir, "raw_audiveris.musicxml")
        shutil.copy2(xml_path, raw_xml_path)

        return {
            "success": True,
            "xml_path": raw_xml_path,
            "raw_xml_path": raw_xml_path,
            "omr_paths": omr_files,
            "exit_code": exit_code,
            "log": log
        }
    else:
        return {
            "success": False,
            "error": "Không tìm thấy file MusicXML trong output. Xem log để debug.",
            "exit_code": exit_code,
            "log": log,
            "xml_path": None
        }


# ───────── Pipeline chính ─────────
def process(
    input_path: str,
    output_dir: str,
    audiveris_hint=None,
    include_lyrics: bool = True,
    include_chords: bool = True,
    source_page_number: int = 1,
    pages_dir: str | None = None,
    retry_page_index: int | None = None,
) -> dict:
    input_path = os.path.abspath(input_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    audiveris_cli = find_audiveris_cli(audiveris_hint)
    if not audiveris_cli:
        if os.getenv("ENABLE_EXPERIMENTAL_CV_FALLBACK") != "1":
            return {
                "success": False,
                "error": "Không tìm thấy Audiveris; nhận dạng thử nghiệm chưa được bật.",
                "xml_path": None,
            }
        print("[Hybrid-OMR] Audiveris CLI not found; experimental CV fallback is enabled.")
        try:
            from cv_omr_engine import ComputerVisionOmrEngine
            cv_engine = ComputerVisionOmrEngine()
            fallback_result = cv_engine.process(input_path, output_dir)
            fallback_result["engine"] = "cv_experimental"
            fallback_result["needs_review"] = True
            return fallback_result
        except Exception as e:
            return {
                "success": False,
                "error": f"Lỗi thực thi CV OMR: {e}",
                "xml_path": None
            }

    ext = Path(input_path).suffix.lower()

    # Bước 1: Chuyển PDF sang PNG nếu cần
    if ext == '.pdf':
        try:
            if pages_dir is not None:
                from preprocessing.extract_pdf import list_rendered_pages
                pages = list_rendered_pages(pages_dir, 50)
            else:
                png_dir = os.path.join(output_dir, "pages")
                pages = pdf_to_png_pages(input_path, png_dir, dpi=300)
        except Exception as e:
            return {"success": False, "error": f"Lỗi trích PNG từ PDF: {e}", "xml_path": None}

        if not pages:
            return {"success": False, "error": "PDF không có trang nào.", "xml_path": None}
        if retry_page_index is not None and not 0 <= retry_page_index < len(pages):
            return {"success": False, "error": "Requested page index is outside the document.", "xml_path": None}

        if len(pages) > 1:
            from page_progress import PageProgress
            progress = PageProgress(os.path.join(output_dir, "page_progress.json"), len(pages))
            page_results = []
            for page_index, page_path in enumerate(pages, start=1):
                progress.start_page(page_index)
                page_output = os.path.join(output_dir, f"page_result_{page_index:04d}")
                os.makedirs(page_output, exist_ok=True)
                checkpoint_path = os.path.join(page_output, "page_checkpoint.json")
                source_sha256 = _file_sha256(page_path)
                page_result = None if retry_page_index == page_index - 1 else _load_page_checkpoint(
                    checkpoint_path, require_lyrics=include_lyrics, source_sha256=source_sha256
                )
                if page_result:
                    print(f"[Hybrid-OMR] Resume: page {page_index}/{len(pages)} already completed.")
                else:
                    print(f"[Hybrid-OMR] Processing page {page_index}/{len(pages)}.")
                    # Preserve each page's authoritative harmony data. Output-mode filtering
                    # happens only after the pages are merged, so checkpoints stay reusable.
                    page_result = process(
                        page_path, page_output, audiveris_cli, include_lyrics, True, page_index
                    )
                if not page_result.get("success"):
                    progress.fail_page(page_index, str(page_result.get('error', 'unknown error')))
                    return {
                        "success": False,
                        "error": f"OMR failed on PDF page {page_index}: {page_result.get('error', 'unknown error')}",
                        "xml_path": None,
                    }
                page_result["source_sha256"] = source_sha256
                _save_page_checkpoint(checkpoint_path, page_result)
                page_results.append(page_result)
                progress.complete_page(page_index)

            from xml_tools.page_merger import merge_musicxml_pages
            raw_pages = [item["raw_xml_path"] for item in page_results]
            enriched_pages = [item["xml_path"] for item in page_results]
            merged_raw = os.path.join(output_dir, "raw_audiveris.musicxml")
            merged_enriched = os.path.join(output_dir, "notation_with_lyrics.musicxml")
            if not merge_musicxml_pages(raw_pages, merged_raw, "Merged Audiveris score"):
                return {"success": False, "error": "Could not merge raw MusicXML pages", "xml_path": None}
            if include_lyrics:
                if not merge_musicxml_pages(enriched_pages, merged_enriched, "Merged score with lyrics"):
                    return {"success": False, "error": "Could not merge lyric MusicXML pages", "xml_path": None}
            else:
                write_notation_only(merged_raw, merged_enriched, Path(input_path).stem)
            if include_lyrics and not include_chords:
                without_chords = os.path.join(output_dir, "without_chords.musicxml")
                merged_enriched = write_without_chords(merged_enriched, without_chords)
            lyrics_artifacts = [item.get("lyrics_artifact_path") for item in page_results]
            lyrics_artifacts = [path for path in lyrics_artifacts if path and os.path.isfile(path)]
            merged_lyrics_artifact = None
            if include_lyrics and lyrics_artifacts:
                merged_lyrics_artifact = merge_lyrics_artifacts(
                    lyrics_artifacts, os.path.join(output_dir, "lyrics.json")
                )
            return {
                "success": True,
                "xml_path": merged_enriched,
                "raw_xml_path": merged_raw,
                "page_count": len(page_results),
                "pages_completed": len(page_results),
                "resumable": True,
                "page_omr_paths": [
                    path for item in page_results for path in item.get("omr_paths", []) if os.path.isfile(path)
                ],
                "lyrics_separated": include_lyrics,
                "lyrics_artifact_path": merged_lyrics_artifact,
                # Document-level header comes from the opening page, not a later page's header.
                "document_artifact_path": page_results[0].get('document_artifact_path'),
                "chords_included": include_lyrics and include_chords,
                "lyrics_confidence": round(mean(float(item.get("lyrics_confidence", 0.0)) for item in page_results), 6) if include_lyrics else 0.0,
                "lyrics_confidence_note": "Model confidence only; not ground-truth accuracy.",
                "log": "Processed every PDF page independently with notation-first separation.",
            }

        source_png = pages[0]
    elif ext in ('.png', '.jpg', '.jpeg', '.tif', '.tiff'):
        source_png = input_path
    else:
        return {"success": False, "error": f"Định dạng không hỗ trợ: {ext}", "xml_path": None}

    # Bước 2: Tiền xử lý ảnh thông minh (CLAHE + Denoise)
    preprocessed_png = os.path.join(output_dir, "preprocessed.png")
    final_png = preprocess_image(source_png, preprocessed_png)

    page_model = None
    layout_base = os.path.join(output_dir, f"page_{source_page_number:03d}_regions")
    try:
        from preprocessing.page_layout import PageLayoutAnalyzer
        layout_base = os.path.join(output_dir, f"page_{source_page_number:03d}_regions")
        page_model = PageLayoutAnalyzer().analyze(final_png, layout_base + ".json", layout_base + "_debug.png")
        page_model['page'] = source_page_number
    except Exception as layout_error:
        print(f"[AudiverisRunner] Page layout notice: {layout_error}")

    # Bước 2b: 3-Zone Spatial Decomposition (Tách Header, Bản Nhạc Nốt Thuần Khiết, Lời & Hợp Âm)
    decomp_meta = None
    full_content_png = final_png
    try:
        from xml_tools.vietnamese_universal_ocr import decompose_sheet_3zones
        decomp = decompose_sheet_3zones(final_png, page_model=page_model)
        import cv2
        model = decomp.get('page_model')
        if model is not None:
            for name, mask in decomp.get('text_masks', {}).items():
                mask_path = os.path.join(output_dir, f"mask_{name}.png")
                if not cv2.imwrite(mask_path, mask):
                    raise RuntimeError(f"Cannot write text mask: {mask_path}")
                model['masks'][name] = os.path.basename(mask_path)
            model_path = os.path.join(output_dir, 'page_model.json')
            PageLayoutAnalyzer.save(model, cv2.imread(full_content_png), model_path, layout_base + '_debug.png')
            PageLayoutAnalyzer.save(model, cv2.imread(full_content_png), layout_base + '.json', layout_base + '_debug.png')
        if decomp.get("pure_notation_img") is not None:
            import cv2
            pure_png = os.path.join(output_dir, "pure_notation.png")
            cv2.imwrite(pure_png, decomp["pure_notation_img"])
            final_png = pure_png
        if include_lyrics:
            decomp_meta = decomp
    except Exception as e_decomp:
        print(f"[AudiverisRunner] 3-zone decomposition notice: {e_decomp}")

    # Bước 3: Chạy Audiveris OMR trên bản nhạc đã làm sạch + music21 Auto-Healer
    omr_out_dir = os.path.join(output_dir, "omr_out")
    result = run_audiveris(final_png, omr_out_dir, audiveris_cli)
    if result.get('success') and result.get('omr_paths'):
        try:
            from xml_tools.omr_anchors import OmrAnchorReader
            anchor_model = OmrAnchorReader().read(result['omr_paths'][0], result['raw_xml_path'], page_model)
            anchor_path = os.path.join(output_dir, 'note_anchors.json')
            with open(anchor_path, 'w', encoding='utf-8') as target:
                json.dump(anchor_model, target, ensure_ascii=False, indent=2)
            result['note_anchors_path'] = anchor_path
        except Exception as anchor_error:
            print(f'[AudiverisRunner] Pixel anchors unavailable: {anchor_error}')
    if result.get('success') and result.get('omr_paths'):
        # Derived copy only: raw_xml_path stays byte-for-byte Audiveris output.
        try:
            from xml_tools.clef_check import correct_octave_clefs
            checked_path = os.path.join(output_dir, 'clef_checked.musicxml')
            interline = float((page_model or {}).get('interline') or 20.0)
            result['clef_check'] = correct_octave_clefs(result['xml_path'], result['omr_paths'][0], final_png,
                                                        checked_path, interline)
            result['xml_path'] = checked_path
        except Exception as clef_error:
            print(f'[AudiverisRunner] Clef check notice: {clef_error}')

    # Dual-layer OMR: primary notes come from the notation-priority image;
    # directions and harmony may be recovered from the unmasked grayscale run.
    # The byte-for-byte primary export remains result['raw_xml_path'].
    if (result.get("success") and include_lyrics and final_png != full_content_png
            and os.getenv("ENABLE_DUAL_LAYER_OMR", "1") == "1"):
        auxiliary = run_audiveris(full_content_png, os.path.join(output_dir, "omr_full_content"), audiveris_cli)
        if auxiliary.get("success") and auxiliary.get("xml_path"):
            semantic_path = os.path.join(output_dir, "notation_with_semantics.musicxml")
            merge_semantic_elements(result["xml_path"], auxiliary["xml_path"], semantic_path, include_harmony=False)
            result["xml_path"] = semantic_path
            result["dual_layer_omr"] = True
        else:
            result["dual_layer_omr"] = False

    # Experimental CV output must never silently replace authoritative OMR.
    if (not result.get("success") or not result.get("xml_path")) and os.getenv("ENABLE_EXPERIMENTAL_CV_FALLBACK") == "1":
        print("[Hybrid-OMR] Audiveris failed; experimental CV fallback explicitly enabled.")
        try:
            from cv_omr_engine import ComputerVisionOmrEngine
            cv_engine = ComputerVisionOmrEngine()
            cv_res = cv_engine.process(input_path, output_dir)
            if cv_res.get("success"):
                result = cv_res
        except Exception as e:
            print(f"[Hybrid-OMR] CV fallback notice: {e}")

    if not result.get("success") or not result.get("xml_path"):
        result["success"] = False
        result["error"] = result.get("error", "Audiveris did not produce authoritative MusicXML")
        result["requires_manual_review"] = True

    # Ghi log ra file
    log_path = os.path.join(output_dir, "audiveris.log")
    if "log" in result:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(result["log"])
    result["log_path"] = log_path

    # Lyrics are enriched on a derived artifact; raw Audiveris output stays immutable.
    if result.get("success") and result.get("xml_path") and decomp_meta:
        try:
            from xml_tools.vietnamese_universal_ocr import inject_3zone_metadata_and_lyrics
            from xml_tools.lyrics_aligner import align_lyrics_artifact
            from xml_tools.lyric_structure import LyricStructureAnalyzer
            structure = LyricStructureAnalyzer().analyze(decomp_meta.get('lyrics', []),
                decomp_meta.get('page_model', {}).get('text_lines', []),
                anchor_model.get('anchors', []) if result.get('note_anchors_path') else [])
            decomp_meta['sections'] = structure['sections']
            enriched_path = os.path.join(output_dir, "notation_with_lyrics.musicxml")
            result["lyrics_artifact_path"] = write_lyrics_artifact(
                decomp_meta, os.path.join(output_dir, "lyrics.json"), source_page_number
            )
            document_model = decomp_meta.get("header", {}).get("document_model")
            if document_model:
                document_path = os.path.join(output_dir, "document.json")
                with open(document_path + ".tmp", "w", encoding="utf-8") as document_file:
                    json.dump(document_model, document_file, ensure_ascii=False, indent=2)
                os.replace(document_path + ".tmp", document_path)
                result["document_artifact_path"] = document_path
            shutil.copy2(result["xml_path"], enriched_path)
            if inject_3zone_metadata_and_lyrics(enriched_path, decomp_meta, inject_lyrics=False):
                from xml_tools.chord_alignment import inject_chords
                chord_summary = inject_chords(enriched_path, decomp_meta.get('harmonies', []) if include_chords else [],
                                              anchor_model.get('anchors', []) if result.get('note_anchors_path') else [])
                result['chord_alignment'] = chord_summary
                notation_path = os.path.join(output_dir, 'notation.musicxml')
                notation_tree = ET.parse(enriched_path)
                for parent in notation_tree.getroot().iter():
                    for child in list(parent):
                        if child.tag.rsplit('}', 1)[-1] == 'lyric':
                            parent.remove(child)
                notation_tree.write(notation_path, encoding='utf-8', xml_declaration=True)
                alignment_summary = align_lyrics_artifact(
                    enriched_path,
                    result["lyrics_artifact_path"],
                    enriched_path,
                    result["lyrics_artifact_path"],
                    acceptance_threshold=float(os.getenv('LYRIC_ALIGNMENT_THRESHOLD', '0.55')),
                    note_anchors_path=result.get('note_anchors_path'),
                )
                lyric_stats = confidence_summary(decomp_meta.get("lyrics", []))
                result["xml_path"] = enriched_path
                score_path = os.path.join(output_dir, 'score.musicxml')
                shutil.copy2(enriched_path, score_path)
                result['xml_path'] = score_path
                result["lyrics_separated"] = True
                result["lyrics_alignment"] = alignment_summary
                result["lyrics_confidence"] = lyric_stats["mean"]
                result["lyrics_confidence_stats"] = lyric_stats
                result["lyrics_confidence_note"] = "Model confidence only; not ground-truth accuracy."
                report_path = os.path.join(output_dir, "recognition_report.json")
                with open(result['lyrics_artifact_path'], encoding='utf-8') as artifact_file:
                    aligned_sections = json.load(artifact_file).get('sections', [])
                with open(report_path, "w", encoding="utf-8") as report_file:
                    json.dump({
                        "ground_truth_used": False,
                        "accuracy_available": False,
                        "lyrics": lyric_stats,
                        "lyrics_alignment": alignment_summary,
                        "notation_separation": decomp_meta.get("notation_separation", {}),
                        "chord_alignment": chord_summary,
                        "clef_check": result.get('clef_check'),
                        "section_count": len(structure['sections']),
                        "verse_count": structure['verse_count'],
                        "sections": [{key: section.get(key) for key in ('id', 'type', 'verse_count', 'measure_range',
                                     'systems', 'needs_review', 'alignment_summary')} for section in aligned_sections],
                        "message": "Provide verified reference MusicXML to calculate note accuracy and lyric CER/WER.",
                    }, report_file, ensure_ascii=False, indent=2)
                result["recognition_report_path"] = report_path
                print("[AudiverisRunner] Injected separately recognized lyrics into derived MusicXML.")
        except Exception as e_inj:
            print(f"[AudiverisRunner] Lyrics injection notice: {e_inj}")

    if result.get("success") and result.get("xml_path") and not include_lyrics:
        notation_path = os.path.join(output_dir, "notation_only.musicxml")
        result["xml_path"] = write_notation_only(result["xml_path"], notation_path, Path(input_path).stem)
        result["lyrics_separated"] = False
        result["recognition_mode"] = "notation_only"

    if result.get("success") and result.get("xml_path") and include_lyrics and not include_chords:
        without_chords = os.path.join(output_dir, "without_chords.musicxml")
        result["xml_path"] = write_without_chords(result["xml_path"], without_chords)
        result["chords_included"] = False

    return result


# ───────── CLI Entry Point ─────────
def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="Hybrid OMR Runner — SheetTools")
    parser.add_argument("--input", required=True, help="Đường dẫn file PDF hoặc PNG")
    parser.add_argument("--output", required=True, help="Thư mục output")
    parser.add_argument("--pages-dir", default=None, help="Ảnh trang đã render trong project")
    parser.add_argument("--retry-page-index", type=int, default=None, help="Chỉ nhận dạng lại trang này (0-based)")
    parser.add_argument("--audiveris", default=None, help="Đường dẫn Audiveris CLI (tùy chọn)")
    parser.add_argument("--notation-only", action="store_true", help="Bỏ qua OCR lời và loại lời khỏi MusicXML")
    parser.add_argument("--no-chords", action="store_true", help="Loại ký hiệu hợp âm khỏi MusicXML dẫn xuất")
    args = parser.parse_args()

    result = process(
        args.input,
        args.output,
        args.audiveris,
        include_lyrics=not args.notation_only,
        include_chords=not args.no_chords,
        pages_dir=args.pages_dir,
        retry_page_index=args.retry_page_index,
    )
    print("__OMR_JSON_RESULT__")
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
