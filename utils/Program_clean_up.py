import pandas as pd
import re

# 1. Load your excel file
# Change 'data.xlsx' to your actual file name
input_file = '/Users/sravan/projects/Scraper_UI/University_of_Michigan_Final.csv'
df = pd.read_csv(input_file)

# 2. Define the mapping logic for departments (University of Michigan)
def map_departments(text):
    # Convert to string and handle empty/NaN cells
    val = str(text).strip()
    
    # Handle special case for "0" or empty values
    if val == "0" or val == "" or val.lower() == "nan":
        return "Rackham Graduate School Admissions"
    
    # Taubman College Admissions
    if "Taubman College" in val or "Architecture and Urban Planning" in val:
        return "Taubman College Admissions"
    
    # Rackham Graduate School Admissions
    # This includes all departments that mention Rackham
    elif "Rackham Graduate School" in val or "Rackham" in val or "Horace H. Rackham" in val:
        return "Rackham Graduate School Admissions"
    
    # Full-Time MBA Admissions (Ross School of Business)
    elif "Ross School of Business" in val or "Stephen M. Ross" in val:
        return "Full-Time MBA Admissions"
    
    # School of Music, Theatre & Dance Admissions
    elif "Music, Theatre & Dance" in val or "Music, Theatre and Dance" in val:
        return "School of Music, Theatre & Dance Admissions"
    
    # Medical School, School of Public Health, School of Nursing, School of Dentistry, School of Pharmacy
    # School of Kinesiology, School for Environment and Sustainability, School of Information
    # Marsal Family School of Education, Gerald R. Ford School of Public Policy
    # These typically have graduate programs and would fall under Rackham unless specified
    elif any(school in val for school in [
        "Medical School", "School of Public Health", "School of Nursing", 
        "School of Dentistry", "School of Pharmacy", "School of Kinesiology",
        "School for Environment and Sustainability", "School of Information",
        "Marsal Family School of Education", "Gerald R. Ford School of Public Policy"
    ]):
        return "Rackham Graduate School Admissions"
    
    # Law School has its own admissions
    elif "Law School" in val or "Michigan Law" in val:
        return "Rackham Graduate School Admissions"  # Adjust if Law has separate graduate admissions
    
    # College of Engineering (standalone or with LSA)
    elif "College of Engineering" in val or "Engineering" in val:
        # Check if it's combined with Rackham
        if "Rackham" in val:
            return "Rackham Graduate School Admissions"
        else:
            return "Rackham Graduate School Admissions"
    
    # College of Literature, Science, and the Arts (LSA)
    elif "Literature, Science, and the Arts" in val or "LSA" in val or "College of Arts & Sciences" in val:
        # If combined with Rackham, it's graduate
        if "Rackham" in val:
            return "Rackham Graduate School Admissions"
        else:
            return "Rackham Graduate School Admissions"
    
    # Penny W. Stamps School of Art & Design
    elif "Stamps School" in val or "Art & Design" in val:
        return "Rackham Graduate School Admissions"
    
    # College of Health Sciences (UM-Flint)
    elif "College of Health Sciences" in val:
        return "Rackham Graduate School Admissions"
    # International Institute
    elif "International Institute" in val:
        return "Rackham Graduate School Admissions"
    
    # Default mapping for undergraduate programs
    else:
        return "Rackham Graduate School Admissions"

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
output_file = '/Users/sravan/projects/Scraper_UI/University_of_Michigan_Final_Fixed.csv'
df.to_csv(output_file, index=False)

print(f"Success! Created column 'dept' and saved to {output_file}")