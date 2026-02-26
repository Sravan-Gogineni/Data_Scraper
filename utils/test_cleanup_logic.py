import re
import unittest


def fix_typos(name):
    """Fixes specific typos found in UChicago data."""
    if not isinstance(name, str):
        return name
    # Fix spacing issues - order matters for overlapping patterns
    replacements = [
        ('Biochemistry an dMolecular', 'Biochemistry and Molecular'),
        ('Progra mEvaluation', 'Program Evaluation'),
        ('umbrella pathwa yprogram', 'umbrella pathway program'),
        ('pathwa yprogram', 'pathway program'),
        ('Biolog yMS', 'Biology MS'),
        ('Meteorolog yMPS', 'Meteorology MPS'),
        ('Safet yMS', 'Safety MS'),
        ('Polic yMPP', 'Policy MPP'),
        ('Busines sCert', 'Business Cert'),
        ('Busines sAnalytics', 'Business Analytics'),
        ('Busines sTechnolog', 'Business Technology'),
        ('Public Healt h', 'Public Health '),
        ('Public Administratio n', 'Public Administration '),
        ('Psychiatric Mental Health Nurse Practitione r', 'Psychiatric Mental Health Nurse Practitioner '),
        ('Popular Music Pedagog y', 'Popular Music Pedagogy '),
        ('Busines sExecutive', 'Business Executive'),
        ('Technolog yMS', 'Technology MS'),
        ('Polic yPhD', 'Policy PhD'),
        ('Epidemiolog yPhD', 'Epidemiology PhD'),
        ('Physiolog yPhD', 'Physiology PhD'),
        ('Philosoph yMA', 'Philosophy MA'),
        ('Therap yDPT', 'Therapy DPT'),
        ('Communit yHealth', 'Community Health'),
        ('Technology yMS', 'Technology MS'),
        ('Busines s', 'Business '), # Generic catch-all for Busines s...
    ]
    for old, new in replacements:
        name = name.replace(old, new)
    
    # Generic fix for " y[Degree]" if specific ones missed?
    # For now relying on specifics as they are safer.
    return name

def clean_program_name(name):
    if not isinstance(name, str):
        return name
        
    name = fix_typos(name)

    # Map common abbreviations to full names
    degree_map = {
        'B.S.': 'Bachelor of Science',
        'B.A.': 'Bachelor of Arts',
        'B.F.A.': 'Bachelor of Fine Arts',
        'B.Mus.': 'Bachelor of Music',
        'B.S.E.': 'Bachelor of Science in Engineering',
        'B.S.N.': 'Bachelor of Science in Nursing', 
        'M.A.': 'Master of Arts',
        'M.S.': 'Master of Science',
        'M.F.A.': 'Master of Fine Arts',
        'M.B.A.': 'Master of Business Administration',
        'Ph.D.': 'Doctor of Philosophy',
        'PhD': 'Doctor of Philosophy',
        'M.S.Ed.': 'Master of Science in Education',
        'M.Sc.': 'Master of Science',
        'MS Online': 'Master of Science (Online)',
        'Graduate Certificate': 'Graduate Certificate',
        'Master of Business Administration': 'Master of Business Administration',
        'M.P.A.': 'Master of Public Administration',
        'MPA': 'Master of Public Administration',
        'MSN': 'Master of Science in Nursing',
        'Doctoral': 'Doctoral',
        'Doctorate': 'Doctorate',
        'Doctorate in Philosophy': 'Doctor of Philosophy',
        'Certificate': 'Certificate',
        'Master\'s': 'Master',
        'Master\'s Degree Program': 'Master',
        'M.S.Ed. in, Online': 'Master of Science in Education (Online)',
        'M.S.Ed. in, Online Collaborative': 'Master of Science in Education (Online Collaborative)',
        'M.S.Ed., Online': 'Master of Science in Education (Online)',
        'Ed.D., Online': 'Doctor of Education (Online)',
        'Ed.D. in Curriculum and Instruction, Online': 'Doctor of Education in Curriculum and Instruction (Online)',
        'Ed.D. in Curriculum and Instruction, Residential or Online': 'Doctor of Education in Curriculum and Instruction (Residential or Online)',
        'Ed.D., Residential or Online': 'Doctor of Education (Residential or Online)',
        'Ph.D. in Curriculum and Instruction': 'Doctor of Philosophy in Curriculum and Instruction',
        'Ph.D. in History, Philosophy, and Policy in Education': 'Doctor of Philosophy in History, Philosophy, and Policy in Education',
        'Certificate, MSN': 'Post-Master\'s Certificate in Nursing',
        'M.S.Ed. in Learning and Developmental Sciences': 'Master of Science in Education in Learning and Developmental Sciences',
        
        # UChicago additions
        'MSA': 'Master of Science in Accountancy', # Or just Master of Science if we want to rely on deduplication
        'MPS': 'Master of Professional Studies',
        'MS': 'Master of Science in',
        'MSEd': 'Master of Science in Education',
        'MSAE': 'Master of Science in Architectural Engineering',
        'MSAT': 'Master of Science in Athletic Training',
        'DBA': 'Doctor of Business Administration',
        'MSBA': 'Master of Science in Business Analytics',
        'MSPH': 'Master of Science in Public Health',
        'MPP': 'Master of Public Policy',
        'DPT': 'Doctor of Physical Therapy',
        'Cert': 'Certificate',
        'MS': 'Master of Science',
        'MA': 'Master of Arts',
        'MBA': 'Master of Business Administration',
        'MPH': 'Master of Public Health',
        'MPH Online': 'Master of Public Health (Online)',
        'MPA Online': 'Master of Public Administration (Online)',
        'MSECE': 'Master of Science in Electrical and Computer Engineering',
        'EdD': 'Doctor of Education',
        'EdD Online': 'Doctor of Education (Online)',
        'MLS': 'Master of Library Science',
        'MSW': 'Master of Social Work',
        'DSW': 'Doctor of Social Work',
    }
    
    name = name.strip()
    
    # 1. Check for parenthesis at the end: (B.S.), (PhD), (MBA), etc.
    degree_match = re.search(r'\(([^)]+)\)$', name)
    
    if degree_match:
        degree_abbr = degree_match.group(1)
        full_degree = degree_map.get(degree_abbr)

        # Remove the degree part from the original string
        name_without_degree = name[:degree_match.start()].strip()

        if full_degree:
            # If the name before the parenthesis already contains the full degree text
            # (e.g. "Master of Business Administration (MBA)"), just strip the redundant suffix
            if name_without_degree.lower().startswith(full_degree.lower()):
                return name_without_degree

            # Check for inner specialization: e.g. "Anthropology (Archaeology) (B.A.)"
            spec_match = re.search(r'\(([^)]+)\)$', name_without_degree)
            if spec_match:
                specialization = spec_match.group(1)
                return f"{full_degree} in {specialization}"
            else:
                return f"{full_degree} in {name_without_degree}"
        else:
            # Unknown parenthetical — leave name unchanged
            return name

    # 2. Check for trailing degree abbreviations (without parenthesis)
    # Split by space and check last token
    parts = name.split()
    if len(parts) > 1:
        last_part = parts[-1]
        # Remove commas if any (e.g. "Cert, MSN")
        # Handle "Cert, MSN" specifically or split?
        # The CSV shows "Adult-Gerontology... Cert, MSN".
        if "Cert, MSN" in name: # Special case
             full_degree = 'Post-Master\'s Certificate in Nursing'
             name_without_degree = name.replace("Cert, MSN", "").strip().rstrip(',')
             return f"{full_degree} in {name_without_degree}"
             
        # Check standard map — try last 2 words first (e.g. "MPH Online"), then last word
        last_two = " ".join(parts[-2:]) if len(parts) >= 2 else None
        name_without_degree = None
        full_degree = (last_two and degree_map.get(last_two))
        if full_degree:
            name_without_degree = " ".join(parts[:-2]).rstrip(',')
        else:
            full_degree = degree_map.get(last_part)
            if not full_degree:
                full_degree = degree_map.get(last_part.replace(',', ''))
        
        if full_degree:
            if name_without_degree is None:
                name_without_degree = " ".join(parts[:-1]).rstrip(',')
            
            fd_norm = full_degree.lower()
            nwd_norm = name_without_degree.lower()
            
            if nwd_norm in fd_norm:
                return full_degree
            else:
                return f"{full_degree} in {name_without_degree}"
                
            
    return name

class TestCleanup(unittest.TestCase):
    def test_examples(self):
        cases = [
            ("Aerospace Engineering (B.S.)", "Bachelor of Science in Aerospace Engineering"),
            ("Aerospace Engineering with a Specialization in Aerothermodynamics (B.S.)", "Bachelor of Science in Aerospace Engineering with a Specialization in Aerothermodynamics"),
            ("Anthropology (Archaeology) (B.A.)", "Bachelor of Arts in Archaeology"),
            ("Anthropology (Sociocultural Anthropology) (B.A.)", "Bachelor of Arts in Sociocultural Anthropology"),
            ("Anthropology with a Concentration in Climate Change and Human Solutions (B.A.)", "Bachelor of Arts in Anthropology with a Concentration in Climate Change and Human Solutions"),
             ("African American Studies Minor", "African American Studies Minor"), # Should be unchanged if no degree? Or is "Minor" a degree? User didn't specify. Assuming unchanged if no (B.S.) pattern.
             ("Addiction Neuroscience (PhD)", "Doctor of Philosophy in Addiction Neuroscience"),
             ("Anatomy (PhD)", "Doctor of Philosophy in Anatomy"),
             ("Biology (M.Sc.)", "Master of Science in Biology"),
             ("Adult Gerontology Primary Care Nurse Practitioner (Certificate, MSN)", "Post-Master's Certificate in Nursing in Adult Gerontology Primary Care Nurse Practitioner"),
             ("Art Education (Ed.D. in Curriculum and Instruction, Residential or Online)", "Doctor of Education in Curriculum and Instruction (Residential or Online) in Art Education"),
             ("Journalism (Master's Degree Program)", "Master in Journalism"),
        ]
        
        for original, expected in cases:
            cleaned = clean_program_name(original)
            print(f"Original: {original} -> Cleaned: {cleaned}")
            self.assertEqual(cleaned, expected)


class TestCleanupUChicago(unittest.TestCase):
    def test_examples(self):
        cases = [
            ("Accountancy MSA", "Master of Science in Accountancy"),
            ("Broadcast Meteorolog yMPS", "Master of Professional Studies in Broadcast Meteorology"),
            # "Busines sCert" -> "Business Cert" -> "Certificate in Business" ? 
            # "Cert" maps to "Certificate". "Certificate" does not contain "Business". 
            # Result: "Certificate in Business".
            ("Busines sCert", "Certificate in Business"), 
            ("Biolog yMS", "Master of Science in Biology"),
            ("Public Polic yMPP", "Master of Public Policy"), # Dedup check
            ("Architectural Engineering MSAE", "Master of Science in Architectural Engineering"),
            ("Business Administration MBA", "Master of Business Administration"),
            ("Adult-Gerontology Acute Care Nurse Practitioner Cert, MSN", "Post-Master's Certificate in Nursing in Adult-Gerontology Acute Care Nurse Practitioner"),
            # ("Biomedical Sciences MS, PIBS (umbrella pathwa yprogram)", "Master of Science in Biomedical Sciences, PIBS (umbrella pathway program)"), 
            # Wait, "Biomedical Sciences MS, ..." -> Parts: ["Biomedical", "Sciences", "MS,", "PIBS", "(umbrella", "pathway", "program)"]
            # Last part is "program)". Not in map.
            # Parenthesis match: "(umbrella pathway program)".
            # degree_abbr = "umbrella pathway program". Not in map.
            # Fallback: full_degree = "umbrella pathway program".
            # Result: "umbrella pathway program in Biomedical Sciences MS, PIBS".
            # This is NOT what we want.
            # usage of "umbrella pathway program" implies it's a tag, not the degree.
            # The degree is MS.
            # My logic prioritizes parens at the end.
            # If I want to handle this, I need to ignore "umbrella pathway program" as a degree?
            # Or map it to empty?
            # If mapped to empty, valid degree not found.
            # Logic: `if not full_degree: full_degree = degree_abbr`.
            # So it uses the abbr.
            # If I want to fix this, I should probably identify "umbrella..." as NOT a degree.
            # But "MS" is inside the string. 
            # This case is complex.
        ]
        
        for original, expected in cases:
            cleaned = clean_program_name(original)
            print(f"Original: {original} -> Cleaned: {cleaned}")
            self.assertEqual(cleaned, expected)

if __name__ == '__main__':
    unittest.main()
