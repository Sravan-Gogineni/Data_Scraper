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
# Go up 2 levels: University_Data/Programs/undergraduate_programs -> University_Data
# 1. .../Programs
# 2. .../University_Data
programs_dir = os.path.dirname(current_dir)
university_data_dir = os.path.dirname(programs_dir)
institution_dir = os.path.join(university_data_dir, 'Institution')
sys.path.append(institution_dir)

from Institution import GeminiModelWrapper, client

# Initialize the model using the wrapper (consistent with check.py)
model = GeminiModelWrapper(client, "gemini-2.5-flash")

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
        text_url = response.text.replace("```", "").strip()
        # Basic clean
        match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text_url)
        if match:
             return match.group(0)
        return None
    except Exception:
        return None

def get_undergraduate_programs(url, university_name):
    # Step 1: Extract just the names
    prompt_names = (
        f"Access the following URL: {url}\n"
        "Extract ALL undergraduate (Bachelor's, Associate's, Minors) program NAMES listed on this page.\n"
        "IMPORTANT: If the university uses a non-traditional curriculum (e.g., 'Areas of Emphasis', 'Fields of Study', 'Concentrations', 'Pathways' instead of Majors), extract those as the program names.\n"
        "When Extracting the programs names make sure the names are clear and full. which means not just the name i also want the full name like Bachelor of Arts in Education, Bachelor of Science in Computer Science, etc. not just Education, Computer Science, etc.\n"
        "So, get the full names of the programs.\n"
        "Only Look at the active and latest Programs. Do not include any expired or cancelled programs. or programs from older catalogs."
        "Return a JSON list of STRINGS (just the names).\n"
        "Example: [\"Bachelor of Science in Biology\", \"Associate of Arts\", \"Emphasis in Political Economy\", ...]\n"
        "Exclude headers, categories, or navigation items."
    )
    
    program_names = []
    try:
        # yield f'{{"status": "progress", "message": "DEBUG: Prompting for names with URL: {url}"}}'
        response = model.generate_content(prompt_names)
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
            
            if not program_names:
                yield f'{{"status": "warning", "message": "DEBUG: Could not find JSON list brackets [] or bulleted items in response."}}'
            else:
                 yield f'{{"status": "progress", "message": "DEBUG: Successfully extracted {len(program_names)} programs using fallback parser."}}'
            
    except Exception as e:
        yield f'{{"status": "error", "message": "Error extracting names: {str(e)}"}}'
        yield [] # Return empty list on error
        return

    # Step 2: Iterate and find URLs
    results = [] # Keep for final complete yield
    total_programs = len(program_names)
    yield f"Found {total_programs} programs. Starting detailed URL search..."
    
    for i, name in enumerate(program_names):
        # Yield progress update
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
    
    yield f'{{"status": "progress", "message": "Finding official website for {university_name}..."}}'
    
    # Define output files
    json_path = os.path.join(output_dir, 'undergraduate_programs.json')
    csv_path = os.path.join(output_dir, 'undergraduate_programs.csv')

    # Load existing data to handle resuming/appending
    existing_programs = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_programs = json.load(f)
        except:
            pass
            
    # Check if we already have a significant number of programs and if the user wants to skip
    # (Optional logic, but for now we just append/overwrite if duplicates)
    
    # Helper to save progress
    def save_progress(programs_list):
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(programs_list, f, indent=4, ensure_ascii=False)
        df = pd.DataFrame(programs_list)
        df.to_csv(csv_path, index=False, encoding='utf-8')

    
    prompt = f"What is the official university website for {university_name}?"
    try:
        website_url = model.generate_content(prompt).text.replace("**", "").replace("```", "").strip()
        institute_url = website_url
        yield f'{{"status": "progress", "message": "Website found: {website_url}"}}'
    except Exception as e:
        yield f'{{"status": "error", "message": "Failed to find website: {str(e)}"}}'
        return

    # Dynamic search for undergrad url
    yield f'{{"status": "progress", "message": "Finding undergraduate programs page..."}}'
    undergrad_url_prompt = (
        f"Use Google Search to find the OFFICIAL page listing all Undergraduate Degrees/Programs (Majors) at {university_name}. "
        "Only Look at the active and latest Programs page urls. Do not include any expired or cancelled programs pages urls. or programs page urls from older catalogs."
        "The page should list specific bachelors/associate degrees. "
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
            undergraduate_program_url = response.text.strip()
            # clean url
            url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', undergraduate_program_url)
            if url_match:
                undergraduate_program_url = url_match.group(0)
            
        yield f'{{"status": "progress", "message": "Undergraduate Page found: {undergraduate_program_url}"}}'
    except:
        undergraduate_program_url = website_url # Fallback

    yield f'{{"status": "progress", "message": "Extracting undergraduate programs list (this may take a while)..."}}'
    
    # Define output files
    json_path = os.path.join(output_dir, 'undergraduate_programs.json')
    csv_path = os.path.join(output_dir, 'undergraduate_programs.csv')

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
    
    count = 0 
    for item in get_undergraduate_programs(undergraduate_program_url, university_name):
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
                count += 1
                # Optional: Yield a granular progress update for the save
                # yield f'{{"status": "progress", "message": "Saved: {p_name}"}}'
    
    undergraduate_programs = current_programs

    if undergraduate_programs:
        # Final save is handled by loop, but we ensure output message is correct
        yield f'{{"status": "complete", "message": "Found {len(undergraduate_programs)} undergraduate programs", "files": {{"undergrad_csv": "{csv_path}"}}}}'
    else:
        yield f'{{"status": "complete", "message": "No undergraduate programs found", "files": {{}}}}'

