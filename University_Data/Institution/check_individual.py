import pandas as pd 
import os
from dotenv import load_dotenv
import json
import csv
import logging
from google import genai
from google.genai import types


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configure the client (using google-genai SDK 1.57.0)
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Wrapper for compatibility with existing code structure
class GeminiModelWrapper:
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt):
        # Configure the search tool for every call to ensure live data
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool]
            )
        )
        return response

    def generate_text_safe(self, prompt):
        try:
            response = self.generate_content(prompt)
            if response and response.text:
                return response.text.replace("**", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"Error generating content: {e}")
        return ""

# Initialize the model wrapper
model = GeminiModelWrapper(client, "gemini-2.5-pro")    

# Define global helper function that uses the model instance
def generate_text_safe(prompt):
    return model.generate_text_safe(prompt)

def get_grad_tuition(website_url, university_name, graduate_tuition_fee_urls=None, common_tuition_fee_urls=None):
    # Use specific URL if provided, else use common URL, else use website_url
    url_to_use = graduate_tuition_fee_urls if graduate_tuition_fee_urls else (common_tuition_fee_urls if common_tuition_fee_urls else website_url)
    prompt = (
        f"What is the graduate tuition for the university {university_name} at {url_to_use}? "
        "Return only the graduate tuition, no other text. "
        "No fabrication or guessing, just the graduate tuition. "
        "Only if the graduate tuition is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the graduate tuition is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_tuition_fee_url(university_name, website_url):
    prompt = (
        f"What is the tuition fee URL for the university {university_name} at {website_url}? "
        "Return only the tuition fee URL, no other text. "
        "No fabrication or guessing, just the tuition fee URL. "
        "Only if the tuition fee URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the tuition fee URL is explicitly stated."
    )
    return generate_text_safe(prompt)

university_name = "University of California, Berkeley"

# Now we can safely call functions or use them in __main__
if __name__ == "__main__":
    # Get website URL first
    print(f"Finding website for {university_name}...")
    prompt = (
        f"What is the website URL for the university {university_name}? "
        "Return only the website URL, no other text. "
        "No fabrication or guessing, just the website URL. "
        "Only if the website URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the website URL is explicitly stated."
    )
    website_url = generate_text_safe(prompt)
    print(f"Website URL: {website_url}")

    if website_url:
        print(f"Finding tuition fee URL...")
        tuition_url = get_tuition_fee_url(university_name, website_url)
        print(f"Tuition Fee URL: {tuition_url}")
        
        print(f"Finding graduate tuition...")
        grad_tuition = get_grad_tuition(website_url, university_name)
        print(f"Graduate Tuition: {grad_tuition}")