from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
import sys
import os
import threading
import json

# Add the directory containing the scraping script to sys.path
# Assuming the structure:
# projects/Scraper_UI/web-app/backend/app.py
# projects/Scraper_UI/University_Data/Institution/Institution.py
MAIN_PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
INSTITUTION_DIR = os.path.join(MAIN_PROJECT_DIR, "University_Data", "Institution")
OUTPUT_DIR = os.path.join(INSTITUTION_DIR, "Inst_outputs")
sys.path.append(INSTITUTION_DIR)

try:
    from Institution import process_institution_extraction
except ImportError as e:
    print(f"Error importing Institution script: {e}")
    # We will handle this error gracefully in the route if needed

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/download/<path:filename>")
def download_file(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

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

if __name__ == "__main__":
    app.run(debug=True, port=5000)
