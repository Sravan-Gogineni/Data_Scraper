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
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(script_dir, 'graduate_programs.csv')
json_path = os.path.join(output_dir, 'program_details_financial.json')

# Check if CSV file exists
if not os.path.exists(csv_path):
    print(f"ERROR: CSV file not found: {csv_path}")
    print("Please create a CSV file with columns: 'Program name', 'Program Page url'")
    print("Example:")
    print("Program name,Program Page url")
    print("Computer Science,https://example.com/cs")
    exit(1)

program_data = pd.read_csv(csv_path)

# Check if CSV has data
if program_data.empty:
    print(f"WARNING: CSV file is empty: {csv_path}")
    print("Please add program data to the CSV file.")
    exit(1)

# Check if required columns exist
required_columns = ['Program name', 'Program Page url']
missing_columns = [col for col in required_columns if col not in program_data.columns]
if missing_columns:
    print(f"ERROR: CSV file is missing required columns: {', '.join(missing_columns)}")
    print(f"Required columns: {', '.join(required_columns)}")
    exit(1)

# Institute level URL for fallback
institute_url = "https://www.k-state.edu/"
university_name = "Kansas State University"
# Load existing data if the JSON file exists (for resuming)
program_details_data = []
processed_programs = set()
if os.path.exists(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            program_details_data = json.load(f)
            # Track which programs have already been processed
            for record in program_details_data:
                program_name = record.get('Program name')
                if program_name:
                    processed_programs.add(program_name)
        print(f"Loaded {len(program_details_data)} existing records from {json_path}")
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

def extract_program_details(program_name, program_url, institute_url):
    """Extract program details, rankings, and financial information.
    For Tuition fee and CostPerCredit: ONLY program level (no fallback).
    For other fields: first program level, then institute level."""
    
    # Fields that should ONLY be extracted at program level (no fallback)
    program_only_fields = ['Tuition fee', 'CostPerCredit']
    
    # First, try program level for ALL fields
    prompt_program = (
        f"You are extracting program details, rankings, GPA requirements, deadlines, and financial information "
        f"for the program '{program_name}' from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website ({institute_url} and its subdomains). "
        f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
        f"Program URL: {program_url}\n\n"
        f"Extract the following fields ONLY if they are present on the official {university_name} website for THIS SPECIFIC PROGRAM:\n\n"
        f"1. QsWorldRanking: QS World University Ranking for the university. Return as number or null.\n"
        f"2. School: The school/college/department name that offers this program. Return null if not specified.\n"
        f"3. MaxFails: Maximum number of failed courses allowed. Return as number or null.\n"
        f"4. MaxGPA: Maximum GPA requirement or limit. Return as number (typically 0-4.0 scale) or null.\n"
        f"5. MinGPA: Minimum GPA requirement. Return as number (typically 0-4.0 scale) or null.\n"
        f"6. PreviousYearAcceptanceRates: Acceptance rate from previous year(s). Return as percentage (number) or null.\n"
        f"7. Term: Application terms available (e.g., 'Fall', 'Spring', 'Summer', 'Fall, Spring'). Return as string or null.\n"
        f"8. LiveDate: Program start date or live date. Return as date string (YYYY-MM-DD format preferred) or null.\n"
        f"9. DeadlineDate: Application deadline date. Return as date string (YYYY-MM-DD format preferred) or null.\n"
        f"10. Fees: Application fees or other fees. Return as number (dollar amount) or null.\n"
        f"11. AverageScholarshipAmount: Average scholarship amount offered. Return as number (dollar amount) or null.\n"
        f"12. CostPerCredit: Cost per credit hour for THIS SPECIFIC PROGRAM. Return as number (dollar amount) or null. "
        f"   IMPORTANT: This must be program-specific, not general university tuition.\n"
        f"13. ScholarshipAmount: Scholarship amount available. Return as number (dollar amount) or null.\n"
        f"14. ScholarshipPercentage: Scholarship percentage. Return as number (percentage) or null.\n"
        f"15. ScholarshipType: Type of scholarship (e.g., 'Merit-based', 'Need-based', 'Graduate Assistantship'). Return as string or null.\n"
        f"16. Program duration: Duration of the program (e.g., '2 years', '36 credits', '4 semesters'). Return as string or null.\n"
        f"17. Tuition fee: Total tuition fee for THIS SPECIFIC PROGRAM. Return as number (dollar amount) or null. "
        f"   IMPORTANT: This must be program-specific tuition, not general university tuition. "
        f"   If only general university tuition is available, return null.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {program_url} or other official {university_name} pages\n"
        f"- Extract information SPECIFIC to this program '{program_name}'\n"
        f"- For 'Tuition fee' and 'CostPerCredit': These MUST be program-specific. If only general university tuition is mentioned, return null.\n"
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found on the program page, return null for that field\n"
        f"- All URLs must be from the {university_name} domain or its subdomains\n"
        f"- Ensure all extracted text is accurate and verbatim from the source\n\n"
        f"Return the data in a JSON format with the following exact keys: "
        f"'QsWorldRanking', 'School', 'MaxFails', 'MaxGPA', 'MinGPA', 'PreviousYearAcceptanceRates', "
        f"'Term', 'LiveDate', 'DeadlineDate', 'Fees', 'AverageScholarshipAmount', 'CostPerCredit', "
        f"'ScholarshipAmount', 'ScholarshipPercentage', 'ScholarshipType', 'Program duration', 'Tuition fee'. "
        f"Return a single JSON object, not an array. Use null for any field where information is not available on the official website."
    )
    
    program_data_result = {}
    try:
        response = model.generate_content(prompt_program)
        response_text = response.text
        parsed_data = parse_json_from_response(response_text)
        
        if parsed_data and isinstance(parsed_data, dict):
            program_data_result = parsed_data
            # Check if we got any non-null values (excluding program-only fields)
            non_program_only_fields = {k: v for k, v in parsed_data.items() if k not in program_only_fields}
            has_data = any(v is not None and v != "" for v in non_program_only_fields.values())
            
            if has_data:
                program_data_result['extraction_level'] = 'program'
    except Exception as e:
        print(f"  Error extracting from program level: {str(e)}")
    
    # For fields other than program-only fields, try institute level if not found
    # But ONLY if we didn't get program-level data for those fields
    institute_data_result = {}
    
    # Check which fields need institute-level fallback (excluding program-only fields)
    fields_needing_fallback = []
    for field in ['QsWorldRanking', 'School', 'MaxFails', 'MaxGPA', 'MinGPA', 'PreviousYearAcceptanceRates',
                   'Term', 'LiveDate', 'DeadlineDate', 'Fees', 'AverageScholarshipAmount',
                   'ScholarshipAmount', 'ScholarshipPercentage', 'ScholarshipType', 'Program duration']:
        if program_data_result.get(field) is None or program_data_result.get(field) == "":
            fields_needing_fallback.append(field)
    
    # Only try institute level if we have fields that need fallback
    if fields_needing_fallback:
        print(f"  Some fields not found at program level, trying institute level for: {', '.join(fields_needing_fallback)}")
        prompt_institute = (
            f"You are extracting general program details, rankings, GPA requirements, deadlines, and financial information "
            f"from the official {university_name} website.\n\n"
            f"IMPORTANT: You MUST ONLY use information from the official {university_name} website ({institute_url} and its subdomains). "
            f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
            f"Institute URL: {institute_url}\n\n"
            f"Extract the following fields ONLY if they are present on the official {university_name} website as GENERAL/INSTITUTE-LEVEL information:\n\n"
            f"1. QsWorldRanking: QS World University Ranking for the university. Return as number or null.\n"
            f"2. School: General school/college information. Return null if not specified.\n"
            f"3. MaxFails: Maximum number of failed courses allowed (general policy). Return as number or null.\n"
            f"4. MaxGPA: Maximum GPA requirement or limit (general policy). Return as number (typically 0-4.0 scale) or null.\n"
            f"5. MinGPA: Minimum GPA requirement (general policy). Return as number (typically 0-4.0 scale) or null.\n"
            f"6. PreviousYearAcceptanceRates: General acceptance rate from previous year(s). Return as percentage (number) or null.\n"
            f"7. Term: General application terms available (e.g., 'Fall', 'Spring', 'Summer'). Return as string or null.\n"
            f"8. LiveDate: General program start dates. Return as date string (YYYY-MM-DD format preferred) or null.\n"
            f"9. DeadlineDate: General application deadline dates. Return as date string (YYYY-MM-DD format preferred) or null.\n"
            f"10. Fees: General application fees. Return as number (dollar amount) or null.\n"
            f"11. AverageScholarshipAmount: Average scholarship amount offered (general). Return as number (dollar amount) or null.\n"
            f"12. ScholarshipAmount: General scholarship amount available. Return as number (dollar amount) or null.\n"
            f"13. ScholarshipPercentage: General scholarship percentage. Return as number (percentage) or null.\n"
            f"14. ScholarshipType: General type of scholarship. Return as string or null.\n"
            f"15. Program duration: This field should be null at institute level (program-specific). Return null.\n\n"
            f"CRITICAL REQUIREMENTS:\n"
            f"- All data must be extracted ONLY from {institute_url} or other official {university_name} pages\n"
            f"- Extract GENERAL/INSTITUTE-LEVEL information (not program-specific)\n"
            f"- Do NOT infer, assume, or make up any information\n"
            f"- If a field is not found, return null for that field\n"
            f"- All URLs must be from the {university_name} domain or its subdomains\n\n"
            f"Return the data in a JSON format with the following exact keys: "
            f"'QsWorldRanking', 'School', 'MaxFails', 'MaxGPA', 'MinGPA', 'PreviousYearAcceptanceRates', "
            f"'Term', 'LiveDate', 'DeadlineDate', 'Fees', 'AverageScholarshipAmount', "
            f"'ScholarshipAmount', 'ScholarshipPercentage', 'ScholarshipType', 'Program duration'. "
            f"Return a single JSON object, not an array. Use null for any field where information is not available on the official website."
        )
        
        try:
            response = model.generate_content(prompt_institute)
            response_text = response.text
            parsed_data = parse_json_from_response(response_text)
            
            if parsed_data and isinstance(parsed_data, dict):
                institute_data_result = parsed_data
        except Exception as e:
            print(f"  Error extracting from institute level: {str(e)}")
    
    # Merge results: prefer program-level data, use institute-level for missing fields (except program-only fields)
    final_result = {}
    
    # Initialize all fields
    all_fields = ['QsWorldRanking', 'School', 'MaxFails', 'MaxGPA', 'MinGPA', 'PreviousYearAcceptanceRates',
                  'Term', 'LiveDate', 'DeadlineDate', 'Fees', 'AverageScholarshipAmount', 'CostPerCredit',
                  'ScholarshipAmount', 'ScholarshipPercentage', 'ScholarshipType', 'Program duration', 'Tuition fee']
    
    for field in all_fields:
        # For program-only fields, only use program-level data
        if field in program_only_fields:
            final_result[field] = program_data_result.get(field)
        else:
            # For other fields, prefer program-level, fallback to institute-level
            final_result[field] = program_data_result.get(field) or institute_data_result.get(field)
    
    # Determine extraction level
    if any(program_data_result.get(field) for field in all_fields if field not in program_only_fields):
        final_result['extraction_level'] = 'program'
    elif any(institute_data_result.get(field) for field in all_fields if field not in program_only_fields):
        final_result['extraction_level'] = 'institute'
    else:
        final_result['extraction_level'] = 'none'
    
    return final_result

for index, row in program_data.iterrows():
    program_name = row['Program name']
    program_page_url = row['Program Page url']
    
    # Skip if already processed
    if program_name in processed_programs:
        print(f"Skipping {program_name} (already processed)")
        continue
    
    print(f"Processing: {program_name}")
    
    try:
        extracted_data = extract_program_details(program_name, program_page_url, institute_url)
        
        # Add program name and URL to the data
        extracted_data['Program name'] = program_name
        extracted_data['Program Page url'] = program_page_url
        program_details_data.append(extracted_data)
        processed_programs.add(program_name)
        
        # Save immediately to preserve progress
        save_to_json(program_details_data, json_path)
        print(f"✓ Processed and saved: {program_name} (level: {extracted_data.get('extraction_level', 'unknown')})")
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    except Exception as e:
        print(f"Error processing program {program_name}: {str(e)}")
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
        print(f"✗ Error saved for program {program_name}")

# Final save
save_to_json(program_details_data, json_path)

# Also save as CSV
csv_output_path = os.path.join(output_dir, university_name + '_program_details_financial.csv')
if program_details_data:
    df = pd.DataFrame(program_details_data)
    df.to_csv(csv_output_path, index=False, encoding='utf-8')
    print(f"\nSuccessfully processed {len(program_details_data)} programs")
    print(f"Data saved to {json_path} and {csv_output_path}")
else:
    print("No data to save")

