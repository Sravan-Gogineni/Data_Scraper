import pandas as pd
import os

def run(university_name=None):
    yield f'{{"status": "progress", "message": "Starting final merge of Graduate and Undergraduate programs..."}}'
    
    if not university_name:
        yield f'{{"status": "error", "message": "University name not provided for final merge."}}'
        return

    sanitized_name = university_name.replace(" ", "_").replace("/", "_")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Paths to the final CSVs
    grad_csv_path = os.path.join(script_dir, 'graduate_programs', 'Grad_prog_outputs', f'{sanitized_name}_graduate_programs_final.csv')
    undergrad_csv_path = os.path.join(script_dir, 'undergraduate_programs', 'Undergrad_prog_outputs', f'{sanitized_name}_undergraduate_programs_final.csv')
    
    output_csv_path = os.path.join(script_dir, f'{sanitized_name}_Final.csv')
    
    dfs = []
    
    # Load Graduate Programs
    if os.path.exists(grad_csv_path):
        df_grad = pd.read_csv(grad_csv_path)
        yield f'{{"status": "progress", "message": "Loaded {len(df_grad)} graduate programs"}}'
        dfs.append(df_grad)
    else:
        yield f'{{"status": "progress", "message": "Graduate programs file not found at {grad_csv_path}"}}'
        
    # Load Undergraduate Programs
    if os.path.exists(undergrad_csv_path):
        df_undergrad = pd.read_csv(undergrad_csv_path)
        yield f'{{"status": "progress", "message": "Loaded {len(df_undergrad)} undergraduate programs"}}'
        dfs.append(df_undergrad)
    else:
        yield f'{{"status": "progress", "message": "Undergraduate programs file not found at {undergrad_csv_path}"}}'
        
    if not dfs:
        yield f'{{"status": "error", "message": "No data found to merge."}}'
        return



    # Merge
    yield f'{{"status": "progress", "message": "Merging datasets..."}}'
    final_df = pd.concat(dfs, ignore_index=True)
    final_df['QsWorldRanking'] = ""
    final_df['CollegeApplicationFee'] = ""
    final_df['IsNewlyLaunched'] = "FALSE"
    final_df['IsImportVerified'] = "FALSE"
    final_df['Is_Recommendation_Sponser'] = "FALSE"
    final_df['IsRecommendationSystemOpted'] = "FALSE"
    final_df['Term']="Fall 2026"
    final_df['LiveDate']=""
    final_df['DeadlineDate']=""
    final_df['PreviousYearAcceptanceRates']=""
    final_df['IsStemProgram']= final_df['IsStemProgram'].fillna(False)
    final_df['IsStemProgram']= final_df['IsStemProgram'].astype(bool)
    final_df['IsACTRequired']= final_df['IsACTRequired'].fillna(False)
    final_df['IsACTRequired']= final_df['IsACTRequired'].astype(bool)
    final_df['IsSATRequired']= final_df['IsSATRequired'].fillna(False)
    final_df['IsSATRequired']= final_df['IsSATRequired'].astype(bool)
    final_df['IsAnalyticalNotRequired'] = final_df['IsAnalyticalNotRequired'].fillna(True)
    final_df['IsAnalyticalNotRequired'] = final_df['IsAnalyticalNotRequired'].astype(bool)
    final_df['IsAnalyticalOptional'] = final_df['IsAnalyticalOptional'].fillna(True)
    final_df['IsAnalyticalOptional'] = final_df['IsAnalyticalOptional'].astype(bool)

    final_df['ProgramName'] = final_df['ProgramName'].apply(standardize_program_name)

    
    ###############
    final_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    yield f'{{"status": "complete", "message": "Successfully merged {len(final_df)} programs", "files": {{"final_csv": "{output_csv_path}"}}}}'


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
        "AOS": "Associate of Science in",
    }
    
    for suffix, prefix in mappings.items():
        if name_str.endswith(suffix):
            # Remove the suffix (e.g. " MS") and prepend the prefix
            # Original: "Program MS" -> "Program" -> "Master of Science in Program"
            clean_name = name_str[:-len(suffix)]
            return f"{prefix} {clean_name}"
            
    return name_str