import pandas as pd
import os
import json

# Define the target schema and column mapping
TARGET_COLUMNS = [
    'Id', 'ProgramName', 'ProgramCode', 'Status', 'CreatedDate', 'UpdatedDate', 'Level', 'Term',
    'TermCode', 'LiveDate', 'DeadlineDate', 'Resume', 'StatementOfPurpose', 'GreOrGmat',
    'EnglishScore', 'Requirements', 'WritingSample', 'CollegeId', 'IsAnalyticalNotRequired',
    'IsAnalyticalOptional', 'IsDuoLingoRequired', 'IsELSRequired', 'IsGMATOrGreRequired',
    'IsGMATRequired', 'IsGRERequired', 'IsIELTSRequired', 'IsLSATRequired', 'IsMATRequired',
    'IsMCATRequired', 'IsPTERequired', 'IsTOEFLIBRequired', 'IsTOEFLPBTRequired',
    'IsEnglishNotRequired', 'IsEnglishOptional', 'AcademicYear', 'AlternateProgram',
    'ApplicationType', 'Department', 'Fees', 'IsAvailable', 'ProgramType',
    'AdmissionDepartmentId', 'CreatedBy', 'UpdatedBy', 'Concentration', 'Description',
    'OtherConcentrations', 'ProgramWebsiteURL', 'Accredidation', 'AverageScholarshipAmount',
    'CostPerCredit', 'IsRecommendationSystemOpted', 'IsStemProgram', 'MaxFails', 'MaxGPA',
    'MinGPA', 'PreviousYearAcceptanceRates', 'QsWorldRanking', 'TotalAccepetedApplications',
    'TotalCredits', 'TotalDeniedApplications', 'TotalI20sIssued', 'TotalScholarshipsAwarded',
    'TotalSubmittedApplications', 'TotalVisasSecured', 'UsNewsRanking', 'CollegeApplicationFee',
    'IsCollegePaying', 'MEContractNegotiatedFee', 'MyGradAppFee', 'ProgramCategory',
    'IsCollegeApplicationFree', 'IsCouponAllowed', 'IsACTRequired', 'IsSATRequired',
    'SftpDestinationId', 'MinimumACTScore', 'MinimumDuoLingoScore', 'MinimumELSScore',
    'MinimumGMATScore', 'MinimumGreScore', 'MinimumIELTSScore', 'MinimumMATScore',
    'MinimumMCATScore', 'MinimumPTEScore', 'MinimumSATScore', 'MinimumTOEFLScore',
    'MLModelName', 'MinimumAnalyticalScore', 'MinimumEnglishScore', 'MinimumExperience',
    'MinimumSopRating', 'WeightAnalytical', 'WeightEnglish', 'WeightExperience', 'WeightGPA',
    'WeightSop', 'ScholarshipAmount', 'ScholarshipPercentage', 'ScholarshipType',
    'IsNewlyLaunched', 'BatchId', 'IsImported', 'IsImportVerified', 'Is_Recommendation_Sponser',
    'AnalyticalScore', 'MinimumLSATScore'
]

COLUMN_MAPPING = {
    # Base
    'Program name': 'ProgramName',
    'Level': 'Level',
    'Program Page url': 'ProgramWebsiteURL',
    
    # Financial
    'QsWorldRanking': 'QsWorldRanking',
    'School': 'Department', 
    'MaxFails': 'MaxFails',
    'MaxGPA': 'MaxGPA',
    'MinGPA': 'MinGPA',
    'PreviousYearAcceptanceRates': 'PreviousYearAcceptanceRates',
    'Term': 'Term',
    'LiveDate': 'LiveDate',
    'DeadlineDate': 'DeadlineDate',
    'Fees': 'CollegeApplicationFee', # Mapping extracted 'Fees' (which are usually app fees) to CollegeApplicationFee
    'Tuition fee': 'Fees',           # Mapping extracted 'Tuition fee' -> Fees column
    'AverageScholarshipAmount': 'AverageScholarshipAmount',
    'CostPerCredit': 'CostPerCredit',
    'ScholarshipAmount': 'ScholarshipAmount',
    'ScholarshipPercentage': 'ScholarshipPercentage',
    'ScholarshipType': 'ScholarshipType',
    
    # Test Scores
    'GreOrGmat': 'GreOrGmat',
    'EnglishScore': 'EnglishScore',
    'IsDuoLingoRequired': 'IsDuoLingoRequired',
    'IsELSRequired': 'IsELSRequired',
    'IsGMATOrGreRequired': 'IsGMATOrGreRequired',
    'IsGMATRequired': 'IsGMATRequired',
    'IsGRERequired': 'IsGRERequired',
    'IsIELTSRequired': 'IsIELTSRequired',
    'IsLSATRequired': 'IsLSATRequired',
    'IsMATRequired': 'IsMATRequired',
    'IsMCATRequired': 'IsMCATRequired',
    'IsPTERequired': 'IsPTERequired',
    'IsTOEFLIBRequired': 'IsTOEFLIBRequired',
    'IsTOEFLPBTRequired': 'IsTOEFLPBTRequired',
    'IsEnglishNotRequired': 'IsEnglishNotRequired',
    'IsEnglishOptional': 'IsEnglishOptional',
    'MinimumDuoLingoScore': 'MinimumDuoLingoScore',
    'MinimumELSScore': 'MinimumELSScore',
    'MinimumGMATScore': 'MinimumGMATScore',
    'MinimumGreScore': 'MinimumGreScore',
    'MinimumIELTSScore': 'MinimumIELTSScore',
    'MinimumMATScore': 'MinimumMATScore',
    'MinimumMCATScore': 'MinimumMCATScore',
    'MinimumPTEScore': 'MinimumPTEScore',
    'MinimumTOEFLScore': 'MinimumTOEFLScore',
    'MinimumLSATScore': 'MinimumLSATScore',
    
    # Application Requirements
    'Resume': 'Resume',
    'StatementOfPurpose': 'StatementOfPurpose',
    'Requirements': 'Requirements',
    'WritingSample': 'WritingSample',
    'IsAnalyticalNotRequired': 'IsAnalyticalNotRequired',
    'IsAnalyticalOptional': 'IsAnalyticalOptional',
    'IsRecommendationSystemOpted': 'IsRecommendationSystemOpted',
    'IsStemProgram': 'IsStemProgram',
    'IsACTRequired': 'IsACTRequired',
    'IsSATRequired': 'IsSATRequired',
    'MinimumACTScore': 'MinimumACTScore',
    'MinimumSATScore': 'MinimumSATScore',
    
    # Extra Fields
    'Concentration name': 'Concentration',
    'description': 'Description',
    'ProgramCategory': 'ProgramCategory',
    'Accreditation status': 'Accredidation'
}

def load_json_data(filepath):
    if not os.path.exists(filepath):
        print(f"Warning: File not found: {filepath}")
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def run(university_name=None):
    yield f'{{"status": "progress", "message": "Starting data merge and standardization..."}}'
    
    if not university_name:
        yield f'{{"status": "error", "message": "University name not provided for merge step."}}'
        return

    sanitized_name = university_name.replace(" ", "_").replace("/", "_")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "Undergrad_prog_outputs")
    os.makedirs(output_dir, exist_ok=True)
    
    # File paths
    base_csv_path = os.path.join(output_dir, f'{sanitized_name}_undergraduate_programs.csv')
    financial_json_path = os.path.join(output_dir, f'{sanitized_name}_program_details_financial.json')
    test_scores_json_path = os.path.join(output_dir, f'{sanitized_name}_test_scores_requirements.json')
    app_req_json_path = os.path.join(output_dir, f'{sanitized_name}_application_requirements.json')
    extra_fields_json_path = os.path.join(output_dir, f'{sanitized_name}_extra_fields_data.json')
    
    # 1. Load Base Data
    if not os.path.exists(base_csv_path):
        yield f'{{"status": "complete", "message": "Base CSV not found at {base_csv_path}. Skipping merge step.", "files": {{}}}}'
        return
        
    df_base = pd.read_csv(base_csv_path)
    yield f'{{"status": "progress", "message": "Loaded {len(df_base)} programs from base CSV"}}'
    
    # 2. Load and Prepare Merge Data
    master_json_path = os.path.join(output_dir, f'{sanitized_name}_master_data.json')
    merge_key = 'Program name'
    final_df = df_base.copy()

    if os.path.exists(master_json_path):
        yield f'{{"status": "progress", "message": "Merging fields from master_data.json..."}}'
        master_data = load_json_data(master_json_path)
        df_master = pd.DataFrame(master_data) if master_data else pd.DataFrame()
        
        if not df_master.empty and merge_key in df_master.columns:
            # Drop duplicates and duplicate URL column if present
            df_master = df_master.drop_duplicates(subset=[merge_key])
            if 'Program Page url' in df_master.columns:
                df_master = df_master.drop(columns=['Program Page url'])
            
            final_df = pd.merge(final_df, df_master, on=merge_key, how='left')
            yield f'{{"status": "progress", "message": "Merged master dataset successfully."}}'
        else:
            yield f'{{"status": "warning", "message": "Master data is empty or missing key."}}'
    else:
        yield f'{{"status": "warning", "message": "No master data found at {os.path.basename(master_json_path)}. Final CSV will be incomplete."}}'

    # 3. Rename Columns
    # Rename columns that exist in the mapping
    final_df = final_df.rename(columns=COLUMN_MAPPING)
    
    # 4. Add Missing Columns
    for col in TARGET_COLUMNS:
        if col not in final_df.columns:
            final_df[col] = ""  # Initialize with empty string
            
    # 5. Select and Reorder Columns
    # Only keep columns that are in TARGET_COLUMNS
    final_df = final_df[TARGET_COLUMNS]
    
    # Define keywords for undergraduate levels
    # Using lowercase for case-insensitive matching
    levels_map = {
        "Undergraduate-Certificate": ["certificate", "certification", "cert"],
        "Associate": ["associate", "aa", "as", "aas"],
         
    }

    # Determine level logic:
    # Default to 'Undergraduate' (which covers general Bachelors if not explicitly matched, or we can default to Bachelor)
    # The user asked for specific logic for certs, but we should make it robust for undergrad.
    final_df['Level'] = final_df['ProgramName'].apply(lambda x: next((k for k, v in levels_map.items() if any(keyword in str(x).lower() for keyword in v)), 'Undergraduate'))


    # 6. Save Final CSV
    output_csv_path = os.path.join(output_dir, f'{sanitized_name}_undergraduate_programs_final.csv')
    final_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    
    yield f'{{"status": "complete", "message": "Successfully merged and standardized data", "files": {{"undergrad_final_csv": "{output_csv_path}"}}}}'


if __name__ == "__main__":
    for update in run():
        print(update)
