import pandas as pd
import re

# 1. Load your excel file
# Change 'data.xlsx' to your actual file name
input_file = '/Users/sravan/projects/Scraper_UI/Carnegie_Mellon_University_Final(in).csv'
df = pd.read_csv(input_file)

# 2. Define the mapping logic for departments
def map_departments(text):
    # Convert to string and handle empty/NaN cells
    val = str(text).strip()
    
    if "College of Engineering" in val or "Engineering" in val:
        return "College of Engineering Admissions"
    elif "Architecture" in val:
        return "Architecture Graduate Admissions"
    else:
        # Default mapping if no match is found
        return "Office of Graduate and Postdoctoral Affairs"

# 3. Create the new 'dept' column based on the 'Department' column
df['dept'] = df['Department'].apply(map_departments)

# 4. Define function to reformat program names
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
    else:
        # If no match, return as is
        return val

# 5. Apply the reformatting to the ProgramName column
df['ProgramName'] = df['ProgramName'].apply(reformat_program_name)

# 4. Save to a new file so you don't overwrite your original data
output_file = '/Users/sravan/projects/Scraper_UI/Carnegie_Mellon_University_Final(in)_Fixed.csv'
df.to_csv(output_file, index=False)

print(f"Success! Created column 'dept' and saved to {output_file}")