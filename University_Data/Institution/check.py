
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import sys

# Add current directory to path to allow importing Institution
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from Institution import GeminiModelWrapper, client

import requests
from dotenv import load_dotenv

load_dotenv()

# Initialize the model using the wrapper from Institution.py
# ensuring we use a search-capable model
model = GeminiModelWrapper(client, "gemini-2.5-flash") 

def resolve_redirect(url):
    try:
        # Use HEAD request to follow redirects without downloading content
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception:
        return url

def generate_text_safe(prompt):
    try:
        response = model.generate_content(prompt)
        
        real_urls = []
        if response.candidates and response.candidates[0].grounding_metadata:
            print("\n--- RESOLVING SEARCH RESULTS ---")
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if chunk.web:
                    vertex_url = chunk.web.uri
                    original_url = resolve_redirect(vertex_url)
                    print(f"Original URL: {original_url}")
                    real_urls.append(original_url)
            print("--------------------------------\n")
        
        # Filter for .edu links
        edu_urls = [u for u in real_urls if ".edu" in u]
        if edu_urls:
            return edu_urls[0] # Return the first .edu link
        elif real_urls:
             return real_urls[0] # Fallback to first link
             
        # Fallback to text generation if no links found
        if response and response.text:
            return response.text.replace("**", "").replace("```", "").strip()
            
    except Exception as e:
        print(f"Error generating content: {e}")
    return ""

# 3. The Test Execution
print("Starting live search test...")
test_prompt = "University of Findlay Master of Arts in Education official program page"
result = generate_text_safe(test_prompt)

print("RESULT (Best URL):")
print(result)