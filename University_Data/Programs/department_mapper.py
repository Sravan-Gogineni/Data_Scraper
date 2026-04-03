import os
import sys
import json
import pandas as pd
import re
import time
from typing import List, Dict

# Add parent directories to path for imports
MAIN_PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
INSTITUTION_DIR = os.path.join(MAIN_PROJECT_DIR, "University_Data", "Institution")
DEPARTMENT_DIR = os.path.join(MAIN_PROJECT_DIR, "University_Data", "Departments")
PROGRAMS_DIR = os.path.join(MAIN_PROJECT_DIR, "University_Data", "Programs")

sys.path.append(INSTITUTION_DIR)
from Institution import GeminiModelWrapper, client

def _extract_json_from_text(text: str) -> dict:
    """Helper to safely extract JSON from LLM responses."""
    text = text.strip()
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
    except Exception:
        return {}

def process_department_mapping(university_name: str, programs_csv: str = None, departments_csv: str = None):
    """
    Logic to map programs to departments for a given university.
    Generator yielding SSE progress updates.
    """
    if not programs_csv or not departments_csv:
        sanitized_name = university_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        
        # 1. Locate Files (Automated mode)
        programs_csv = os.path.join(PROGRAMS_DIR, f"{sanitized_name}_Final.csv")
        departments_csv = os.path.join(DEPARTMENT_DIR, "Dept_outputs", f"{sanitized_name}_departments.csv")
        
        yield json.dumps({"status": "progress", "message": f"Locating files for {university_name}..."})
        
        if not os.path.exists(programs_csv):
            yield json.dumps({"status": "error", "message": f"Final programs CSV not found: {os.path.basename(programs_csv)}"})
            return
            
        if not os.path.exists(departments_csv):
            yield json.dumps({"status": "error", "message": f"Departments CSV not found: {os.path.basename(departments_csv)}"})
            return
    else:
        yield json.dumps({"status": "progress", "message": "Using uploaded files for mapping..."})
        # If university name is not provided clearly, try to infer from filename
        if not university_name or university_name == "Uploaded":
            university_name = os.path.basename(programs_csv).split('_')[0].replace('_', ' ')

    # 2. Load Data
    try:
        programs_df = pd.read_csv(programs_csv)
        departments_df = pd.read_csv(departments_csv)
    except Exception as e:
        yield json.dumps({"status": "error", "message": f"Error loading CSVs: {str(e)}"})
        return

    if 'ProgramName' not in programs_df.columns:
        # Try finding a name column
        name_cols = [c for c in programs_df.columns if 'name' in c.lower() or 'program' in c.lower()]
        if name_cols:
             programs_df.rename(columns={name_cols[0]: 'ProgramName'}, inplace=True)
        else:
             yield json.dumps({"status": "error", "message": "Could not identify Program Name column in programs file."})
             return

    # 3. Prepare Department List
    # Assume department file has a 'DepartmentName' or similar column
    dept_col = next((c for c in departments_df.columns if 'DepartmentName' in c.lower() or 'dept' in c.lower()), departments_df.columns[0])
    department_list = departments_df[dept_col].dropna().unique().tolist()
    
    if not department_list:
        yield json.dumps({"status": "error", "message": "No departments found in departments file."})
        return

    yield json.dumps({"status": "progress", "message": f"Found {len(programs_df)} programs and {len(department_list)} departments."})

    # 4. Perform Mapping using Gemini
    model = GeminiModelWrapper(client, os.getenv("MODEL"))
    
    program_names = programs_df['ProgramName'].tolist()
    mapping_results = {}
    
    batch_size = 20
    total_programs = len(program_names)
    
    for i in range(0, total_programs, batch_size):
        batch = program_names[i:i+batch_size]
        yield json.dumps({"status": "progress", "message": f"Mapping batch {i//batch_size + 1}: {batch[0]}..."})
        
        prompt = (
            f"You are an academic registrar specialized in organizational structures at {university_name}.\n\n"
            f"TASKS:\n"
            f"1. Given the following list of PROGRAMS and a list of official DEPARTMENTS, assign each program to the SINGLE most appropriate department.\n"
            f"2. DECENTRALIZED MAPPING RULES:\n"
            f"   - If a specific college/department admissions office (e.g., 'College of Engineering Admissions', 'Business School Admissions') exists in the list for this program, you MUST prioritize it.\n"
            f"   - Only fall back to 'Undergraduate Admissions', 'Graduate Admissions' if no specific office is found for that program.\n"
            f"3. Return the result ONLY as a JSON object where keys are the Program Names (EXACTLY as listed) and values are the Department Names (EXACTLY from the list).\n\n"
            f"DEPARTMENTS LIST:\n"
            f"{json.dumps(department_list, indent=2)}\n\n"
            f"PROGRAMS TO MAP:\n"
            f"{json.dumps(batch, indent=2)}"
        )
        
        try:
            response = model.generate_content(prompt)
            batch_mapping = _extract_json_from_text(response.text)
            
            # Robust normalization and mapping
            matched_count = 0
            for prog in batch:
                # 1. Try Exact Match
                if prog in batch_mapping:
                    mapping_results[prog] = batch_mapping[prog]
                    matched_count += 1
                else:
                    # 2. Try Normalized Match (Case + Whitespace)
                    normalized_batch = {str(k).strip().lower(): v for k, v in batch_mapping.items()}
                    prog_norm = str(prog).strip().lower()
                    if prog_norm in normalized_batch:
                        mapping_results[prog] = normalized_batch[prog_norm]
                        matched_count += 1
                    else:
                        mapping_results[prog] = "Unassigned"
            
            yield json.dumps({"status": "progress", "message": f"Batch {i//batch_size + 1}: Matched {matched_count}/{len(batch)} programs."})
            
        except Exception as e:
            yield json.dumps({"status": "warning", "message": f"Failed to map batch starting with {batch[0]}: {str(e)}"})
            # Fallback for this batch
            for p in batch:
                mapping_results[p] = "Unassigned"

    # 5. Apply Mapping and Save
    yield json.dumps({"status": "progress", "message": "Finalizing and saving mapping..."})
    
    # Ensure 'Department' column exists and populated correctly
    programs_df['Department'] = programs_df['ProgramName'].map(lambda x: mapping_results.get(x, "Unassigned"))
    
    # Save back to CSV
    try:
        programs_df.to_csv(programs_csv, index=False)
        yield json.dumps({
            "status": "complete", 
            "message": f"Successfully mapped departments for {total_programs} programs.",
            "files": {"final_mapped_csv": programs_csv}
        })
    except Exception as e:
        yield json.dumps({"status": "error", "message": f"Error saving mapped CSV: {str(e)}"})

if __name__ == "__main__":
    # Test logic
    for update in process_department_mapping("Amridge University"):
        print(update)
