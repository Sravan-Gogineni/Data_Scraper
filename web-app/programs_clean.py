from os import name
import pandas as pd

df = pd.read_csv("/Users/sravan/projects/Scraper_UI/Post_University_Final.csv")

# level
df['QsWorldRanking'] = ""

def get_level(program_name):
    name = str(program_name).lower()
    
    # Explicit overrides for common tricky ones
    if "mba" in name:
        return "Graduate"
        
    if "minor" in name and ("certificate" in name or "certification" in name):
        return "Undergraduate-Certificate"
    
    if "advanced certificate" in name or "graduate certificate" in name:
        return "Graduate-Certificate"
        
    levels_map = {
        "Doctoral": ["phd", "edd", "dpt", "pharmd", "otd", "doctor"],
        "Graduate-Certificate": ["graduate certificate", "advanced certificate"],
        "Associate": ["associate", "aa", "as", "aas"],
        "Graduate": ["master", "masters", "ma", "m.s", "ms", "mfa", "mba"],
        "Undergraduate": ["bachelor", "bachelors", "baccalaureate", "ba", "bs", "minor", "bsc", "bfa"]
    }

    # Re-doing the map logic to be order sensitive
    # 1. Doctoral
    if any(k in name for k in levels_map["Doctoral"]):
        return "Doctoral"
        
    # 2. Graduate Certificate (specific checking already done above, but safe to keep)
    if any(k in name for k in levels_map["Graduate-Certificate"]):
        return "Graduate-Certificate"

    # 3. Graduate (Masters)
    if any(k in name for k in levels_map["Graduate"]):
        return "Graduate"
        
    # 4. Undergraduate
    if any(k in name for k in levels_map["Undergraduate"]):
        if "post-baccalaureate" in name or "post baccalaureate" in name:
             return "Graduate-Certificate"
        return "Undergraduate"
        
    # 5. Associates
    if any(k in name for k in levels_map["Associate"]):
        return "Associate"
    
    # Fallback for generic 'Certificate' if not caught above
    if "certificate" in name:
        return "Graduate-Certificate" 
        
    return "Graduate"

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
    }
    
    for suffix, prefix in mappings.items():
        if name_str.endswith(suffix):
            # Remove the suffix (e.g. " MS") and prepend the prefix
            # Original: "Program MS" -> "Program" -> "Master of Science in Program"
            clean_name = name_str[:-len(suffix)]
            return f"{prefix} {clean_name}"
            
    return name_str

df['ProgramName'] = df['ProgramName'].apply(standardize_program_name)


df['Level'] = df['ProgramName'].apply(get_level)

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
df.to_csv("Post_University_Cleaned.csv", index=False)
print("done")
