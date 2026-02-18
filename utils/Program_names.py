import pandas as pd
import re

# 1. Load your CSV file
input_file = '/Users/sravan/projects/Scraper_UI/University_Data/Programs/Purdue_University_Final.csv'
df = pd.read_csv(input_file)

# 2. Define function to reformat program names
def reformat_program_name(program_name):
    # Convert to string and handle empty/NaN cells
    val = str(program_name).strip()
    
    # Check if the program name ends with a degree in parentheses
    # Pattern: matches text ending with (something)
    match = re.match(r'^(.+?)\s*\(([^)]+)\)$', val)
    
    if match:
        program_part = match.group(1).strip()  # The program name
        degree_part = match.group(2).strip()   # The degree type (e.g., Ph.D., M.S.)
        
        # Reformat to "(Degree) in Program Name"
        return f"({degree_part}) in {program_part}"
    
    # Check if the program name ends with a credential type without parentheses
    # Pattern: matches text ending with Minor, Certificate, Specialization, Concentration, etc.
    credential_types = [
        'Minor', 'Certificate', 'Specialization', 'Concentration', 
        'Endorsement', 'Track', 'Option', 'Emphasis'
    ]
    
    for credential in credential_types:
        # Case-insensitive match at the end of the string
        pattern = r'^(.+?)\s+(' + re.escape(credential) + r')$'
        match = re.match(pattern, val, re.IGNORECASE)
        
        if match:
            program_part = match.group(1).strip()  # The subject/program name
            credential_part = match.group(2).strip()  # The credential type
            
            # Reformat to "Credential in Program Name"
            return f"{credential_part} in {program_part}"
    
    # If no match, return as is
    return val

# 3. Apply the reformatting to the ProgramName column
df['ProgramName'] = df['ProgramName'].apply(reformat_program_name)

# 4. Save to a new file
output_file = '/Users/sravan/projects/Scraper_UI/University_Data/Programs/Purdue_University_Final_NameFixed.csv'
df.to_csv(output_file, index=False)

print(f"Success! Reformatted ProgramName column and saved to {output_file}")
