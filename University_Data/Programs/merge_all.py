import pandas as pd
import os

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Paths to the final CSVs
    grad_csv_path = os.path.join(script_dir, 'graduate_programs', 'Grad_prog_outputs', 'graduate_programs_final.csv')
    undergrad_csv_path = os.path.join(script_dir, 'undergraduate_programs', 'undergrad_prog_outputs', 'undergraduate_programs_final.csv')
    
    output_csv_path = os.path.join(script_dir, 'Quinnipiac_University_Final.csv')
    
    dfs = []
    
    # Load Graduate Programs
    if os.path.exists(grad_csv_path):
        df_grad = pd.read_csv(grad_csv_path)
        print(f"Loaded {len(df_grad)} graduate programs.")
        dfs.append(df_grad)
    else:
        print(f"Warning: Graduate programs file not found at {grad_csv_path}")
        
    # Load Undergraduate Programs
    if os.path.exists(undergrad_csv_path):
        df_undergrad = pd.read_csv(undergrad_csv_path)
        print(f"Loaded {len(df_undergrad)} undergraduate programs.")
        dfs.append(df_undergrad)
    else:
        print(f"Warning: Undergraduate programs file not found at {undergrad_csv_path}")
        
    if not dfs:
        print("No data found to merge.")
        return

    # Merge
    final_df = pd.concat(dfs, ignore_index=True)
    
    # Save
    final_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    print(f"Successfully saved merged dataset to {output_csv_path}")
    print(f"Total programs: {len(final_df)}")

if __name__ == "__main__":
    main()
