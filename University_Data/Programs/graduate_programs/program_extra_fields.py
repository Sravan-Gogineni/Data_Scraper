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
output_dir = os.path.join(script_dir, "Grad_prog_outputs")
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(output_dir, 'graduate_programs.csv')
json_path = os.path.join(output_dir, 'extra_fields_data.json')


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

def process_single_program(row, university_name):
    """Process a single program to extract extra fields."""
    program_name = row['Program name']
    program_page_url = row['Program Page url']
    
    prompt = (
        f"You are extracting information about the program '{program_name}' from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website. "
        f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
        f"Program URL: {program_page_url}\n\n"
        f"Extract the following fields ONLY if they are present on the official {university_name} website:\n"
        f"1. Concentration name: The specific concentration, specialization, or track name if the program offers concentrations. "
        f"   If no concentration is mentioned, return null.\n"
        f"2. Description: A comprehensive description of the program, its objectives, and what students will learn. "
        f"   Extract the full program description from the official page. If not available, return null.\n"
        f"3. Program website url: The official URL of the program page on {university_name} website. "
        f"   This should be a direct link to the program information page. Must be from official domain only.\n"
        f"4. Accreditation status: Any accreditation information mentioned for this specific program. "
        f"   Include the accrediting body name and status if available. If not mentioned, return null.\n\n"
        f"5. Level: The level of the program. The level can be either any of these and these are just examples : Masters, Doctoral, Associate,Certificate,MA,Minor,PhD,MBA,MFA."
        f"   This should be determined from the {program_page_url} when you are extracting there itself distingnuish the program level. If not mentioned, return null.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {program_page_url} or other official {university_name} pages\n"
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found on the official website, return null for that field\n"
        f"- All URLs must be from the {university_name} domain or its subdomains\n"
        f"- Ensure all extracted text is accurate and verbatim from the source\n\n"
        f"Return the data in a JSON format with the following exact keys: 'Concentration name', 'description', 'program website url', 'Accreditation status'. "
        f"Return a single JSON object, not an array. Use null for any field where information is not available on the official website."
    )
    
    try:
        print(f"[DEBUG] Generating content for program: {program_name} using model {model.model_name}")
        response = model.generate_content(prompt)
        print(f"[DEBUG] Received response for program: {program_name}")
        response_text = response.text
        parsed_data = parse_json_from_response(response_text)
        
        if parsed_data:
            if isinstance(parsed_data, list) and len(parsed_data) > 0:
                parsed_data = parsed_data[0]
            
            parsed_data['Program name'] = program_name
            parsed_data['Program Page url'] = program_page_url
            return parsed_data
        else:
            return {
                'Program name': program_name, 'Program Page url': program_page_url,
                'Concentration name': None, 'description': None, 'program website url': None,
                'Accreditation status': None, 'error': 'Failed to parse JSON response'
            }
    
    except Exception as e:
        return {
            'Program name': program_name, 'Program Page url': program_page_url,
            'Concentration name': None, 'description': None, 'program website url': None,
            'Accreditation status': None, 'error': str(e)
        }

def run(university_name_input):
    global university_name
    university_name = university_name_input
    
    # Check if CSV file exists
    # Check if CSV file exists
    if not os.path.exists(csv_path):
        yield f'{{"status": "complete", "message": "CSV file not found: {csv_path}. Skipping Step 2.", "files": {{}}}}'
        return

    program_data = pd.read_csv(csv_path)

    if program_data.empty:
        yield f'{{"status": "error", "message": "CSV file is empty. Please check Step 1 results."}}'
        return

    # Check if required columns exist
    required_columns = ['Program name', 'Program Page url']
    missing_columns = [col for col in required_columns if col not in program_data.columns]
    if missing_columns:
        yield f'{{"status": "error", "message": "Missing columns: {", ".join(missing_columns)}"}}'
        return
        
    # Load existing data
    extra_fields_data = []
    processed_programs = set()
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                extra_fields_data = json.load(f)
                for record in extra_fields_data:
                    program_name = record.get('Program name')
                    if program_name:
                        processed_programs.add(program_name)
            yield f'{{"status": "progress", "message": "Resuming: Loaded {len(extra_fields_data)} existing records"}}'
        except Exception as e:
            pass

    # Filter out already processed programs
    programs_to_process = []
    for index, row in program_data.iterrows():
        if row['Program name'] not in processed_programs:
            programs_to_process.append(row)

    total_programs = len(program_data)
    processed_count = len(processed_programs)
    
    yield f'{{"status": "progress", "message": "Starting extraction for {total_programs} programs ({len(programs_to_process)} remaining)..."}}'

    for index, row in program_data.iterrows():
        program_name = row['Program name']
        program_page_url = row['Program Page url']
        
        if program_name in processed_programs:
            continue
        
        processed_count += 1
        yield f'{{"status": "progress", "message": "Processing [{processed_count}/{total_programs}]: {program_name}"}}'
        
        try:
            result = process_single_program(row, university_name)
            
            # Update shared data structures
            extra_fields_data.append(result)
            processed_programs.add(program_name)
            
            # Save progress (thread-safe due to lock in save_to_json)
            save_to_json(extra_fields_data, json_path)
            time.sleep(1) # Rate limit handling
            
        except Exception as e:
            yield f'{{"status": "warning", "message": "Error processing {program_name}: {str(e)}"}}'

    # Final save
    csv_output_path = os.path.join(output_dir, 'extra_fields_data.csv')
    if extra_fields_data:
        df = pd.DataFrame(extra_fields_data)
        df.to_csv(csv_output_path, index=False, encoding='utf-8')
        yield f'{{"status": "complete", "message": "Completed extraction for {len(extra_fields_data)} programs", "files": {{"grad_extra_csv": "{csv_output_path}"}}}}'
    else:
        yield f'{{"status": "complete", "message": "No data extracted", "files": {{}}}}'