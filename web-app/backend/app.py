import sys
import os
import threading
import json
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context

# Add the directory containing the scraping script to sys.path
# Assuming the structure:
# projects/Scraper_UI/web-app/backend/app.py
# projects/Scraper_UI/University_Data/Institution/Institution.py
MAIN_PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
INSTITUTION_DIR = os.path.join(MAIN_PROJECT_DIR, "University_Data", "Institution")
DEPARTMENT_DIR = os.path.join(MAIN_PROJECT_DIR, "University_Data", "Departments")
PROGRAMS_DIR = os.path.join(MAIN_PROJECT_DIR, "University_Data", "Programs")
PROGRAMS_GRAD_OUTPUT_DIR = os.path.join(PROGRAMS_DIR, "graduate_programs", "Grad_prog_outputs")
PROGRAMS_UNDERGRAD_OUTPUT_DIR = os.path.join(PROGRAMS_DIR, "undergraduate_programs", "Undergrad_prog_outputs")

# Also need to define Inst and Dept output dirs here for the download route
INST_OUTPUT_DIR = os.path.join(INSTITUTION_DIR, "Inst_outputs")
DEPT_OUTPUT_DIR = os.path.join(DEPARTMENT_DIR, "Dept_outputs")

sys.path.append(INSTITUTION_DIR)
sys.path.append(DEPARTMENT_DIR)
sys.path.append(PROGRAMS_DIR)

from Institution import process_institution_extraction
from Department import process_department_extraction

try:
    from Programs import process_programs_extraction
    from department_mapper import process_department_mapping
except ImportError as e:
    _programs_import_error = str(e)
    print(f"Error importing Programs script: {_programs_import_error}")
    def process_programs_extraction(university_name, step, **kwargs):
        """Stub used when the Programs module is unavailable."""
        import json as _j
        yield _j.dumps({"status": "error", "message": f"Programs extraction module could not be loaded: {_programs_import_error}"})

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/department.html")
def department():
    return send_from_directory(app.static_folder, "department.html")

@app.route("/programs.html")
def programs():
    return send_from_directory(app.static_folder, "programs.html")

@app.route("/all_extraction.html")
def all_extraction():
    return send_from_directory(app.static_folder, "all_extraction.html")

@app.route("/api/download/<path:filename>")
def download_file(filename):
    # Check if file is in Institution output or Department output or Programs output
    
    # Try temp_uploads FIRST (for files modified during "uploaded mapping")
    temp_uploads_dir = os.path.join(os.path.dirname(__file__), "temp_uploads")
    if os.path.exists(os.path.join(temp_uploads_dir, filename)):
         return send_from_directory(temp_uploads_dir, filename, as_attachment=True)
         
    # Try Institution
    if os.path.exists(os.path.join(INST_OUTPUT_DIR, filename)):
         return send_from_directory(INST_OUTPUT_DIR, filename, as_attachment=True)
    
    # Try Department
    if os.path.exists(os.path.join(DEPT_OUTPUT_DIR, filename)):
         return send_from_directory(DEPT_OUTPUT_DIR, filename, as_attachment=True)

    # Try Programs (Root) - Deprecated but keeping for legacy
    if os.path.exists(os.path.join(PROGRAMS_DIR, filename)):
         return send_from_directory(PROGRAMS_DIR, filename, as_attachment=True)

    # Try Programs (Grad)
    if os.path.exists(os.path.join(PROGRAMS_GRAD_OUTPUT_DIR, filename)):
         return send_from_directory(PROGRAMS_GRAD_OUTPUT_DIR, filename, as_attachment=True)

    # Try Programs (Undergrad)
    if os.path.exists(os.path.join(PROGRAMS_UNDERGRAD_OUTPUT_DIR, filename)):
         return send_from_directory(PROGRAMS_UNDERGRAD_OUTPUT_DIR, filename, as_attachment=True)
         
    return jsonify({"error": "File not found"}), 404

@app.route("/api/extract", methods=["POST"])
def extract_data():
    data = request.json
    university_name = data.get("university_name")
    
    if not university_name:
        return jsonify({"error": "University name is required"}), 400
    
    # Optional parameters
    undergraduate_tuition_fee_urls = data.get("undergraduate_tuition_fee_urls")
    graduate_tuition_fee_urls = data.get("graduate_tuition_fee_urls")
    undergraduate_financial_aid_urls = data.get("undergraduate_financial_aid_urls")
    graduate_financial_aid_urls = data.get("graduate_financial_aid_urls")
    common_financial_aid_urls = data.get("common_financial_aid_urls")
    common_tuition_fee_urls = data.get("common_tuition_fee_urls")

    def generate():
        try:
            # Run extraction - now returns a generator
            generator = process_institution_extraction(
                university_name,
                undergraduate_tuition_fee_urls=undergraduate_tuition_fee_urls,
                graduate_tuition_fee_urls=graduate_tuition_fee_urls,
                undergraduate_financial_aid_urls=undergraduate_financial_aid_urls,
                graduate_financial_aid_urls=graduate_financial_aid_urls,
                common_financial_aid_urls=common_financial_aid_urls,
                common_tuition_fee_urls=common_tuition_fee_urls
            )
            
            for update in generator:
                # Assuming update is a JSON string already from the generator
                # Check if it's the final result or a progress update
                try:
                    update_obj = json.loads(update)
                    if update_obj.get("status") == "complete":
                        # Modify result_files to return relative filenames for download
                        download_links = {}
                        for key, path in update_obj["files"].items():
                            filename = os.path.basename(path)
                            download_links[key] = f"/api/download/{filename}"
                        update_obj["files"] = download_links
                        yield f"data: {json.dumps(update_obj)}\n\n"
                    else:
                         yield f"data: {update}\n\n"
                except json.JSONDecodeError:
                    # Fallback if raw string
                     yield f"data: {json.dumps({'status': 'progress', 'message': update})}\n\n"
                     
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/api/extract/department", methods=["POST"])
def extract_department_data():
    data = request.json
    university_name = data.get("university_name")
    
    if not university_name:
        return jsonify({"error": "University name is required"}), 400

    def generate():
        try:
            # Run extraction
            generator = process_department_extraction(university_name)
            
            for update in generator:
                try:
                    update_obj = json.loads(update)
                    if update_obj.get("status") == "complete":
                        # Modify result_files to return relative filenames for download
                        download_links = {}
                        for key, path in update_obj["files"].items():
                            filename = os.path.basename(path)
                            # We can just use the download route we set up, which checks both dirs
                            download_links[key] = f"/api/download/{filename}"
                        update_obj["files"] = download_links
                        yield f"data: {json.dumps(update_obj)}\n\n"
                    else:
                         yield f"data: {update}\n\n"
                except json.JSONDecodeError:
                     yield f"data: {json.dumps({'status': 'progress', 'message': update})}\n\n"
                     
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/api/extract/programs", methods=["POST"])
def extract_programs_data():
    data = request.json
    university_name = data.get("university_name")
    step = data.get("step")
    
    if not university_name:
        return jsonify({"error": "Universities name is required"}), 400
    if not step:
         return jsonify({"error": "Step number is required"}), 400

    def generate():
        try:
            # Run extraction
            generator = process_programs_extraction(university_name, step)
            
            for update in generator:
                try:
                    update_obj = json.loads(update)
                    
                    # Transform file paths in ANY update that contains them
                    if "files" in update_obj and update_obj["files"]:
                        download_links = {}
                        for key, path in update_obj["files"].items():
                            filename = os.path.basename(path)
                            download_links[key] = f"/api/download/{filename}"
                        update_obj["files"] = download_links
                    
                    yield f"data: {json.dumps(update_obj)}\n\n"
                except json.JSONDecodeError:
                     yield f"data: {json.dumps({'status': 'progress', 'message': update})}\n\n"
                     
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/api/extract/all", methods=["POST"])
def extract_all_data():
    """Sequential extraction: Institution -> Department -> Programs"""
    data = request.json
    university_name = data.get("university_name")
    
    if not university_name:
        return jsonify({"error": "University name is required"}), 400

    def generate():
        all_files = {}
        try:
            # Prepare paths for checking existing files
            sanitized_name = university_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            inst_csv_path = f"/Users/sravan/projects/Scraper_UI/University_Data/Institution/Inst_outputs/{sanitized_name}_Institution.csv"
            dept_csv_path = f"/Users/sravan/projects/Scraper_UI/University_Data/Departments/Dept_outputs/{sanitized_name}_departments.csv"
            
            # Step 1: Institution (check if exists first)
            yield f"data: {json.dumps({'status': 'progress', 'message': '--- Step 1: Institution Extraction ---'})}\n\n"
            
            if os.path.exists(inst_csv_path):
                yield f"data: {json.dumps({'status': 'progress', 'message': '[Institution] CSV already exists - skipping extraction'})}\n\n"
                # Add existing file to results
                filename = os.path.basename(inst_csv_path)
                all_files[f"inst_csv"] = f"/api/download/{filename}"
            else:
                inst_generator = process_institution_extraction(university_name)
                for update in inst_generator:
                    try:
                        update_obj = json.loads(update)
                        if update_obj.get("status") == "complete":
                            yield f"data: {json.dumps({'status': 'progress', 'message': '[Institution] Complete'})}\n\n"
                            if "files" in update_obj:
                                for key, path in update_obj["files"].items():
                                    filename = os.path.basename(path)
                                    all_files[f"inst_{key}"] = f"/api/download/{filename}"
                        else:
                            yield f"data: {json.dumps({'status': 'progress', 'message': f"[Institution] {update_obj.get('message', '')}"})}\n\n"
                    except json.JSONDecodeError:
                        yield f"data: {json.dumps({'status': 'progress', 'message': f'[Institution] {update}'})}\n\n"
            
            # Step 2: Department (with retry)
            yield f"data: {json.dumps({'status': 'progress', 'message': '--- Step 2: Department Extraction ---'})}\n\n"
            
            departments_found = False
            retry_count = 0
            max_retries = 10
            
            while not departments_found and retry_count < max_retries:
                # Check if file exists first
                if os.path.exists(dept_csv_path):
                    yield f"data: {json.dumps({'status': 'progress', 'message': '[Department] CSV already exists - skipping extraction'})}\n\n"
                    departments_found = True
                    # Add existing file to results
                    filename = os.path.basename(dept_csv_path)
                    all_files[f"dept_csv"] = f"/api/download/{filename}"
                    break
                if retry_count > 0:
                    yield f"data: {json.dumps({'status': 'warning', 'message': f'Retry attempt {retry_count} for departments...'})}\n\n"
                    import time
                    time.sleep(5)
                
                dept_generator = process_department_extraction(university_name)
                dept_files_found = False
                
                for update in dept_generator:
                    try:
                        update_obj = json.loads(update)
                        if update_obj.get("status") == "complete":
                            if "files" in update_obj and len(update_obj["files"]) > 0:
                                departments_found = True
                                dept_files_found = True
                                yield f"data: {json.dumps({'status': 'progress', 'message': '[Department] Complete - Departments found'})}\n\n"
                                for key, path in update_obj["files"].items():
                                    filename = os.path.basename(path)
                                    all_files[f"dept_{key}"] = f"/api/download/{filename}"
                            else:
                                yield f"data: {json.dumps({'status': 'warning', 'message': '[Department] No departments found'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'status': 'progress', 'message': f"[Department] {update_obj.get('message', '')}"})}\n\n"
                    except json.JSONDecodeError:
                        yield f"data: {json.dumps({'status': 'progress', 'message': f'[Department] {update}'})}\n\n"
                
                if not dept_files_found:
                    retry_count += 1
                    if retry_count < max_retries:
                        yield f"data: {json.dumps({'status': 'warning', 'message': f'No departments found. Retrying in 5 seconds... (Attempt {retry_count}/{max_retries})'})}\n\n"
            
            if not departments_found:
                yield f"data: {json.dumps({'status': 'warning', 'message': 'Max retries reached for department extraction. Proceeding to programs...'})}\n\n"
            
            # Step 3: Programs (Full Extraction + Merge)
            yield f"data: {json.dumps({'status': 'progress', 'message': '--- Step 3: Programs Full Extraction ---'})}\n\n"
            
            # First run step 9 (full automation: extract + enrich)
            yield f"data: {json.dumps({'status': 'progress', 'message': '[Programs] Running full automation (extraction + enrichment)...'})}\n\n"
            prog_generator_step9 = process_programs_extraction(university_name, 9)
            
            for update in prog_generator_step9:
                try:
                    update_obj = json.loads(update)
                    if update_obj.get("status") == "complete":
                        yield f"data: {json.dumps({'status': 'progress', 'message': '[Programs] Full automation completed. Starting merge...'})}\n\n"
                        break
                    else:
                        yield f"data: {json.dumps({'status': 'progress', 'message': f"[Programs] {update_obj.get('message', '')}"})}\n\n"
                except json.JSONDecodeError:
                    yield f"data: {json.dumps({'status': 'progress', 'message': f'[Programs] {update}'})}\n\n"
            
            # Then run step 6 (standardize + merge)
            yield f"data: {json.dumps({'status': 'progress', 'message': '[Programs] Running standardization and merge...'})}\n\n"
            prog_generator_step6 = process_programs_extraction(university_name, 6)
            programs_final_file = None
            
            for update in prog_generator_step6:
                try:
                    update_obj = json.loads(update)
                    if update_obj.get("status") == "complete":
                        yield f"data: {json.dumps({'status': 'progress', 'message': '[Programs] Merge completed successfully'})}\n\n"
                        if "files" in update_obj:
                            # Look for the final merged CSV
                            for key, path in update_obj["files"].items():
                                if "_Final.csv" in path or "final_csv" in key:
                                    programs_final_file = path
                                    break
                        break
                    else:
                        yield f"data: {json.dumps({'status': 'progress', 'message': f"[Programs] {update_obj.get('message', '')}"})}\n\n"
                except json.JSONDecodeError:
                    yield f"data: {json.dumps({'status': 'progress', 'message': f'[Programs] {update}'})}\n\n"
            
            # Build final output with only 3 essential files
            final_output_files = {}
            
            # 1. Institution file (look for CSV)
            for key, path in all_files.items():
                if key.startswith("inst_") and "csv" in key.lower():
                    final_output_files["institution_data"] = path
                    break
            
            # 2. Department file (look for CSV)
            for key, path in all_files.items():
                if key.startswith("dept_") and "csv" in key.lower():
                    final_output_files["departments_data"] = path
                    break
            
            # 3. Programs final merged file
            if programs_final_file:
                filename = os.path.basename(programs_final_file)
                final_output_files["programs_final"] = f"/api/download/{filename}"
            
            # Final completion
            yield f"data: {json.dumps({'status': 'complete', 'message': 'All extractions completed successfully', 'files': final_output_files})}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/api/map_departments", methods=["POST"])
def map_departments():
    # Check if files are uploaded
    if 'programs_file' in request.files and 'departments_file' in request.files:
        programs_file = request.files['programs_file']
        departments_file = request.files['departments_file']
        university_name = request.form.get("university_name", "Uploaded")
        
        # Save files temporarily
        upload_dir = os.path.join(os.path.dirname(__file__), "temp_uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        from werkzeug.utils import secure_filename
        prog_path = os.path.join(upload_dir, secure_filename(programs_file.filename))
        dept_path = os.path.join(upload_dir, secure_filename(departments_file.filename))
        
        programs_file.save(prog_path)
        departments_file.save(dept_path)
        
        args = (university_name, prog_path, dept_path)
    else:
        # Fallback to university name if no files (original behavior)
        data = request.json or {}
        university_name = data.get("university_name")
        if not university_name:
             return jsonify({"error": "Either file uploads or University name is required"}), 400
        args = (university_name,)

    def generate():
        try:
            # Run department mapping with either university name or explicit files
            generator = process_department_mapping(*args)
            
            for update in generator:
                try:
                    update_obj = json.loads(update)
                    if update_obj.get("status") == "complete":
                        # Modify result_files to return relative filenames for download
                        download_links = {}
                        for key, path in update_obj["files"].items():
                            filename = os.path.basename(path)
                            download_links[key] = f"/api/download/{filename}"
                        update_obj["files"] = download_links
                        yield f"data: {json.dumps(update_obj)}\n\n"
                    else:
                         yield f"data: {update}\n\n"
                except json.JSONDecodeError:
                     yield f"data: {json.dumps({'status': 'progress', 'message': update})}\n\n"
                     
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/api/extract/batch", methods=["POST"])
def extract_batch():
    """Accept a CSV or XLSX file with a 'university name' column and extract each one sequentially."""
    if 'batch_file' not in request.files:
        return jsonify({"error": "No file uploaded. Send a CSV or XLSX with a 'university name' column."}), 400

    batch_file = request.files['batch_file']
    if not batch_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    upload_dir = os.path.join(os.path.dirname(__file__), "temp_uploads")
    os.makedirs(upload_dir, exist_ok=True)

    from werkzeug.utils import secure_filename
    import pandas as pd

    saved_path = os.path.join(upload_dir, secure_filename(batch_file.filename))
    batch_file.save(saved_path)

    try:
        if saved_path.endswith(".xlsx"):
            df = pd.read_excel(saved_path)
        else:
            df = pd.read_csv(saved_path)
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 400

    # Find the university name column (case-insensitive)
    col_map = {c.strip().lower(): c for c in df.columns}
    uni_col = col_map.get("university name") or col_map.get("university_name")
    if not uni_col:
        return jsonify({"error": "File must contain a column named 'university name'"}), 400

    universities = [str(v).strip() for v in df[uni_col].dropna() if str(v).strip()]
    if not universities:
        return jsonify({"error": "No university names found in the file"}), 400
    if len(universities) > 10:
        universities = universities[:10]

    def generate():
        total = len(universities)
        yield f"data: {json.dumps({'status': 'batch_start', 'message': f'Starting batch extraction for {total} universities', 'total': total})}\n\n"

        for idx, university_name in enumerate(universities, start=1):
            yield f"data: {json.dumps({'status': 'university_start', 'message': f'[{idx}/{total}] Starting: {university_name}', 'index': idx, 'total': total, 'university': university_name})}\n\n"

            all_files = {}
            try:
                sanitized_name = university_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                inst_csv_path = os.path.join(INST_OUTPUT_DIR, f"{sanitized_name}_Institution.csv")
                dept_csv_path = os.path.join(DEPT_OUTPUT_DIR, f"{sanitized_name}_departments.csv")

                # Step 1: Institution
                yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] --- Step 1: Institution Extraction ---'})}\n\n"

                if os.path.exists(inst_csv_path):
                    yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Institution] CSV already exists - skipping'})}\n\n"
                    all_files["inst_csv"] = f"/api/download/{os.path.basename(inst_csv_path)}"
                else:
                    for update in process_institution_extraction(university_name):
                        try:
                            update_obj = json.loads(update)
                            if update_obj.get("status") == "complete":
                                yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Institution] Complete'})}\n\n"
                                for key, path in update_obj.get("files", {}).items():
                                    all_files[f"inst_{key}"] = f"/api/download/{os.path.basename(path)}"
                            else:
                                msg = update_obj.get("message", "")
                                yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Institution] {msg}'})}\n\n"
                        except json.JSONDecodeError:
                            yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Institution] {update}'})}\n\n"

                # Step 2: Department (with retry)
                yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] --- Step 2: Department Extraction ---'})}\n\n"

                departments_found = False
                retry_count = 0
                max_retries = 10

                while not departments_found and retry_count < max_retries:
                    if os.path.exists(dept_csv_path):
                        yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Department] CSV already exists - skipping'})}\n\n"
                        departments_found = True
                        all_files["dept_csv"] = f"/api/download/{os.path.basename(dept_csv_path)}"
                        break
                    if retry_count > 0:
                        yield f"data: {json.dumps({'status': 'warning', 'message': f'[{idx}/{total}] Retry attempt {retry_count} for departments...'})}\n\n"
                        import time
                        time.sleep(5)

                    dept_files_found = False
                    for update in process_department_extraction(university_name):
                        try:
                            update_obj = json.loads(update)
                            if update_obj.get("status") == "complete":
                                if update_obj.get("files"):
                                    departments_found = True
                                    dept_files_found = True
                                    yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Department] Complete'})}\n\n"
                                    for key, path in update_obj["files"].items():
                                        all_files[f"dept_{key}"] = f"/api/download/{os.path.basename(path)}"
                                else:
                                    yield f"data: {json.dumps({'status': 'warning', 'message': f'[{idx}/{total}] [Department] No departments found'})}\n\n"
                            else:
                                msg = update_obj.get("message", "")
                                yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Department] {msg}'})}\n\n"
                        except json.JSONDecodeError:
                            yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Department] {update}'})}\n\n"

                    if not dept_files_found:
                        retry_count += 1
                        if retry_count < max_retries:
                            yield f"data: {json.dumps({'status': 'warning', 'message': f'[{idx}/{total}] No departments found. Retrying... ({retry_count}/{max_retries})'})}\n\n"

                if not departments_found:
                    yield f"data: {json.dumps({'status': 'warning', 'message': f'[{idx}/{total}] Max retries reached for departments. Proceeding...'})}\n\n"

                # Step 3: Programs
                yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] --- Step 3: Programs Full Extraction ---'})}\n\n"

                for update in process_programs_extraction(university_name, 9):
                    try:
                        update_obj = json.loads(update)
                        if update_obj.get("status") == "complete":
                            yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Programs] Full automation completed. Starting merge...'})}\n\n"
                            break
                        else:
                            msg = update_obj.get("message", "")
                            yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Programs] {msg}'})}\n\n"
                    except json.JSONDecodeError:
                        yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Programs] {update}'})}\n\n"

                programs_final_file = None
                for update in process_programs_extraction(university_name, 6):
                    try:
                        update_obj = json.loads(update)
                        if update_obj.get("status") == "complete":
                            yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Programs] Merge completed'})}\n\n"
                            for key, path in update_obj.get("files", {}).items():
                                if "_Final.csv" in path or "final_csv" in key:
                                    programs_final_file = path
                                    break
                            break
                        else:
                            msg = update_obj.get("message", "")
                            yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Programs] {msg}'})}\n\n"
                    except json.JSONDecodeError:
                        yield f"data: {json.dumps({'status': 'progress', 'message': f'[{idx}/{total}] [Programs] {update}'})}\n\n"

                # Collect final files
                final_files = {}
                for key, path in all_files.items():
                    if key.startswith("inst_") and "csv" in key.lower():
                        final_files["institution_data"] = path
                        break
                for key, path in all_files.items():
                    if key.startswith("dept_") and "csv" in key.lower():
                        final_files["departments_data"] = path
                        break
                if programs_final_file:
                    final_files["programs_final"] = f"/api/download/{os.path.basename(programs_final_file)}"

                yield f"data: {json.dumps({'status': 'university_complete', 'message': f'[{idx}/{total}] Completed: {university_name}', 'index': idx, 'total': total, 'university': university_name, 'files': final_files})}\n\n"

            except Exception as e:
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'status': 'university_error', 'message': f'[{idx}/{total}] Error for {university_name}: {str(e)}', 'index': idx, 'total': total, 'university': university_name})}\n\n"

        yield f"data: {json.dumps({'status': 'batch_complete', 'message': f'Batch extraction finished for all {total} universities', 'total': total})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


if __name__ == "__main__":
    app.run(debug=False, port=5002)
