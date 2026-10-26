# PDF to Speech Text Skill

Convert a PDF document into a plain text file optimized for text-to-speech (TTS) synthesis.

## Trigger

Use this skill when the user asks to:
- Convert a PDF to audio / speech / mp3
- Extract speakable text from a PDF
- Prepare a PDF for text-to-speech

## What this skill does

Takes a PDF file path as input and produces a clean `.txt` file ready for TTS engines. The output strips visual formatting noise (page numbers, headers/footers, hyphenation artifacts, footnotes, links) and restructures the text so it reads naturally when spoken aloud.

## Steps

1. **Extract raw text from the PDF**
   - Use `pdfplumber` (preferred) or `pypdf` as fallback
   - Extract page-by-page, preserving paragraph order
   - Note the total page count for progress reporting

2. **Clean the extracted text**
   - Remove page numbers (standalone digits on their own line)
   - Remove running headers and footers along with footnotes and links (repeated short lines across pages)
   - Rejoin hyphenated line-breaks: `re.sub(r'-\n(\w)', r'\1', text)`
   - Collapse excessive whitespace: multiple blank lines → single blank line
   - Strip leading/trailing whitespace per paragraph

3. **Structure for natural speech**
   - Preserve paragraph breaks as double newlines (TTS engines use these as pauses)
   - Expand common abbreviations that TTS engines mispronounce:
     - `e.g.` → `for example`
     - `i.e.` → `that is`
     - `etc.` → `et cetera`
     - `vs.` → `versus`
     - `Fig.` → `Figure`
     - `No.` (when followed by a digit) → `Number`
   - Convert ordinals for clarity: `1st` → `first`, `2nd` → `second`, `3rd` → `third`
   - Spell out symbols: `%` → `percent`, `&` → `and`, `@` → `at`
   - Normalize quotes and dashes: curly quotes → straight, em-dash `—` → `, `

4. **Handle special sections**
   - Skip or summarize tables: replace table blocks with `[Table: <caption if available>]`
   - Skip or label figures: replace image/figure blocks with `[Figure: <caption if available>]`
   - Preserve footnote text inline, wrapped in commas: `[Footnote: <text>]`

5. **Write the output file**
   - Output path: same directory as input, same base name, `.txt` extension
   - Encoding: UTF-8
   - Report: print total character count and estimated reading time (avg 150 wpm, ~5 chars/word)

6. **Send text to Kokoro TTS and save MP3**
   - Split the cleaned text into chunks of ≤ 500 words (Kokoro handles long input poorly in one shot)
   - For each chunk POST to the Kokoro FastAPI container:
     ```
     POST http://localhost:8880/v1/audio/speech
     Content-Type: application/json

     {
       "model": "kokoro",
       "input": "<chunk text>",
       "voice": "af_bella",
       "response_format": "mp3",
       "speed": 1.0
     }
     ```
   - Stream the binary response directly to disk for each chunk
   - Concatenate all chunk MP3 bytes in order into a single output file
   - Output path: same directory as input PDF, same base name, `.mp3` extension
   - Print progress: `Chunk N/M synthesized...` and final file size

   **Voice options** (pass via `--voice` flag):
   | Voice ID | Style |
   |---|---|
   | `af_bella` | American Female, warm (default) |
   | `af_sky` | American Female, bright |
   | `am_adam` | American Male |
   | `bf_emma` | British Female |
   | `bm_george` | British Male |

   **Combining voices**: `af_bella(2)+af_sky(1)` mixes at 2:1 ratio.

   **If Kokoro is unreachable**: print a clear error —
   `ERROR: Cannot reach Kokoro at http://localhost:8880 — is the Docker container running?`
   and exit with code 1.

## Usage

```bash
python pdf_to_speech.py <input.pdf> [--output <output.mp3>] [--voice af_bella] [--speed 1.0] [--host http://localhost:8880] [--skip-tables] [--skip-figures]
```

## Output format example

```
Chapter One: The Beginning

It was a cold morning in November. The kind of morning that made you want to stay in bed.

John walked to the window and looked out at the grey sky. He had been awake since four, turning the problem over in his mind.

[Figure: Map of the city centre]

The answer, he realized, had been there all along.
```

## Dependencies

- `pdfplumber>=0.10` — primary PDF extraction
- `pypdf>=4.0` — fallback extraction
- `httpx>=0.27` — async HTTP client for Kokoro API calls
- `re` — standard library, regex cleaning

Install: `pip install pdfplumber pypdf httpx`

## Kokoro Docker setup

```bash
# CPU (no GPU required)
docker run -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest

# GPU (NVIDIA)
docker run --gpus all -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu:latest
```

API docs available at `http://localhost:8880/docs` once running.

## Notes

- If the PDF is scanned (image-only), extraction will return empty text. In that case, notify the user and suggest running OCR first (e.g. with `ocrmypdf`).
- Academic papers with two-column layouts may need column-order correction — flag this to the user if detected.
- Very long PDFs (500+ pages) should be processed in chunks and output streamed to avoid memory issues.
