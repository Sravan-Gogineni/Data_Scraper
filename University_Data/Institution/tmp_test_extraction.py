from pydantic import BaseModel, Field
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    vertexai=True, 
    project=os.getenv("GCP_PROJECT"), 
    location=os.getenv("GCP_REGION")
)

Model = os.getenv("MODEL")

class UniversityDetails(BaseModel):
    CollegeName: str = Field(description="The exact official name of the university.")
    Phone: str = Field(description="The primary contact phone number for the university. Return empty string if not found.")
    Email: str = Field(description="The primary contact email address for the university. Return empty string if not found.")
    SecondaryEmail: str = Field(description="A secondary contact email address for the university. Return empty string if not found.")
    Street1: str = Field(description="The primary street address (e.g., '123 Main St'). Return empty string if not found.")
    Street2: str = Field(description="Secondary address information such as suite or building. Return empty string if not found.")
    County: str = Field(description="The county where the university is located. Return empty string if not found.")
    City: str = Field(description="The city where the university is located. Return empty string if not found.")
    State: str = Field(description="The state where the university is located. Return empty string if not found.")
    Country: str = Field(description="The country where the university is located. Return empty string if not found.")
    ZipCode: str = Field(description="The zip or postal code. Return empty string if not found.")

def test_extraction(university_name):
    print(f"Testing extraction for {university_name}")
    grounding_prompt = f"Find the official, exact name and the main official website URL for the university commonly known as '{university_name}'. Return ONLY a JSON string with keys 'exact_name' and 'url'."
    
    grounding_config = GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
    )
    
    grounding_response = client.models.generate_content(
        model=Model, 
        contents=grounding_prompt, 
        config=grounding_config
    )
    
    text = grounding_response.text.strip()
    try:
        # Assuming the model returns markdown JSON block or just JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        ground_truth = json.loads(text)
        exact_name = ground_truth.get("exact_name", university_name)
        url = ground_truth.get("url", "")
    except Exception as e:
        print("Error parsing ground truth:", e)
        exact_name = university_name
        url = ""
    
    print(f"Ground truth found: Name={exact_name}, URL={url}")

    extraction_prompt = (
        f"You are a strict data extractor. Use the following ground truths:\n"
        f"- Exact Name: {exact_name}\n"
        f"- Official URL: {url}\n\n"
        f"Using primarily these ground truths and the official website, extract exactly "
        f"the required fields for this university. "
        f"Do not hallucinate. Use empty strings for any information that genuinely cannot be found.\n"
        f"You MUST return ONLY a valid JSON object matching this schema, with no additional text or markdown formatting:\n"
        f'{json.dumps(UniversityDetails.model_json_schema(), indent=2)}'
    )
    
    extraction_config = GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
    )
    
    extraction_response = client.models.generate_content(
        model=Model,
        contents=extraction_prompt,
        config=extraction_config
    )
    
    ext_text = extraction_response.text.strip()
    try:
        if "```json" in ext_text:
            ext_text = ext_text.split("```json")[1].split("```")[0].strip()
        elif "```" in ext_text:
             ext_text = ext_text.split("```")[1].strip()
             if ext_text.startswith("json"):
                 ext_text = ext_text[4:].strip()
        result = json.loads(ext_text)
    except Exception as e:
        print("Error parsing final result:", e)
        print("Raw output:", ext_text)
        result = {}
    print("Final Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_extraction("MIT")
