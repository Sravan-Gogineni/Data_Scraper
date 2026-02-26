import pandas as pd
import sys
import os

# Import the shared cleanup logic
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_cleanup_logic import clean_program_name

# Load the CSV
df = pd.read_csv("programs_collegeid_93.csv")

print("=== Preview of Original Program Names ===")
print(df["ProgramName"].to_string(index=False))
print(f"\nTotal programs: {len(df)}")

# Apply cleanup and add a new column alongside the original
df["CleanedProgramName"] = df["ProgramName"].apply(clean_program_name)

# Show a side-by-side comparison of changes
changed = df[df["ProgramName"] != df["CleanedProgramName"]]
print(f"\n=== {len(changed)} names were updated ===")
if not changed.empty:
    for _, row in changed.iterrows():
        print(f"  BEFORE: {row['ProgramName']}")
        print(f"   AFTER: {row['CleanedProgramName']}")
        print()

# Save updated CSV with both columns (original + cleaned)
output_path = "programs_collegeid_93_cleaned.csv"
df.to_csv(output_path, index=False)
print(f"\nSaved cleaned CSV to: {output_path}")
