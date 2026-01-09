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
output_dir = os.path.join(script_dir, 'undergrad_prog_outputs')
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)
csv_path = os.path.join(script_dir, 'undergraduate_programs.csv')
json_path = os.path.join(output_dir, 'test_scores_requirements.json')

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
test_scores_data = []
processed_programs = set()
if os.path.exists(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            test_scores_data = json.load(f)
            # Track which programs have already been processed
            for record in test_scores_data:
                program_name = record.get('Program name')
                if program_name:
                    processed_programs.add(program_name)
        print(f"Loaded {len(test_scores_data)} existing records from {json_path}")
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

def extract_test_scores(program_name, program_url, institute_url):
    """Extract test scores and English requirements, first from program level, then institute level."""
    
    # First, try program level
    prompt_program = (
        f"You are extracting test score requirements and English language requirements for the program '{program_name}' "
        f"from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website (unh.edu and its subdomains like *.unh.edu). "
        f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
        f"Program URL: {program_url}\n\n"
        f"Extract the following fields ONLY if they are present on the official {university_name} website for THIS SPECIFIC PROGRAM:\n\n"
        f"1. GreOrGmat: Whether GRE or GMAT is required, optional, or not required. Return 'GRE', 'GMAT', 'Either', 'Optional', 'Not Required', or null.\n"
        f"2. EnglishScore: General English language requirement description if mentioned. Return null if not specified.\n"
        f"3. IsDuoLingoRequired: Boolean (true/false) - Is Duolingo English test required? Return true, false, or null.\n"
        f"4. IsELSRequired: Boolean (true/false) - Is ELS (English Language Services) required? Return true, false, or null.\n"
        f"5. IsGMATOrGreRequired: Boolean (true/false) - Is either GMAT or GRE required? Return true, false, or null.\n"
        f"6. IsGMATRequired: Boolean (true/false) - Is GMAT specifically required? Return true, false, or null.\n"
        f"7. IsGreRequired: Boolean (true/false) - Is GRE specifically required? Return true, false, or null.\n"
        f"8. IsIELTSRequired: Boolean (true/false) - Is IELTS required? Return true, false, or null.\n"
        f"9. IsLSATRequired: Boolean (true/false) - Is LSAT required? Return true, false, or null.\n"
        f"10. IsMATRequired: Boolean (true/false) - Is MAT required? Return true, false, or null.\n"
        f"11. IsMCATRequired: Boolean (true/false) - Is MCAT required? Return true, false, or null.\n"
        f"12. IsPTERequired: Boolean (true/false) - Is PTE (Pearson Test of English) required? Return true, false, or null.\n"
        f"13. IsTOEFLIBRequired: Boolean (true/false) - Is TOEFL iBT (Internet-based Test) required? Return true, false, or null.\n"
        f"14. IsTOEFLPBTRequired: Boolean (true/false) - Is TOEFL PBT (Paper-based Test) required? Return true, false, or null.\n"
        f"15. IsEnglishNotRequired: Boolean (true/false) - Is English test not required? Return true, false, or null.\n"
        f"16. IsEnglishOptional: Boolean (true/false) - Is English test optional? Return true, false, or null.\n"
        f"17. MinimumDuoLingoScore: Minimum required Duolingo score as a number. Return null if not specified.\n"
        f"18. MinimumELSScore: Minimum required ELS score as a number. Return null if not specified.\n"
        f"19. MinimumGMATScore: Minimum required GMAT score as a number. Return null if not specified.\n"
        f"20. MinimumGreScore: Minimum required GRE score. Can be total score or section scores. Return as string or number. Return null if not specified.\n"
        f"21. MinimumIELTSScore: Minimum required IELTS score as a number (typically 0-9). Return null if not specified.\n"
        f"22. MinimumMATScore: Minimum required MAT score as a number. Return null if not specified.\n"
        f"23. MinimumMCATScore: Minimum required MCAT score as a number. Return null if not specified.\n"
        f"24. MinimumPTEScore: Minimum required PTE score as a number. Return null if not specified.\n"
        f"25. MinimumTOEFLScore: Minimum required TOEFL score as a number. Return null if not specified.\n"
        f"26. MinimumLSATScore: Minimum required LSAT score as a number. Return null if not specified.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {program_url} or other official {university_name} pages (unh.edu or *.unh.edu subdomains)\n"
        f"- Extract information SPECIFIC to this program '{program_name}'\n"
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found on the program page, return null for that field\n"
        f"- All URLs must be from the unh.edu domain or its subdomains\n"
        f"- Ensure all extracted text is accurate and verbatim from the source\n\n"
        f"Return the data in a JSON format with the following exact keys: "
        f"'GreOrGmat', 'EnglishScore', 'IsDuoLingoRequired', 'IsELSRequired', 'IsGMATOrGreRequired', "
        f"'IsGMATRequired', 'IsGreRequired', 'IsIELTSRequired', 'IsLSATRequired', 'IsMATRequired', "
        f"'IsMCATRequired', 'IsPTERequired', 'IsTOEFLIBRequired', 'IsTOEFLPBTRequired', "
        f"'IsEnglishNotRequired', 'IsEnglishOptional', 'MinimumDuoLingoScore', 'MinimumELSScore', "
        f"'MinimumGMATScore', 'MinimumGreScore', 'MinimumIELTSScore', 'MinimumMATScore', "
        f"'MinimumMCATScore', 'MinimumPTEScore', 'MinimumTOEFLScore', 'MinimumLSATScore'. "
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
        f"You are extracting general test score requirements and English language requirements "
        f"from the official {university_name} website.\n\n"
        f"IMPORTANT: You MUST ONLY use information from the official {university_name} website (unh.edu and its subdomains like *.unh.edu). "
        f"Do NOT use information from any other sources. If the information is not available on the official {university_name} website, return null for that field.\n\n"
        f"Institute URL: {institute_url}\n\n"
        f"Extract the following fields ONLY if they are present on the official {university_name} website as GENERAL/INSTITUTE-LEVEL requirements:\n\n"
        f"1. GreOrGmat: Whether GRE or GMAT is generally required, optional, or not required. Return 'GRE', 'GMAT', 'Either', 'Optional', 'Not Required', or null.\n"
        f"2. EnglishScore: General English language requirement description if mentioned. Return null if not specified.\n"
        f"3. IsDuoLingoRequired: Boolean (true/false) - Is Duolingo English test required? Return true, false, or null.\n"
        f"4. IsELSRequired: Boolean (true/false) - Is ELS (English Language Services) required? Return true, false, or null.\n"
        f"5. IsGMATOrGreRequired: Boolean (true/false) - Is either GMAT or GRE required? Return true, false, or null.\n"
        f"6. IsGMATRequired: Boolean (true/false) - Is GMAT specifically required? Return true, false, or null.\n"
        f"7. IsGreRequired: Boolean (true/false) - Is GRE specifically required? Return true, false, or null.\n"
        f"8. IsIELTSRequired: Boolean (true/false) - Is IELTS required? Return true, false, or null.\n"
        f"9. IsLSATRequired: Boolean (true/false) - Is LSAT required? Return true, false, or null.\n"
        f"10. IsMATRequired: Boolean (true/false) - Is MAT required? Return true, false, or null.\n"
        f"11. IsMCATRequired: Boolean (true/false) - Is MCAT required? Return true, false, or null.\n"
        f"12. IsPTERequired: Boolean (true/false) - Is PTE (Pearson Test of English) required? Return true, false, or null.\n"
        f"13. IsTOEFLIBRequired: Boolean (true/false) - Is TOEFL iBT (Internet-based Test) required? Return true, false, or null.\n"
        f"14. IsTOEFLPBTRequired: Boolean (true/false) - Is TOEFL PBT (Paper-based Test) required? Return true, false, or null.\n"
        f"15. IsEnglishNotRequired: Boolean (true/false) - Is English test not required? Return true, false, or null.\n"
        f"16. IsEnglishOptional: Boolean (true/false) - Is English test optional? Return true, false, or null.\n"
        f"17. MinimumDuoLingoScore: Minimum required Duolingo score as a number. Return null if not specified.\n"
        f"18. MinimumELSScore: Minimum required ELS score as a number. Return null if not specified.\n"
        f"19. MinimumGMATScore: Minimum required GMAT score as a number. Return null if not specified.\n"
        f"20. MinimumGreScore: Minimum required GRE score. Can be total score or section scores. Return as string or number. Return null if not specified.\n"
        f"21. MinimumIELTSScore: Minimum required IELTS score as a number (typically 0-9). Return null if not specified.\n"
        f"22. MinimumMATScore: Minimum required MAT score as a number. Return null if not specified.\n"
        f"23. MinimumMCATScore: Minimum required MCAT score as a number. Return null if not specified.\n"
        f"24. MinimumPTEScore: Minimum required PTE score as a number. Return null if not specified.\n"
        f"25. MinimumTOEFLScore: Minimum required TOEFL score as a number. Return null if not specified.\n"
        f"26. MinimumLSATScore: Minimum required LSAT score as a number. Return null if not specified.\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"- All data must be extracted ONLY from {institute_url} or other official {university_name} pages (unh.edu or *.unh.edu subdomains)\n"
        f"- Extract GENERAL/INSTITUTE-LEVEL requirements (not program-specific)\n"
        f"- Do NOT infer, assume, or make up any information\n"
        f"- If a field is not found, return null for that field\n"
        f"- All URLs must be from the unh.edu domain or its subdomains\n\n"
        f"Return the data in a JSON format with the following exact keys: "
        f"'GreOrGmat', 'EnglishScore', 'IsDuoLingoRequired', 'IsELSRequired', 'IsGMATOrGreRequired', "
        f"'IsGMATRequired', 'IsGreRequired', 'IsIELTSRequired', 'IsLSATRequired', 'IsMATRequired', "
        f"'IsMCATRequired', 'IsPTERequired', 'IsTOEFLIBRequired', 'IsTOEFLPBTRequired', "
        f"'IsEnglishNotRequired', 'IsEnglishOptional', 'MinimumDuoLingoScore', 'MinimumELSScore', "
        f"'MinimumGMATScore', 'MinimumGreScore', 'MinimumIELTSScore', 'MinimumMATScore', "
        f"'MinimumMCATScore', 'MinimumPTEScore', 'MinimumTOEFLScore', 'MinimumLSATScore'. "
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
        'GreOrGmat': None, 'EnglishScore': None, 'IsDuoLingoRequired': None, 'IsELSRequired': None,
        'IsGMATOrGreRequired': None, 'IsGMATRequired': None, 'IsGreRequired': None, 'IsIELTSRequired': None,
        'IsLSATRequired': None, 'IsMATRequired': None, 'IsMCATRequired': None, 'IsPTERequired': None,
        'IsTOEFLIBRequired': None, 'IsTOEFLPBTRequired': None, 'IsEnglishNotRequired': None, 'IsEnglishOptional': None,
        'MinimumDuoLingoScore': None, 'MinimumELSScore': None, 'MinimumGMATScore': None, 'MinimumGreScore': None,
        'MinimumIELTSScore': None, 'MinimumMATScore': None, 'MinimumMCATScore': None, 'MinimumPTEScore': None,
        'MinimumTOEFLScore': None, 'MinimumLSATScore': None, 'extraction_level': 'none'
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
        extracted_data = extract_test_scores(program_name, program_page_url, institute_url)
        
        # Add program name and URL to the data
        extracted_data['Program name'] = program_name
        extracted_data['Program Page url'] = program_page_url
        test_scores_data.append(extracted_data)
        processed_programs.add(program_name)
        
        # Save immediately to preserve progress
        save_to_json(test_scores_data, json_path)
        print(f"✓ Processed and saved: {program_name} (level: {extracted_data.get('extraction_level', 'unknown')})")
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    except Exception as e:
        print(f"Error processing program {program_name}: {str(e)}")
        error_record = {
            'Program name': program_name,
            'Program Page url': program_page_url,
            'GreOrGmat': None, 'EnglishScore': None, 'IsDuoLingoRequired': None, 'IsELSRequired': None,
            'IsGMATOrGreRequired': None, 'IsGMATRequired': None, 'IsGreRequired': None, 'IsIELTSRequired': None,
            'IsLSATRequired': None, 'IsMATRequired': None, 'IsMCATRequired': None, 'IsPTERequired': None,
            'IsTOEFLIBRequired': None, 'IsTOEFLPBTRequired': None, 'IsEnglishNotRequired': None, 'IsEnglishOptional': None,
            'MinimumDuoLingoScore': None, 'MinimumELSScore': None, 'MinimumGMATScore': None, 'MinimumGreScore': None,
            'MinimumIELTSScore': None, 'MinimumMATScore': None, 'MinimumMCATScore': None, 'MinimumPTEScore': None,
            'MinimumTOEFLScore': None, 'MinimumLSATScore': None, 'extraction_level': 'error', 'error': str(e)
        }
        test_scores_data.append(error_record)
        processed_programs.add(program_name)
        save_to_json(test_scores_data, json_path)
        print(f"✗ Error saved for program {program_name}")

# Final save
save_to_json(test_scores_data, json_path)

# Also save as CSV
csv_output_path = os.path.join(output_dir, 'test_scores_requirements.csv')
if test_scores_data:
    df = pd.DataFrame(test_scores_data)
    df.to_csv(csv_output_path, index=False, encoding='utf-8')
    print(f"\nSuccessfully processed {len(test_scores_data)} programs")
    print(f"Data saved to {json_path} and {csv_output_path}")
else:
    print("No data to save")

