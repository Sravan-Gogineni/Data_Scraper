import pandas as pd
import os
import json

# Define the target schema and column mapping
TARGET_COLUMNS = [
    'Id', 'ProgramName', 'ProgramCode', 'Status', 'CreatedDate', 'UpdatedDate', 'Level', 'Term',
    'TermCode', 'LiveDate', 'DeadlineDate', 'Resume', 'StatementOfPurpose', 'GreOrGmat',
    'EnglishScore', 'Requirements', 'WritingSample', 'CollegeId', 'IsAnalyticalNotRequired',
    'IsAnalyticalOptional', 'IsDuoLingoRequired', 'IsELSRequired', 'IsGMATOrGreRequired',
    'IsGMATRequired', 'IsGreRequired', 'IsIELTSRequired', 'IsLSATRequired', 'IsMATRequired',
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
    'IsGreRequired': 'IsGreRequired',
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
    financial_data = load_json_data(financial_json_path)
    test_scores_data = load_json_data(test_scores_json_path)
    app_req_data = load_json_data(app_req_json_path)
    extra_fields_data = load_json_data(extra_fields_json_path)
    
    # Convert to DataFrames
    df_fin = pd.DataFrame(financial_data) if financial_data else pd.DataFrame()
    df_test = pd.DataFrame(test_scores_data) if test_scores_data else pd.DataFrame()
    df_app = pd.DataFrame(app_req_data) if app_req_data else pd.DataFrame()
    df_extra = pd.DataFrame(extra_fields_data) if extra_fields_data else pd.DataFrame()
    
    # Merge Key
    merge_key = 'Program name'
    
    # Ensure merge key exists in all DFs before merging
    dfs_to_merge = [df_fin, df_test, df_app, df_extra]
    final_df = df_base.copy()
    
    for i, df in enumerate(dfs_to_merge):
        if not df.empty and merge_key in df.columns:
            # Drop duplicates in join tables if any
            df = df.drop_duplicates(subset=[merge_key])
            # Drop Program Page url from merge tables to avoid suffixes, keep it from base
            if 'Program Page url' in df.columns:
                df = df.drop(columns=['Program Page url'])
            
            final_df = pd.merge(final_df, df, on=merge_key, how='left')
            yield f'{{"status": "progress", "message": "Merged dataset {i+1}..."}}'
        else:
            yield f'{{"status": "progress", "message": "Skipping dataset {i+1} (empty or missing key)"}}'

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
    
    # 6. Save Final CSV
    output_csv_path = os.path.join(output_dir, f'{sanitized_name}_undergraduate_programs_final.csv')
    final_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    
    yield f'{{"status": "complete", "message": "Successfully merged and standardized data", "files": {{"undergrad_final_csv": "{output_csv_path}"}}}}'


if __name__ == "__main__":
    for update in run():
        print(update)
