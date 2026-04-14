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

# Known patterns for JS-rendered program finders with embedded JSON APIs
KNOWN_PROGRAM_JSON_PATHS = [
    '/_data/program-data.json',
    '/api/programs',
    '/programs.json',
    '/academics/programs.json',
    '/data/programs.json',
]

def try_js_api_discovery(base_domain):
    """
    Detects JS-rendered program finders (like SEMO's Alpine.js programFinder)
    that load program data from a JSON endpoint. Returns a list of formatted
    program dicts if successful, or None if not found.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    # Normalize domain: try both www and non-www variants
    domains_to_try = [base_domain]
    if 'www.' not in base_domain:
        domains_to_try.append(base_domain.replace('https://', 'https://www.', 1))
    else:
        domains_to_try.append(base_domain.replace('https://www.', 'https://', 1))

    # Step 1: Check if the programs page references a known JSON fetch path
    for _domain in domains_to_try:
        programs_page_url = f'{_domain.rstrip("/")}/programs/'
        try:
            r = requests.get(programs_page_url, headers=headers, timeout=10)
            if r.status_code == 200:
                page_text = r.text.replace('&quot;', '"').replace('&#34;', '"')
                fetch_urls = re.findall(r'fetch\(["\']([^"\' ]+\.json)["\']', page_text)
                for furl in fetch_urls:
                    if 'program' in furl.lower() or 'data' in furl.lower():
                        KNOWN_PROGRAM_JSON_PATHS.insert(0, furl)
                break  # Use first working domain
        except Exception:
            continue

    # Step 2: Try each known path across all domain variants
    # Step 2: Try each known path across all domain variants
    for path in KNOWN_PROGRAM_JSON_PATHS:
        for _d in domains_to_try:
            url = _d.rstrip('/') + path
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200 and 'json' in r.headers.get('content-type', '').lower():
                    data = r.json()
                    programs = data if isinstance(data, list) else data.get('programs', [])
                    if programs and len(programs) > 5:
                        # Filter to graduate only
                        grad_programs = [
                            p for p in programs
                            if 'Graduate' in (p.get('programType', []) if isinstance(p.get('programType'), list) else [p.get('programType', '')])
                        ]
                        if not grad_programs:
                            # Try alternate field names
                            grad_programs = [
                                p for p in programs
                                if any(kw in str(p.get('tags', '') or p.get('type', '') or p.get('level', '')).lower() for kw in ['graduate', 'master', 'doctoral'])
                            ]
                        
                        if grad_programs:
                            # Format to standard output format
                            formatted = []
                            for p in grad_programs:
                                name = p.get('title') or p.get('name') or p.get('programName', '')
                                link = p.get('link') or p.get('url') or p.get('href', '')
                                if not link.startswith('http'):
                                    link = _d.rstrip('/') + link
                                degree = p.get('degreeType', '')
                                if isinstance(degree, list):
                                    degree = degree[0] if degree else ''
                                formatted.append({
                                    'Program name': name,
                                    'Program Page url': link,
                                    'Degree Type': degree,
                                })
                            return formatted, url
            except Exception:
                continue
    return None, None
    return None, None

def get_graduate_programs(url, university_name, existing_data=None):
    from robust_extraction_utils import get_base_domain, fetch_links_with_pagination, _extract_json_from_text, scrape_page_text, validate_program_against_source
    import os
    
    base_domain = get_base_domain(url)
    if not base_domain:
         yield f'{{"status": "error", "message": "Failed to extract base domain from {url}"}}'
         return
    
    # === STAGE 0: JS API Detection (handles sites like SEMO w/ Alpine.js programFinders) ===
    yield f'{{"status": "progress", "message": "STAGE 0: Checking for JS-rendered program API endpoint..."}}'  
    api_programs, api_source_url = try_js_api_discovery(base_domain)
    if api_programs:
        yield f'{{"status": "progress", "message": "Found {len(api_programs)} graduate programs via JS API at {api_source_url}. Skipping web scraping."}}'  
        for p in api_programs:
            yield p
        return
    
    portal_discovery_prompt = (
        f"Find the top 3 official URLs of webpages that list graduate programs (Masters, PhD, Doctoral) at {university_name}. "
        f"Prioritize the main 'Graduate Programs' list or 'Program Finder' page. "
        f"Return ONLY a JSON object with a key 'portal_urls' which is a list of strings: {{'portal_urls': ['url1', 'url2', 'url3']}}"
    )
    
    portal_urls = []
    try:
        portal_resp = client.models.generate_content(
            model=os.getenv("MODEL"),
            contents=portal_discovery_prompt,
            config=GenerateContentConfig(tools=[Tool(google_search=GoogleSearch())])
        )
        portal_data = _extract_json_from_text(portal_resp.text)
        if isinstance(portal_data, dict) and 'portal_urls' in portal_data:
            portal_urls = portal_data.get('portal_urls', [])
        elif isinstance(portal_data, dict) and 'portal_url' in portal_data:
            portal_urls = [portal_data.get('portal_url')]
    except Exception as e:
         yield f'{{"status": "warning", "message": "Discovery failed: {str(e)}"}}'

    if not portal_urls:
         portal_urls = [url] # Use the verified grad_url as single candidate

    # SEQUENTIAL VALIDATION: Try each portal until one works
    valid_portal = None
    source_text = ""
    
    for p_url in portal_urls:
        yield f'{{"status": "progress", "message": "Validating candidate portal {p_url}..."}}'
        from robust_extraction_utils import verify_legit_url
        checked_url = verify_legit_url(p_url, None)
        
        if checked_url:
            yield f'{{"status": "progress", "message": "STAGE 2: Scraping HTML content from {checked_url}..."}}'
            source_text = scrape_page_text(checked_url)
            
            if source_text and len(source_text) > 500:
                valid_portal = checked_url
                portal_url = checked_url
                break
            else:
                yield f'{{"status": "warning", "message": "Portal {p_url} returned empty or too short content. Trying next..."}}'
        else:
            yield f'{{"status": "warning", "message": "Candidate portal {p_url} is dead (404/Error). Trying next..."}}'

    # If no portals worked, try expanded crawl on the first one or fallback to Tier 3
    if not valid_portal:
        yield f'{{"status": "warning", "message": "Native scraping failed for all candidates. Triggering Tier 3 Google Grounding fallback..."}}'
        from robust_extraction_utils import get_google_search_snippets_text
        source_text = get_google_search_snippets_text(university_name, client, os.getenv("MODEL"), base_domain)
        portal_url = portal_urls[0] # metadata fallback
    else:
        # If the valid portal text is still a bit short, try one deep crawl step
        if len(source_text) < 2000:
            yield f'{{"status": "progress", "message": "Portal text is short. Expanding crawl scope (Max 30 pages)..."}}'
            grad_keywords = ['graduate', 'master', 'phd', 'doctor', 'cert', 'degree', 'program', 'curriculum', 'academics', 'catalog', 'departments']
            crawled_links = fetch_links_with_pagination(portal_url, base_domain, filter_keywords=grad_keywords, max_pages=30)
            if crawled_links:
                source_text += " " + " ".join([link['text'] for link in crawled_links])
        
    if not source_text or len(source_text.strip()) < 100:
        yield f'{{"status": "error", "message": "Extracted source text is too short or empty. Aborting to prevent hallucination."}}'
        return

    # Basic check for common junk words (if it's just an error page)
    junk_indicators = ["403 Forbidden", "404 Not Found", "Access Denied", "Cloudflare"]
    if any(indicator in source_text for indicator in junk_indicators) and len(source_text) < 500:
        yield f'{{"status": "error", "message": "Source text appears to be an error page. Aborting."}}'
        return

    yield f'{{"status": "progress", "message": "STAGE 3: Extracting programs using LLM..."}}'
    
    prompt = (
        f"You are a professional academic data extractor. Your task is to extract a list of official graduate programs for {university_name}.\n\n"
        f"SOURCE TEXT (EXTRACTED FROM GOOGLE/WEB):\n"
        f"===\n{source_text[:120000]}\n===\n\n" 
        f"STRICT EXTRACTION RULES:\n"
        f"1. ONLY extract programs that are EXPLICITLY NAMED in the Source Text above.\n"
        f"2. If the Source Text does not contain a specific program, DO NOT include it, even if you think the university offers it.\n"
        f"3. If the Source Text is junk or doesn't contain programs, return an empty list [].\n"
        f"4. DO NOT use your internal knowledge to 'fill in the blanks'.\n"
        f"5. STANDARDIZE names (e.g., 'MS in CS' -> 'Master of Science in Computer Science').\n"
        f"6. SEPARATE COMBINED PROGRAMS: If a department name like 'Chemical and Biological Engineering' represents distinct separate programs (e.g., 'Master of Science in Chemical Engineering' and 'Master of Science in Biological Engineering'), split them into separate dictionary entries. Do not group them as one unless it is officially a single combined degree.\n\n"
        f"Return ONLY a clean JSON list: [{{ \"Program name\": \"...\", \"Program Page url\": \"{portal_url}\" }}]\n"
    )
    
    try:
        response = client.models.generate_content(
            model=os.getenv("MODEL"),
            contents=prompt,
            config=GenerateContentConfig(temperature=0.1)
        )
        program_data = _extract_json_from_text(response.text)
        
        blacklist = [
            "graduate catalog", "graduate studies", "online programs", 
            "graduate admissions", "apply now", "contact us", "graduate school",
            "graduate programs", "academics", "program list", "degrees and programs",
            "certificate", "doctoral", "master's"
        ]

        valid_programs = []
        if isinstance(program_data, list) and len(program_data) > 0:
            for p in program_data:
                name = p.get("Program name", "").lower()
                clean_name_check = name.strip()
                if not clean_name_check or any(term == clean_name_check or clean_name_check == f"{term}s" for term in blacklist):
                    continue
                # Validate against source to prevent hallucination
                if validate_program_against_source(p.get("Program name", ""), source_text):
                    valid_programs.append(p)
                else:
                    rej = p.get('Program name', '')
                    safe_rej = rej.replace('"', '\\"')
                    yield f'{{"status": "progress", "message": "Rejected hallucinated program: {safe_rej}"}}'
        
        # DEEP DISCOVERY RETRY: If count is very low or zero, we trigger Google Grounding search
        if len(valid_programs) < 5:
            yield f'{{"status": "warning", "message": "Only found {len(valid_programs)} programs. Attempting Deep Discovery via targeted searches..."}}'
            # Trigger Tier 3 and merge
            from robust_extraction_utils import get_google_search_snippets_text
            secondary_source = get_google_search_snippets_text(f"{university_name} list of all graduate master phd programs", client, os.getenv("MODEL"), base_domain)
            if secondary_source and len(secondary_source) > 500:
                yield f'{{"status": "progress", "message": "Secondary discovery successful. Re-extracting from search snippets..."}}'
                # Generate a new prompt with the secondary source
                secondary_prompt = (
                    f"You are a professional academic data extractor. Extract graduate programs (Master, PhD) for {university_name}.\n"
                    f"SOURCE TEXT:\n===\n{secondary_source[:120000]}\n===\n"
                    f"RULES:\n"
                    f"- STANDARDIZE names.\n"
                    f"- SEPARATE COMBINED PROGRAMS (e.g., split 'Chemical and Biological Engineering' into separate entries for 'Chemical Engineering' and 'Biological Engineering' if they are distinct programs).\n"
                    f"Return ONLY a JSON list: [{{ \"Program name\": \"...\", \"Program Page url\": \"{portal_url}\" }}]\n"
                )
                sec_resp = client.models.generate_content(model=os.getenv("MODEL"), contents=secondary_prompt, config=GenerateContentConfig(temperature=0.1))
                sec_data = _extract_json_from_text(sec_resp.text)
                if isinstance(sec_data, list):
                    # Collect new candidate program names (deduped)
                    candidates = [
                        sp for sp in sec_data
                        if sp.get("Program name") and sp.get("Program name") not in [vp.get("Program name") for vp in valid_programs]
                    ]
                    if candidates:
                        candidate_names = [sp["Program name"] for sp in candidates]
                        yield f'{{"status": "progress", "message": "Batch-verifying {len(candidate_names)} grounding programs in chunks of 20..."}}'  
                        from robust_extraction_utils import verify_programs_batch
                        confirmed_names = set(verify_programs_batch(candidate_names, university_name, client, os.getenv("MODEL")))
                        removed = [n for n in candidate_names if n not in confirmed_names]
                        for sp in candidates:
                            if sp["Program name"] in confirmed_names:
                                valid_programs.append(sp)
                        if removed:
                            safe_removed = str(removed).replace('"', "'")
                            yield f'{{"status": "progress", "message": "Grounding check removed {len(removed)} unconfirmed programs: {safe_removed[:200]}"}}'  

        
        if len(valid_programs) > 0:
            yield f'{{"status": "progress", "message": "Extraction complete. Found {len(valid_programs)} valid programs after verification."}}'
            for prog in valid_programs:
                yield prog
        else:
            yield f'{{"status": "warning", "message": "Extraction failed. No graduate programs could be verified from source text."}}'
            
    except Exception as e:
         yield f'{{"status": "error", "message": "Extraction failed: {str(e)}"}}'


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

    # === EARLY EXIT: JS API Detection ===
    # Many modern university sites use JS-rendered program finders (Alpine.js, React, etc.)
    # that load all programs from a JSON endpoint. Detect this before any scraping or LLM calls.
    from robust_extraction_utils import get_base_domain
    base_domain_early = get_base_domain(website_url)
    if base_domain_early:
        yield f'{{\"status\": \"progress\", \"message\": \"Checking for JS-rendered program API...\"}}'
        api_programs_early, api_source_url_early = try_js_api_discovery(base_domain_early)
        if api_programs_early:
            yield f'{{\"status\": \"progress\", \"message\": \"Found {len(api_programs_early)} graduate programs via program API. Writing results...\"}}'
            json_path_early = os.path.join(output_dir, f'{sanitized_name}_graduate_programs.json')
            csv_path_early = os.path.join(output_dir, f'{sanitized_name}_graduate_programs.csv')
            with open(json_path_early, 'w', encoding='utf-8') as f:
                json.dump(api_programs_early, f, indent=4, ensure_ascii=False)
            pd.DataFrame(api_programs_early).to_csv(csv_path_early, index=False, encoding='utf-8')
            yield f'{{\"status\": \"complete\", \"message\": \"Found {len(api_programs_early)} graduate programs (via program API)\", \"files\": {{\"grad_csv\": \"{csv_path_early}\"}}}}'
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
        # Final Step: Standardize program names (preserves original names, adds 'Standardized Program Name' field)
        yield f'{"{\"status\": \"progress\", \"message\": \"Standardizing names for "}' + str(len(current_programs)) + '{" extracted programs...\"}"}'
        from robust_extraction_utils import standardize_program_names_batch
        
        # Determine model to use
        _model_name = os.getenv("MODEL", "gemini-2.5-flash")
        try:
            current_programs = standardize_program_names_batch(current_programs, client, _model_name)
            save_progress(current_programs)
            yield '{"status": "progress", "message": "Program name standardization complete."}'
        except Exception as e:
            safe_err = str(e).replace('"', "'")
            yield f'{"{\"status\": \"warning\", \"message\": \"Standardization failed: "}' + safe_err + '{" Original names preserved.\"}"}'
            
        csv_path_safe = os.path.join(output_dir, f"{sanitized_name}_graduate_programs.csv").replace('"', "'")
        yield f'{"{\"status\": \"complete\", \"message\": \"Found "}' + str(len(current_programs)) + '{" graduate programs\", \"files\": {\"grad_csv\": \""}' + csv_path_safe + '{"\"}}"}'
    else:
        yield '{"status": "complete", "message": "No graduate programs found", "files": {}}'
