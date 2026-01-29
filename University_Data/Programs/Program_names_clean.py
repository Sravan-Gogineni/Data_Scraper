import pandas as pd
import re

Programs_file_location = "/Users/sravan/projects/Scraper_UI/University_Data/Programs/Mt._San_Antonio_College_Final.csv"

def clean_program_name(name):
    """
    Clean program names by:
    1. Converting degree abbreviations to full form as prefix
    2. Removing certificate codes (e.g., E0504, N0460, etc.)
    """
    if pd.isna(name):
        return name
    
    name_str = str(name).strip()
    
    # Degree mappings - convert abbreviation to full form
    degree_mappings = {
        r'\(AS Degree[^)]*\)': 'Associate of Science in',
        r'\(AA Degree[^)]*\)': 'Associate of Arts in',
        r'\(AS-T Degree[^)]*\)': 'Associate of Science for Transfer in',
        r'\(AA-T Degree[^)]*\)': 'Associate of Arts for Transfer in',
        r'\(BS Degree[^)]*\)': 'Bachelor of Science in',
        r'\(BA Degree[^)]*\)': 'Bachelor of Arts in',
        r'\(MS Degree[^)]*\)': 'Master of Science in',
        r'\(MA Degree[^)]*\)': 'Master of Arts in',
        r'\(MBA Degree[^)]*\)': 'Master of Business Administration in',
    }
    
    # Certificate patterns - remove codes like E0504, N0460, T0883, etc.
    certificate_patterns = [
        r'\(Certificate [A-Z]\d+\)',  # (Certificate E0504)
        r'\(Skills Certificate [A-Z]\d+\)',  # (Skills Certificate E0433)
    ]
    
    # First, handle degrees
    for pattern, prefix in degree_mappings.items():
        if re.search(pattern, name_str):
            # Remove the degree suffix
            clean_name = re.sub(pattern, '', name_str).strip()
            # Add prefix
            return f"{prefix} {clean_name}"
    
    # Then, handle certificates - just remove the code, keep "Certificate"
    for pattern in certificate_patterns:
        if re.search(pattern, name_str):
            # Replace with just "Certificate"
            clean_name = re.sub(pattern, 'Certificate', name_str).strip()
            # Clean up any double spaces
            clean_name = re.sub(r'\s+', ' ', clean_name)
            return clean_name
    
    return name_str


# Load the CSV
df = pd.read_csv(Programs_file_location)

# Apply cleaning function
df['ProgramName'] = df['ProgramName'].apply(clean_program_name)

# Save cleaned version
output_file = Programs_file_location.replace('_Final.csv', '_Cleaned.csv')
df.to_csv(output_file, index=False)

print(f"Cleaned program names saved to: {output_file}")
print(f"\nSample cleaned names:")
print(df['ProgramName'].head(20).to_string())
