import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

tools = [
    genai.protos.Tool(
        google_search=genai.protos.Tool.GoogleSearch()
    )
]
model = genai.GenerativeModel("gemini-2.5-pro", tools=tools)

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(script_dir, "Grad_prog_outputs")
# Create directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

university_name = "Kansas State University"
prompt = f"What is the official university website for {university_name}?"
website_url = model.generate_content(prompt).text.replace("**", "").replace("```", "").strip()
print(website_url)
institute_url = website_url
# Use a more generic search or let the model find the grad page if needed, 
# but for now, we'll try to find the grad programs page dynamically or start from the main page if specific URL is unknown
graduate_program_url = "https://www.k-state.edu/grad/academics/degrees-certificates.html"

def get_program_names(website_url):
    prompt = (
        f"Extract information about graduate programs offered by {university_name} from {website_url}. "
        f"Step 1: LIST ONLY THE GRADUATE PROGRAM NAMES AND LEVELS. Do NOT try to find URLs yet. "
        f"CRITICAL: EXCLUDE any combined bachelor/master programs (e.g., '3+1', '4+1', 'BS/MS', 'Dual Degree' with undergraduate). "
        f"Extract ONLY purely graduate level programs (Master's, Doctoral, Certificate). "
        f"Return the data in a JSON array of objects with keys: 'Program name', 'Level'. "
        f"Example: [{{\"Program name\": \"Master of Science in Biology\", \"Level\": \"Master's\"}}]"
    )
    
    try:
        response = model.generate_content(prompt).text
        response = response.replace("**", "").replace("```json", "").replace("```", "").strip()
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
        return json.loads(response)
    except Exception as e:
        print(f"Error getting program names: {e}")
        return []

def get_program_url(program_name, level):
    prompt = (
        f"Find the OFFICIAL, WORKING URL for the '{program_name}' ({level}) graduate program at {university_name}. "
        f"The URL must be a valid page on {institute_url} or its subdomains. "
        f"Return ONLY the URL string. Do not return JSON. Do not return markdown. Just the URL."
    )
    try:
        response = model.generate_content(prompt).text.strip()
        # Clean up any potential extra text if the model is chatty
        url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', response)
        if url_match:
            return url_match.group(0)
        return response
    except Exception as e:
        print(f"Error getting URL for {program_name}: {e}")
        return None

def get_graduate_programs(website_url):
    print("Step 1: Extracting program names...")
    programs = get_program_names(website_url)
    
    if not programs:
        print("No programs found in Step 1.")
        return []

    print(f"Found {len(programs)} programs. Step 2: Finding URLs for each...")
    
    complete_programs = []
    for prog in programs:
        program_name = prog.get('Program name')
        level = prog.get('Level')
        
        # Double check filtering on client side
        if program_name and not any(x in program_name.lower() for x in ['3+1', '4+1', 'bs/', 'ba/', 'dual degree']):
            print(f"Finding URL for: {program_name}")
            url = get_program_url(program_name, level)
            
            prog['Program Page url'] = url
            complete_programs.append(prog)
            
    return complete_programs

graduate_programs = get_graduate_programs(graduate_program_url)

if graduate_programs:
    # Save the graduate programs to JSON file
    json_path = os.path.join(output_dir, 'graduate_programs.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(graduate_programs, f, indent=4, ensure_ascii=False)
    print(f"Data saved to JSON: {json_path}")
    
    # Save the graduate programs to CSV file
    csv_path = os.path.join(output_dir, 'graduate_programs.csv')
    df = pd.DataFrame(graduate_programs)
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"Data saved to CSV: {csv_path}")
    print(f"Total programs found: {len(graduate_programs)}")
    
    # Also save to the script directory for easy access
    script_json_path = os.path.join(script_dir, 'graduate_programs.json')
    script_csv_path = os.path.join(script_dir, 'graduate_programs.csv')
    
    with open(script_json_path, 'w', encoding='utf-8') as f:
        json.dump(graduate_programs, f, indent=4, ensure_ascii=False)
    
    df.to_csv(script_csv_path, index=False, encoding='utf-8')
    print(f"Also saved to script directory: {script_csv_path}")
    
    print("\nFirst few programs:")
    print(graduate_programs[:3] if len(graduate_programs) > 3 else graduate_programs)
else:
    print("No graduate programs found or error occurred.")

