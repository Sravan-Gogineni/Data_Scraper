from os import name
import pandas as pd

df = pd.read_csv("/Users/sravan/projects/Scraper_UI/University_Data/Programs/SUNY_Brockport_Final.csv")

# level
df['QsWorldRanking'] = ""



def standardize_program_name(name):
    name_str = str(name).strip()
    # Mapping of suffix to prefix
    mappings = {
        " MS": "Master of Science in",
        " MFA": "Master of Fine Arts in",
        " BS": "Bachelor of Science in",
        " BA": "Bachelor of Arts in",
        " MA": "Master of Arts in",
        "AAS": "Associate of Applied Science in",
        "AS": "Associate of Science in",
        "AA": "Associate of Arts in",
        "BFA": "Bachelor of Fine Arts in",
        "MBA": "Master of Business Administration in",
        " (MS)": "Master of Science in",
        " (MFA)": "Master of Fine Arts in",
        " (BS)": "Bachelor of Science in",
        " (BA)": "Bachelor of Arts in",
        " (MA)": "Master of Arts in",
        " (AAS)": "Associate of Applied Science in",
        " (AS)": "Associate of Science in",
        " (AA)": "Associate of Arts in",
        " (BFA)": "Bachelor of Fine Arts in",
        " (MBA)": "Master of Business Administration in",
        "(BA, BS)": "Bachelor of Arts in"
    }
    
    for suffix, prefix in mappings.items():
        if name_str.endswith(suffix):
            # Remove the suffix (e.g. " MS" or " (BS)") and prepend the prefix
            # Original: "Program MS" -> "Program" -> "Master of Science in Program"
            # Original: "Program (BS)" -> "Program" -> "Bachelor of Science in Program"
            clean_name = name_str[:-len(suffix)]
            return f"{prefix} {clean_name}"
            
    return name_str

df['ProgramName'] = df['ProgramName'].apply(standardize_program_name)



df["Term"] = "Fall 2026"
df["LiveDate"] = ""
df["DeadlineDate"] = ""
df['QsWorldRanking'] = ""
df['CollegeApplicationFee'] = ""
df['IsNewlyLaunched'] = "FALSE"
df['IsImportVerified'] = "FALSE"
df['Is_Recommendation_Sponser'] = "FALSE"
df['IsRecommendationSystemOpted'] = "FALSE"
df['PreviousYearAcceptanceRates']=""
df['EnglishScore']="Required"
df['IsStemProgram']= df['IsStemProgram'].fillna(False)
df['IsStemProgram']= df['IsStemProgram'].astype(bool)
df['IsACTRequired']= df['IsACTRequired'].fillna(False)
df['IsACTRequired']= df['IsACTRequired'].astype(bool)
df['IsSATRequired']= df['IsSATRequired'].fillna(False)
df['IsSATRequired']= df['IsSATRequired'].astype(bool)
df['IsAnalyticalNotRequired'] = df['IsAnalyticalNotRequired'].fillna(True)
df['IsAnalyticalNotRequired'] = df['IsAnalyticalNotRequired'].astype(bool)
df['IsAnalyticalOptional'] = df['IsAnalyticalOptional'].fillna(True)
df['IsAnalyticalOptional'] = df['IsAnalyticalOptional'].astype(bool)
#column rename
df.rename(columns={'IsGreRequired':'IsGRERequired'}, inplace=True)
df['IsGRERequired'] = df['IsGRERequired'].fillna(False)
df['IsGRERequired'] = df['IsGRERequired'].astype(bool) 
#remove "[", "]", " ' "in column concentration
df['Concentration'] = df['Concentration'].str.replace('[', '', regex=False)
df['Concentration'] = df['Concentration'].str.replace(']', '', regex=False)
df['Concentration'] = df['Concentration'].str.replace("'", '', regex=False)
    
# save to csv
df.to_csv("SUNY_Brockport_Cleaned.csv", index=False)
print("done")
