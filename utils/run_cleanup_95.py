import pandas as pd
import re
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_cleanup_logic import clean_program_name, fix_typos

# Degree map for the trailing abbreviations used in college 95
DEGREE_MAP_95 = {
    'B.S.': 'Bachelor of Science',
    'B.A.': 'Bachelor of Arts',
    'B.F.A.': 'Bachelor of Fine Arts',
    'B.B.A.': 'Bachelor of Business Administration',
    'B.M.':  'Bachelor of Music',
    'B.S.N.': 'Bachelor of Science in Nursing',
    'B.S.W.': 'Bachelor of Social Work',
    'M.S.':  'Master of Science',
    'M.S': 'Master of Science',
    # dual options – pick B.S. as instructed
    'B.S./B.A.': 'Bachelor of Science',
}


def clean_95(name):
    """Clean a single program name for college 95."""
    if not isinstance(name, str):
        return name

    name = fix_typos(name.strip())

    # ── Already fully spelled out — just clean up redundant subject repetition ──
    # e.g. "Bachelor of Music in Music – Commercial Songwriting"
    #   → "Bachelor of Music in Commercial Songwriting"
    bom_match = re.match(r'^(Bachelor of Music) in Music\s*[–-]\s*(.+)$', name)
    if bom_match:
        return f"{bom_match.group(1)} in {bom_match.group(2)}"

    # e.g. "Bachelor of Music in Music – Music Industry" where concentration starts with "Music"
    # Already handled above, but also strip plain "Bachelor of Music in Music" (no concentration)
    if name == 'Bachelor of Music in Music':
        return 'Bachelor of Music'

    # ── Special case: "Aerospace B.S. (note...)" ────────────────────────────
    # e.g. "Aerospace B.S. (Aerospace Technology, Flight Dispatch and Maintenance Management only)"
    aero_match = re.match(r'^Aerospace B\.S\.\s*\((.+)\)$', name)
    if aero_match:
        note = aero_match.group(1)
        return f"Bachelor of Science in Aerospace ({note})"

    # ── Already fully spelled out (Bachelor/Master/Doctor of ...) - pass through ──
    if re.match(r'^(Bachelor|Master|Doctor)\s+of\b', name):
        return name

    # ── Pattern: "Subject[, Concentration], DEGREE" ──────────────────────────
    parts = [p.strip() for p in name.split(',')]

    if len(parts) >= 2:
        last = parts[-1]
        full_degree = DEGREE_MAP_95.get(last)

        if full_degree:
            rest = parts[:-1]
            subject = rest[0]
            concentration = rest[1] if len(rest) > 1 else None

            if concentration:
                concentration = re.sub(r'\s+Concentration$', '', concentration, flags=re.I).strip()
                return f"{full_degree} in {subject} – {concentration}"
            else:
                if subject.lower() in full_degree.lower():
                    return full_degree
                return f"{full_degree} in {subject}"

        if 'certificate' in last.lower():
            subject = ', '.join(parts[:-1])
            return f"{last.strip()} in {subject}"

    # Fallback to the shared cleaner
    return clean_program_name(name)


# ── Run ───────────────────────────────────────────────────────────────────────
df = pd.read_csv("programs_collegeid_95.csv")
print(f"Total programs: {len(df)}\n")

df["CleanedProgramName"] = df["ProgramName"].apply(clean_95)

changed = df[df["ProgramName"] != df["CleanedProgramName"]]
print(f"=== {len(changed)} names updated ===")
for _, row in changed.iterrows():
    print(f"  BEFORE: {row['ProgramName']}")
    print(f"   AFTER: {row['CleanedProgramName']}\n")

output_path = "programs_collegeid_95_cleaned.csv"
df.to_csv(output_path, index=False)
print(f"Saved to: {output_path}")
