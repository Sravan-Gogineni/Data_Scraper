import os
import time
import random
import logging
import json
import re
import requests
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

class GeminiModelWrapper:
    """Wrapper for Gemini API with retry logic and exponential backoff, tailored for Vertex AI quotas."""
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt, max_retries=5, base_delay=3, tools=None, temperature=0.1):
        if tools is None:
            # Default to no tools unless required, saves token space
            tools = []
            
        config = GenerateContentConfig(tools=tools, temperature=temperature)
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                return response
            except Exception as e:
                error_str = str(e)
                # Handle quota and rate limits generously
                if "503" in error_str or "429" in error_str or "Too Many Requests" in error_str or "Overloaded" in error_str:
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt) + random.uniform(1, 3)
                        logger.warning(f"Vertex AI API Attempt {attempt + 1} failed (Rate Limit). Retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        continue
                logger.error(f"Vertex AI API Failed after {attempt + 1} attempts: {e}")
                raise e

def _extract_json_from_text(text: str) -> dict:
    """Helper to safely extract JSON from LLM responses containing markdown."""
    text = text.strip()
    try:
        # Check if the result is already clean json
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        
        # Try finding the first '{' or '[' if there is junk
        start = text.find('{')
        start_array = text.find('[')
        
        if start_array != -1 and (start == -1 or start_array < start):
            end = text.rfind(']') + 1
            if end != 0:
                 return json.loads(text[start_array:end])
        elif start != -1:
            end = text.rfind('}') + 1
            if end != 0:
                 return json.loads(text[start:end])
                 
        return json.loads(text)
    except Exception:
        return {}
        
def fetch_links_from_url(url: str, base_domain: str, filter_keywords=None) -> list:
    """Fetches text and <a> href links natively from a webpage to feed into the LLM context, bypassing GoogleSearch tool."""
    links = []
    if not url: return links
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url, headers=headers, timeout=10)
        
        # simple regex to extract href and text
        matches = re.findall(r'<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', resp.text, re.IGNORECASE | re.DOTALL)
        
        seen_urls = set()
        for href, text in matches:
            # Clean text
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if not clean_text or len(clean_text) < 4:
                continue
                
            # Build absolute URL
            absolute_url = urljoin(url, href)
            
            # Filter to make sure it belongs to the base domain
            parsed_abs = urlparse(absolute_url)
            if base_domain not in parsed_abs.netloc:
                continue
                
            # Filter keywords if provided (e.g., 'master', 'bs', 'ba', 'phd')
            if filter_keywords:
                matches_keyword = any(kw.lower() in clean_text.lower() or kw.lower() in href.lower() for kw in filter_keywords)
                if not matches_keyword:
                    continue
                    
            if absolute_url not in seen_urls:
                 seen_urls.add(absolute_url)
                 links.append({"text": clean_text, "url": absolute_url})
                 
    except Exception as e:
        logger.error(f"Error fetching links from {url}: {e}")
        
    return links

def fetch_links_with_pagination(start_url: str, base_domain: str, filter_keywords=None, max_pages=15, yield_func=None) -> list:
    """Crawls local pagination links natively to exhaustively fetch all academic <a> tags."""
    all_links = []
    visited_urls = set()
    urls_to_visit = [start_url]
    seen_academic_urls = set()
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    while urls_to_visit and len(visited_urls) < max_pages:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls: continue
        visited_urls.add(current_url)
        
        if yield_func:
            try:
                 yield_func(f'{{"status": "progress", "message": "Crawling page {len(visited_urls)}: {current_url}"}}')
            except: pass
            
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(current_url, headers=headers, timeout=15)
            
            # Immediately halt if we get a bot block or real error!
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch links from {current_url}: Status {resp.status_code}")
                # Don't parse links from 403 pages, as they can cause hallucinations
                continue
                
            matches = re.findall(r'<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>(.*?)</a>', resp.text, re.IGNORECASE | re.DOTALL)
            
            for href, raw_text in matches:
                clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()
                absolute_url = urljoin(current_url, href)
                parsed_abs = urlparse(absolute_url)
                
                if base_domain not in parsed_abs.netloc:
                    continue
                    
                text_lower = clean_text.lower()
                href_lower = href.lower()
                
                is_pagination = False
                if 'page' in href_lower or 'p=' in href_lower or text_lower in ['next', '>>', 'older', 'all', 'full']:
                    is_pagination = True
                elif clean_text.isdigit() and len(clean_text) <= 3:
                    is_pagination = True
                    
                if is_pagination:
                    base_path = urlparse(start_url).path
                    if base_path == '' or base_path == '/':
                         if absolute_url not in visited_urls and absolute_url not in urls_to_visit:
                              urls_to_visit.append(absolute_url)
                    elif base_path in parsed_abs.path or parsed_abs.path in base_path:
                        if absolute_url not in visited_urls and absolute_url not in urls_to_visit:
                            urls_to_visit.append(absolute_url)
                            
                if len(clean_text) < 4:
                    continue
                    
                if filter_keywords:
                    matches_keyword = any(kw.lower() in clean_text.lower() or kw.lower() in href_lower for kw in filter_keywords)
                    if not matches_keyword:
                        continue
                        
                if absolute_url not in seen_academic_urls:
                    seen_academic_urls.add(absolute_url)
                    all_links.append({"text": clean_text, "url": absolute_url})
                    
        except Exception as e:
            logger.error(f"Error crawling {current_url}: {e}")
            
    return all_links

def get_base_domain(url: str) -> str:
    """Takes a full url and returns the root domain e.g. 'yale.edu'"""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        # Get last two segments (or more for .ac.uk, .edu.au etc, but standard .edu is just two)
        parts = netloc.split('.')
        if len(parts) > 2 and parts[-2] in ['edu', 'ac', 'co', 'go', 'org']:
             return '.'.join(parts[-3:])
        return '.'.join(parts[-2:])
    except:
        return ""

def verify_legit_url(url, fallback_domain):
    """
    Tests if a URL is actually working (200 OK) and not a 404/Error page.
    If it's a dead link, it tries the base domain.
    """
    import urllib.parse
    import requests
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        r = requests.get(url, timeout=10, allow_redirects=True, headers=headers)
        
        # Check status code
        if r.status_code == 200:
            # Check content for "Not Found" or "404" which some servers return with 200 OK
            content_lower = r.text.lower()
            error_indicators = ["404 not found", "page not found", "access denied", "403 forbidden", "site maintenance"]
            # But only if the page is very short, as some valid pages might contains these words in the footer
            if len(r.text) < 2000 and any(indicator in content_lower for indicator in error_indicators):
                pass # Treat as failure
            else:
                return url
    except Exception:
        pass
        
    # If the exact path fails, try just the parsed base domain of that url
    try:
        parsed = urllib.parse.urlparse(url)
        root_url = f'{parsed.scheme}://{parsed.netloc}'
        r = requests.get(root_url, timeout=10, allow_redirects=True, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            return root_url
    except Exception:
        pass
        
    return fallback_domain


def scrape_page_text(url: str) -> str:
    """
    Fetches actual visible text from a URL.
    This is used as the ground truth to prevent the LLM from hallucinating programs.
    """
    import requests
    import re
    try:
        from bs4 import BeautifulSoup
        has_bs4 = True
    except ImportError:
        has_bs4 = False

    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = scraper.get(url, headers=headers, timeout=15, allow_redirects=True)
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {url}: Status {response.status_code}")
            return ""
            
        html_content = response.text
        
        if has_bs4:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            text = soup.get_text(separator=' ', strip=True)
        else:
            # Fallback regex parsing
            # Remove scripts/styles
            html_content = re.sub(r'<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>', ' ', html_content, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', html_content)
            
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return ""

def validate_program_against_source(program_name, source_text, threshold=0.7):
    """
    Determines if a program name hallucinated by the LLM is actually present in the source text.
    Returns True if valid, False if it appears to be a hallucination.
    """
    import re
    
    if not source_text or not source_text.strip() or len(source_text) < 100:
        # If the source is empty or junk, we cannot validate, so we reject.
        return False
        
    # Clean up the program name
    # We remove punctuation but keep spaces to split into tokens
    clean_name = re.sub(r'[^\w\s]', ' ', program_name.lower())
    clean_source = re.sub(r'[^\w\s]', ' ', source_text.lower())
    
    # Remove common degree words and filler
    stop_words = [
        "master", "of", "science", "in", "arts", "doctor", "philosophy", 
        "ph.d.", "m.s.", "m.a.", "phd", "ms", "ma", "certificate", "ph.d", 
        "program", "degree", "the", "and", "undergraduate", "graduate",
        "professional", "studies", "specialization", "concentration", "minor", "major"
    ]
    
    # Tokenize
    name_tokens = [w for w in clean_name.split() if w not in stop_words and len(w) >= 2]
    
    if not name_tokens:
        # If it's just 'Master of Science', we check if the full phrase exists (unlikely to be alone)
        return clean_name in clean_source
        
    # Check if core tokens exist in the source text
    # We use a set to avoid rewarding duplicate words
    unique_tokens = list(set(name_tokens))
    matched_tokens = 0
    
    # Pre-tokenize source for faster whole-word checking
    source_words = set(clean_source.split())
    
    for token in unique_tokens:
        # direct match (token is a sub-phrase or word)
        if token in clean_source:
            matched_tokens += 1
            continue
            
        # Partial match: check if any word in the source is a prefix/suffix of the token
        # (e.g. source has 'Info' and token is 'Information')
        is_partial = False
        for sword in source_words:
            if len(sword) > 3:
                if sword.startswith(token) or token.startswith(sword):
                    is_partial = True
                    break
        if is_partial:
            matched_tokens += 1
    
    match_ratio = matched_tokens / len(unique_tokens)
    
    # REQUIREMENT: At least one "rare" word (longer than 4 chars) must match
    # We are more lenient here too
    rare_tokens = [t for t in unique_tokens if len(t) > 4]
    if rare_tokens:
        rare_match = False
        for t in rare_tokens:
            if t in clean_source:
                rare_match = True
                break
            if any(len(sw) > 3 and (sw.startswith(t) or t.startswith(sw)) for sw in source_words):
                rare_match = True
                break
                
        if not rare_match and match_ratio < 0.8:
            return False

    return match_ratio >= threshold


def standardize_program_names_batch(programs: list, client, model_name: str, batch_size: int = 15) -> list:
    """
    Standardizes extracted program names by expanding abbreviations and degree codes.

    Examples:
        "Teaching English as a Second Language (TESOL) (MA)"
            -> "Master of Arts in Teaching English as a Second Language"
        "Athletic Training (MS)"
            -> "Master of Science in Athletic Training"
        "MBA: Human Resource Management"
            -> "Master of Business Administration in Human Resource Management"
        "Cloud Computing Graduate Certificate"
            -> "Graduate Certificate in Cloud Computing"

    Rules:
        - Overwrites the original 'Program name' field with the standardized name
        - If standardization fails or is uncertain for a program, the original name is kept untouched

    Returns the same list of program dicts with 'Program name' updated.
    """
    try:
        from google.genai.types import GenerateContentConfig
        import json as _json, re as _re
    except ImportError:
        return programs

    degree_map = {
        'MS': 'Master of Science',
        'MA': 'Master of Arts',
        'MBA': 'Master of Business Administration',
        'MFA': 'Master of Fine Arts',
        'MPA': 'Master of Public Administration',
        'MSN': 'Master of Science in Nursing',
        'MEd': 'Master of Education',
        'MAT': 'Master of Arts in Teaching',
        'EdS': 'Education Specialist',
        'EdD': 'Doctor of Education',
        'PhD': 'Doctor of Philosophy',
    }

    for chunk_start in range(0, len(programs), batch_size):
        chunk = programs[chunk_start:chunk_start + batch_size]
        names = [p.get('Program name', '') for p in chunk]

        numbered = '\n'.join(f'{i+1}. {name}' for i, name in enumerate(names))
        degree_examples = ', '.join(f'{k}={v}' for k, v in list(degree_map.items())[:6])

        prompt = (
            f"Standardize these graduate program names into their full official form. "
            f"Expand degree abbreviations: {degree_examples}, etc. "
            f"Format: 'Degree in Subject' (e.g. 'Master of Science in Data Science'). "
            f"Return ONLY a JSON array of standardized names in the SAME order, same count.\n\n"
            f"{numbered}"
        )

        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=GenerateContentConfig(temperature=0.1)
            )
            raw = (resp.text or '').strip()
            # Extract JSON array
            match = _re.search(r'\[.*?\]', raw, _re.DOTALL)
            standardized = _json.loads(match.group(0)) if match else []

            if isinstance(standardized, list) and len(standardized) == len(chunk):
                for p, std_name in zip(chunk, standardized):
                    if std_name and std_name.strip():
                        p['Program name'] = std_name.strip()
            else:
                logger.warning(f"Standardization length mismatch: got {len(standardized)}, expected {len(chunk)}")
                # On mismatch, keep original program names as they are

        except Exception as e:
            logger.warning(f"Standardization batch failed: {e}")
            # On exception, keep original program names as they are

    return programs

def verify_programs_batch(program_names: list, university_name: str, client, model_name: str, batch_size: int = 20) -> list:
    """
    Batch verification of programs via Google Search grounding.
    
    Splits programs into chunks of batch_size and runs one grounding call per chunk.
    Much faster than one call per program (e.g. 48 programs = 3 calls instead of 48).
    Returns the subset of program_names that are confirmed (or unrejected).
    """
    from google.genai.types import GenerateContentConfig, Tool, GoogleSearch
    import re as _re
    if not program_names:
        return []
    
    confirmed_all = []
    
    for chunk_start in range(0, len(program_names), batch_size):
        chunk = program_names[chunk_start:chunk_start + batch_size]
        try:
            numbered = '\n'.join(f'{i+1}. {name}' for i, name in enumerate(chunk))
            prompt = (
                f"Search the official website of {university_name}. "
                f"Below is a list of graduate programs. Identify ONLY the programs that are NOT currently offered there. "
                f"Return ONLY the numbers of programs not offered, comma-separated (e.g. '3, 7'). "
                f"If all are offered, return 'none'.\n\n"
                f"{numbered}"
            )
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.0,
                    tools=[Tool(google_search=GoogleSearch())]
                )
            )
            answer = (resp.text or '').strip().lower()
            logger.info(f"Batch {chunk_start//batch_size + 1} verification response: {answer[:150]}")
            
            if 'none' in answer or not answer:
                confirmed_all.extend(chunk)
                continue
            
            rejected_indices = set()
            for m in _re.findall(r'\b(\d+)\b', answer):
                idx = int(m) - 1
                if 0 <= idx < len(chunk):
                    rejected_indices.add(idx)
            
            confirmed = [name for i, name in enumerate(chunk) if i not in rejected_indices]
            rejected = [chunk[i] for i in rejected_indices]
            if rejected:
                logger.info(f"Batch removed: {rejected}")
            confirmed_all.extend(confirmed)
            
        except Exception as e:
            logger.warning(f"Batch verification failed for chunk {chunk_start//batch_size + 1}: {e}")
            confirmed_all.extend(chunk)
    
    return confirmed_all

# Keep single-program version for backwards compatibility
def verify_program_with_grounding(program_name: str, university_name: str, client, model_name: str) -> bool:
    return bool(verify_programs_batch([program_name], university_name, client, model_name))

def get_google_search_snippets_text(university_name: str, client, model_name: str, base_domain: str) -> str:
    """
    Tier 3 Fallback: Aggressively uses Google Search grounding with multiple queries
    to find real program text when direct portals are blocked.
    
    The returned text is used as source for BOTH extraction and validation.
    """
    try:
        from google.genai.types import GenerateContentConfig, Tool, GoogleSearch
        logger.info(f"Triggering Enhanced Tier 3 fallback for {university_name}")
        
        queries = [
            f"official list of all graduate programs at {university_name} masters phd doctoral degrees",
            f"{university_name} academic catalog graduate programs",
            f"site:{base_domain} graduate programs masters" if base_domain else f"{university_name} degrees masters list"
        ]
        
        all_source_text = ""
        unique_urls = set()
        
        for query in queries:
            try:
                logger.debug(f"Searching: {query}")
                resp = client.models.generate_content(
                    model=model_name,
                    contents=query,
                    config=GenerateContentConfig(
                        temperature=0.1,
                        tools=[Tool(google_search=GoogleSearch())]
                    )
                )
                
                if resp.text:
                    all_source_text += "\n" + resp.text
                
                # Extract URIs from grounding metadata
                if resp.candidates and resp.candidates[0].grounding_metadata and resp.candidates[0].grounding_metadata.grounding_chunks:
                    for chunk in resp.candidates[0].grounding_metadata.grounding_chunks:
                        if chunk.web and chunk.web.uri:
                            unique_urls.add(chunk.web.uri)
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {str(e)}")
        
        # Scrape top unique URLs found across all searches
        grounded_urls = list(unique_urls)
        for url in grounded_urls[:5]:
            try:
                logger.debug(f"Scraping grounded URL: {url}")
                text = scrape_page_text(url)
                if text and len(text) > 500:
                    all_source_text += f"\n--- SOURCE FROM {url} ---\n" + text[:25000]
            except Exception:
                continue
                
        return all_source_text.strip()
        
    except Exception as e:
        logger.error(f"Google grounding search failed: {e}")
        return ""
