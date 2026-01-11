import os
import logging
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class GeminiModelWrapper:
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def resolve_redirect(self, url):
        """Follows the Google redirect to find the original university URL."""
        try:
            # allow_redirects=True follows the chain to the final destination
            response = requests.head(url, allow_redirects=True, timeout=10)
            return response.url
        except Exception as e:
            logger.warning(f"Could not resolve URL {url}: {e}")
            return url  # Fallback to the original redirect link if resolution fails

    def generate_content_with_sources(self, prompt):
        """Calls Gemini and extracts clean, original source URLs."""
        try:
            google_search_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[google_search_tool],
                    temperature=0.0
                )
            )

            if not response or not response.candidates:
                return "No data found.", []

            generated_text = response.text.strip()
            sources = []
            
            # Access the grounding metadata for real links
            metadata = response.candidates[0].grounding_metadata
            if metadata and metadata.grounding_chunks:
                for chunk in metadata.grounding_chunks:
                    if chunk.web and chunk.web.uri:
                        # RESOLVE the redirect here
                        original_url = self.resolve_redirect(chunk.web.uri)
                        sources.append(original_url)
            
            # Remove duplicates
            unique_sources = list(dict.fromkeys(sources))
            return generated_text, unique_sources

        except Exception as e:
            logger.error(f"Error during API call: {e}")
            return f"Error: {str(e)}", []

# Initialize API Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
model_wrapper = GeminiModelWrapper(client, "gemini-2.5-pro")

def run_scraper(university_name):
    print(f"\n[Searching for {university_name}...]")
    
    # 1. Find Website URL first
    website_prompt = f"What is the official website URL for {university_name}? Return only the URL."
    website_response, _  = model_wrapper.generate_content_with_sources(website_prompt)
    website_url = website_response.strip()
    print(f"Official Website: {website_url}")

    # 2. Find Tuition Fee URL (restricted to official website)
    tuition_url_prompt = (
        f"Find the tuition fee URL for the university {university_name}. "
        f"Search query: site:{website_url} tuition fees cost of attendance "
        "Return only the tuition fee URL, no other text. "
    )
    tuition_url_response, _ = model_wrapper.generate_content_with_sources(tuition_url_prompt)
    tuition_url = tuition_url_response.strip()
    print(f"Tuition Webpage: {tuition_url}")

    # 3. Prompting for tuition extraction with site restriction (using the found tuition URL or main site)
    # We prioritize searching within the specific tuition URL found, but allow falling back to the main site domain
    prompt = (
        f"Look for the tuition fees for the university {university_name} on the website {tuition_url} or {website_url}. "
        f"Search query: site:{website_url} tuition fees {university_name} "
        "Please find the tuition fee for semester or year according to the website for the for both the undergraduate and graduate programs. "
        "The answer should be like this: 'Undergraduate (Full-Time): ~$7,438 per year (Resident), ~$19,318 (Non-Resident/Supplemental Tuition).Graduate (Full-Time): ~$8,872 per year (Resident), ~$18,952 (Non-Resident/Supplemental Tuition).' "
        "Look correctly and do not cross map the undergraduate and graduate tuition fees and resident and non-resident tuition fees. answer based on what you find in the website."
        "Return exactly how the above format is. "
        "No fabrication or guessing, just the answer you find in the website. or it's pages. "
        "Only if the tuition fees are explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the tuition fees are explicitly stated."
    )
    
    data, links = model_wrapper.generate_content_with_sources(prompt)

    print("-" * 30)
    print(f"RESULTS:\n{data}")
    print("\nORIGINAL SOURCE LINKS:")
    for i, link in enumerate(links, 1):
        print(f"[{i}] {link}")

if __name__ == "__main__":
    run_scraper("University of Kansas")