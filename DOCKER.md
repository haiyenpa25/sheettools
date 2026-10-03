# SheetTools on Docker Desktop

## Start

Docker Desktop must be running in Linux containers mode.

```powershell
docker compose up -d --build
docker compose ps
```

Open <http://localhost:8080>. The API health endpoint is available at
<http://localhost:8080/api/health>.

To use another host port, create a `.env` file containing, for example:

```dotenv
SHEETTOOLS_PORT=8088
OMR_TIMEOUT_SECONDS=600
```

## Data and lifecycle

Project files, source scans, `source.omr`, raw/current/final MusicXML and exports
are stored in the named volume `sheettools-storage`. Rebuilding or replacing the
container does not remove this volume.

```powershell
docker compose logs -f app
docker compose restart app
docker compose down
```

`docker compose down` preserves project data. Only
`docker compose down --volumes` deletes the named volume and must be used with
care.

## Verification

```powershell
docker compose exec app php tests/run_all.php
docker compose exec app tesseract --list-langs
docker compose exec app /opt/venv/bin/python -c "import cv2,lxml,music21; print('Python OMR libs OK')"
docker compose exec app /opt/audiveris/bin/Audiveris -version
```

The production image contains Vue/Vite static assets, Apache with PHP 8.3,
Python/OpenCV/music21/lxml, Tesseract OCR with Vietnamese and English language
data, Java 21 and Audiveris 5.11.0.

