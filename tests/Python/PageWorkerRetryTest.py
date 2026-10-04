"""Multi-page worker reuses healthy checkpoints and reruns only the selected page."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "workers"))
import audiveris_runner
from xml_tools import page_merger

SCORE = '<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Music</part-name></score-part></part-list><part id="P1"><measure number="1"><note><rest/><duration>1</duration></note></measure></part></score-partwise>'


class PageWorkerRetryTest(unittest.TestCase):
    def test_selected_page_reruns_while_other_checkpoint_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.pdf"
            source.write_bytes(b"source")
            pages = root / "pages"
            pages.mkdir()
            for number in (1, 2):
                (pages / f"page-{number:03d}.png").write_bytes(f"page {number}".encode())
            output = root / "omr"
            calls = []
            original_process = audiveris_runner.process

            def fake_process(input_path, output_dir, *args, **kwargs):
                if input_path == str(source):
                    return original_process(input_path, output_dir, *args, **kwargs)
                calls.append(Path(input_path).name)
                folder = Path(output_dir)
                folder.mkdir(parents=True, exist_ok=True)
                raw = folder / "raw.musicxml"
                raw.write_text(SCORE)
                document = folder / 'document.json'
                document.write_text(json.dumps({'composer': {'text': 'First page composer'}}))
                return {"success": True, "raw_xml_path": str(raw), "xml_path": str(raw),
                        'document_artifact_path': str(document)}

            def fake_merge(_paths, destination, _title):
                if Path(destination).name == 'notation_with_lyrics.musicxml':
                    self.assertIsNone(_title, 'pipeline must preserve the recognized title when merging')
                Path(destination).write_text(SCORE)
                return True

            with patch.object(audiveris_runner, "find_audiveris_cli", return_value="fake"), \
                 patch.object(audiveris_runner, "process", side_effect=fake_process), \
                 patch.object(page_merger, "merge_musicxml_pages", side_effect=fake_merge):
                result = original_process(str(source), str(output), include_lyrics=True, pages_dir=str(pages))
                self.assertTrue(result["success"])
                self.assertEqual(str(output / 'page_result_0001' / 'document.json'), result.get('document_artifact_path'))
                self.assertEqual(["page-001.png", "page-002.png"], calls)
                calls.clear()
                self.assertTrue(original_process(str(source), str(output), include_lyrics=False,
                                                 pages_dir=str(pages), retry_page_index=1)["success"])
                self.assertEqual(["page-002.png"], calls)
                progress = json.loads((output / "page_progress.json").read_text())
                self.assertEqual("completed", progress["status"])
                self.assertEqual(2, progress["processed_pages"])


if __name__ == "__main__":
    unittest.main()
