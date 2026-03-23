import csv
import os

# Maps degree abbreviations to their full names
degree_map = {
    'M.S.': 'Master of Science',
    'M.A.': 'Master of Arts',
    'M.B.A.': 'Master of Business Administration',
    'M.F.A.': 'Master of Fine Arts',
    'M.Arch.': 'Master of Architecture',
    'M.Mus.': 'Master of Music',
    'M.P.A.': 'Master of Public Administration',
    'M.S.W.': 'Master of Social Work',
    'M.H.A.': 'Master of Health Administration',
    'Ph.D.': 'Doctor of Philosophy',
    'Ed.D.': 'Doctor of Education',
    'J.D.': 'Juris Doctor',
    'LL.M.': 'Master of Laws',
    'C.A.S.': 'Certificate of Advanced Study',
    'Certificate of Advanced Study': 'Certificate of Advanced Study',
    # Dual degree combo
    'M.A./M.S.': 'Master of Arts/Master of Science',
    'M.P.A./M.A. (I.R.)': 'Master of Public Administration/Master of Arts in International Relations',
    # Special suffix on M.A.
    'M.A. (Audio Arts)': 'Master of Arts',
}

# Known degree abbreviations (used to correctly split the subject from the degree)
# These are checked at the END of the name string
KNOWN_ABBREVS = [
    'M.P.A./M.A. (I.R.)',
    'M.A. (Audio Arts)',
    'M.A./M.S.',
    'Certificate of Advanced Study',
    'M.Arch.',
    'M.Mus.',
    'M.B.A.',
    'M.S.W.',
    'M.H.A.',
    'M.F.A.',
    'Ph.D.',
    'Ed.D.',
    'LL.M.',
    'C.A.S.',
    'M.A.',
    'M.S.',
    'J.D.',
]

# Programs that already have correct names (pass-through)
ALREADY_CORRECT_PREFIXES = (
    'Master of', 'Doctor of', 'Juris', 'Bachelor of', 'Minor in',
    'Executive Master', 'Certificate', 'Graduate Certificate',
    'Associate', 'Ph.D.', 'PhD',
)

# Direct overrides for special/tricky cases
DIRECT_MAP = {
    'Public Administration and International Relations, M.P.A./M.A. (I.R.)': 
        'Master of Public Administration/Master of Arts in International Relations in Public Administration and International Relations',
    'Law, LL.M.': 'Juris Doctor (LL.M.) in Law',
    'American Law, LL.M.': 'Master of Laws in American Law',
}


# Degree abbreviations that are already subject-specific
# (their full name implies the subject, so "in Subject" would be redundant)
SELF_CONTAINED_ABBREVS = {
    'M.B.A.',    # Master of Business Administration
    'M.P.A.',    # Master of Public Administration
    'M.Arch.',   # Master of Architecture
    'M.S.W.',    # Master of Social Work
    'M.H.A.',    # Master of Health Administration
    'J.D.',      # Juris Doctor
    'LL.M.',     # Master of Laws (unless there's a subject, handled in DIRECT_MAP)
}

def clean_syracuse_program_name(name):
    """
    Convert program names from 'Subject, Degree' to 'Full Degree Name in Subject'.
    Examples:
      "Accounting, M.S."           -> "Master of Science in Accounting"
      "Anthropology, Ph.D."        -> "Doctor of Philosophy in Anthropology"
      "Philosophy, Ph.D."          -> "Doctor of Philosophy in Philosophy"
      "Architecture, M.Arch."      -> "Master of Architecture"
      "Business Administration, M.B.A." -> "Master of Business Administration"
      "Educational Leadership, C.A.S." -> "Certificate of Advanced Study in Educational Leadership"
    """
    if not isinstance(name, str) or not name.strip():
        return name

    name = name.strip()

    # If name already starts with a well-formed degree, return as-is
    for prefix in ALREADY_CORRECT_PREFIXES:
        if name.startswith(prefix):
            return name

    # Check direct overrides first
    if name in DIRECT_MAP:
        return DIRECT_MAP[name]

    # Find the degree abbreviation by checking known abbrevs at the end of the name
    degree_abbrev = None
    subject = None
    for abbrev in KNOWN_ABBREVS:
        suffix = ', ' + abbrev
        if name.endswith(suffix):
            degree_abbrev = abbrev
            subject = name[:-len(suffix)].strip()
            break

    if degree_abbrev is None:
        # No known abbrev found - return original
        return name

    full_degree = degree_map.get(degree_abbrev)
    if not full_degree:
        return name

    # Special audio arts case
    if degree_abbrev == 'M.A. (Audio Arts)':
        return f"Master of Arts in {subject} (Audio Arts)"

    # For dual degree abbreviations like "M.A./M.S." or "M.P.A./M.A. (I.R.)"
    if '/' in degree_abbrev:
        return f"{full_degree} in {subject}"

    # For self-contained degrees (where the abbreviation already names the specific field),
    # only return the full degree name if the subject matches the degree's implied field.
    # e.g., "Business Administration, M.B.A." -> "Master of Business Administration"
    # But "Health Administration, M.H.A." -> "Master of Health Administration in Health Administration" is redundant too,
    # so we just return full_degree for all self-contained abbrevs.
    if degree_abbrev in SELF_CONTAINED_ABBREVS:
        # If subject is literally redundant (already in full_degree), skip "in Subject"
        # e.g. "Business Administration" in "Master of Business Administration"
        # But if subject adds info (e.g., "Health Services Management and Policy, M.H.A."), keep it
        if subject.lower() in full_degree.lower():
            return full_degree
        else:
            return f"{full_degree} in {subject}"

    return f"{full_degree} in {subject}"


def run_cleanup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, 'Syracuse_University_Final.csv')
    output_file = os.path.join(base_dir, 'Syracuse_University_Cleaned.csv')

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    changed = 0
    for row in rows:
        original = row['ProgramName']
        cleaned = clean_syracuse_program_name(original)
        if cleaned != original:
            print(f"  CHANGED: {repr(original)}")
            print(f"       TO: {repr(cleaned)}")
            changed += 1
        row['ProgramName'] = cleaned

    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nCleanup complete. {changed} program names updated.")
    print(f"Saved to {output_file}")


if __name__ == '__main__':
    run_cleanup()
