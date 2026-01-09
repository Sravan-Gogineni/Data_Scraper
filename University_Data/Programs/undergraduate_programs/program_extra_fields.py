import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

tools = [genai.protos.Tool(google_search=genai.protos.Tool.GoogleSearch())]
model = genai.GenerativeModel("gemini-3-pro-preview", tools=tools)

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, 'undergrad_prog_outputs')
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(script_dir, 'undergraduate_programs.csv')
json_path = os.path.join(output_dir, 'extra_fields_data.json')

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

university_name = "Kansas State University"

# Load existing data if the JSON file exists (for resuming)
extra_fields_data = []
processed_programs = set()
if os.path.exists(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            extra_fields_data = json.load(f)
            # Track which programs have already been processed
            for record in extra_fields_data:
                program_name = record.get('Program name')
                if program_name:
                    processed_programs.add(program_name)
        print(f"Loaded {len(extra_fields_data)} existing records from {json_path}")
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
    # Look for JSON object or array
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

for index, row in program_data.iterrows():
    program_name = row['Program name']
    program_page_url = row['Program Page url']
    
    # Skip if already processed
    if program_name in processed_programs:
        print(f"Skipping {program_name} (already processed)")
        continue
    
    prompt = (
        f"You are extracting information about the program '{program_name}' from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website (unh.edu and its subdomains like *.unh.edu). "
        f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
        f"Program URL: {program_page_url}\n\n"
        f"Extract the following fields ONLY if they are present on the official {university_name} website:\n"
        f"1. Concentration name: The specific concentration, specialization, or track name if the program offers concentrations. "
        f"   If no concentration is mentioned, return null.\n"
        f"2. Description: A comprehensive description of the program, its objectives, and what students will learn. "
        f"   Extract the full program description from the official page. If not available, return null.\n"
        f"3. Program website url: The official URL of the program page on unh.edu or its subdomains. "
        f"   This should be a direct link to the program information page. Must be from *.unh.edu domain only.\n"
        f"4. Accreditation status: Any accreditation information mentioned for this specific program. "
        f"   Include the accrediting body name and status if available. If not mentioned, return null.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {program_page_url} or other official {university_name} pages (unh.edu or *.unh.edu subdomains)\n"
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found on the official website, return null for that field\n"
        f"- All URLs must be from the unh.edu domain or its subdomains\n"
        f"- Ensure all extracted text is accurate and verbatim from the source\n\n"
        f"Return the data in a JSON format with the following exact keys: 'Concentration name', 'description', 'program website url', 'Accreditation status'. "
        f"Return a single JSON object, not an array. Use null for any field where information is not available on the official website."
    )
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        parsed_data = parse_json_from_response(response_text)
        
        if parsed_data:
            # Ensure it's a dict, not a list
            if isinstance(parsed_data, list) and len(parsed_data) > 0:
                parsed_data = parsed_data[0]
            
            # Add program name and URL to the data
            parsed_data['Program name'] = program_name
            parsed_data['Program Page url'] = program_page_url
            extra_fields_data.append(parsed_data)
            processed_programs.add(program_name)
            # Save immediately to preserve progress
            save_to_json(extra_fields_data, json_path)
            print(f"✓ Processed and saved: {program_name}")
        else:
            # If parsing failed, store error info
            error_record = {
                'Program name': program_name,
                'Program Page url': program_page_url,
                'Concentration name': None,
                'description': None,
                'program website url': None,
                'Accreditation status': None,
                'error': 'Failed to parse JSON response'
            }
            extra_fields_data.append(error_record)
            processed_programs.add(program_name)
            # Save immediately to preserve progress
            save_to_json(extra_fields_data, json_path)
            print(f"⚠ Warning: Failed to parse JSON for program {program_name} (saved with error)")
    
    except Exception as e:
        print(f"Error processing program {program_name}: {str(e)}")
        error_record = {
            'Program name': program_name,
            'Program Page url': program_page_url,
            'Concentration name': None,
            'description': None,
            'program website url': None,
            'Accreditation status': None,
            'error': str(e)
        }
        extra_fields_data.append(error_record)
        processed_programs.add(program_name)
        # Save immediately to preserve progress even on errors
        save_to_json(extra_fields_data, json_path)
        print(f"✗ Error saved for program {program_name}")

# Final save (redundant but ensures consistency)
save_to_json(extra_fields_data, json_path)

csv_output_path = os.path.join(output_dir, 'extra_fields_data.csv')
if extra_fields_data:
    df = pd.DataFrame(extra_fields_data)
    df.to_csv(csv_output_path, index=False, encoding='utf-8')
    print(f"\nSuccessfully processed {len(extra_fields_data)} programs")
    print(f"Data saved to {json_path} and {csv_output_path}")
else:
    print("No data to save")

