import csv
import os
import re

# ──────────────────────────────────────────────────────────────────────────────
# Maps degree abbreviation → full degree name
# ──────────────────────────────────────────────────────────────────────────────
DEGREE_EXPAND = {
    'MSECE': 'Master of Science in Electrical and Computer Engineering',
    'MSPH':  'Master of Science in Public Health',
    'MSBA':  'Master of Science in Business Analytics',
    'MSBE':  'Master of Science in Biomedical Engineering',
    'MSAE':  'Master of Science in Architectural Engineering',
    'MSAT':  'Master of Science in Athletic Training',
    'MSEd':  'Master of Science in Education',
    'MSN':   'Master of Science in Nursing',
    'MSA':   'Master of Science in Accountancy',
    'MPS':   'Master of Professional Studies',
    'MPP':   'Master of Public Policy',
    'MPA':   'Master of Public Administration',
    'MPH':   'Master of Public Health',
    'MBA':   'Master of Business Administration',
    'DBA':   'Doctor of Business Administration',
    'DPT':   'Doctor of Physical Therapy',
    'EdD':   'Doctor of Education',
    'PhD':   'Doctor of Philosophy',
    'MS':    'Master of Science',
    'MA':    'Master of Arts',
    'JD':    'Juris Doctor',
}

# Prefixes that indicate the program name is already well-formed — leave as-is
ALREADY_CORRECT_PREFIXES = (
    'Master of',
    'Doctor of',
    'Juris',
    'Bachelor of',
    'Minor in',
    'Associate of',
    'Executive Master',
    'Certificate of',
)

# ──────────────────────────────────────────────────────────────────────────────
# Direct overrides for tricky names
# ──────────────────────────────────────────────────────────────────────────────
DIRECT_MAP = {
    # PhD concentrations
    'Business PhD, Accounting':
        'Doctor of Philosophy in Business - Accounting',
    'Business PhD, Finance':
        'Doctor of Philosophy in Business - Finance',
    'Business PhD, Management':
        'Doctor of Philosophy in Business - Management',
    'Business PhD, Management Science':
        'Doctor of Philosophy in Business - Management Science',

    # PIBS is not a degree
    'Biomedical Sciences MS, PIBS (umbrella pathway program)':
        'Master of Science in Biomedical Sciences (PIBS umbrella pathway program)',

    # Product Design specialisations
    'Product Design MS, Cosmetics and Consumer Goods':
        'Master of Science in Product Design - Cosmetics and Consumer Goods',
    'Product Design MS, Pharmaceutical and Biopharmaceutical':
        'Master of Science in Product Design - Pharmaceutical and Biopharmaceutical',
    'Product Design MS, Nanotechnology':
        'Master of Science in Product Design - Nanotechnology',

    # Public Admin / Public Health multi-option
    'Public Administration Cert, MPA, MPA Online':
        'Master of Public Administration',
    'Public Health Cert, MPH, MPH Online, Accelerated MPH, MSPH, Accelerated MSPH':
        'Master of Public Health',

    # MSN nurse practitioner programmes
    'Adult-Gerontology Acute Care Nurse Practitioner Cert, MSN':
        'Master of Science in Nursing in Adult-Gerontology Acute Care Nurse Practitioner',
    'Adult-Gerontology Primary Care Nurse Practitioner Cert, MSN':
        'Master of Science in Nursing in Adult-Gerontology Primary Care Nurse Practitioner',

    # DBA
    'Business Executive DBA':
        'Doctor of Business Administration (Executive)',

    # DPT — "Doctor of Physical Therapy" already encodes the subject
    'Physical Therapy DPT, PhD':
        'Doctor of Physical Therapy',

    # MPP, MPA, MPH — full degree name already encodes the subject
    'Public Policy MPP':
        'Master of Public Policy',
}

# Build sorted list of abbreviations (longest first) for regex matching
ABBREV_LIST = sorted(DEGREE_EXPAND.keys(), key=len, reverse=True)
DEGREE_PAT = '|'.join(re.escape(a) for a in ABBREV_LIST)


def split_trailing_degrees(name):
    """
    Detect pattern: <subject> <DEGREE>[, DEGREE2, ...][<suffix>]

    Returns (subject, first_degree_abbrev, suffix) or (None, None, None).
    """
    m = re.match(
        r'^(.+?)\s+(' + DEGREE_PAT + r')'       # subject + first degree abbrev
        r'((?:,\s*(?:' + DEGREE_PAT + r'))*)'   # optional ", DEG2, DEG3 …" (discarded)
        r'(.*?)$',                               # optional trailing text
        name
    )
    if not m:
        return None, None, None

    subject = m.group(1).strip()
    first_degree = m.group(2)
    suffix = m.group(4).strip()
    return subject, first_degree, suffix


def clean_georgetown_program_name(name):
    """
    Convert Georgetown program names so abbreviations expand to full degree names
    and move to the front.

    Examples:
      "Accountancy MSA"                    -> "Master of Science in Accountancy"
      "Atmospheric Sciences MS, MPS, PhD"  -> "Master of Science in Atmospheric Sciences"
      "Philosophy MA, PhD"                 -> "Master of Arts in Philosophy"
      "MSBE with emphasis in …"            -> left as-is (already starts with known prefix triggers
                                              are handled by DIRECTLY checking the abbrev at start)
    """
    if not isinstance(name, str) or not name.strip():
        return name

    name = name.strip()

    # ── 1. Already well-formed? ──────────────────────────────────────────────
    for prefix in ALREADY_CORRECT_PREFIXES:
        if name.startswith(prefix):
            return name

    # ── 2. Direct override? ─────────────────────────────────────────────────
    if name in DIRECT_MAP:
        return DIRECT_MAP[name]

    # ── 3. Generic trailing-degree detection ─────────────────────────────────
    subject, first_abbrev, suffix = split_trailing_degrees(name)
    if first_abbrev is None:
        return name

    full_degree = DEGREE_EXPAND[first_abbrev]

    # For degree abbreviations whose full name already encodes the subject
    # (e.g. MSAE = "Master of Science in Architectural Engineering"), we need to
    # decide whether to append "in <subject>" or not.
    # The rule: if the subject is already embedded in the full degree name, omit it.
    subject_lower = subject.lower()
    full_lower    = full_degree.lower()

    # Remove the generic "Master/Doctor of … in " prefix to get the embedded subject
    # e.g. "master of science in architectural engineering" → "architectural engineering"
    embedded_match = re.match(r'(?:master|doctor) of .+ in (.+)', full_lower)
    embedded = embedded_match.group(1) if embedded_match else None

    if embedded and subject_lower == embedded:
        # Subject already baked in — e.g. MSAE in Architectural Engineering → don't duplicate
        result = full_degree
    else:
        result = f"{full_degree} in {subject}"

    if suffix:
        result += f" {suffix}"

    return result


def run_cleanup():
    base_dir    = os.path.dirname(os.path.abspath(__file__))
    input_file  = os.path.join(base_dir, 'Georgetown_University_Final.csv')
    output_file = os.path.join(base_dir, 'Georgetown_University_Cleaned.csv')

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    changed = 0
    unchanged = []
    for row in rows:
        original = row['ProgramName']
        cleaned  = clean_georgetown_program_name(original)
        if cleaned != original:
            print(f"  CHANGED: {repr(original)}")
            print(f"       TO: {repr(cleaned)}")
            changed += 1
        else:
            unchanged.append(original)
        row['ProgramName'] = cleaned

    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCleanup complete. {changed} program name(s) updated.")
    if unchanged:
        print(f"\nUnchanged names (first 20):")
        for n in unchanged[:20]:
            print(f"  {repr(n)}")
    print(f"\nSaved to {output_file}")


if __name__ == '__main__':
    run_cleanup()
