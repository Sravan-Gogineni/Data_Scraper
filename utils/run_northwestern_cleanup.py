import csv
import os
import re

degree_map = {
    'MS': 'Master of Science',
    'MA': 'Master of Arts',
    'MBA': 'Master of Business Administration',
    'MPA': 'Master of Public Administration',
    'MPH': 'Master of Public Health',
    'MSN': 'Master of Science in Nursing',
    'MSE': 'Master of Science in Engineering',
    'MSPH': 'Master of Science in Public Health',
    'MSEd': 'Master of Science in Education',
    'M.S.': 'Master of Science',
    'M.A.': 'Master of Arts',
    'M.B.A.': 'Master of Business Administration',
    'M.P.A.': 'Master of Public Administration',
    'M.P.H.': 'Master of Public Health',
    'M.S.N.': 'Master of Science in Nursing',
    'M.S.E.': 'Master of Science in Engineering',
    'Graduate Certificate': 'Graduate Certificate',
    'Certificate': 'Certificate',
    'Advanced Graduate Certificate': 'Advanced Graduate Certificate',
    'Post-Master\'s Certificate': 'Post-Master\'s Certificate',
    'MBEE': 'Master of Biotechnology Enterprise and Entrepreneurship',
    'MSEE': 'Master of Science in Engineering',
    'MLA': 'Master of Liberal Arts',
    'MEHP': 'Master of Education in the Health Professions',
    'MBI': 'Master of Biological Illustration',
    'MSAE': 'Master of Science in Anatomy Education',
    'MSAT': 'Master of Science in Athletic Training',
    'MSBA': 'Master of Science in Business Analytics',
    'MPS': 'Master of Professional Studies',
    'DPT': 'Doctor of Physical Therapy',
    'DBA': 'Doctor of Business Administration',
    'DSW': 'Doctor of Social Work',
    'EdD': 'Doctor of Education',
    'MLS': 'Master of Library Science',
    'MSW': 'Master of Social Work',
    'MSECE': 'Master of Science in Electrical and Computer Engineering',
    'MSL': 'Master of Science in Law',
    'LLM': 'Master of Laws',
    'AuD': 'Doctor of Audiology',
    'EdM': 'Master of Education',
    'MFA': 'Master of Fine Arts',
}

def clean_northwestern_program_name(name):
    if not isinstance(name, str) or not name:
        return name
    
    # 1. Handle weird quoting and trailing commas in the CSV content
    # e.g., "Master of Science in Advanced Manufacturing,"
    name = name.strip().strip('"').strip().rstrip(',').strip()
    
    # 2. Handle cases where there is a delimiter (usually comma)
    # Northwestern names often look like "Program Name, Degree"
    # or "Program Name, Degree Specialization"
    parts = [p.strip() for p in name.split(',')]
    
    if len(parts) <= 1:
        # Check if it already starts with a full degree name
        for d in set(degree_map.values()) | {"Doctor of Philosophy", "PhD", "Master of Fine Arts"}:
            if name.startswith(d):
                return name
        return name
    
    base_name = parts[0]
    degree_part = parts[1]
    
    # Handle combined degrees like BS/MA or MS,msbee
    if '/' in degree_part:
        degree_part = degree_part.split('/')[-1].strip()
    
    degree_key = degree_part.rstrip(';').strip()
    
    # PhD Rule: move to front but no expansion
    if degree_key.lower() in ['phd', 'ph.d.']:
        # If base_name is already "Name, PhD", it would be reordered here
        return f"PhD in {base_name}"
        
    # Map abbreviation to full name
    full_degree = degree_map.get(degree_key)
    if not full_degree:
        full_degree = degree_map.get(degree_key.replace('.', ''))
    
    # If not in map, but is a full name already
    if not full_degree:
        if degree_key.startswith(('Master', 'Bachelor', 'Doctor', 'Certificate', 'Graduate', 'Advanced Graduate')):
            full_degree = degree_key
            
    if full_degree:
        # If base_name contains the degree already (e.g., "Master of Arts in..."), strip it
        for d in set(degree_map.values()) | {"Doctor of Philosophy", "PhD"}:
            if base_name.startswith(d + " in "):
                base_name = base_name.replace(d + " in ", "").strip()
            elif base_name.startswith(d + ","):
                base_name = base_name.replace(d + ",", "").strip()
            elif base_name.startswith(d):
                # Only strip if it's the exact degree name at the start
                # Be careful not to strip "Art History" if we are looking for "Art"
                # A simple regex boundary would be safer but let's try simple match first
                candidate = base_name.replace(d, "", 1).strip().lstrip(',').strip()
                if candidate:
                    base_name = candidate
        
        return f"{full_degree} in {base_name}"
        
    return name

def run_cleanup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, 'Northwestern_University_Final.csv')
    output_file = os.path.join(base_dir, 'Northwestern_University_Cleaned.csv')
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
        
    for row in rows:
        level = row.get('Level', '').lower()
        original = row['ProgramName']
        cleaned = clean_northwestern_program_name(original)
        row['ProgramName'] = cleaned
            
    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Cleanup complete. Saved to {output_file}")

if __name__ == '__main__':
    run_cleanup()
