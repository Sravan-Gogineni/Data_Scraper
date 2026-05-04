"""
Fetches QS World University Rankings by Subject AND US News Best Global
Universities by Subject for all programs in a given input CSV using Gemini
with Google Search grounding.

Usage:
    python fetch_qs_from_web.py --input program_qs_rankings_part1.csv

    All checkpoint and output files are scoped to the input filename so multiple
    machines can run different parts in parallel without interfering.

Inputs:
    <input_csv>                        CSV produced by db.py

Outputs (all written inside this folder, prefixed by input stem):
    <stem>_qs_subject_map.json         program → QS subject
    <stem>_usnews_subject_map.json     program → US News subject
    <stem>_qs_rankings.json            (college, QS-subject) → ranking
    <stem>_usnews_rankings.json        (college, USNews-subject) → ranking
    <stem>_batches/batch_001.csv …     one CSV per batch
    <stem>_filled.csv                  merged final output

Resumable: re-running the script skips completed batch files and reloads all
checkpoint JSONs, so it continues exactly where it left off.
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

load_dotenv(ROOT / ".env")
MODEL      = os.getenv("MODEL", "gemini-2.5-pro")
DELAY      = 1.5   # seconds between API calls
BATCH_SIZE = 200   # rows per output CSV batch
CLASS_SIZE = 80    # program names per classification call


@dataclass
class Paths:
    input_csv:          Path
    output_csv:         Path
    batches_dir:        Path
    qs_subject_map:     Path
    usnews_subject_map: Path
    qs_rankings:        Path
    usnews_rankings:    Path

    @classmethod
    def from_input(cls, input_csv: Path) -> "Paths":
        stem = input_csv.stem
        return cls(
            input_csv          = input_csv,
            output_csv         = HERE / f"{stem}_filled.csv",
            batches_dir        = HERE / f"{stem}_batches",
            qs_subject_map     = HERE / f"{stem}_qs_subject_map.json",
            usnews_subject_map = HERE / f"{stem}_usnews_subject_map.json",
            qs_rankings        = HERE / f"{stem}_qs_rankings.json",
            usnews_rankings    = HERE / f"{stem}_usnews_rankings.json",
        )


# ── Gemini client ────────────────────────────────────────────────────────────────

def make_client() -> genai.Client:
    # Prefer Vertex AI when GCP_PROJECT is configured (uses ADC or GOOGLE_APPLICATION_CREDENTIALS)
    if os.getenv("GCP_PROJECT"):
        region = os.getenv("GCP_REGION", "us-central1")
        logger.info("Using Vertex AI: project=%s region=%s", os.getenv("GCP_PROJECT"), region)
        return genai.Client(
            vertexai=True,
            project=os.getenv("GCP_PROJECT"),
            location=region,
        )

    # Fallback to API key auth
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)

    raise ValueError(
        "No valid Google credentials found. Please set one of:\n"
        "  1. GCP_PROJECT (+ optional GCP_REGION) — uses Application Default Credentials\n"
        "  2. GOOGLE_API_KEY environment variable\n"
        "Create a .env file in the repo root with your credentials."
    )


class GeminiModelWrapper:
    def __init__(self, client: genai.Client, model_name: str, use_search: bool = True):
        self.client = client
        self.model_name = model_name
        self.use_search = use_search

    def generate_content(self, prompt: str, max_retries: int = 5, base_delay: float = 2) -> str:
        config_kwargs: dict = {"temperature": 0}
        if self.use_search:
            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
                return response.text or ""
            except Exception as e:
                err = str(e)
                if "generate_content_free_tier_" in err and "limit: 0" in err:
                    logger.error(
                        "Quota exhausted for free tier on Gemini model %s. "
                        "Enable billing or use a paid quota credential (Vertex AI or paid API key).",
                        self.model_name,
                    )
                    return ""
                if any(code in err for code in ("503", "429", "Too Many Requests", "Overloaded")):
                    if attempt < max_retries - 1:
                        wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait:.1f}s…")
                        time.sleep(wait)
                        continue
                logger.error(f"Failed after {attempt + 1} attempts: {e}")
                return ""
        return ""


# ── subject taxonomies ───────────────────────────────────────────────────────────

QS_SUBJECTS = [
    "Accounting & Finance", "Agriculture & Forestry", "Anatomy & Physiology",
    "Archaeology", "Architecture & Built Environment", "Art & Design",
    "Biological Sciences", "Business & Management Studies", "Chemical Engineering",
    "Chemistry", "Civil & Structural Engineering", "Communication & Media Studies",
    "Computer Science & Information Systems", "Data Science & Artificial Intelligence",
    "Dentistry", "Development Studies", "Earth & Marine Sciences",
    "Economics & Econometrics", "Education & Training",
    "Electrical & Electronic Engineering", "English Language & Literature",
    "Environmental Studies", "Geography", "History",
    "Hospitality & Leisure Management", "Law", "Library & Information Management",
    "Linguistics", "Materials Science", "Mathematics", "Mechanical Engineering",
    "Medicine", "Mineral & Mining Engineering", "Modern Languages", "Nursing",
    "Performing Arts", "Petroleum Engineering", "Philosophy", "Physics & Astronomy",
    "Politics & International Studies", "Psychology",
    "Social Policy & Administration", "Sociology", "Sports-related Subjects",
    "Statistics & Operational Research", "Theology & Religious Studies",
    "Veterinary Science", "Not Applicable",
]

USNEWS_SUBJECTS = [
    "Arts and Humanities", "Biology and Biochemistry", "Chemistry",
    "Clinical Medicine", "Computer Science", "Economics and Business",
    "Engineering", "Environment and Ecology", "Geosciences", "Immunology",
    "Materials Science", "Mathematics", "Microbiology",
    "Molecular Biology and Genetics", "Neuroscience and Behavior", "Oncology",
    "Pharmacology and Toxicology", "Physics", "Plant and Animal Science",
    "Psychiatry and Psychology", "Public Health and Health Sciences",
    "Social Sciences and Public Health", "Space Science", "Surgery",
    "Not Applicable",
]

QS_SUBJECTS_STR     = "\n".join(f"- {s}" for s in QS_SUBJECTS)
USNEWS_SUBJECTS_STR = "\n".join(f"- {s}" for s in USNEWS_SUBJECTS)


# ── helpers ──────────────────────────────────────────────────────────────────────

def extract_ranking(text: str) -> str:
    text = text.strip()
    m = re.search(r"#?(\d+)\s*[-–]\s*(\d+)", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"#?(\d+)\+", text)
    if m:
        return f"{m.group(1)}+"
    m = re.search(r"#?(\d{1,4})", text)
    if m:
        return m.group(1)
    return "Not Ranked"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _classify_batch(
    classifier: GeminiModelWrapper, programs: list[str], subjects_str: str, label: str
) -> dict[str, str]:
    numbered = "\n".join(f"{i+1}. {p}" for i, p in enumerate(programs))
    prompt = f"""Classify each academic program below into the best-matching {label} subject area.

Available subject categories:
{subjects_str}

Rules:
- Use "Not Applicable" for certificates, associate/foundation degrees, minors, or anything outside scope.
- Return a JSON object: keys = program names (exactly as given), values = subject category.
- Return ONLY the JSON. No explanation.

Programs:
{numbered}
"""
    text = classifier.generate_content(prompt)
    try:
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except Exception as e:
        tqdm.write(f"  Classification error ({label}): {e}")
        return {}


def _classify_chunk(
    classifier: GeminiModelWrapper,
    programs: list[str],
    mapping: dict[str, str],
    checkpoint: Path,
    classify_fn,
    label: str,
) -> None:
    pending = [p for p in programs if p not in mapping]
    if not pending:
        return
    for sub in tqdm([pending[i:i+CLASS_SIZE] for i in range(0, len(pending), CLASS_SIZE)],
                    desc=f"    Classifying ({label})", leave=False):
        result = classify_fn(classifier, sub)
        for p in sub:
            mapping[p] = result.get(p, "Not Applicable")
        checkpoint.write_text(json.dumps(mapping, indent=2))
        time.sleep(DELAY)


def _fetch_missing_rankings(
    searcher: GeminiModelWrapper,
    chunk: list[dict],
    program_subject: dict[str, str],
    college_rankings: dict[str, str],
    checkpoint: Path,
    fetch_fn,
    label: str,
) -> None:
    needed = {
        (r["CollegeName"], program_subject.get(r["ProgramName"], "Not Applicable"))
        for r in chunk
        if program_subject.get(r["ProgramName"], "Not Applicable") != "Not Applicable"
    }
    missing = [(col, sub) for col, sub in sorted(needed) if f"{col}||{sub}" not in college_rankings]
    if not missing:
        return
    print(f"    [{label}] Fetching {len(missing)} new (college, subject) rankings...")
    for college, subject in tqdm(missing, desc=f"    {label}", leave=False):
        key = f"{college}||{subject}"
        college_rankings[key] = fetch_fn(searcher, college, subject)
        tqdm.write(f"    {college!r:50s} | {subject!r:40s} => {college_rankings[key]}")
        checkpoint.write_text(json.dumps(college_rankings, indent=2))
        time.sleep(DELAY)


# ── ranking fetch prompts ────────────────────────────────────────────────────────

def fetch_qs_ranking(searcher: GeminiModelWrapper, college: str, subject: str) -> str:
    prompt = (
        f"What is the QS World University Rankings by Subject 2026 ranking for "
        f"'{college}' in '{subject}'? "
        "Search the web and return ONLY the ranking value (e.g. '47', '101-150', '451-500+') "
        "or 'Not Ranked' if not ranked. No explanation — just the value."
    )
    text = searcher.generate_content(prompt)
    return extract_ranking(text) if text else ""


def fetch_usnews_ranking(searcher: GeminiModelWrapper, college: str, subject: str) -> str:
    prompt = (
        f"What is the US News Best Global Universities by Subject 2025 ranking for "
        f"'{college}' in '{subject}'? "
        "Search the web and return ONLY the ranking value (e.g. '47', '101-150', '451-500+') "
        "or 'Not Ranked' if not ranked. No explanation — just the value."
    )
    text = searcher.generate_content(prompt)
    return extract_ranking(text) if text else ""


# ── phases ───────────────────────────────────────────────────────────────────────

def process_batches(
    classifier: GeminiModelWrapper,
    searcher: GeminiModelWrapper,
    rows: list[dict],
    fieldnames: list[str],
    paths: Paths,
) -> None:
    qs_subject     = _load_json(paths.qs_subject_map)
    usnews_subject = _load_json(paths.usnews_subject_map)
    qs_rankings    = _load_json(paths.qs_rankings)
    usnews_rankings= _load_json(paths.usnews_rankings)

    for col in ("QsSubject", "QsWorldRanking", "UsNewsSubject", "UsNewsRanking"):
        if col not in fieldnames:
            fieldnames.append(col)

    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Processing {len(rows):,} rows in {total_batches} batches of {BATCH_SIZE}...\n")

    for batch_idx in range(total_batches):
        batch_num  = batch_idx + 1
        batch_file = paths.batches_dir / f"batch_{batch_num:03d}.csv"

        if batch_file.exists():
            print(f"  Batch {batch_num:03d}/{total_batches}: already exists, skipping.")
            continue

        chunk          = rows[batch_idx * BATCH_SIZE : (batch_idx + 1) * BATCH_SIZE]
        chunk_programs = sorted({r["ProgramName"] for r in chunk})

        print(f"  Batch {batch_num:03d}/{total_batches}: "
              f"{len(chunk)} rows | {len(chunk_programs)} unique programs")

        _classify_chunk(classifier, chunk_programs, qs_subject,
                        paths.qs_subject_map, lambda c, p: _classify_batch(c, p, QS_SUBJECTS_STR, "QS World University Rankings"), "QS")
        _classify_chunk(classifier, chunk_programs, usnews_subject,
                        paths.usnews_subject_map, lambda c, p: _classify_batch(c, p, USNEWS_SUBJECTS_STR, "US News Best Global Universities"), "US News")

        _fetch_missing_rankings(searcher, chunk, qs_subject, qs_rankings,
                                paths.qs_rankings, fetch_qs_ranking, "QS")
        _fetch_missing_rankings(searcher, chunk, usnews_subject, usnews_rankings,
                                paths.usnews_rankings, fetch_usnews_ranking, "US News")

        with open(batch_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in chunk:
                qs_sub = qs_subject.get(row["ProgramName"], "Not Applicable")
                row["QsSubject"]      = qs_sub
                row["QsWorldRanking"] = (
                    "Not Applicable" if qs_sub == "Not Applicable"
                    else qs_rankings.get(f"{row['CollegeName']}||{qs_sub}", "")
                )
                un_sub = usnews_subject.get(row["ProgramName"], "Not Applicable")
                row["UsNewsSubject"]  = un_sub
                row["UsNewsRanking"]  = (
                    "Not Applicable" if un_sub == "Not Applicable"
                    else usnews_rankings.get(f"{row['CollegeName']}||{un_sub}", "")
                )
                writer.writerow(row)

        print(f"  Batch {batch_num:03d}/{total_batches}: saved → {batch_file.name}")

    print("\nAll batches complete.\n")


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

    all_rows = list(csv.DictReader(open(paths.output_csv, newline="", encoding="utf-8")))

    def _count(rows, col):
        ranked = not_ranked = na = errors = 0
        for row in rows:
            v = row.get(col, "")
            if v not in ("", "Not Ranked", "Not Applicable"):
                ranked += 1
            elif v == "Not Ranked":
                not_ranked += 1
            elif v == "Not Applicable":
                na += 1
            else:
                errors += 1
        return ranked, not_ranked, na, errors

    for label, col in [("QS World", "QsWorldRanking"), ("US News", "UsNewsRanking")]:
        r, nr, na, err = _count(all_rows, col)
        print(f"\n  [{label}]")
        print(f"    Ranked         : {r:,}")
        print(f"    Not Ranked     : {nr:,}")
        print(f"    Not Applicable : {na:,}")
        print(f"    Missing/Error  : {err:,}")

    print(f"\nFinal output : {paths.output_csv}")


# ── entry point ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch QS and US News rankings for programs.")
    parser.add_argument(
        "--input", required=True,
        help="Input CSV file (e.g. program_qs_rankings_part1.csv). "
             "Can be a filename relative to the repo root or an absolute path."
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    paths = Paths.from_input(input_path)
    paths.batches_dir.mkdir(exist_ok=True)

    print(f"Input  : {paths.input_csv}")
    print(f"Output : {paths.output_csv}")
    print(f"Batches: {paths.batches_dir}\n")

    client     = make_client()
    classifier = GeminiModelWrapper(client, MODEL, use_search=False)
    searcher   = GeminiModelWrapper(client, MODEL, use_search=True)

    rows: list[dict] = []
    fieldnames: list[str] = []
    with open(paths.input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    print(f"Loaded {len(rows):,} rows, {len(fieldnames)} columns.\n")

    process_batches(classifier, searcher, rows, fieldnames, paths)
    phase3_merge(fieldnames, paths)


if __name__ == "__main__":
    main()
