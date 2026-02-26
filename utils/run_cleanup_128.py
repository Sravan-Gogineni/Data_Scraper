import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_cleanup_logic import clean_program_name

df = pd.read_csv("programs_collegeid_128.csv")

print(f"Total programs: {len(df)}\n")

df["CleanedProgramName"] = df["ProgramName"].apply(clean_program_name)

changed = df[df["ProgramName"] != df["CleanedProgramName"]]
print(f"=== {len(changed)} names updated ===")
for _, row in changed.iterrows():
    print(f"  BEFORE: {row['ProgramName']}")
    print(f"   AFTER: {row['CleanedProgramName']}\n")

output_path = "programs_collegeid_128_cleaned.csv"
df.to_csv(output_path, index=False)
print(f"Saved to: {output_path}")
