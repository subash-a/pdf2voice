#!/usr/bin/env python3
"""Convert a PDF document to an MP3 audio file using Kokoro TTS."""

import argparse
import re
import sys
from pathlib import Path

import httpx

ABBREVIATIONS = [
    (r"\be\.g\.", "for example"),
    (r"\bi\.e\.", "that is"),
    (r"\betc\.", "et cetera"),
    (r"\bvs\.", "versus"),
    (r"\bFig\.", "Figure"),
    (r"\bNo\.(?=\s*\d)", "Number"),
]

ORDINALS = {
    "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth",
    "5th": "fifth", "6th": "sixth", "7th": "seventh", "8th": "eighth",
    "9th": "ninth", "10th": "tenth",
}

SYMBOLS = [
    (r"(\d)\s*%", r"\1 percent"),
    (r"\s&\s", " and "),
    (r"\s@\s", " at "),
]

# Curly quotes → straight; em/en dash → comma-space
NORMALISE = [
    ("\u2018", "'"), ("\u2019", "'"),
    ("\u201c", '"'), ("\u201d", '"'),
    ("\u2014", ", "), ("\u2013", ", "),
]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_text(pdf_path: Path, multi_column: bool = False) -> tuple[list[str], int]:
    """Return (pages_text, page_count). Uses pdfplumber, falls back to pypdf."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages = [p.extract_text(layout=multi_column) or "" for p in pdf.pages]
        return pages, len(pages)
    except ImportError:
        pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return pages, len(pages)
    except ImportError:
        print("ERROR: Neither pdfplumber nor pypdf is installed.")
        print("Install with: pip install pdfplumber pypdf")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def detect_repeated_lines(pages: list[str], threshold: int = 3) -> set[str]:
    """Find short lines that appear on many pages — likely headers/footers."""
    from collections import Counter
    line_counts: Counter = Counter()
    for page_text in pages:
        seen_on_page = set()
        for line in page_text.splitlines():
            stripped = line.strip()
            if stripped and len(stripped) < 80:
                if stripped not in seen_on_page:
                    line_counts[stripped] += 1
                    seen_on_page.add(stripped)
    return {line for line, count in line_counts.items() if count >= threshold}


def clean_page(text: str, repeated: set[str]) -> str:
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Drop page numbers (standalone digit strings)
        if re.fullmatch(r"\d+", stripped):
            continue
        # Drop repeated headers/footers
        if stripped in repeated:
            continue
        # Drop bare URLs / DOIs
        if re.match(r"https?://\S+$", stripped) or re.match(r"doi:\S+$", stripped, re.I):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def clean_text(pages: list[str], skip_tables: bool, skip_figures: bool) -> str:
    repeated = detect_repeated_lines(pages)
    parts = []
    for page_text in pages:
        text = clean_page(page_text, repeated)
        # Rejoin hyphenated line-breaks
        text = re.sub(r"-\n(\w)", r"\1", text)
        parts.append(text)

    full = "\n\n".join(parts)

    # Collapse excessive blank lines
    full = re.sub(r"\n{3,}", "\n\n", full)

    # Abbreviations
    for pattern, replacement in ABBREVIATIONS:
        full = re.sub(pattern, replacement, full)

    # Ordinals
    for abbr, word in ORDINALS.items():
        full = re.sub(rf"\b{re.escape(abbr)}\b", word, full)

    # Symbols
    for pattern, replacement in SYMBOLS:
        full = re.sub(pattern, replacement, full)

    # Normalise punctuation
    for char, replacement in NORMALISE:
        full = full.replace(char, replacement)

    # Handle tables / figures
    if skip_tables:
        full = re.sub(r"(?i)\[Table:[^\]]*\]", "", full)
    if skip_figures:
        full = re.sub(r"(?i)\[Figure:[^\]]*\]", "", full)

    return full.strip()


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_words: int = 500) -> list[str]:
    """Split text into chunks at paragraph boundaries, ≤ max_words words each."""
    paragraphs = re.split(r"\n\n+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > max_words and current:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0
        current.append(para)
        current_words += para_words

    if current:
        chunks.append("\n\n".join(current))

    return chunks


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

def synthesize_chunks(
    chunks: list[str],
    host: str,
    voice: str,
    speed: float,
    output_path: Path,
) -> None:
    url = f"{host.rstrip('/')}/v1/audio/speech"

    # Connectivity check
    try:
        httpx.get(f"{host.rstrip('/')}/v1/audio/voices", timeout=5)
    except httpx.ConnectError:
        print(f"ERROR: Cannot reach Kokoro at {host} — is the Docker container running?")
        sys.exit(1)
    except httpx.TimeoutException:
        print(f"ERROR: Kokoro at {host} timed out — is the Docker container running?")
        sys.exit(1)

    total = len(chunks)
    with output_path.open("wb") as out_file:
        for i, chunk in enumerate(chunks, 1):
            print(f"  Synthesizing chunk {i}/{total}...", end="\r", flush=True)
            payload = {
                "model": "kokoro",
                "input": chunk,
                "voice": voice,
                "response_format": "mp3",
                "speed": speed,
            }
            with httpx.stream("POST", url, json=payload, timeout=120) as response:
                if response.status_code != 200:
                    body = response.read().decode(errors="replace")
                    print(f"\nERROR: Kokoro returned {response.status_code}: {body}")
                    sys.exit(1)
                for data in response.iter_bytes():
                    out_file.write(data)

    print(f"  Synthesized {total}/{total} chunks.          ")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a PDF to an MP3 using Kokoro TTS."
    )
    parser.add_argument("input", type=Path, help="Path to the input PDF")
    parser.add_argument("--output", type=Path, default=None, help="Output MP3 path (default: <input>.mp3)")
    parser.add_argument("--voice", default="af_bella", help="Kokoro voice ID (default: af_bella)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed (default: 1.0)")
    parser.add_argument("--host", default="http://localhost:8880", help="Kokoro API base URL")
    parser.add_argument("--skip-tables", action="store_true", help="Remove table placeholders from output")
    parser.add_argument("--skip-figures", action="store_true", help="Remove figure placeholders from output")
    parser.add_argument("--multi-column", action="store_true", help="Use layout-aware extraction to handle multi-column PDFs")
    parser.add_argument("--txt-only", action="store_true", help="Extract and clean text only, skip TTS")
    args = parser.parse_args()

    pdf_path: Path = args.input.resolve()
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        print(f"ERROR: Input must be a PDF file, got: {pdf_path.suffix}")
        sys.exit(1)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_mp3: Path = args.output or output_dir / pdf_path.with_suffix(".mp3").name
    output_txt: Path = output_dir / pdf_path.with_suffix(".txt").name

    # --- Extract ---
    print(f"Extracting text from {pdf_path.name}...")
    pages, page_count = extract_text(pdf_path, multi_column=args.multi_column)
    print(f"  {page_count} pages found.")

    if all(p.strip() == "" for p in pages):
        print("ERROR: No text extracted. The PDF may be scanned (image-only).")
        print("Tip: run `ocrmypdf <input.pdf> <output.pdf>` first to add a text layer.")
        sys.exit(1)

    # --- Clean ---
    print("Cleaning text...")
    text = clean_text(pages, args.skip_tables, args.skip_figures)

    char_count = len(text)
    word_count = len(text.split())
    reading_minutes = round(word_count / 150)
    print(f"  {char_count:,} characters, ~{word_count:,} words, ~{reading_minutes} min read.")

    output_txt.write_text(text, encoding="utf-8")
    print(f"  Text saved to {output_txt.name}")

    if args.txt_only:
        print("Done (--txt-only, skipping TTS).")
        return

    # --- Synthesize ---
    chunks = chunk_text(text, max_words=500)
    print(f"Synthesizing {len(chunks)} chunks via Kokoro ({args.voice}, speed {args.speed})...")
    synthesize_chunks(chunks, args.host, args.voice, args.speed, output_mp3)

    size_mb = output_mp3.stat().st_size / (1024 * 1024)
    print(f"Done. MP3 saved to {output_mp3.name} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
