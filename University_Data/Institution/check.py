
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import sys

# Add current directory to path to allow importing Institution
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from Institution import GeminiModelWrapper, client

load_dotenv()

# 1. Update the initialization with a valid model name
# 'gemini-2.0-flash' is generally fastest and most cost-effective for search
model = GeminiModelWrapper(client, "gemini-2.5-flash") 

# 2. Refined generate_content to print the actual Search Entry Point (the UI snippet)
def generate_content(self, prompt):
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

    # This is how you verify it worked:
    # Grounding metadata contains the search chunks and the HTML snippet for the search box
    if response.candidates and response.candidates[0].grounding_metadata:
        print("\n--- GROUNDING CHECK ---")
        print("Search was performed successfully.")
        # This shows the text that would appear in a 'Google Search' button
        if response.candidates[0].grounding_metadata.search_entry_point:
            print(f"Search Query used: {response.candidates[0].grounding_metadata.search_entry_point.rendered_content}")
        print("-----------------------\n")
        
    return response

# Re-assign the fixed method to your wrapper
GeminiModelWrapper.generate_content = generate_content

def generate_text_safe(prompt):
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.replace("**", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error generating content: {e}")
    return ""

# 3. The Test Execution
print("Starting live search test...")
test_prompt
result = generate_text_safe(test_prompt)

print("RESULT FROM MODEL:")
print(result)