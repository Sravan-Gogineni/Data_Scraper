import csv
import os

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
}

def clean_jhu_program_name(name):
    if not isinstance(name, str) or not name:
        return name
    
    # Pre-clean typos if any (optional but good)
    name = name.strip().rstrip(',').strip()
    
    parts = [p.strip() for p in name.split(',')]
    
    if len(parts) <= 1:
        # Check if it already starts with a degree
        for d in set(degree_map.values()) | {"Doctor of Philosophy"}:
            if name.startswith(d):
                return name
        return name
    
    base_name = parts[0]
    # The degree part is the first one after the name
    degree_part = parts[1]
    
    # Rule 6: combine like bs/ma -> consider ma
    if '/' in degree_part:
        degree_part = degree_part.split('/')[-1].strip()
        
    # Rule 5: multiple after delimiter -> consider first (already done by parts[1])
    
    degree_key = degree_part.rstrip(';').strip()
    
    # Rule: except for the phd leave (User updated: move to front but no expansion)
    if degree_key.lower() in ['phd', 'ph.d.']:
        # Ensure we keep the original casing or normalize to PhD? 
        # User said "for phd i want you to bring to front". 
        # I'll use "PhD" or the original casing. Let's use "PhD".
        return f"PhD in {base_name}"
        
    # Map abbreviation to full name
    # Try literal lookup, then lookup without dots
    full_degree = degree_map.get(degree_key)
    if not full_degree:
        full_degree = degree_map.get(degree_key.replace('.', ''))
    
    # If not in map, but is a full name already
    if not full_degree:
        if degree_key.startswith(('Master', 'Bachelor', 'Doctor', 'Certificate', 'Graduate')):
            full_degree = degree_key
            
    if full_degree:
        # If base_name contains the degree already, strip it
        for d in set(degree_map.values()) | {"Doctor of Philosophy"}:
            if base_name.startswith(d + " in "):
                base_name = base_name.replace(d + " in ", "").strip()
            elif base_name.startswith(d + ","):
                base_name = base_name.replace(d + ",", "").strip()
            elif base_name.startswith(d):
                base_name = base_name.replace(d, "").strip().lstrip(',').strip()
        
        # Strip trailing "in" or connector words from base_name
        base_name = base_name.strip()
        
        return f"{full_degree} in {base_name}"
        
    return name

def run_cleanup():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, 'Northwestern_University_Final.csv')
    output_file = os.path.join(base_dir, 'Northwestern_University_Cleaned.csv')
    
    with open(input_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
        
    for row in rows:
        level = row.get('Level', '').lower()
        # Only for graduate/certification programs
        if 'graduate' in level or 'doctoral' in level or 'certificate' in level:
            original = row['ProgramName']
            cleaned = clean_jhu_program_name(original)
            row['ProgramName'] = cleaned
            
    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Cleanup complete. Saved to {output_file}")

if __name__ == '__main__':
    run_cleanup()
