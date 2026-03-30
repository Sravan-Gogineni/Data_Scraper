import re

def standardize_program_name(name):
    name_str = str(name).strip()
    
    # Define degree mappings
    degree_mappings = {
        "M.S.": "Master of Science",
        "MS": "Master of Science",
        "M.A.": "Master of Arts",
        "MA": "Master of Arts",
        "Ph.D.": "Ph.D.",
        "MFA": "Master of Fine Arts",
        "B.S.": "Bachelor of Science",
        "BS": "Bachelor of Science",
        "B.A.": "Bachelor of Arts",
        "BA": "Bachelor of Arts",
        "MBA": "Master of Business Administration",
    }
    
    # Regex to match: <Program Name>, <Degree> [Concentration in <Concentration>]
    # example: "Engineering, M.S. Concentration in Aerospace..."
    # example: "Artificial Intelligence, M.S."
    
    pattern = r"^(.*?),\s*([A-Za-z\.]+)(?:\s+(Concentration in\s+.*))?$"
    match = re.search(pattern, name_str, re.IGNORECASE)
    
    if match:
        prog_name = match.group(1).strip()
        degree_abbr = match.group(2).strip()
        concentration = match.group(3)
        
        # Look up degree expansion, or keep original if not found
        # (Case-insensitive lookup)
        expanded_degree = None
        for abbr, expansion in degree_mappings.items():
            if abbr.lower() == degree_abbr.lower():
                expanded_degree = expansion
                break
        
        if not expanded_degree:
            expanded_degree = degree_abbr
            
        # Format: <Degree> in <Program Name> [Concentration in ...]
        # E.g. Master of Science in Artificial Intelligence
        # E.g. Ph.D. in Engineering Concentration in Aerospace and mechanical engineering
        
        new_name = f"{expanded_degree} in {prog_name}"
        if concentration:
            new_name += f" {concentration}"
            
        return new_name
        
    return name_str

# Test cases
test_names = [
    'Artificial Intelligence, M.S.',
    'Engineering, Ph.D. Concentration in Aerospace and mechanical engineering',
    'Chemical Biology, M.A.',
    'Meteorology, Ph.D.',
    'Engineering, M.S. Concentration in Civil engineering',
    'Bachelor of Science in Aeronautics'
]

for name in test_names:
    print(f"Original: {name}")
    print(f"Cleaned : {standardize_program_name(name)}\n")
