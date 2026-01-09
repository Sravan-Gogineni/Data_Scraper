import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
import time

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

tools = [genai.protos.Tool(google_search=genai.protos.Tool.GoogleSearch())]
model = genai.GenerativeModel("gemini-2.5-pro", tools=tools)

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# output_dir = "/home/my-laptop/scraper/Quinnipiac_university/Programs/graduate_programs/Grad_prog_outputs"
output_dir = os.path.join(script_dir, "Grad_prog_outputs")
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(script_dir, 'graduate_programs.csv')
json_path = os.path.join(output_dir, 'application_requirements.json')

# Check if CSV file exists
if not os.path.exists(csv_path):
    print(f"ERROR: CSV file not found: {csv_path}")
    print("Please create a CSV file with columns: 'Program name', 'Program Page url'")
    exit(1)

program_data = pd.read_csv(csv_path)

# Check if CSV has data
if program_data.empty:
    print(f"WARNING: CSV file is empty: {csv_path}")
    exit(1)

# Check if required columns exist
required_columns = ['Program name', 'Program Page url']
missing_columns = [col for col in required_columns if col not in program_data.columns]
if missing_columns:
    print(f"ERROR: CSV file is missing required columns: {', '.join(missing_columns)}")
    exit(1)

# Institute level URL for fallback
institute_url = "https://www.k-state.edu/"
university_name = "Kansas State University"

# Load existing data if the JSON file exists (for resuming)
application_data = []
processed_programs = set()
if os.path.exists(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            application_data = json.load(f)
            # Track which programs have already been processed
            for record in application_data:
                program_name = record.get('Program name')
                if program_name:
                    processed_programs.add(program_name)
        print(f"Loaded {len(application_data)} existing records from {json_path}")
    except Exception as e:
        print(f"Warning: Could not load existing JSON file: {e}")

def save_to_json(data, filepath):
    """Save data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def parse_json_from_response(text):
    """Parse JSON from Gemini response, handling markdown code blocks."""
    # Remove markdown formatting
    text = text.replace("**", "").replace("```json", "").replace("```", "").strip()
    
    # Try to extract JSON from the text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # If no match, try parsing the whole text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

def extract_application_requirements(program_name, program_url, institute_url):
    """Extract application requirements and documents, first from program level, then institute level."""
    
    # First, try program level
    prompt_program = (
        f"You are extracting application requirements and required documents for the program '{program_name}' "
        f"from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website ({institute_url} and its subdomains). "
        f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
        f"Program URL: {program_url}\n\n"
        f"Extract the following fields ONLY if they are present on the official {university_name} website for THIS SPECIFIC PROGRAM:\n\n"
        f"1. Resume: Is a resume/CV required? Return 'Required', 'Optional', 'Not Required', or null.\n"
        f"2. StatementOfPurpose: Is a statement of purpose required? Return 'Required', 'Optional', 'Not Required', or null.\n"
        f"3. Requirements: General application requirements text/description. Return null if not specified.\n"
        f"4. WritingSample: Is a writing sample required? Return 'Required', 'Optional', 'Not Required', or null.\n"
        f"5. IsAnalyticalNotRequired: Boolean (true/false) - Is analytical writing section not required? Return true, false, or null.\n"
        f"6. IsAnalyticalOptional: Boolean (true/false) - Is analytical writing section optional? Return true, false, or null.\n"
        f"7. IsRecommendationSystemOpted: Boolean (true/false) - Is a recommendation system/letters of recommendation used? Return true, false, or null.\n"
        f"8. IsStemProgram: Boolean (true/false) - Is this a STEM program? Return true, false, or null.\n"
        f"9. IsACTRequired: Boolean (true/false) - Is ACT required? Return true, false, or null.\n"
        f"10. IsSATRequired: Boolean (true/false) - Is SAT required? Return true, false, or null.\n"
        f"11. MinimumACTScore: Minimum required ACT score as a number. Return null if not specified.\n"
        f"12. MinimumSATScore: Minimum required SAT score as a number. Return null if not specified.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {program_url} or other official {university_name} pages\n"
        f"- Extract information SPECIFIC to this program '{program_name}'\n"
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found on the program page, return null for that field\n"
        f"- All URLs must be from the {university_name} domain or its subdomains\n"
        f"- Ensure all extracted text is accurate and verbatim from the source\n\n"
        f"Return the data in a JSON format with the following exact keys: "
        f"'Resume', 'StatementOfPurpose', 'Requirements', 'WritingSample', 'IsAnalyticalNotRequired', "
        f"'IsAnalyticalOptional', 'IsRecommendationSystemOpted', 'IsStemProgram', 'IsACTRequired', "
        f"'IsSATRequired', 'MinimumACTScore', 'MinimumSATScore'. "
        f"Return a single JSON object, not an array. Use null for any field where information is not available on the official website."
    )
    
    try:
        response = model.generate_content(prompt_program)
        response_text = response.text
        parsed_data = parse_json_from_response(response_text)
        
        if parsed_data and isinstance(parsed_data, dict):
            # Check if we got any non-null values
            has_data = any(v is not None and v != "" for v in parsed_data.values())
            
            if has_data:
                parsed_data['extraction_level'] = 'program'
                return parsed_data
    except Exception as e:
        print(f"  Error extracting from program level: {str(e)}")
    
    # If no data found at program level, try institute level
    print(f"  No program-specific data found, trying institute level...")
    prompt_institute = (
        f"You are extracting general application requirements and required documents "
        f"from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website ({institute_url} and its subdomains). "
        f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
        f"Institute URL: {institute_url}\n\n"
        f"Extract the following fields ONLY if they are present on the official {university_name} website as GENERAL/INSTITUTE-LEVEL requirements:\n\n"
        f"1. Resume: Is a resume/CV generally required? Return 'Required', 'Optional', 'Not Required', or null.\n"
        f"2. StatementOfPurpose: Is a statement of purpose generally required? Return 'Required', 'Optional', 'Not Required', or null.\n"
        f"3. Requirements: General application requirements text/description. Return null if not specified.\n"
        f"4. WritingSample: Is a writing sample generally required? Return 'Required', 'Optional', 'Not Required', or null.\n"
        f"5. IsAnalyticalNotRequired: Boolean (true/false) - Is analytical writing section not required? Return true, false, or null.\n"
        f"6. IsAnalyticalOptional: Boolean (true/false) - Is analytical writing section optional? Return true, false, or null.\n"
        f"7. IsRecommendationSystemOpted: Boolean (true/false) - Is a recommendation system/letters of recommendation used? Return true, false, or null.\n"
        f"8. IsStemProgram: Boolean (true/false) - This field should be null at institute level (program-specific). Return null.\n"
        f"9. IsACTRequired: Boolean (true/false) - Is ACT required? Return true, false, or null.\n"
        f"10. IsSATRequired: Boolean (true/false) - Is SAT required? Return true, false, or null.\n"
        f"11. MinimumACTScore: Minimum required ACT score as a number. Return null if not specified.\n"
        f"12. MinimumSATScore: Minimum required SAT score as a number. Return null if not specified.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {institute_url} or other official {university_name} pages\n"
        f"- Extract GENERAL/INSTITUTE-LEVEL requirements (not program-specific)\n"
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found, return null for that field\n"
        f"- All URLs must be from the {university_name} domain or its subdomains\n\n"
        f"Return the data in a JSON format with the following exact keys: "
        f"'Resume', 'StatementOfPurpose', 'Requirements', 'WritingSample', 'IsAnalyticalNotRequired', "
        f"'IsAnalyticalOptional', 'IsRecommendationSystemOpted', 'IsStemProgram', 'IsACTRequired', "
        f"'IsSATRequired', 'MinimumACTScore', 'MinimumSATScore'. "
        f"Return a single JSON object, not an array. Use null for any field where information is not available on the official website."
    )
    
    try:
        response = model.generate_content(prompt_institute)
        response_text = response.text
        parsed_data = parse_json_from_response(response_text)
        
        if parsed_data and isinstance(parsed_data, dict):
            parsed_data['extraction_level'] = 'institute'
            return parsed_data
    except Exception as e:
        print(f"  Error extracting from institute level: {str(e)}")
    
    # Return empty dict with null values if nothing found
    return {
        'Resume': None, 'StatementOfPurpose': None, 'Requirements': None, 'WritingSample': None,
        'IsAnalyticalNotRequired': None, 'IsAnalyticalOptional': None, 'IsRecommendationSystemOpted': None,
        'IsStemProgram': None, 'IsACTRequired': None, 'IsSATRequired': None,
        'MinimumACTScore': None, 'MinimumSATScore': None, 'extraction_level': 'none'
    }

for index, row in program_data.iterrows():
    program_name = row['Program name']
    program_page_url = row['Program Page url']
    
    # Skip if already processed
    if program_name in processed_programs:
        print(f"Skipping {program_name} (already processed)")
        continue
    
    print(f"Processing: {program_name}")
    
    try:
        extracted_data = extract_application_requirements(program_name, program_page_url, institute_url)
        
        # Add program name and URL to the data
        extracted_data['Program name'] = program_name
        extracted_data['Program Page url'] = program_page_url
        application_data.append(extracted_data)
        processed_programs.add(program_name)
        
        # Save immediately to preserve progress
        save_to_json(application_data, json_path)
        print(f"✓ Processed and saved: {program_name} (level: {extracted_data.get('extraction_level', 'unknown')})")
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    except Exception as e:
        print(f"Error processing program {program_name}: {str(e)}")
        error_record = {
            'Program name': program_name,
            'Program Page url': program_page_url,
            'Resume': None, 'StatementOfPurpose': None, 'Requirements': None, 'WritingSample': None,
            'IsAnalyticalNotRequired': None, 'IsAnalyticalOptional': None, 'IsRecommendationSystemOpted': None,
            'IsStemProgram': None, 'IsACTRequired': None, 'IsSATRequired': None,
            'MinimumACTScore': None, 'MinimumSATScore': None, 'extraction_level': 'error', 'error': str(e)
        }
        application_data.append(error_record)
        processed_programs.add(program_name)
        save_to_json(application_data, json_path)
        print(f"✗ Error saved for program {program_name}")

# Final save
save_to_json(application_data, json_path)

# Also save as CSV
csv_output_path = os.path.join(output_dir, 'application_requirements.csv')
if application_data:
    df = pd.DataFrame(application_data)
    df.to_csv(csv_output_path, index=False, encoding='utf-8')
    print(f"\nSuccessfully processed {len(application_data)} programs")
    print(f"Data saved to {json_path} and {csv_output_path}")
else:
    print("No data to save")

