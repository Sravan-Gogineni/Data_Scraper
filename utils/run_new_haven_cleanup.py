import csv
import os
import re

# Map abbreviated degrees to full names
degree_abbrev_map = {
    'M.S.': 'Master of Science',
    'M.A.': 'Master of Arts',
    'M.B.A.': 'Master of Business Administration',
    'M.H.A.': 'Master of Healthcare Administration',
    'M.M.S.': 'Master of Medical Science',
    'Ph.D.': 'Doctor of Philosophy',
    'M.S.W.': 'Master of Social Work',
    'M.F.A.': 'Master of Fine Arts',
    'M.P.H.': 'Master of Public Health',
    'M.P.A.': 'Master of Public Administration',
    'M.Ed.': 'Master of Education',
}

def clean_new_haven_program_name(name):
    """
    Convert program names from "Subject, Degree[, Concentration]" format
    to "Full Degree in Subject[ - Concentration]" format.

    Examples:
      "Accounting, M.S."
        -> "Master of Science in Accounting"
      "Accounting, M.S., Corporate Track Concentration"
        -> "Master of Science in Accounting - Corporate Track Concentration"
      "Business Administration, M.B.A., Data Analytics (STEM) Concentration"
        -> "Master of Business Administration in Business Administration - Data Analytics (STEM) Concentration"
      "Criminal Justice, Ph.D."
        -> "Doctor of Philosophy in Criminal Justice"
    """
    if not isinstance(name, str) or not name.strip():
        return name

    name = name.strip()

    # Split by comma — be careful: parts[0]=subject, parts[1]=degree abbrev, parts[2+]=concentration
    parts = [p.strip() for p in name.split(',')]

    if len(parts) < 2:
        # No comma — check if it already starts with a full degree
        return name

    subject = parts[0].strip()
    degree_abbrev = parts[1].strip()

    # Look up full degree name
    full_degree = degree_abbrev_map.get(degree_abbrev)

    if not full_degree:
        # Not a known degree abbreviation — return as-is
        return name

    # Collect any trailing concentration parts (parts[2] onward)
    concentration = ', '.join(parts[2:]).strip() if len(parts) > 2 else ''

    # Build the cleaned name
    if concentration:
        cleaned = f"{full_degree} in {subject} - {concentration}"
    else:
        cleaned = f"{full_degree} in {subject}"

    return cleaned


def run_cleanup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, 'University_of_New_Haven_Final.csv')
    output_file = os.path.join(base_dir, 'University_of_New_Haven_Cleaned.csv')

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    changed = 0
    for row in rows:
        level = row.get('Level', '')
        # Only clean Graduate (non-certificate) programs
        if 'Graduate' in level and 'Certificate' not in level:
            original = row['ProgramName']
            cleaned = clean_new_haven_program_name(original)
            if cleaned != original:
                print(f"  BEFORE: {original}")
                print(f"  AFTER : {cleaned}")
                print()
                changed += 1
            row['ProgramName'] = cleaned

    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Cleanup complete. {changed} program(s) renamed.")
    print(f"Output saved to: {output_file}")


if __name__ == '__main__':
    run_cleanup()
