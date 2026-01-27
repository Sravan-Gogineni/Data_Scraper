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
except ImportError as e:
    print(f"Error importing Programs script: {e}")

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

@app.route("/api/download/<path:filename>")
def download_file(filename):
    # Check if file is in Institution output or Department output or Programs output
    
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

if __name__ == "__main__":
    app.run(debug=False, port=5002)
