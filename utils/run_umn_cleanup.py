import pandas as pd
import sys
import os

# Import the shared cleanup logic
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_cleanup_logic import clean_program_name

# Load the CSV
input_path = "University_of_Minnesota_Twin_Cities_Final.csv"
df = pd.read_csv(input_path)

print(f"=== Cleaning {input_path} ===")
print(f"Total programs: {len(df)}")

# Apply cleanup
df["ProgramName"] = df["ProgramName"].apply(clean_program_name)

# Save updated CSV
output_path = "University_of_Minnesota_Twin_Cities_Cleaned.csv"
df.to_csv(output_path, index=False)
print(f"\nFinalized {len(df)} programs. ProgramName column has been UPDATED.")
print(f"Saved to: {output_path}")
