import pandas as pd
import os

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Paths
    all_programs_path = os.path.join(script_dir, 'Middle_Tennessee_State_University_Final(in).csv')
    departments_path = "/Users/sravan19/projects/Scraper_UI/University_Data/Departments/Dept_outputs/Middle_Tennessee_State_University_departments.csv"
    
    if not os.path.exists(all_programs_path):
        print(f"Error: Programs file not found at {all_programs_path}")
        return
    if not os.path.exists(departments_path):
        print(f"Error: Departments file not found at {departments_path}")
        return

    try:
        all_programs_df = pd.read_csv(all_programs_path, encoding='utf-8')
    except UnicodeDecodeError:
        print(f"Warning: UTF-8 encoding failed for {all_programs_path}, trying latin1...")
        all_programs_df = pd.read_csv(all_programs_path, encoding='latin1')

    try:
        departments_df = pd.read_csv(departments_path, encoding='utf-8')
    except UnicodeDecodeError:
        print(f"Warning: UTF-8 encoding failed for {departments_path}, trying latin1...")
        departments_df = pd.read_csv(departments_path, encoding='latin1')
    
    print(f"Loaded {len(all_programs_df)} programs and {len(departments_df)} departments.")

    # 1. Identify the target Undergraduate and Graduate offices from the extracted departments
    dept_names = departments_df['DepartmentName'].unique()
    
    # Findlay specific department names
    undergrad_dept_name = next((d for d in dept_names if 'Office of Admissions' in d or 'Undergraduate' in d), None)
    grad_dept_name = next((d for d in dept_names if 'Graduate' in d), None)
    
    print(f"Identified Undergraduate Office: {undergrad_dept_name}")
    print(f"Identified Graduate Office: {grad_dept_name}")
    
    if not undergrad_dept_name or not grad_dept_name:
        print("Error: Could not find both Undergraduate and Graduate admissions offices in dictionary.")
        # fallback based on what we saw in the file if exact match fails, but the above should catch it
        if not undergrad_dept_name: undergrad_dept_name = "Office of Admissions"
        if not grad_dept_name: grad_dept_name = "Graduate Admissions"
        print(f"Using fallbacks: UG='{undergrad_dept_name}', Grad='{grad_dept_name}'")

    # 2. Define the mapping function based STRICTLY on Level
    def get_admission_dept(row):
        # Normalize level
        level = str(row.get('Level', '')).strip().lower()
        
        # Keywords based on user request and common variations
        undergrad_keywords = [
            'undergraduate', 'bachelor', 'associate', 'minor', 
            'ba', 'bs', 'bsc', 'b.eng', 'bba', 'bfa', 'bsn'
        ]
        
        grad_keywords = [
            'master', 'ma', 'mfa', 'mba', 'graduate certificate'
        ]
        
        doctoral_keywords = [
            'phd', 'doctoral', 'doctorate', 'edd', 'dpt', 'pharmd', 'otd'
        ]
        
        # Check for Undergraduate
        if any(k in level for k in undergrad_keywords):
            return undergrad_dept_name
            
        # Check for Graduate
        if any(k in level for k in grad_keywords):
            return grad_dept_name
            
        # Check for Doctoral
        if any(k in level for k in doctoral_keywords):
            return grad_dept_name
        
        # Default fallback (usually Grad for unclassified post-secondary, but check content)
        # If it's completely unknown, maybe default to Grad or check if it matches "certificate" broadly
        return grad_dept_name

    # 3. Apply mapping
    all_programs_df['Department'] = all_programs_df.apply(get_admission_dept, axis=1)

    # 4. Validation
    print("\nMapping Summary:")
    counts = all_programs_df['Department'].value_counts()
    print(counts)
    
    # 5. Save
    all_programs_df.to_csv(all_programs_path, index=False)
    print(f"\nSuccessfully updated 'Department' in {all_programs_path}")

if __name__ == '__main__':
    main()
