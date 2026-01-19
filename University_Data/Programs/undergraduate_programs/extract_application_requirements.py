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
output_dir = os.path.join(script_dir, "Undergrad_prog_outputs")
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(output_dir, 'undergraduate_programs.csv')
json_path = os.path.join(output_dir, 'application_requirements.json')

university_name = None
institute_url = None

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
    application_requirements_page_url = None
    prompt = """ Find the website url of the application requirements page for the program '{program_name}' from the official {university_name} website. Return the url if found, otherwise return null. """
    prompt_institute_level = """ Find the Application Requirements page url for the {university_name} website. Return the url if found, otherwise return null. """
    response = model.generate_content(prompt)
    response_text = response.text
    parsed_data = parse_json_from_response(response_text)
    if parsed_data and isinstance(parsed_data, dict):
        application_requirements_page_url = parsed_data.get('application_requirements_page_url')
    else:
        response = model.generate_content(prompt_institute_level)
        response_text = response.text
        parsed_data = parse_json_from_response(response_text)
        if parsed_data and isinstance(parsed_data, dict):
            application_requirements_page_url = parsed_data.get('application_requirements_page_url')
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
        f"5. IsAnalyticalNotRequired: MANDATORY BOOLEAN. Is analytical writing section not required? Return true or false.\n"
        f"6. IsAnalyticalOptional: MANDATORY BOOLEAN. Is analytical writing section optional if it's optional? Return true or false.\n"
        f"7. IsStemProgram: MANDATORY BOOLEAN. Is this a STEM program? Return true or false.\n"
        f"8. IsACTRequired: MANDATORY BOOLEAN. Is ACT required to apply for {program_name}? Return true if required, false if not required, or null if not specified.\n"
        f"9. IsSATRequired: MANDATORY BOOLEAN. Is SAT required to apply for {program_name}? Return true if required, false if not required, or null if not specified.\n"
        f"10. MinimumACTScore: Minimum required ACT score required to apply for {program_name} as a number. Return null if not specified.\n"
        f"11. MinimumSATScore: Minimum required SAT score required to apply for {program_name} as a number. Return null if not specified.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {program_url} or other official {university_name} pages\n"
        f"- Extract information SPECIFIC to this program '{program_name}'\n"
        f"- Browse all "
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found on the program page, return null for that field\n"
        f"- All URLs must be from the {university_name} domain or its subdomains\n"
        f"- Ensure all extracted text is accurate and verbatim from the source\n"
        f"- FOR MANDATORY BOOLEAN FIELDS: You MUST return true or false. Do not return null unless absolutely no information is available. If not mentioned as required, default to false.\n\n"
        f"Return the data in a JSON format with the following exact keys: "
        f"'Resume', 'StatementOfPurpose', 'Requirements', 'WritingSample', 'IsAnalyticalNotRequired', "
        f"'IsAnalyticalOptional', 'IsStemProgram', 'IsACTRequired', "
        f"'IsSATRequired', 'MinimumACTScore', 'MinimumSATScore'. "
        f"Return a single JSON object, not an array. Use null for non-boolean fields if info not available."
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
        f"6. IsAnalyticalOptional: Boolean (true/false) - Is analytical writing section optional if it's optional? Return true, false, or null.\n"
        f"7. IsStemProgram: Boolean (true/false) - This field should be null at institute level (program-specific). Return null.\n"
        f"8. IsACTRequired: Boolean (true/false) - Is ACT exam required for this program to apply? Return true, false, or null.\n"
        f"9. IsSATRequired: Boolean (true/false) - Is SAT exam required for this program to apply? Return true, false, or null.\n"
        f"10. MinimumACTScore: Minimum required ACT score as a number. Return null if not specified.\n"
        f"11. MinimumSATScore: Minimum required SAT score as a number. Return null if not specified.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {institute_url} or other official {university_name} pages\n"
        f"- Extract GENERAL/INSTITUTE-LEVEL requirements (not program-specific)\n"
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found, return null for that field\n"
        f"- All URLs must be from the {university_name} domain or its subdomains\n\n"
        f"Return the data in a JSON format with the following exact keys: "
        f"'Resume', 'StatementOfPurpose', 'Requirements', 'WritingSample', 'IsAnalyticalNotRequired', "
        f"'IsAnalyticalOptional', 'IsStemProgram', 'IsACTRequired', "
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
        'IsAnalyticalNotRequired': False, 'IsAnalyticalOptional': False, 'IsRecommendationSystemOpted': False,
        'IsStemProgram': False, 'IsACTRequired': False, 'IsSATRequired': False,
        'MinimumACTScore': None, 'MinimumSATScore': None, 'extraction_level': 'none'
    }

# Institute level URL for fallback
def run(university_name_input):
    global university_name, institute_url
    university_name = university_name_input
    
    yield f'{{"status": "progress", "message": "Initializing application requirements extraction for {university_name}..."}}'
    
    # Quick fetch of website url for context
    try:
        website_url_prompt = f"What is the official university website for {university_name}?"
        institute_url = model.generate_content(website_url_prompt).text.replace("**", "").replace("```", "").strip()
    except:
        institute_url = f"https://www.google.com/search?q={university_name}"

    # Check if CSV file exists
    if not os.path.exists(csv_path):
        yield f'{{"status": "complete", "message": "CSV file not found: {csv_path}. Skipping Step.", "files": {{}}}}'
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
    application_data = []
    processed_programs = set()
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                application_data = json.load(f)
                for record in application_data:
                    program_name = record.get('Program name')
                    if program_name:
                        processed_programs.add(program_name)
            yield f'{{"status": "progress", "message": "Resuming: Loaded {len(application_data)} existing records"}}'
        except Exception as e:
            pass

    # Filter out already processed programs
    programs_to_process = []
    for index, row in program_data.iterrows():
        if row['Program name'] not in processed_programs:
            programs_to_process.append(row)

    total_programs = len(program_data)
    processed_count = len(processed_programs)
    
    if not programs_to_process:
         yield f'{{"status": "progress", "message": "All {total_programs} programs already processed. Skipping extraction."}}'
    else:
         yield f'{{"status": "progress", "message": "Starting extraction for {total_programs} programs ({len(programs_to_process)} remaining)..."}}'

    for index, row in program_data.iterrows():
        program_name = row['Program name']
        program_page_url = row['Program Page url']
        
        if program_name in processed_programs:
            continue
        
        processed_count += 1
        yield f'{{"status": "progress", "message": "Processing [{processed_count}/{total_programs}]: {program_name}"}}'
        
        try:
            extracted_data = extract_application_requirements(program_name, program_page_url, institute_url)
            
            extracted_data['Program name'] = program_name
            extracted_data['Program Page url'] = program_page_url
            application_data.append(extracted_data)
            processed_programs.add(program_name)
            
            save_to_json(application_data, json_path)
            time.sleep(1) # Rate limit handling
        
        except Exception as e:
            error_record = {
                'Program name': program_name, 'Program Page url': program_page_url,
                'Resume': None, 'StatementOfPurpose': None, 'Requirements': None, 'WritingSample': None,
                'IsAnalyticalNotRequired': None, 'IsAnalyticalOptional': None, 'IsRecommendationSystemOpted': None,
                'IsStemProgram': None, 'IsACTRequired': None, 'IsSATRequired': None,
                'MinimumACTScore': None, 'MinimumSATScore': None, 'extraction_level': 'error', 'error': str(e)
            }
            application_data.append(error_record)
            processed_programs.add(program_name)
            save_to_json(application_data, json_path)

    # Final save
    csv_output_path = os.path.join(output_dir, 'application_requirements.csv')
    if application_data:
        df = pd.DataFrame(application_data)
        df.to_csv(csv_output_path, index=False, encoding='utf-8')
        yield f'{{"status": "complete", "message": "Completed extraction for {len(application_data)} programs", "files": {{"undergrad_app_req_csv": "{csv_output_path}"}}}}'
    else:
        yield f'{{"status": "complete", "message": "No data extracted", "files": {{}}}}'
