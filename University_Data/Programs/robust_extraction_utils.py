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
            resp = requests.get(current_url, headers=headers, timeout=10)
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
    Tests if a URL is actually working (200 OK) using HTTP requests.
    If it's a 404 dead link, it strips back to the base domain which mathematically must work.
    """
    import urllib.parse
    import requests
    try:
        r = requests.get(url, timeout=10, allow_redirects=True, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
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
