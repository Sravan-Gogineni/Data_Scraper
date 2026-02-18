import re
import unittest

def clean_program_name(name):
    if not isinstance(name, str):
        return name
        
    # Map common abbreviations to full names
    degree_map = {
        'B.S.': 'Bachelor of Science',
        'B.A.': 'Bachelor of Arts',
        'B.F.A.': 'Bachelor of Fine Arts',
        'B.Mus.': 'Bachelor of Music',
        'B.S.E.': 'Bachelor of Science in Engineering',
        'B.S.N.': 'Bachelor of science in Nursing', 
        'M.A.': 'Master of Arts',
        'M.S.': 'Master of Science',
        'M.F.A.': 'Master of Fine Arts',
        'M.B.A.': 'Master of Business Administration',
        'Ph.D.': 'Doctor of Philosophy',
        # Add more if needed
    }
    
    # Regex to find degree at the end: (B.S.), (B.A.), etc.
    # We look for parenthesis at the end of string
    degree_match = re.search(r'\(([^)]+)\)$', name.strip())
    
    if degree_match:
        degree_abbr = degree_match.group(1)
        # Check if the content inside last parenthesis is a known degree or looks like one
        # For now, let's treat it as a degree if it's in our map or looks like "B..."/"M..."
        
        full_degree = degree_map.get(degree_abbr)
        
        # If not in map, but looks like a degree (e.g. contains dots and upper case), maybe keep it or try to expand?
        # For this specific task, let's assume if it matches the pattern (B.X.) it's a degree.
        # If we can't map it, we might just use the abbreviation or "Bachelor of ..." if we can guess.
        # Let's stick to the map and maybe a fallback if the user wants. 
        # But for now, if it's not in map, let's assume it's part of the name OR just use the abbr.
        if not full_degree:
             # Basic heuristic: if it starts with B. assume Bachelor, M. assume Master? 
             # Let's just use the abbreviation if unknown for now to avoid errors, or 'Bachelor of ...' if user specified pattern.
             full_degree = degree_abbr

        # Remove the degree part from the original string
        name_without_degree = name[:degree_match.start()].strip()
        
        # Now check for specialization in parenthesis at the END of the remaining string
        # e.g. "Anthropology (Archaeology)"
        spec_match = re.search(r'\(([^)]+)\)$', name_without_degree)
        
        if spec_match:
            specialization = spec_match.group(1)
            # If specialization exists, that becomes the "Program Name"
            return f"{full_degree} in {specialization}"
        else:
            # No specialization, so the whole remaining part is the program
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
        ]
        
        for original, expected in cases:
            cleaned = clean_program_name(original)
            print(f"Original: {original} -> Cleaned: {cleaned}")
            self.assertEqual(cleaned, expected)

if __name__ == '__main__':
    unittest.main()
