# PDF to Speech

Convert a PDF document to an MP3 audio file using [Kokoro TTS](https://github.com/remsky/kokoro-fastapi).

## How it works

1. Extracts text from the PDF (via `pdfplumber` or `pypdf`)
2. Cleans the text — strips headers/footers, page numbers, bare URLs, fixes hyphenated line-breaks, normalises abbreviations and punctuation
3. Splits the cleaned text into ~500-word chunks at paragraph boundaries
4. Sends each chunk to a locally running Kokoro TTS server and streams the audio into a single MP3

## Requirements

- Python 3.10+
- Docker (for the Kokoro TTS server)
- `httpx` plus one PDF library: `pdfplumber` (preferred) or `pypdf`

```bash
pip install httpx pdfplumber
```

## Setup

Start the Kokoro TTS server:

```bash
docker compose up -d
```

The server listens on `http://localhost:8880`. Wait for the health-check to pass before running the converter (usually ~30 s on first boot while models download).

For GPU acceleration, edit `docker-compose.yml` and swap in the `kokoro-fastapi-gpu` image (see the comments in the file).

## Usage

```bash
python pdf_to_speech.py <input.pdf> [options]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--output PATH` | `output/<input>.mp3` | Output MP3 file path |
| `--voice ID` | `af_bella` | Kokoro voice ID |
| `--speed FLOAT` | `1.0` | Playback speed multiplier |
| `--host URL` | `http://localhost:8880` | Kokoro API base URL |
| `--skip-tables` | off | Drop table placeholders from the text |
| `--skip-figures` | off | Drop figure placeholders from the text |
| `--txt-only` | off | Extract and clean text only, skip TTS |
| `--multi-column` | off | Use layout-aware extraction for multi-column PDFs (e.g. academic papers) |

### Examples

```bash
# Basic conversion
python pdf_to_speech.py paper.pdf

# Custom voice and faster speed
python pdf_to_speech.py paper.pdf --voice af_sky --speed 1.25

# Just extract the cleaned text, no audio
python pdf_to_speech.py paper.pdf --txt-only

# Save to a specific path
python pdf_to_speech.py paper.pdf --output ~/audiobooks/paper.mp3

# Multi-column layout (e.g. two-column academic paper)
python pdf_to_speech.py paper.pdf --multi-column
```

Output files are written to the `output/` directory by default (both the cleaned `.txt` and the `.mp3`).

## Scanned PDFs

If the PDF contains only images (no text layer), extraction will fail with a clear error. Pre-process it with [ocrmypdf](https://ocrmypdf.readthedocs.io/) first:

```bash
ocrmypdf input.pdf input_ocr.pdf
python pdf_to_speech.py input_ocr.pdf
```
