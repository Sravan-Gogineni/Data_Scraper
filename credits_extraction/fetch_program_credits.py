"""Extract program credit requirements from the web for each academic program.

Usage:
    python fetch_program_credits.py --input program_qs_rankings_part1.csv

Inputs:
    <input_csv>                        CSV produced by Program_Rankings_extraction/db.py

Outputs (all written inside this folder, prefixed by input stem):
    <stem>_credits.json              cached program credit values
    <stem>_batches/batch_001.csv ... per-batch filled CSVs
    <stem>_filled.csv                merged final output with Credits added

This script is resumable: existing batch files and cache JSONs are reused when rerunning.
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from Program_Rankings_extraction.fetch_qs_from_web import make_client, GeminiModelWrapper

load_dotenv(ROOT / ".env")
MODEL      = os.getenv("MODEL", "gemini-2.5-pro")
DELAY      = 0.2
BATCH_SIZE = 1000


@dataclass
class Paths:
    input_csv:    Path
    output_csv:   Path
    batches_dir:  Path
    credits_json: Path

    @classmethod
    def from_input(cls, input_csv: Path) -> "Paths":
        stem = input_csv.stem
        return cls(
            input_csv    = input_csv,
            output_csv   = HERE / f"{stem}_filled.csv",
            batches_dir  = HERE / f"{stem}_batches",
            credits_json = HERE / f"{stem}_credits.json",
        )


def extract_credit_value(text: str) -> str:
    text = text.strip()
    if not text:
        return "Not Available"

    normalized = text.lower().strip()
    if any(token in normalized for token in ("not available", "not applicable", "unknown", "n/a", "none", "no credit")):
        return "Not Available"

    # Normalize comma separators and remove markdown blocks.
    normalized = re.sub(r"[\n\r]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    # Common credit hour patterns.
    patterns = [
        r"(\d{1,3})\s*(?:credit hours|credit hrs|credit hr|credits|credit)\b",
        r"(\d{1,3})\s*-\s*(\d{1,3})\s*(?:credit hours|credit hrs|credit hr|credits|credit)\b",
        r"(\d{1,3})\s*to\s*(\d{1,3})\s*(?:credit hours|credits|credit)\b",
        r"(?:total )?(\d{1,3})\s*cr\b",
    ]

    for pat in patterns:
        m = re.search(pat, normalized)
        if m:
            if len(m.groups()) == 2 and m.group(2):
                return f"{m.group(1)}-{m.group(2)} credits"
            return f"{m.group(1)} credits"

    # Accept a numeric value if it appears without an explicit unit but likely represents credits.
    m = re.search(r"\b(\d{1,3})\b", normalized)
    if m:
        return f"{m.group(1)} credits"

    return "Not Available"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _unique_program_key(row: dict[str, str]) -> str:
    program_id = row.get("ProgramId", "").strip()
    level = row.get("Level", "").strip()
    return f"{program_id}||{row.get('CollegeName', '').strip()}||{row.get('ProgramName', '').strip()}||{level}"


def _fetch_missing_credits(
    searcher: GeminiModelWrapper,
    rows: list[dict],
    credits_cache: dict[str, str],
    checkpoint: Path,
) -> None:
    missing_rows: list[tuple[str, str, str, str]] = []
    for row in rows:
        key = _unique_program_key(row)
        if key not in credits_cache:
            missing_rows.append((key, row.get('CollegeName', '').strip(), row.get('ProgramName', '').strip(), row.get('Level', '').strip()))

    if not missing_rows:
        return

    missing_rows = sorted({r for r in missing_rows}, key=lambda x: (x[1].lower(), x[2].lower(), x[3].lower()))
    print(f"    Fetching credits for {len(missing_rows)} unique program rows...")

    for key, college, program, level in tqdm(missing_rows, desc="    Credits", leave=False):
        prompt = (
            f"Search the web for the total credit requirement for the {level or 'program'} '{program}' at '{college}'. "
            "Return ONLY the credit requirement in a normalized form such as '120 credits', '36 credits', '30-36 credits', "
            "or 'Not Available' if no reliable total credit requirement is published. No explanation, no extra text. "
            "Look at official university pages, program curriculum pages. Do not guess or infer if the information is not explicitly stated. "
            "If you find multiple values, try to determine the most recent or official one. If you cannot find a clear answer, return 'Not Available'. "
            "Strictly do not hallucinate or fabricate credit values. If the search results do not contain a clear credit requirement, return 'Not Available'. "
            "The reliability of the information is more important than completeness. It's better to return 'Not Available' than to return an incorrect credit requirement."
        )
        raw = searcher.generate_content(prompt)
        credits_cache[key] = extract_credit_value(raw)
        tqdm.write(f"    {college!r:40s} | {program!r:60s} | {level!r:15s} => {credits_cache[key]}")
        checkpoint.write_text(json.dumps(credits_cache, indent=2))
        time.sleep(DELAY)


def process_batches(rows: list[dict], fieldnames: list[str], paths: Paths, searcher: GeminiModelWrapper) -> None:
    credits_cache = _load_json(paths.credits_json)
    if "Credits" not in fieldnames:
        fieldnames.append("Credits")

    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Processing {len(rows):,} rows in {total_batches} batches of {BATCH_SIZE}...\n")

    _fetch_missing_credits(searcher, rows, credits_cache, paths.credits_json)

    for batch_idx in range(total_batches):
        batch_num = batch_idx + 1
        batch_file = paths.batches_dir / f"batch_{batch_num:03d}.csv"

        if batch_file.exists():
            print(f"  Batch {batch_num:03d}/{total_batches}: already exists, skipping.")
            continue

        chunk = rows[batch_idx * BATCH_SIZE : (batch_idx + 1) * BATCH_SIZE]
        print(f"  Batch {batch_num:03d}/{total_batches}: {len(chunk)} rows")

        with open(batch_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in chunk:
                key = _unique_program_key(row)
                row["Credits"] = credits_cache.get(key, "Not Available")
                writer.writerow(row)

        print(f"  Batch {batch_num:03d}/{total_batches}: saved → {batch_file.name}")

    print()


def phase3_merge(fieldnames: list[str], paths: Paths) -> None:
    batch_files = sorted(paths.batches_dir.glob("batch_*.csv"))
    if not batch_files:
        print("Phase 3: no batch files found, nothing to merge.")
        return

    print(f"Phase 3: merging {len(batch_files)} batch files → {paths.output_csv.name} ...")
    with open(paths.output_csv, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for bf in batch_files:
            with open(bf, newline="", encoding="utf-8") as inp:
                for row in csv.DictReader(inp):
                    writer.writerow(row)

    total = sum(1 for _ in csv.DictReader(open(paths.output_csv, newline="", encoding="utf-8")))
    print(f"Final output : {paths.output_csv} ({total:,} rows)")


def main():
    parser = argparse.ArgumentParser(description="Fetch program credit requirements for programs.")
    parser.add_argument(
        "--input", required=True,
        help="Input CSV file (e.g. program_qs_rankings_part1.csv). Can be a filename relative to the repo root or an absolute path."
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    paths = Paths.from_input(input_path)
    paths.batches_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input  : {paths.input_csv}")
    print(f"Output : {paths.output_csv}")
    print(f"Batches: {paths.batches_dir}\n")

    client = make_client()
    searcher = GeminiModelWrapper(client, MODEL, use_search=True)

    with open(paths.input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    print(f"Loaded {len(rows):,} rows, {len(fieldnames)} columns.\n")
    process_batches(rows, fieldnames, paths, searcher)
    phase3_merge(fieldnames, paths)


if __name__ == "__main__":
    main()
