# Genuine Audiveris 5.11 fixtures

Generated 2026-10-04 using the official Audiveris 5.11.0 package in
`sheettools:local`, from existing repository inputs:

- `002.omr` / `002.musicxml`: `public/samples/1.pdf` (Từ Cõi Lòng).
- `003.omr` / `003.musicxml`: `public/samples/2.pdf` (Trọn Cả Tấm Lòng).

Command: `python workers/audiveris_runner.py --input public/samples/2.pdf --output storage/roadmap1_real_003 --notation-only`
(equivalent command for 002). MusicXML fixtures are byte-for-byte RAW exports.
The .omr ZIPs are preserved whole, including book version and binary page.

These are schema/mapping regression fixtures, **not human-verified ground truth**.
Audiveris logged missing legacy English Tesseract components; its note export
completed successfully. This warning is retained in runtime logs under storage.
