import pandas as pd
import os
import sys
from dotenv import load_dotenv
import json
import re
import requests
from Institution import GeminiModelWrapper, client


load_dotenv()

# Add parent directories to sys.path to allow importing from Institution
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up 2 levels: University_Data/Programs/undergraduate_programs -> University_Data
# 1. .../Programs
# 2. .../University_Data
programs_dir = os.path.dirname(current_dir)
university_data_dir = os.path.dirname(programs_dir)
institution_dir = os.path.join(university_data_dir, 'Institution')
sys.path.append(institution_dir)


# Initialize the model using the wrapper (consistent with check.py)
model = GeminiModelWrapper(client, "gemini-2.0-flash")

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "Undergrad_prog_outputs")
# Create directory if it doesn't exist
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
        if not response.text:
             return None
        text_url = response.text.replace("```", "").strip()
        # Basic clean
        match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text_url)
        if match:
             return match.group(0)
        return None
    except Exception:
        return None

def get_undergraduate_programs(url, university_name, existing_data=None):
    # Step 1: Extract just the names
    prompt_names = (
        f"I am providing you with the URL of the official undergraduate programs listing for {university_name}: {url}\n\n"
        "Your task is to identify and extract the names of ALL undergraduate programs (Majors, Bachelors, Associates, and Minors) listed on that page.\n"
        "1. Carefully identify every program name.\n"
        "2. Include the full degree designation if available (e.g., 'Bachelor of Science in Biology' instead of just 'Biology').\n"
        "3. Only include active programs.\n"
        "4. If the university uses 'Concentrations', 'Areas of Study', or 'Fields of Study', treat those as the program names.\n\n"
        "RETURN ONLY A JSON LIST OF STRINGS.\n"
        "Example format: [\"Bachelor of Science in Computer Science\", \"Associate of Applied Science in Nursing\"]\n\n"
        "DO NOT explain your limitations or mention your search tools. Just return the JSON list based on your knowledge of this page's structure or by searching for its content."
    )
    
    program_names = []
    max_attempts = 2
    for attempt_num in range(1, max_attempts + 1):
        try:
            # yield f'{{"status": "progress", "message": "DEBUG: Prompting for names with URL: {url}"}}'
            response = model.generate_content(prompt_names)
            if not response.text:
                if attempt_num < max_attempts: continue
                yield f'{{"status": "error", "message": "Error extracting names: Model returned empty response (text is None)"}}'
                yield []
                return
                
            text = response.text.replace("```json", "").replace("```", "").strip()
            
            # Escape quotes for JSON safety in the message
            safe_text = text.replace('"', "'").replace('\n', ' ')
            yield f'{{"status": "progress", "message": "DEBUG: Raw response text: {safe_text}"}}'
            
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != -1:
                 program_names = json.loads(text[start:end])
            else:
                # Fallback: Try to parse bulleted list
                print("DEBUG: JSON not found, attempting fallback parsing for bulleted list.")
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    # Match lines starting with *, -, or numbers 1.
                    if line.startswith(('*', '-', '•')) or (len(line) > 0 and line[0].isdigit() and line[1] == '.'):
                        # Clean up the line
                        clean_name = re.sub(r'^[\*\-•\d\.]+\s*', '', line).strip()
                        if clean_name:
                            program_names.append(clean_name)
                
            if program_names:
                break # Success
            elif attempt_num < max_attempts:
                yield f'{{"status": "warning", "message": "Attempt {attempt_num} failed to parse program names. Retrying with refined focus..."}}'
                # Slightly refine prompt for retry
                prompt_names += "\n\nCRITICAL: You must return a list of at least 5-10 programs. Do not return an empty list."
                
        except Exception as e:
            if attempt_num < max_attempts: continue
            yield f'{{"status": "error", "message": "Error extracting names: {str(e)}"}}'
            yield [] # Return empty list on error
            return

    if not program_names:
        yield f'{{"status": "warning", "message": "DEBUG: Could not find any program names after {max_attempts} attempts."}}'

    # Step 2: Iterate and find URLs
    results = existing_data if existing_data else []
    existing_urls = {p['Program name']: p['Program Page url'] for p in results if p.get('Program Page url') and p['Program Page url'] != url}
    existing_names = set(p['Program name'] for p in results)

    total_programs = len(program_names)
    yield f"Found {total_programs} programs. Starting detailed URL search..."
    
    for i, name in enumerate(program_names):
        # Skip if already found with a valid URL
        if name in existing_urls:
            yield f"Skipping (already found) ({i+1}/{total_programs}): {name}"
            continue

        # Yield progress update
        if name in existing_names:
             yield f"Skipping existing program: {name}"
             continue

        yield f"Finding URL for ({i+1}/{total_programs}): {name}"
        
        found_url = find_program_url(name, university_name)
        program_entry = {
            "Program name": name,
            "Program Page url": found_url if found_url else url
        }
        
        # Yield the individual result
        yield program_entry
            
def run(university_name_input):
    global university_name, institute_url
    university_name = university_name_input
    
    sanitized_name = university_name.replace(" ", "_").replace("/", "_")
    
    # Define output files
    json_path = os.path.join(output_dir, f'{sanitized_name}_undergraduate_programs.json')
    csv_path = os.path.join(output_dir, f'{sanitized_name}_undergraduate_programs.csv')

    # Early check for completed list
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        count = len(pd.read_csv(csv_path))
        yield f'{{"status": "progress", "message": "Undergraduate programs list for {university_name} already exists. Skipping extraction."}}'
        yield f'{{"status": "complete", "message": "Found {count} undergraduate programs (using existing list)", "files": {{"undergrad_csv": "{csv_path}"}}}}'
        return

    # Load existing data to handle resuming/appending
    existing_programs = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_programs = json.load(f)
            yield f'{{"status": "progress", "message": "Resuming: Loaded {len(existing_programs)} already found programs."}}'
        except:
            pass
    
    # Helper to save progress
    def save_progress(programs_list):
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(programs_list, f, indent=4, ensure_ascii=False)
        df = pd.DataFrame(programs_list)
        df.to_csv(csv_path, index=False, encoding='utf-8')

    
    prompt = f"What is the official university website for {university_name}?"
    try:
        resp = model.generate_content(prompt)
        if resp.text:
            website_url = resp.text.replace("**", "").replace("```", "").strip()
            institute_url = website_url
            yield f'{{"status": "progress", "message": "Website found: {website_url}"}}'
        else:
             raise Exception("Model returned empty text")
    except Exception as e:
        yield f'{{"status": "error", "message": "Failed to find website: {str(e)}"}}'
        return

    # Dynamic search for undergrad url
    yield f'{{"status": "progress", "message": "Finding undergraduate programs page..."}}'
    undergrad_url_prompt = (
        f"Use Google Search to find the OFFICIAL page listing all Undergraduate Degrees/Programs (Majors) at {university_name}. "
        "Only Look at the active and latest Programs page urls. Do not include any expired or cancelled programs pages urls. or programs page urls from older catalogs."
        "The page should list specific bachelors/associate degrees. "
        "the page should belong to the official university domain."
        "Return the URL. Do not generate a hypothetical URL."
    )
    try:
        response = model.generate_content(undergrad_url_prompt)
        
        # Check grounding metadata first for real URLs
        real_urls = []
        if response.candidates and response.candidates[0].grounding_metadata:
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if chunk.web:
                    real_urls.append(resolve_redirect(chunk.web.uri))
        
        # Filter for .edu links
        edu_urls = [u for u in real_urls if ".edu" in u]
        
        if edu_urls:
            undergraduate_program_url = edu_urls[0]
        elif real_urls:
            undergraduate_program_url = real_urls[0]
        else:
             # Fallback to text
            if response.text:
                undergraduate_program_url = response.text.strip()
            else:
                 undergraduate_program_url = ""
            # clean url
            url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', undergraduate_program_url)
            if url_match:
                undergraduate_program_url = url_match.group(0)
            
        yield f'{{"status": "progress", "message": "Undergraduate Page found: {undergraduate_program_url}"}}'
    except:
        undergraduate_program_url = website_url # Fallback

    yield f'{{"status": "progress", "message": "Extracting undergraduate programs list (this may take a while)..."}}'
    
    # Define output files
    sanitized_name = university_name.replace(" ", "_").replace("/", "_")
    json_path = os.path.join(output_dir, f'{sanitized_name}_undergraduate_programs.json')
    csv_path = os.path.join(output_dir, f'{sanitized_name}_undergraduate_programs.csv')

    # Load existing data to handle resuming/appending
    existing_programs = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_programs = json.load(f)
        except:
            pass
            
    # Process the generator
    current_programs = existing_programs.copy()
    existing_names = set(p['Program name'] for p in current_programs)
    
    for item in get_undergraduate_programs(undergraduate_program_url, university_name, existing_data=current_programs):
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
                # yield f'{{"status": "progress", "message": "Saved: {p_name}"}}'
        
    
    undergraduate_programs = current_programs

    if undergraduate_programs:
        # Final save is handled by loop, but we ensure output message is correct
        yield f'{{"status": "complete", "message": "Found {len(undergraduate_programs)} undergraduate programs", "files": {{"undergrad_csv": "{csv_path}"}}}}'
    else:
        yield f'{{"status": "complete", "message": "No undergraduate programs found", "files": {{}}}}'

