import pandas as pd

df = pd.read_csv("/Users/sravan/projects/Scraper_UI/RIT_Cleaned.csv")

mismatches = []

for index, row in df.iterrows():
    program_name = str(row['ProgramName']).lower()
    level = str(row['Level']).lower()
    
    suggested_level = "Unknown"
    
    if "phd" in program_name or "doctor" in program_name:
        suggested_level = "Doctoral"
    elif "certificate" in program_name:
         # Hard to distinguish grad vs undergrad certificate just by name without more context, 
         # but usually if it's not specified, and in a grad file, it's grad.
         # However, let's look for triggers.
         if "advanced certificate" in program_name or "graduate certificate" in program_name:
             suggested_level = "Graduate-Certificate"
         else:
             suggested_level = "Certificate" # Generic
    elif "master" in program_name or "mba" in program_name or "m.s" in program_name or " mfa" in program_name or "ma " in program_name:
        suggested_level = "Graduate"
    elif "bachelor" in program_name or "bs " in program_name or "ba " in program_name or "minor" in program_name:
        suggested_level = "Undergraduate"
        
    # Check for obvious conflicts
    if "mba" in program_name and level != "graduate" and level != "master" and level != "masters":
         mismatches.append(f"Row {index+2}: {row['ProgramName']} -> Marked as '{row['Level']}', Should likely be 'Graduate'")
    elif "master" in program_name and "certificate" not in program_name and level != "graduate" and level != "masters":
         mismatches.append(f"Row {index+2}: {row['ProgramName']} -> Marked as '{row['Level']}', Should likely be 'Graduate'")
    elif "bachelor" in program_name and level != "undergraduate":
         mismatches.append(f"Row {index+2}: {row['ProgramName']} -> Marked as '{row['Level']}', Should likely be 'Undergraduate'")
    elif "phd" in program_name and level != "doctoral":
         mismatches.append(f"Row {index+2}: {row['ProgramName']} -> Marked as '{row['Level']}', Should likely be 'Doctoral'")

for m in mismatches:
    print(m)

if not mismatches:
    print("No obvious mismatches found based on simple keywords.")
