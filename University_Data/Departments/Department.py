import pandas as pd
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import json
import re

load_dotenv()

# Configure the client (using google-genai SDK)
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Define tools and model globally
def generate_text_safe(prompt):
    try:
        # Configure the search tool explicitly for this call to ensure live data
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],
                response_modalities=["TEXT"]
            )
        )
        
        if response and response.text:
            return response.text.replace("**", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error generating content: {e}")
    return ""

def process_department_extraction(university_name):
    yield f'{{"status": "progress", "message": "Starting department extraction for {university_name}..."}}'
    
    # List of the fields that we need to extract from the website
    fields = [
        "DepartmentName", "Description", "Status", "CollegeId", "CreatedDate", 
        "CreatedBy", "UpdatedDate", "UpdatedBy", "City", "Country", "CountryCode", 
        "CountryName", "Email", "PhoneNumber", "PhoneType", "State", "Street1", 
        "Street2", "ZipCode", "StateName", "MaximumApplicationsPerTerm", 
        "IsRecommendationSystemOpted", "AdmissionUrl", "BuildingName", 
        "BatchId", "IsImportVerified", "IsImported", "CollegeName"
    ]

    # 1. Get Website URL
    yield f'{{"status": "progress", "message": "Finding official website for {university_name}..."}}'
    prompt = f"What is the official university website for {university_name}?"
    try:
        website_url = generate_text_safe(prompt)
        print(f"Website URL: {website_url}")
    except Exception as e:
         yield f'{{"status": "error", "message": "Failed to find website URL: {str(e)}"}}'
         return

    # 2. Extract Departments
    yield f'{{"status": "progress", "message": "Extracting admissions departments from {website_url}..."}}'
    
    # Improved prompt
    prompt = (
        f"You are extracting information about ADMISSIONS DEPARTMENTS ONLY from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website ({website_url} and its subdomains). "
        f"Do NOT use information from any other sources. If the information is not available on the official University of New Hampshire website, return null for that field.\n\n"
        f"Website URL: {website_url}\n\n"
        f"EXTRACTION SCOPE:\n"
        f"- Extract ONLY admissions-related departments and offices\n"
        f"- This includes: Undergraduate Admissions, Graduate Admissions, International Admissions, Transfer Admissions, any school specific admissions offices"
        f"  and any other admissions-specific offices\n"
        f"- DO NOT extract academic departments, student services, or any other non-admissions offices\n"
        f"- If no admissions departments are found, return an empty array []\n\n"
        f"For each admissions department/office found, extract the following fields ONLY if they are present on the official University of New Hampshire website:\n\n"
        f"1. Website_url: The official URL of the admissions office page on {website_url} or its subdomains. "
        f"   Must be from the {university_name} domain only. If not available, return null.\n"
        f"2. DepartmentName: The official name of the admissions office (e.g., 'Undergraduate Admissions', 'Graduate Admissions', etc.). "
        f"   Extract the exact name as it appears on the website. If not available, return null.\n"
        f"3. Email: The primary contact email address for the admissions office. "
        f"   Extract the complete email address. If not available, return null.\n"
        f"4. PhoneNumber: The primary contact phone number for admissions. Include area code and format as provided on the website. "
        f"   If not available, return null.\n"
        f"5. PhoneType: The type of phone number (e.g., 'Mobile', 'Landline', etc.). "
        f"   If not specified, return null.\n"
        f"6. AdmissionUrl: The URL specifically for admissions-related information and application process. "
        f"   Must be from the {university_name} domain only. If not available, return null.\n"
        f"7. BuildingName: The name of the building where the admissions office is located. "
        f"   Extract the exact building name as it appears on the website. If not available, return null.\n"
        f"8. Street1: The primary street address (street number and name) of the admissions office. "
        f"   Extract the complete street address line 1. If not available, return null.\n"
        f"9. Street2: Additional address information (suite number, room number, floor, etc.). "
        f"   If not available, return null.\n"
        f"10. City: The city where the admissions office is located. If not available, return null.\n"
        f"11. State: The state abbreviation (e.g., 'NY' for New York). Extract from the website. If not available, return null.\n"
        f"12. StateName: The full name of the state corresponding to the State abbreviation. "
        f"   You may derive this from the State abbreviation using standard US state mappings (e.g., 'CT' -> 'Connecticut', 'NY' -> 'New York'). "
        f"   If State is not available, return null.\n"
        f"13. Country: The country code or abbreviation (e.g., 'US', 'USA'). "
        f"   If the address is in the United States (based on State, City, or other address context), use 'US' or 'USA'. "
        f"   If the location context clearly indicates another country, use that country's code. If unclear, return null.\n"
        f"14. CountryCode: The ISO country code (e.g., 'US' for United States). "
        f"   If the address is in the United States, use 'US'. If the location context clearly indicates another country, use that country's ISO code. If unclear, return null.\n"
        f"15. CountryName: The full name of the country (e.g., 'United States'). "
        f"   If the address is in the United States, use 'United States'. If the location context clearly indicates another country, use that country's full name. If unclear, return null.\n"
        f"16. ZipCode: The postal/ZIP code. Extract the complete ZIP code including extension if provided. "
        f"    If not available, return null.\n"
        f"17. AirportPickup: Does the admissions office or university provide airport pickup service for international students? "
        f"    Return only 'yes' or 'no', no other text. "
        f"    No fabrication or guessing, just yes or no. "
        f"    Only if this information is explicitly stated in the website, otherwise return null. "
        f"    If not available, return null.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- Extract ONLY admissions departments/offices - ignore all other departments\n"
        f"- All data must be extracted ONLY from {website_url} or other official {university_name} pages\n"
        f"- For most fields: Do NOT infer, assume, or make up any information - extract verbatim from the website\n"
        f"- EXCEPTION for derived fields: StateName can be derived from State abbreviation using standard US state mappings. "
        f"  Country, CountryCode, and CountryName can be derived from location context (e.g., US address -> United States)\n"
        f"- If a field is not found on the official website and cannot be reasonably derived, return null for that field\n"
        f"- All URLs must be from the unh.edu domain or its subdomains\n"
        f"- Ensure all extracted text is accurate and verbatim from the source\n"
        f"- Extract ALL admissions departments/offices found on the website\n"
        f"- Return a JSON array of objects, where each object represents one admissions department/office\n"
        f"- Each object must contain all the fields listed above, using null for missing values\n\n"
        f"Return the data as a JSON array with the following exact keys for each admissions department/office: "
        f"'Website_url', 'DepartmentName', 'Email', 'PhoneNumber', 'PhoneType', 'AdmissionUrl', 'BuildingName', "
        f"'Street1', 'Street2', 'City', 'State', 'StateName', 'Country', 'CountryCode', 'CountryName', 'ZipCode', 'AirportPickup'. "
        f"Use null for any field where information is not available on the official website."
    )

    try:
        response_text = generate_text_safe(prompt)
        
        if not response_text:
            print("Error: Empty response from LLM")
            yield '{"status": "error", "message": "Empty response received from AI model"}'
            return

        print(f"Raw Response: {response_text[:200]}...") # Log start of response for debug

        # Remove markdown code blocks if present (handling residues)
        response_text = response_text.replace("json", "", 1) if response_text.startswith("json") else response_text
        response_text = response_text.replace("```", "").strip()
        
        # Parse the JSON response
        try:
             # Try to extract JSON from the response
             json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
             if json_match:
                 json_str = json_match.group(0)
                 departments_data = json.loads(json_str)
             else:
                 departments_data = json.loads(response_text)
                 
             if not isinstance(departments_data, list):
                 if isinstance(departments_data, dict):
                     departments_data = [departments_data]
                 else:
                     departments_data = []

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            yield f'{{"status": "error", "message": "Failed to parse AI response"}}'
            return

        yield f'{{"status": "progress", "message": "Successfully extracted {len(departments_data)} departments"}}'
        
        # Create DataFrame
        if departments_data:
            df = pd.DataFrame(departments_data)
            
            # Ensure all expected columns are present
            for field in fields:
                if field not in df.columns:
                    df[field] = None
            
            # Set specific default values
            df['IsImportVerified'] = False
            df['IsImported'] = False
            df['IsRecommendationSystemOpted'] = False
            df['CollegeName'] = university_name
    
            # Reorder columns
            df = df[fields]
            
            # Save to CSV and JSON
            
            # Use absolute path based on the script location for consistency with app.py
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(script_dir, "Dept_outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            safe_name = university_name.replace(" ", "_")
            csv_path = os.path.join(output_dir, f"{safe_name}_departments.csv")
            json_path = os.path.join(output_dir, f"{safe_name}_departments.json")
            
            df.to_csv(csv_path, index=False, encoding="utf-8")
            
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(departments_data, jf, indent=4)
                
            yield f'{{"status": "complete", "files": {{"csv": "{csv_path}", "json": "{json_path}"}}}}'
            
        else:
            yield '{"status": "complete", "message": "No departments found", "files": {}}'

    except Exception as e:
        yield f'{{"status": "error", "message": "Error processing data: {str(e)}"}}'
