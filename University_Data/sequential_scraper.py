
import os
import sys
import json

# Add parent directories to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'Institution'))
sys.path.insert(0, os.path.join(current_dir, 'Departments'))
sys.path.insert(0, os.path.join(current_dir, 'Programs'))

# Import extraction functions from existing modules
from Institution.Institution import process_institution_extraction
from Departments.Department import process_department_extraction
from Programs.Programs import process_programs_extraction


def run_sequential_extraction(university_name):
    """
    Run complete sequential extraction for a university.
    
    This function orchestrates the extraction of:
    1. Institution data (all university-level information)
    2. Department data (admissions offices and contacts)
    3. Programs data (graduate and undergraduate programs with full details)
    
    Args:
        university_name (str): The name of the university to extract data for
        
    Yields:
        str: JSON-formatted status updates throughout the extraction process.
             Each update contains:
             - status: 'progress', 'complete', or 'error'
             - message: Human-readable status message
             - files: Dictionary of output files (when available)
             
    Example:
        >>> for update in run_sequential_extraction("SUNY Brockport"):
        ...     data = json.loads(update)
        ...     print(data['message'])
    """
    
    yield json.dumps({
        "status": "progress",
        "message": f"Starting sequential extraction for {university_name}...",
        "phase": "initialization"
    })
    
    # Track all output files across all phases
    all_files = {}
    
    # ========================================================================
    # PHASE 1: INSTITUTION EXTRACTION
    # ========================================================================
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 1/3] Starting Institution Extraction...",
        "phase": "institution"
    })
    
    try:
        for update in process_institution_extraction(university_name):
            try:
                # Parse the update to add phase information
                data = json.loads(update)
                data['phase'] = 'institution'
                
                # Collect files if this is a completion update
                if data.get('status') == 'complete' and 'files' in data:
                    all_files.update(data['files'])
                    # Change to progress so we can continue
                    data['status'] = 'progress'
                    data['message'] = f"[PHASE 1/3] Institution extraction completed. Files saved."
                
                yield json.dumps(data)
            except json.JSONDecodeError:
                # If update is not JSON, wrap it
                yield json.dumps({
                    "status": "progress",
                    "message": f"[PHASE 1/3] {update}",
                    "phase": "institution"
                })
    except Exception as e:
        yield json.dumps({
            "status": "error",
            "message": f"[PHASE 1/3] Error in institution extraction: {str(e)}",
            "phase": "institution",
            "error": str(e)
        })
        # Continue to next phase despite error
    
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 1/3] Institution extraction completed.",
        "phase": "institution"
    })
    
    # ========================================================================
    # PHASE 2: DEPARTMENT EXTRACTION
    # ========================================================================
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 2/3] Starting Department Extraction...",
        "phase": "department"
    })
    
    try:
        for update in process_department_extraction(university_name):
            try:
                # Parse the update to add phase information
                data = json.loads(update)
                data['phase'] = 'department'
                
                # Collect files if this is a completion update
                if data.get('status') == 'complete' and 'files' in data:
                    all_files.update(data['files'])
                    # Change to progress so we can continue
                    data['status'] = 'progress'
                    data['message'] = f"[PHASE 2/3] Department extraction completed. Files saved."
                
                yield json.dumps(data)
            except json.JSONDecodeError:
                # If update is not JSON, wrap it
                yield json.dumps({
                    "status": "progress",
                    "message": f"[PHASE 2/3] {update}",
                    "phase": "department"
                })
    except Exception as e:
        yield json.dumps({
            "status": "error",
            "message": f"[PHASE 2/3] Error in department extraction: {str(e)}",
            "phase": "department",
            "error": str(e)
        })
        # Continue to next phase despite error
    
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 2/3] Department extraction completed.",
        "phase": "department"
    })
    
    # ========================================================================
    # PHASE 3: PROGRAMS EXTRACTION (Graduate + Undergraduate)
    # ========================================================================
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 3/3] Starting Programs Extraction...",
        "phase": "programs"
    })
    
    try:
        # Step 9 runs the automated combined flow:
        # - Step 1 (extract program lists) with retry
        # - Steps 2-5 in parallel (extra fields, test scores, requirements, financial)
        for update in process_programs_extraction(university_name, step=9):
            try:
                # Parse the update to add phase information
                data = json.loads(update)
                data['phase'] = 'programs'
                
                # Collect files if present
                if 'files' in data:
                    all_files.update(data['files'])
                
                # Modify complete status to progress since we want to finalize
                if data.get('status') == 'complete':
                    data['status'] = 'progress'
                    data['message'] = f"[PHASE 3/3] Programs extraction completed."
                
                yield json.dumps(data)
            except json.JSONDecodeError:
                # If update is not JSON, wrap it
                yield json.dumps({
                    "status": "progress",
                    "message": f"[PHASE 3/3] {update}",
                    "phase": "programs"
                })
    except Exception as e:
        yield json.dumps({
            "status": "error",
            "message": f"[PHASE 3/3] Error in programs extraction: {str(e)}",
            "phase": "programs",
            "error": str(e)
        })
    
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 3/3] Programs extraction completed.",
        "phase": "programs"
    })
    
    # ========================================================================
    # FINAL COMPLETION
    # ========================================================================
    yield json.dumps({
        "status": "complete",
        "message": f"Successfully completed all extraction phases for {university_name}!",
        "phase": "complete",
        "files": all_files,
        "summary": {
            "university": university_name,
            "phases_completed": ["institution", "department", "programs"],
            "total_files": len(all_files)
        }
    })


def main():
    """
    Command-line interface for the sequential scraper.
    
    Usage:
        python sequential_scraper.py "University Name"
    """
    if len(sys.argv) < 2:
        print("Usage: python sequential_scraper.py \"University Name\"")
        print("Example: python sequential_scraper.py \"SUNY Brockport\"")
        sys.exit(1)
    
    university_name = sys.argv[1]
    
    print(f"\n{'='*80}")
    print(f"Sequential University Data Extraction")
    print(f"University: {university_name}")
    print(f"{'='*80}\n")
    
    files_collected = {}
    
    for update_json in run_sequential_extraction(university_name):
        try:
            update = json.loads(update_json)
            
            # Print status messages
            status = update.get('status', 'unknown')
            message = update.get('message', '')
            phase = update.get('phase', '')
            
            # Color-code the output
            if status == 'error':
                print(f"❌ ERROR: {message}")
            elif status == 'complete':
                print(f"✅ {message}")
            elif status == 'progress':
                print(f"⏳ {message}")
            else:
                print(f"ℹ️  {message}")
            
            # Collect files
            if 'files' in update:
                files_collected.update(update['files'])
                
        except json.JSONDecodeError:
            print(f"ℹ️  {update_json}")
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"Extraction Complete!")
    print(f"{'='*80}")
    if files_collected:
        print(f"\nOutput files ({len(files_collected)}):")
        for file_type, file_path in files_collected.items():
            print(f"  - {file_type}: {file_path}")
    else:
        print("\nNo output files were generated.")
    print()


if __name__ == "__main__":
    main()
