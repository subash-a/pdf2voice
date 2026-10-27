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

def _words_to_text(words: list[dict], page_width: float, multi_column: bool) -> str:
    """Reconstruct reading-order text from a list of pdfplumber word dicts."""
    if not words:
        return ""

    # Detect column separator: find the largest horizontal gap in word midpoints
    # within the central 20-80% of the page width.
    col_split: float | None = None
    if multi_column:
        midpoints = sorted((w["x0"] + w["x1"]) / 2 for w in words)
        lo, hi = page_width * 0.20, page_width * 0.80
        central = [x for x in midpoints if lo <= x <= hi]
        if len(central) >= 4:
            gaps = [(central[i + 1] - central[i], (central[i] + central[i + 1]) / 2)
                    for i in range(len(central) - 1)]
            largest_gap, split_x = max(gaps)
            # Only treat as multi-column if the gap is meaningfully wide (>5% of page)
            if largest_gap > page_width * 0.05:
                col_split = split_x

    def word_column(w: dict) -> int:
        if col_split is None:
            return 0
        return 0 if (w["x0"] + w["x1"]) / 2 < col_split else 1

    # Group words into lines within each column (words within 3pt vertically = same line)
    from collections import defaultdict
    columns: dict[int, list[dict]] = defaultdict(list)
    for w in words:
        columns[word_column(w)].append(w)

    all_lines: list[tuple[float, int, str]] = []  # (top, col_index, line_text)
    for col_idx in sorted(columns):
        col_words = sorted(columns[col_idx], key=lambda w: (w["top"], w["x0"]))
        if not col_words:
            continue
        line_words: list[dict] = [col_words[0]]
        for w in col_words[1:]:
            if abs(w["top"] - line_words[-1]["top"]) <= 3:
                line_words.append(w)
            else:
                line_text = " ".join(lw["text"] for lw in sorted(line_words, key=lambda lw: lw["x0"]))
                all_lines.append((line_words[0]["top"], col_idx, line_text))
                line_words = [w]
        line_text = " ".join(lw["text"] for lw in sorted(line_words, key=lambda lw: lw["x0"]))
        all_lines.append((line_words[0]["top"], col_idx, line_text))

    # Sort: single-column → by top only; multi-column → left col first, then right col
    if col_split is None:
        all_lines.sort(key=lambda t: t[0])
    else:
        all_lines.sort(key=lambda t: (t[1], t[0]))

    return "\n".join(line for _, _, line in all_lines)


def _detect_header_footer_zones(pdf) -> tuple[float | None, float | None]:
    """Return (header_bottom, footer_top) in points by finding text that repeats
    at consistent y-positions across pages.  None means no zone detected."""
    from collections import defaultdict

    # Map each word text → list of (page_index, top, bottom, relative_top)
    top_zone: dict[str, list[tuple[int, float, float]]] = defaultdict(list)
    bot_zone: dict[str, list[tuple[int, float, float]]] = defaultdict(list)

    n_pages = len(pdf.pages)
    threshold = max(2, n_pages // 3)

    for page_idx, page in enumerate(pdf.pages):
        h = page.height
        for w in (page.extract_words() or []):
            rel = w["top"] / h
            if rel < 0.15:
                top_zone[w["text"]].append((page_idx, w["top"], w["bottom"]))
            elif rel > 0.85:
                bot_zone[w["text"]].append((page_idx, w["top"], w["bottom"]))

    header_bottom: float | None = None
    for text, occurrences in top_zone.items():
        if len({p for p, _, _ in occurrences}) >= threshold:
            bottom = max(b for _, _, b in occurrences)
            header_bottom = max(header_bottom or 0.0, bottom)

    footer_top: float | None = None
    for text, occurrences in bot_zone.items():
        if len({p for p, _, _ in occurrences}) >= threshold:
            top = min(t for _, t, _ in occurrences)
            footer_top = min(footer_top or float("inf"), top)

    return header_bottom, footer_top


def extract_text(pdf_path: Path, multi_column: bool = False) -> tuple[list[str], int]:
    """Return (pages_text, page_count). Uses pdfplumber, falls back to pypdf."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            header_bottom, footer_top = _detect_header_footer_zones(pdf)
            pages = []
            for p in pdf.pages:
                # Crop out header/footer zones before extraction
                y0 = (header_bottom + 2) if header_bottom is not None else 0
                y1 = (footer_top - 2) if footer_top is not None else p.height
                # Guard: never crop more than 20% from either end
                y0 = min(y0, p.height * 0.20)
                y1 = max(y1, p.height * 0.80)
                cropped = p.crop((0, y0, p.width, y1))
                if multi_column:
                    words = cropped.extract_words() or []
                    pages.append(_words_to_text(words, p.width, multi_column=True))
                else:
                    pages.append(cropped.extract_text() or "")
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

def clean_text(pages: list[str], skip_tables: bool, skip_figures: bool) -> str:
    parts = []
    for page_text in pages:
        lines = []
        for line in page_text.splitlines():
            stripped = line.strip()
            # Drop standalone page numbers
            if re.fullmatch(r"\d+", stripped):
                continue
            # Drop bare URLs / DOIs
            if re.match(r"https?://\S+$", stripped) or re.match(r"doi:\S+$", stripped, re.I):
                continue
            lines.append(line)
        text = "\n".join(lines)
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
