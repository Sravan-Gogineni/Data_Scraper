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
output_dir = os.path.join(script_dir, "Undergrad_prog_outputs")
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(output_dir, 'undergraduate_programs.csv')
json_path = os.path.join(output_dir, 'program_details_financial.json')

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


def extract_program_details(program_name, program_url, institute_url):
    global university_name
    
    prompt = (
        f"You are extracting program details and financial information for the program '{program_name}' "
        f"from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website ({institute_url} and its subdomains). "
        f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
        f"Program URL: {program_url}\n"
        f"Institute URL: {institute_url}\n\n"
        f"Extract the following fields:\n\n"
        f"1. QsWorldRanking: QS World University Ranking (Instance Level). Return as string or number. Return null if not found.\n"
        f"2. School: The specific school or college offering the program (e.g. 'School of Business'). Return string or null.\n"
        f"3. MaxFails: Maximum number of failing grades allowed. Return number or null.\n"
        f"4. MaxGPA: Maximum GPA scale (e.g., 4.0). Return number or null.\n"
        f"5. MinGPA: Minimum GPA required for admission/graduation. Return number or null.\n"
        f"6. PreviousYearAcceptanceRates: Acceptance rate. Return string/number or null.\n"
        f"7. Term: Admission terms (e.g. 'Fall', 'Spring'). Return string or null.\n"
        f"8. LiveDate: Application opening date. Return string or null. look for fall 2026 application opening date\n"
        f"9. DeadlineDate: Application deadline. Return string or null. look for fall 2026 application deadline\n"
        f"10. Fees: Tuition fee for the program. Return a number.\n"
        f"11. AverageScholarshipAmount: Average scholarship amount. Return string/number or null.\n"
        f"12. CostPerCredit: Cost per credit hour for the program. Return string/number or null.\n"
        f"13. ScholarshipAmount: General scholarship amount available. Return string/number or null.\n"
        f"14. ScholarshipPercentage: Scholarship percentage available. Return string/number or null.\n"
        f"15. ScholarshipType: Types of scholarships available (e.g. 'Merit-based'). Return string or null.\n"
        f"16. Program duration: Duration of the program. Return string or null.\n"
        f"Return data in JSON format with exact keys: 'QsWorldRanking', 'School', 'MaxFails', 'MaxGPA', 'MinGPA', "
        f"'PreviousYearAcceptanceRates', 'Term', 'LiveDate', 'DeadlineDate', 'Fees', 'AverageScholarshipAmount', 'CostPerCredit', "
        f"'ScholarshipAmount', 'ScholarshipPercentage', 'ScholarshipType', 'Program duration', 'Tuition fee'."
    )
    
    try:
        response = model.generate_content(prompt)
        parsed = parse_json_from_response(response.text)
        if parsed and isinstance(parsed, dict):
            return parsed
    except Exception as e:
        print(f"Error details extraction: {e}")
    
    # Return empty dict with nulls if fail
    return {
        'QsWorldRanking': None, 'School': None, 'MaxFails': None, 'MaxGPA': None, 'MinGPA': None,
        'PreviousYearAcceptanceRates': None, 'Term': None, 'LiveDate': None, 'DeadlineDate': None,
        'Fees': None, 'AverageScholarshipAmount': None, 'CostPerCredit': None,
        'ScholarshipAmount': None, 'ScholarshipPercentage': None, 'ScholarshipType': None,
        'Program duration': None, 'Tuition fee': None
    }

def process_single_program(row, institute_url):
    """Wrapper to process a single program."""
    program_name = row['Program name']
    program_page_url = row['Program Page url']
    
    try:
        extracted_data = extract_program_details(program_name, program_page_url, institute_url)
        
        extracted_data['Program name'] = program_name
        extracted_data['Program Page url'] = program_page_url
        return extracted_data
    
    except Exception as e:
        return {
            'Program name': program_name,
            'Program Page url': program_page_url,
            'QsWorldRanking': None, 'School': None, 'MaxFails': None, 'MaxGPA': None, 'MinGPA': None,
            'PreviousYearAcceptanceRates': None, 'Term': None, 'LiveDate': None, 'DeadlineDate': None,
            'Fees': None, 'AverageScholarshipAmount': None, 'CostPerCredit': None,
            'ScholarshipAmount': None, 'ScholarshipPercentage': None, 'ScholarshipType': None,
            'Program duration': None, 'Tuition fee': None, 'extraction_level': 'error', 'error': str(e)
        }

def run(university_name_input):
    global university_name, institute_url
    university_name = university_name_input
    
    yield f'{{"status": "progress", "message": "Initializing program details & financial extraction for {university_name}..."}}'
    
    # Quick fetch of website url for context
    try:
        website_url_prompt = f"What is the official university website for {university_name}?"
        institute_url = model.generate_content(website_url_prompt).text.replace("**", "").replace("```", "").strip()
    except:
        institute_url = f"https://www.google.com/search?q={university_name}"

    # Check if CSV file exists
    if not os.path.exists(csv_path):
        yield f'{{"status": "error", "message": "CSV file not found: {csv_path}. Please run Step 1 first."}}'
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
    program_details_data = []
    processed_programs = set()
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                program_details_data = json.load(f)
                for record in program_details_data:
                    program_name = record.get('Program name')
                    if program_name:
                        processed_programs.add(program_name)
            yield f'{{"status": "progress", "message": "Resuming: Loaded {len(program_details_data)} existing records"}}'
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
            extracted_data = process_single_program(row, institute_url)
            
            program_details_data.append(extracted_data)
            processed_programs.add(program_name)
            
            save_to_json(program_details_data, json_path)
            time.sleep(1) # Rate limit handling
        
        except Exception as e:
            error_record = {
                'Program name': program_name,
                'Program Page url': program_page_url,
                'QsWorldRanking': None, 'School': None, 'MaxFails': None, 'MaxGPA': None, 'MinGPA': None,
                'PreviousYearAcceptanceRates': None, 'Term': None, 'LiveDate': None, 'DeadlineDate': None,
                'Fees': None, 'AverageScholarshipAmount': None, 'CostPerCredit': None,
                'ScholarshipAmount': None, 'ScholarshipPercentage': None, 'ScholarshipType': None,
                'Program duration': None, 'Tuition fee': None, 'extraction_level': 'error', 'error': str(e)
            }
            program_details_data.append(error_record)
            processed_programs.add(program_name)
            save_to_json(program_details_data, json_path)

    # Final save
    csv_output_path = os.path.join(output_dir, 'program_details_financial.csv')
    if program_details_data:
        df = pd.DataFrame(program_details_data)
        df.to_csv(csv_output_path, index=False, encoding='utf-8')
        yield f'{{"status": "complete", "message": "Completed extraction for {len(program_details_data)} programs", "files": {{"undergrad_details_csv": "{csv_output_path}"}}}}'
    else:
        yield f'{{"status": "complete", "message": "No data extracted", "files": {{}}}}'
