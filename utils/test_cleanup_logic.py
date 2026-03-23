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
        'Certificate': 'Certificate',
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
        
        # UChicago & JHU additions
        'MSA': 'Master of Science in Accountancy',
        'MPS': 'Master of Professional Studies',
        'MS': 'Master of Science',
        'MSEd': 'Master of Science in Education',
        'MSAE': 'Master of Science in Architectural Engineering',
        'MSAT': 'Master of Science in Athletic Training',
        'DBA': 'Doctor of Business Administration',
        'MSBA': 'Master of Science in Business Analytics',
        'MSPH': 'Master of Science in Public Health',
        'MPP': 'Master of Public Policy',
        'DPT': 'Doctor of Physical Therapy',
        'Cert': 'Certificate',
        'MA': 'Master of Arts',
        'MBA': 'Master of Business Administration',
        'MPH': 'Master of Public Health',
        'MPH Online': 'Master of Public Health (Online)',
        'MPA Online': 'Master of Public Administration (Online)',
        'MSECE': 'Master of Science in Electrical and Computer Engineering',
        'EdD': 'Doctor of Education',
        'EdD Online': 'Doctor of Education (Online)',
        'M.Ed.': 'Master of Education',
        'MLS': 'Master of Library Science',
        'MSW': 'Master of Social Work',
        'DSW': 'Doctor of Social Work',
        'Master of Science': 'Master of Science',
        'Master of Arts': 'Master of Arts',
        'Master of Science in Engineering': 'Master of Science in Engineering',
        'BA/MS': 'Master of Science',
        'BS/MS': 'Master of Science',
        'BA/MA': 'Master of Arts',
        'MSEE': 'Master of Science in Engineering',
        'MBEE': 'Master of Biotechnology Enterprise and Entrepreneurship',
        'MA;': 'Master of Arts',
        'Master': 'Master of',
        'Master\'s': 'Master of',
        'Postbaccalaureate Certificate': 'Postbaccalaureate Certificate',
        'Postgraduate Certificate': 'Postgraduate Certificate',
        'M S': 'Master of Science',
        'M A': 'Master of Arts',
        'M B A': 'Master of Business Administration',
        'Ph D': 'Doctor of Philosophy',
    }
    
    name = name.strip()
    
    # 1. Check for parenthesis at the end: (B.S.), (PhD), (MBA), etc.
    degree_match = re.search(r'\(([^)]+)\)$', name)
    
    if degree_match:
        degree_abbr = degree_match.group(1).strip()
        full_degree = degree_map.get(degree_abbr)

        # Remove the degree part from the original string
        name_without_degree = name[:degree_match.start()].strip().rstrip(',').strip()

        if full_degree:
            # If the name before the parenthesis already contains the full degree text
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

    # 1b. Check for JHU specific suffixes and remove them
    jhu_suffixes = ["- Jenkins Biophysics Program", "- Program in Molecular Biophysics"]
    for suffix in jhu_suffixes:
        if name.endswith(suffix):
            name = name.replace(suffix, "").strip()

    # 2. Check for trailing degree abbreviations (without parenthesis)
    # Split by space and check last token
    parts = name.split()
    if len(parts) > 1:
        # Check standard map — try last 3 words, then last 2, then last word
        # (e.g. "Master of Science in Engineering", "MPH Online", "MS")
        full_degree = None
        n_words = 0
        
        # Handle cases like "Field, Degree" or "Degree in Field"
        # If it's already "Master of Science in Field", we might want to normalize it
        if "Master of" in name or "Bachelor of" in name or "Doctor of" in name:
             # Basic normalization if it's already "Degree in Field"
             # But if it's "Field, Degree", we want to flip it.
             pass

        last_five = " ".join(parts[-5:]) if len(parts) >= 5 else None
        last_four = " ".join(parts[-4:]) if len(parts) >= 4 else None
        last_three = " ".join(parts[-3:]) if len(parts) >= 3 else None
        last_two = " ".join(parts[-2:]) if len(parts) >= 2 else None
        last_one = parts[-1]

        for candidates in [last_five, last_four, last_three, last_two, last_one]:
            if not candidates: continue
            # Handle cases like "Statistics, Master of..." where comma is on the previous word
            # Actually candidates is "parts[-N:]". If N=5, parts[-5] might have a comma.
            # But the candidates themselves are space-joined.
            # If parts = ["Field,", "Degree"], parts[-1] is "Degree".
            # If parts = ["Field", "Degree,"], parts[-1] is "Degree,".
            # The .rstrip(',') below handles the latter.
            clean_cand = candidates.rstrip(',').strip()
            if clean_cand in degree_map:
                full_degree = degree_map[clean_cand]
                n_words = len(candidates.split())
                break
        
        # Special case for "Cert, MSN"
        if "Cert, MSN" in name:
             full_degree = 'Post-Master\'s Certificate in Nursing'
             name_without_degree = name.replace("Cert, MSN", "").strip().rstrip(',')
             return f"{full_degree} in {name_without_degree}"

        if full_degree:
            name_without_degree = " ".join(parts[:-n_words]).rstrip(',').strip()
            # Remove trailing 'in' or 'of' if they are left over
            if name_without_degree.lower().endswith(' in'):
                name_without_degree = name_without_degree[:-3].strip()
            elif name_without_degree.lower().endswith(' of'):
                name_without_degree = name_without_degree[:-3].strip()
            
            # If name_without_degree is empty, it means the whole string was just the degree (e.g. "PhD")
            if not name_without_degree:
                return full_degree
            
            fd_norm = full_degree.lower()
            nwd_norm = name_without_degree.lower()
            
            # If the degree name is already at the start, just strip the suffix
            # e.g. "Master of Science in Biotechnology" (with MS/M.S. at end removed)
            if nwd_norm.startswith(fd_norm):
                return name_without_degree
            
            # If the name is already the degree name (e.g. "Master of Business Administration")
            if nwd_norm == fd_norm:
                return full_degree

            # If the name is already in the degree (e.g. "MPH Online") and we mapped it
            if nwd_norm in fd_norm:
                return full_degree

            # UMN fix: Handle "Master of" or "Master's" in the suffix
            if full_degree == "Master of":
                return f"Master of {name_without_degree}"
            
            # Handle Certificates
            if "Certificate" in full_degree:
                return f"{full_degree} in {name_without_degree}"

            return f"{full_degree} in {name_without_degree}"
                
    # 3. Check if it starts with "Master of Science in", etc.
    # If it's already "Master of Science in Anatomy Education", we should just return it (maybe strip punctuation)
    for degree_val in set(degree_map.values()):
        if name.startswith(degree_val) and " in " in name:
            return name.rstrip(',').strip()

    return name.rstrip(',').strip()

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


class TestCleanupJHU(unittest.TestCase):
    def test_examples(self):
        cases = [
            ("Master of Science in Anatomy Education", "Master of Science in Anatomy Education"),
            ("Applied and Computational Mathematics, Graduate Certificate", "Graduate Certificate in Applied and Computational Mathematics"),
            ("Applied and Computational Mathematics, Master of Science", "Master of Science in Applied and Computational Mathematics"),
            ("Applied Biomedical Engineering, Graduate Certificate", "Graduate Certificate in Applied Biomedical Engineering"),
            ("Applied Biomedical Engineering, Master of Science", "Master of Science in Applied Biomedical Engineering"),
            ("Master of Science in Applied Health Sciences Informatics", "Master of Science in Applied Health Sciences Informatics"),
            ("Applied Mathematics and Statistics, Master of Science in Engineering", "Master of Science in Engineering in Applied Mathematics and Statistics"),
            ("Applied Physics, Master of Science", "Master of Science in Applied Physics"),
            ("Biology, BA/MS", "Master of Science in Biology"),
            ("Master of Science in Biophysics", "Master of Science in Biophysics"),
            ("Biophysics, PhD - Jenkins Biophysics Program", "Doctor of Philosophy in Biophysics"),
            ("Biophysics, PhD - Program in Molecular Biophysics", "Doctor of Philosophy in Biophysics"),
            ("Biotechnology, MS, MBEE", "Master of Biotechnology Enterprise and Entrepreneurship in Biotechnology"),
            ("Master of Science in Cellular and Molecular Medicine", "Master of Science in Cellular and Molecular Medicine"),
            ("Chemical Biology, MS, MSEE", "Master of Science in Engineering in Chemical Biology"),
            ("Chemistry, BS/MS", "Master of Science in Chemistry"),
            ("Classics, BA/MA", "Master of Arts in Classics"),
            ("Climate, Energy, and Environmental Sustainability, Master of Science", "Master of Science in Climate, Energy, and Environmental Sustainability"),
            ("Master of Arts in Cognitive Science", "Master of Arts in Cognitive Science"),
            ("Applied Mathematics and Statistics, PhD", "Doctor of Philosophy in Applied Mathematics and Statistics"),
            ("Master of Science in Economics, MA;", "Master of Arts in Economics"), # JHU weird case
        ]
        
        for original, expected in cases:
            cleaned = clean_program_name(original)
            print(f"Original: {original} -> Cleaned: {cleaned}")
            self.assertEqual(cleaned, expected)

if __name__ == '__main__':
    unittest.main()
