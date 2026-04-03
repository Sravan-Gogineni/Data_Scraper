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

from Institution import GeminiModelWrapper as OldWrapper, client

# Import robust utils we added
import sys
programs_dir_v2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if programs_dir_v2 not in sys.path:
    sys.path.append(programs_dir_v2)
from robust_extraction_utils import GeminiModelWrapper # Use the new retry-enabled wrapper

# Initialize the model using the wrapper
model = GeminiModelWrapper(client, os.getenv("MODEL"))


# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "Grad_prog_outputs")
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

from robust_extraction_utils import get_base_domain, fetch_links_with_pagination, _extract_json_from_text
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch

## NEW O(1) BATCHED EXTRACTION:
def get_graduate_programs(url, university_name, existing_data=None):
    import os
    
    base_domain = get_base_domain(url)
    if not base_domain:
         yield f'{{"status": "error", "message": "Failed to extract base domain from {url}"}}'
         return
         
    yield f'{{"status": "progress", "message": "STAGE 1: Executing Search-Based Discovery for {university_name}..."}}'
    
    yield f'{{"status": "progress", "message": "STAGE 1: Discovering official Graduate Programs Portal..."}}'
    portal_discovery_prompt = (
        f"Find the official URL of the main webpage that lists all graduate programs (Masters, PhD, Doctoral) at {university_name}. "
        f"This is usually titled 'Graduate Programs', 'Academics', or 'Graduate Studies'. "
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
        f"Extract EVERY SINGLE active graduate (Master's, PhD, Doctorate, Certificate) program name AND its specific official URL for {university_name}.\n\n"
        f"CRITICAL DOMAIN RULE: You MUST use the search operator `site:{base_domain}`. DO NOT return URLs from Wikipedia, U.S. News, Peterson's, or any non-official 3rd party site.\n"
        f"CRITICAL NAME RULE: STANDARDIZE THE NAME. If you see 'MS in CS', output 'Master of Science in Computer Science'. If you see 'Biology, MS', output 'Master of Science in Biology'. DO NOT output abbreviations.\n"
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
        
        # Blacklist for generic titles that aren't real programs
        blacklist = [
            "graduate catalog", "graduate studies", "online programs", 
            "graduate admissions", "apply now", "contact us", "graduate school",
            "graduate programs", "academics", "program list", "degrees and programs"
        ]

        if isinstance(program_data, list) and len(program_data) > 0:
            # Filter the search results
            filtered_search = []
            for p in program_data:
                name = p.get("Program name", "").lower()
                if any(term == name or name == f"{term}s" for term in blacklist):
                    continue
                filtered_search.append(p)
            
            found_search_count = len(filtered_search)
            yield f'{{"status": "progress", "message": "Stage 1 Search found {found_search_count} valid programs."}}'
            for prog in filtered_search:
                yield prog
        else:
            yield f'{{"status": "warning", "message": "Stage 1 Search yielded 0 programs. Proceeding to Stage 2 Crawl..."}}'
            
    except Exception as e:
        yield f'{{"status": "warning", "message": "Stage 1 Search failed: {e}. Proceeding to Stage 2 Crawl..."}}'

    # --- STAGE 2: CRAWL FALLBACK (Deterministic) ---
    # We ALWAYS run Stage 2 for 'Deep Discovery' unless we already have a massive list
    if found_search_count > 80:
         yield f'{{"status": "progress", "message": "Extensive list found in search. Verification sweep starting..."}}'
    else:
         yield f'{{"status": "progress", "message": "STAGE 2: Executing Direct Crawl on {portal_url} for exhaustive coverage..."}}'
    
    # We look for keywords that imply graduate level
    grad_keywords = ['graduate', 'master', 'phd', 'doctor', 'cert', 'degree', 'program', 'curriculum']
    
    # Run the crawler natively from the portal URL (increased to 25 pages for exhaustive coverage)
    crawled_links = fetch_links_with_pagination(portal_url, base_domain, filter_keywords=grad_keywords, max_pages=25)
    
    if not crawled_links:
         yield f'{{"status": "warning", "message": "Stage 2 Crawl found 0 potential links."}}'
         return

    yield f'{{"status": "progress", "message": "Crawled {len(crawled_links)} potential links. Refining and standardizing names..."}}'
    
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
            f"1. Filter this list. Keep ONLY actual graduate-level academic programs (Master's, PhD, Certificates).\n"
            f"2. REMOVE links that are just 'Apply', 'Contact Us', 'About', 'Faculty', or portal headers like 'Graduate School'.\n"
            f"3. STANDARDIZE the names. Convert abbreviations to full names (e.g., 'MS' -> 'Master of Science').\n"
            f"4. Return ONLY a JSON list of objects: [{{ \"Program name\": \"...\", \"Program Page url\": \"{portal_url}\" }}]\n"
            f"   IMPORTANT: For the 'Program Page url', ALWAYS use strictly {portal_url} for all programs. NO EXCEPTIONS.\n"
            f"5. If no links in this chunk are programs, return an empty list []."
        )
        
        try:
            refine_resp = model.generate_content(refine_prompt)
            refined_data = _extract_json_from_text(refine_resp.text)
            if isinstance(refined_data, list):
                for prog in refined_data:
                    # Blacklist check again for AI safety
                    name = prog.get("Program name", "").lower()
                    if any(term == name or name == f"{term}s" for term in blacklist):
                        continue
                    if "Program name" in prog and "Program Page url" in prog:
                        yield prog
        except Exception as e:
            yield f'{{"status": "warning", "message": "Failed to refine crawl chunk {i//chunk_size + 1}: {e}"}}'


import requests

def resolve_redirect(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception:
        return url

def run(university_name_input):
    global university_name, institute_url
    university_name = university_name_input
    
    yield f'{{"status": "progress", "message": "Finding official website for {university_name}..."}}'
    
    sanitized_name = university_name.replace(" ", "_").replace("/", "_")
    
    # Check if we already have the output
    csv_path = os.path.join(output_dir, f'{sanitized_name}_graduate_programs.csv')
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        count = len(pd.read_csv(csv_path))
        # MINIMUM COUNT SANITY CHECK:
        # Most universities have dozens or hundreds of programs. 
        # If the count is < 20, it's likely a partial/lazy result from an older script.
        # We only skip if the count is > 20 to ensure deep discovery.
        if count > 20: 
            yield f'{{"status": "progress", "message": "Graduate programs list for {university_name} already exists with {count} programs. Skipping extraction."}}'
            yield f'{{"status": "complete", "message": "Found {count} graduate programs (using existing list)", "files": {{"grad_csv": "{csv_path}"}}}}'
            return
        else:
            yield f'{{"status": "progress", "message": "Existing list found but count is  low ({count}). Forcing Deep Discovery re-extraction..."}}'

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
                graduate_program_url = url_match.group(0).replace('**', '')
            
    except:
        graduate_program_url = website_url # Fallback
        
    from robust_extraction_utils import verify_legit_url
    graduate_program_url = verify_legit_url(graduate_program_url, website_url)

    yield f'{{"status": "progress", "message": "Graduate Page Verified: {graduate_program_url}"}}'

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

