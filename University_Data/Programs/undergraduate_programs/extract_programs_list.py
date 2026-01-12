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
model = GeminiModelWrapper(client, "gemini-2.5-pro")

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "undergrad_prog_outputs")
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
        "Return a JSON list of STRINGS (just the names).\n"
        "Example: [\"Bachelor of Science in Biology\", \"Associate of Arts\", ...]\n"
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
    results = []
    total_programs = len(program_names)
    yield f"Found {total_programs} programs. Starting detailed URL search..."
    
    for i, name in enumerate(program_names):
        # Yield progress update
        yield f"Finding URL for ({i+1}/{total_programs}): {name}"
        
        found_url = find_program_url(name, university_name)
        if found_url:
            results.append({
                "Program name": name,
                "Program Page url": found_url
            })
        else:
             results.append({
                "Program name": name,
                "Program Page url": url # Fallback to listing page
            })
            
    yield results

def run(university_name_input):
    global university_name, institute_url
    university_name = university_name_input
    
    yield f'{{"status": "progress", "message": "Finding official website for {university_name}..."}}'
    
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
    
    # Process the generator
    undergraduate_programs = []
    for item in get_undergraduate_programs(undergraduate_program_url, university_name):
        if isinstance(item, str):
            # This is a progress message
            safe_msg = item.replace('"', "'")
            yield f'{{"status": "progress", "message": "{safe_msg}"}}'
        elif isinstance(item, list):
            # This is the final result
            undergraduate_programs = item

    if undergraduate_programs:
        # Save the undergraduate programs to JSON file
        json_path = os.path.join(output_dir, 'undergraduate_programs.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(undergraduate_programs, f, indent=4, ensure_ascii=False)
        
        # Save the undergraduate programs to CSV file
        csv_path = os.path.join(output_dir, 'undergraduate_programs.csv')
        df = pd.DataFrame(undergraduate_programs)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        yield f'{{"status": "complete", "message": "Found {len(undergraduate_programs)} undergraduate programs", "files": {{"undergrad_csv": "{csv_path}"}}}}'
    else:
        yield f'{{"status": "complete", "message": "No undergraduate programs found", "files": {{}}}}'

