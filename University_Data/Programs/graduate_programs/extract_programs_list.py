import pandas as pd
import os
import sys
from dotenv import load_dotenv
import json
import re
import requests

load_dotenv()

# Add parent directories to sys.path to allow importing from Institution
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up 2 levels: University_Data/Programs/graduate_programs -> University_Data
# 1. .../Programs
# 2. .../University_Data
programs_dir = os.path.dirname(current_dir)
university_data_dir = os.path.dirname(programs_dir)
institution_dir = os.path.join(university_data_dir, 'Institution')
sys.path.append(institution_dir)

from Institution import GeminiModelWrapper, client

# Initialize the model using the wrapper (same as check.py)
model = GeminiModelWrapper(client, "gemini-2.5-flash")

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "Grad_prog_outputs")
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

def resolve_redirect(url):
    try:
        # Use HEAD request to follow redirects without downloading content
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception:
        return url

def find_program_url(program_name, university_name):
    prompt = (
        f"Use Google Search to find the OFFICIAL '{program_name}' program page on the {university_name} website. "
        "1. Look at the search results. "
        "2. Identify the official '.edu' URL for this specific program. "
        "3. Do NOT return the 'vertexaisearch' or 'google.com' redirect links. "
        "4. Return ONLY the clean, direct official URL."
    )
    try:
        response = model.generate_content(prompt)
        
        # Check grounding metadata first for real URLs
        real_urls = []
        if response.candidates and response.candidates[0].grounding_metadata:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if chunk.web:
                    real_urls.append(resolve_redirect(chunk.web.uri))
        
        # Filter for .edu links
        edu_urls = [u for u in real_urls if ".edu" in u]
        
        if edu_urls:
            return edu_urls[0]
        elif real_urls:
            return real_urls[0]
        
        # Fallback to text
        text_url = response.text.replace("```", "").strip()
        # Basic clean
        match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text_url)
        if match:
             return match.group(0)
        return None
    except Exception:
        return None

def get_graduate_programs(url, university_name, existing_data=None):
    # Step 1: Extract just the names
    prompt_names = (
        f"Access the following URL: {url}\n"
        "Extract ALL graduate (Master's, PhD, Doctorate, Certificate) program NAMES listed on this page.\n"
        "When Extracting the programs names make sure the names are clear and full. which means not just the name i also want the full name like Master of Arts in Education, Master of Science in Computer Science, etc. not just Education, Computer Science, etc.\n"
        "So, get the full names of the programs.\n"
        "If the university uses 'Areas of Emphasis' or 'Concentrations' for graduate studies, include them.\n"
        "Only Look at the active and latest Programs. Do not include any expired or cancelled programs. or programs from older catalogs."
        "Return a JSON list of STRINGS (just the names).\n"
        "Example: [\"Master of Arts in Education\", \"PhD in Pharmacy\", \"Concentration in Public Administration\", ...]\n"
        "Exclude headers, categories, or navigation items."
    )
    
    program_names = []
    try:
        response = model.generate_content(prompt_names)
        text = response.text.replace("```json", "").replace("```", "").strip()
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != -1:
             program_names = json.loads(text[start:end])
    except Exception as e:
        print(f"Error extracting names: {e}")
        yield f"Error extracting program names: {e}"
        yield [] # Return empty list on error
        return

    # Step 2: Iterate and find URLs
    results = existing_data if existing_data else []
    existing_urls = {p['Program name']: p['Program Page url'] for p in results if p.get('Program Page url') and p['Program Page url'] != url}
    
    total_programs = len(program_names)
    yield f"Found {total_programs} programs. Starting detailed URL search..."
    
    for i, name in enumerate(program_names):
        # Skip if already found with a valid URL
        if name in existing_urls:
            yield f"Skipping (already found) ({i+1}/{total_programs}): {name}"
            continue

        # Yield progress update
        yield f"Finding URL for ({i+1}/{total_programs}): {name}"
        
        found_url = find_program_url(name, university_name)
        program_entry = {
            "Program name": name,
            "Program Page url": found_url if found_url else url
        }
        
        # Save incrementally 
        # (We need to communicate this back to run())
        yield program_entry

def run(university_name_input):
    global university_name, institute_url
    university_name = university_name_input
    
    yield f'{{"status": "progress", "message": "Finding official website for {university_name}..."}}'
    
    sanitized_name = university_name.replace(" ", "_").replace("/", "_")
    
    # Check if we already have the output
    csv_path = os.path.join(output_dir, f'{sanitized_name}_graduate_programs.csv')
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        count = len(pd.read_csv(csv_path))
        yield f'{{"status": "progress", "message": "Graduate programs list for {university_name} already exists. Skipping extraction."}}'
        yield f'{{"status": "complete", "message": "Found {count} graduate programs (using existing list)", "files": {{"grad_csv": "{csv_path}"}}}}'
        return

    prompt = f"What is the official university website for {university_name}?"
    try:
        website_url = model.generate_content(prompt).text.replace("**", "").replace("```", "").strip()
        institute_url = website_url
        yield f'{{"status": "progress", "message": "Website found: {website_url}"}}'
    except Exception as e:
        yield f'{{"status": "error", "message": "Failed to find website: {str(e)}"}}'
        return

    # Dynamic search for grad url
    yield f'{{"status": "progress", "message": "Finding graduate programs page..."}}'
    grad_url_prompt = (
        f"Use Google Search to find the OFFICIAL page listing all Graduate Degrees/Programs at {university_name}. "
        "The page should list specific majors/masters/phd programs. "
        "Return the URL. Do not generate a hypothetical URL."
    )
    try:
        response = model.generate_content(grad_url_prompt)
        
        # Check grounding metadata first for real URLs
        real_urls = []
        if response.candidates and response.candidates[0].grounding_metadata:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if chunk.web:
                    real_urls.append(resolve_redirect(chunk.web.uri))
        
        # Filter for .edu links
        edu_urls = [u for u in real_urls if ".edu" in u]
        
        if edu_urls:
            graduate_program_url = edu_urls[0]
        elif real_urls:
            graduate_program_url = real_urls[0]
        else:
            # Fallback to text
            graduate_program_url = response.text.strip()
            # clean url
            url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', graduate_program_url)
            if url_match:
                graduate_program_url = url_match.group(0)
            
        yield f'{{"status": "progress", "message": "Graduate Page found: {graduate_program_url}"}}'
    except:
        graduate_program_url = website_url # Fallback

    yield f'{{"status": "progress", "message": "Extracting graduate programs list (this may take a while)..."}}'
    
    # Reload existing data just in case
    existing_programs = []
    json_path = os.path.join(output_dir, f'{sanitized_name}_graduate_programs.json')
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_programs = json.load(f)
            yield f'{{"status": "progress", "message": "Resuming: Loaded {len(existing_programs)} already found programs."}}'
        except:
            pass

    def save_progress(programs_list):
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(programs_list, f, indent=4, ensure_ascii=False)
        df = pd.DataFrame(programs_list)
        csv_path = os.path.join(output_dir, f'{sanitized_name}_graduate_programs.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8')

    # Process the generator
    current_programs = existing_programs.copy()
    existing_names = set(p['Program name'] for p in current_programs)
    
    for item in get_graduate_programs(graduate_program_url, university_name, existing_data=current_programs):
        if isinstance(item, str):
            # This is a progress message
            safe_msg = item.replace('"', "'")
            yield f'{{"status": "progress", "message": "{safe_msg}"}}'
        elif isinstance(item, dict):
            # This is a single program entry
            p_name = item.get('Program name')
            if p_name not in existing_names:
                current_programs.append(item)
                existing_names.add(p_name)
                save_progress(current_programs)
            else:
                # If name exists but we want to update URL (unlikely but safe)
                for p in current_programs:
                    if p['Program name'] == p_name:
                        p['Program Page url'] = item['Program Page url']
                        break
                save_progress(current_programs)

    if current_programs:
        yield f'{{"status": "complete", "message": "Found {len(current_programs)} graduate programs", "files": {{"grad_csv": "{os.path.join(output_dir, f"{sanitized_name}_graduate_programs.csv")}"}}}}'
    else:
        yield f'{{"status": "complete", "message": "No graduate programs found", "files": {{}}}}'

