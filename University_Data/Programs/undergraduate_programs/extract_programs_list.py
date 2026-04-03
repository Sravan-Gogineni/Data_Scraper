import pandas as pd
import os
import sys
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

# Add parent directories to sys.path to allow importing from Institution
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up 2 levels: University_Data/Programs/undergraduate_programs -> University_Data
# 1. .../Programs
# 2. .../University_Data
programs_dir = os.path.dirname(current_dir)
university_data_dir = os.path.dirname(programs_dir)
institution_dir = os.path.join(university_data_dir, 'Institution')
if institution_dir not in sys.path:
    sys.path.append(institution_dir)

# Import robust utils and Gemini client
programs_dir_v2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if programs_dir_v2 not in sys.path:
    sys.path.append(programs_dir_v2)

from Institution import client
from robust_extraction_utils import GeminiModelWrapper, get_base_domain, fetch_links_with_pagination, _extract_json_from_text
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch

# Initialize the model using the wrapper
model = GeminiModelWrapper(client, os.getenv("MODEL"))


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



## NEW O(1) BATCHED EXTRACTION:
def get_undergraduate_programs(url, university_name, existing_data=None):
    import os
    
    base_domain = get_base_domain(url)
    if not base_domain:
         yield f'{{"status": "error", "message": "Failed to extract base domain from {url}"}}'
         return
         
    yield f'{{"status": "progress", "message": "STAGE 1: Executing Search-Based Discovery for {university_name}..."}}'
    
    yield f'{{"status": "progress", "message": "STAGE 1: Discovering official Undergraduate Programs Portal..."}}'
    portal_discovery_prompt = (
        f"Find the official URL of the main webpage that lists all undergraduate programs at {university_name}. "
        f"This is usually titled 'Undergraduate Programs', 'Academics', or 'Degree Programs'. "
        f"Return ONLY a JSON object with one key 'portal_url'."
    )
    portal_url = url # Default to original if discovery fails
    try:
        portal_resp = client.models.generate_content(
            model=os.getenv("MODEL"),
            contents=portal_discovery_prompt,
            config=GenerateContentConfig(tools=[Tool(google_search=GoogleSearch())])
        )
        portal_data = _extract_json_from_text(portal_resp.text)
        if portal_data.get("portal_url"):
            portal_url = portal_data["portal_url"]
            yield f'{{"status": "progress", "message": "Found Programs Portal: {portal_url}"}}'
    except Exception as e:
        yield f'{{"status": "warning", "message": "Portal discovery failed, using fallback: {url}"}}'

    # --- STAGE 1: SEARCH ---
    prompt = (
        f"You are a strict data extractor compiling a master list of academic programs.\n\n"
        f"Task:\n"
        f"Use the Google Search tool to deeply search the official university website. "
        f"Extract EVERY SINGLE active undergraduate (Bachelor's, Major, Minor, Associate) program name AND its specific official URL for {university_name}.\n\n"
        f"CRITICAL DOMAIN RULE: You MUST use the search operator `site:{base_domain}`. DO NOT return URLs from Wikipedia, U.S. News, Peterson's, or any non-official 3rd party site.\n"
        f"CRITICAL NAME RULE: STANDARDIZE THE NAME. If you see 'Biology, BS', output 'Bachelor of Science in Biology'. If you see 'BA in History', output 'Bachelor of Arts in History'. DO NOT output abbreviations.\n"
        f"CRITICAL URL RULE: Use the EXACT portal URL discovered as the 'Program Page url' for every entry. DO NOT return individual program page URLs.\n"
        f"CRITICAL URL FORMAT: Set 'Program Page url' to exactly {portal_url} for all records. NO EXCEPTIONS.\n"
        f"CRITICAL NO CITATIONS RULE: Strip out any formatting citations like [1], [12], or [2, 4].\n\n"
        f"Return ONLY a clean JSON list of objects containing 'Program name' and 'Program Page url'.\n"
    )
    
    found_search_count = 0
    try:
        response = client.models.generate_content(
            model=os.getenv("MODEL"),
            contents=prompt,
            config=GenerateContentConfig(
                 temperature=0.1, 
                 tools=[Tool(google_search=GoogleSearch())]
            )
        )
        program_data = _extract_json_from_text(response.text)
        
        if isinstance(program_data, list) and len(program_data) > 0:
            found_search_count = len(program_data)
            yield f'{{"status": "progress", "message": "Stage 1 Search found {found_search_count} potential programs. Moving to Stage 2 for exhaustive coverage..."}}'
            for prog in program_data:
                if "Program name" in prog and "Program Page url" in prog:
                    yield prog
        else:
            yield f'{{"status": "warning", "message": "Stage 1 Search yielded 0 programs. Proceeding to Stage 2 Crawl..."}}'
            
    except Exception as e:
        yield f'{{"status": "warning", "message": "Stage 1 Search failed: {e}. Proceeding to Stage 2 Crawl..."}}'

    # --- STAGE 2: CRAWL FALLBACK (Deterministic) ---
    # We ALWAYS run Stage 2 now for 'Deep Discovery'
    yield f'{{"status": "progress", "message": "STAGE 2: Executing Direct Crawl on {portal_url} for exhaustive list..."}}'
    
    # We look for keywords that imply undergraduate level
    undergrad_keywords = ['undergraduate', 'bachelor', 'major', 'minor', 'associate', 'degree', 'program', 'curriculum']
    
    # Run the crawler natively from the portal URL (increased to 20 pages for deep discovery)
    crawled_links = fetch_links_with_pagination(portal_url, base_domain, filter_keywords=undergrad_keywords, max_pages=20)
    
    if not crawled_links:
         yield f'{{"status": "warning", "message": "Stage 2 Crawl found 0 programs."}}'
         return

    yield f'{{"status": "progress", "message": "Crawled {len(crawled_links)} potential program links. Refining and standardizing..."}}'
    
    # Batch process the links through Gemini to filter out non-programs and standardize names
    chunk_size = 30
    for i in range(0, len(crawled_links), chunk_size):
        chunk = crawled_links[i:i + chunk_size]
        links_text = "\n".join([f"- Text: {link['text']} | URL: {link['url']}" for link in chunk])
        
        refine_prompt = (
            f"You are a program list refiner for {university_name}.\n"
            f"I have crawled the following potential program links from the university portal:\n\n"
            f"{links_text}\n\n"
            f"Instructions:\n"
            f"1. Filter this list. Keep ONLY actual undergraduate-level academic programs (Bachelor's, Majors, Minors, Associates).\n"
            f"2. REMOVE links that are just 'Apply', 'Contact Us', 'About', 'Faculty', etc.\n"
            f"3. STANDARDIZE the names. Convert abbreviations to full names (e.g., 'BS' -> 'Bachelor of Science').\n"
            f"4. Return ONLY a JSON list of objects: [{{\"Program name\": \"...\", \"Program Page url\": \"{portal_url}\"}}]\n"
            f"   IMPORTANT: For the 'Program Page url', ALWAYS use strictly {portal_url} for all programs.\n"
            f"5. If no links in this chunk are programs, return an empty list []."
        )
        
        try:
            refine_resp = model.generate_content(refine_prompt)
            refined_data = _extract_json_from_text(refine_resp.text)
            if isinstance(refined_data, list):
                for prog in refined_data:
                    if "Program name" in prog and "Program Page url" in prog:
                        yield prog
        except Exception as e:
            yield f'{{"status": "warning", "message": "Failed to refine crawl chunk {i//chunk_size + 1}: {e}"}}'

            
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
        # MINIMUM COUNT SANITY CHECK:
        # If the count is < 20, it's likely a partial result from previous sessions.
        # We only skip if the count is > 20 to ensure deep discovery for 'at any cost' capture.
        if count > 20:
             yield f'{{"status": "progress", "message": "Undergraduate programs list for {university_name} already exists with {count} programs. Skipping extraction."}}'
             yield f'{{"status": "complete", "message": "Found {count} undergraduate programs (using existing list)", "files": {{"undergrad_csv": "{csv_path}"}}}}'
             return
        else:
             yield f'{{"status": "progress", "message": "Existing list found but count is suspiciously low ({count}). Forcing Deep Discovery re-extraction..."}}'

    # Load existing data to handle resuming/appending
    existing_programs = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_programs = json.load(f)
            yield f'{{"status": "progress", "message": "Resuming: Loaded {len(existing_programs)} already found programs."}}'
        except Exception:
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
                undergraduate_program_url = url_match.group(0).replace('**', '')
            
    except Exception:
        undergraduate_program_url = website_url # Fallback

    from robust_extraction_utils import verify_legit_url
    undergraduate_program_url = verify_legit_url(undergraduate_program_url, website_url)

    yield f'{{"status": "progress", "message": "Undergraduate Page Verified: {undergraduate_program_url}"}}'

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
        except Exception:
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

