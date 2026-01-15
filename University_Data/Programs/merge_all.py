import pandas as pd
import os

def run():
    yield f'{{"status": "progress", "message": "Starting final merge of Graduate and Undergraduate programs..."}}'
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Paths to the final CSVs
    grad_csv_path = os.path.join(script_dir, 'graduate_programs', 'Grad_prog_outputs', 'graduate_programs_final.csv')
    undergrad_csv_path = os.path.join(script_dir, 'undergraduate_programs', 'undergrad_prog_outputs', 'undergraduate_programs_final.csv')
    # Get University Name from Institution CSV
    inst_outputs_dir = os.path.join(script_dir, '..', 'Institution', 'Inst_outputs')
    university_name = "University_Final" # Default fallback
    
    if os.path.exists(inst_outputs_dir):
        inst_files = [f for f in os.listdir(inst_outputs_dir) if f.endswith('_Institution.csv')]
        if inst_files:
            # Taking the first one found, assuming one university being processed at a time
            inst_filename = inst_files[0]
            university_name = inst_filename.replace('_Institution.csv', '')
            yield f'{{"status": "progress", "message": "Identified university: {university_name}"}}'
        else:
             yield f'{{"status": "warning", "message": "No Institution CSV found to extract name in {inst_outputs_dir}. Using default."}}'
    else:
         yield f'{{"status": "warning", "message": "Institution outputs directory not found at {inst_outputs_dir}. Using default name."}}'

    output_csv_path = os.path.join(script_dir, f'{university_name}_Final.csv')
    
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
    
    # Save
    final_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    yield f'{{"status": "complete", "message": "Successfully merged {len(final_df)} programs", "files": {{"final_csv": "{output_csv_path}"}}}}'
