import pandas as pd
import os
import re
import sys
import json
import concurrent.futures
import time
from dotenv import load_dotenv

# Import robust utils and set up paths
current_dir = os.path.dirname(os.path.abspath(__file__))
programs_dir = os.path.dirname(current_dir)
if programs_dir not in sys.path:
    sys.path.append(programs_dir)

from robust_extraction_utils import GeminiModelWrapper
from pydantic import BaseModel, Field
from typing import Optional

load_dotenv()

# We need the naked genai client to pass into the wrapper
from google import genai
client = genai.Client(vertexai=True, project=os.getenv("GCP_PROJECT"), location='us-east4')

model = GeminiModelWrapper(client, os.getenv("MODEL"))

output_dir = os.path.join(current_dir, "Grad_prog_outputs")
os.makedirs(output_dir, exist_ok=True)

# Predefined category list from merge_all.py
PROGRAM_CATEGORIES = [
    "Accounting/Finance", "Administration", "Administration of Justice",
    "Advertising", "Aerospace Engineering", "African Studies", "Agriculture",
    "Agriculture Animal Sciences", "Agriculture Business", "Agriculture Plant Sciences",
    "Agronomy", "Allied Health", "American Studies", "Anatomy", "Anesthesia Tech",
    "Anesthesiology", "Animal Science", "Animation and Digital Arts", "Anthropology",
    "Apparel Merchandising", "Applied Mathematics", "Applied Physics",
    "Applied Studies", "Arabic", "Archaeology", "Architectural Engineering",
    "Architecture", "Art", "Artificial Intelligence", "Art Education", "Art History",
    "Asian Studies", "Asian-American Studies", "Astronautical Engineering",
    "Astronomy", "Athletic Training", "Audiology", "Automation", "Aviation",
    "Bacteriology", "Behavioral Science", "Biochemical Engineering", "Biochemistry",
    "Biochemistry and Molecular Biology", "Bioengineering", "Bioinformatics",
    "Biological Sciences", "Biology", "Biomathematics", "Biomedical Engineering",
    "Biomedical Physics", "Biomedical Science", "Biophysics", "Biostatistics",
    "Biotechnology", "Botany", "Broadcast Arts", "Business Administration",
    "Business Administration 2.0", "Business Information Systems",
    "Business/Management", "Central American Studies", "Chemical Engineering",
    "Chemistry", "Chicano/Latino Studies", "Child and Adolescent Development",
    "Child Development", "Chinese Language and Literature", "Chiropractic",
    "Cinematic Arts", "City and Regional Planning", "Civil Engineering",
    "Clarinet Performance", "Classics", "Clinical Psychology", "Coastal Sciences",
    "Cognitive Studies", "Communication Engineering",
    "Communication Science & Disorders", "Communication Studies",
    "Communications", "Community Development", "Community Health",
    "Comparative Literature", "Composition", "Computer", "Computer Engineering",
    "Computer Science", "Computer Science and Engineering",
    "Computer Science and Technology", "Computer Tomography",
    "Concrete Industry Management", "Conflict Resolution",
    "Construction Management", "Counseling", "Creative Writing",
    "Criminal Justice", "Criminology", "Culinary/Food Studies",
    "Cultural Resources Management", "Cybersecurity", "Dairy Science", "Dance",
    "Data Science", "Decision Sciences", "Deaf Studies", "Demography",
    "Dental Assistant", "Dental Hygiene", "Dentistry", "Dietetics",
    "Early Childhood Education", "Earth Sciences", "East Asian Studies",
    "Ecology", "Economic Policy", "Economics", "Education",
    "Electrical and Electronic Engineering", "Electrical Engineering",
    "Electrical Engineering and Automation",
    "Electronic and Computer Engineering", "Electronic Engineering",
    "Electronic Information Engineering",
    "Electronic Information Science and Technology",
    "Electronic Science and Technology", "Electronics",
    "Electronics and Communication", "Electronics and Communication Engineering",
    "Electronics and Instrumentation", "Electronics and Telecommunications",
    "Elementary Education", "Elementary Teacher Education",
    "Emergency Med-Tech", "Emergency Services Administration", "Energy",
    "Engineering", "Engineering Physics", "English", "Enology", "Entomology",
    "Environmental Engineering", "Environmental Health",
    "Environmental Management", "Environmental Science",
    "Environmental Studies", "Epidemiology", "Ergonomics", "Ethics",
    "Ethnic Studies", "European Studies", "Exercise Science",
    "Facilities Engineering Technology", "Family and Consumer Sciences",
    "Fashion Design", "Film", "Film, Television, and Electronic Media",
    "Finance", "Financial Engineering", "Fine Arts", "Fire Protection",
    "Fisheries Biology", "Folklore", "Food Science", "Foreign Language",
    "Forestry", "French", "Gender Studies", "General Studies",
    "Genetic Counseling", "Genetics", "Geographic Information Systems",
    "Geography", "Geology", "Geomatics Engineering", "Geophysics",
    "Geosciences", "Gerontology", "German", "Global Development Economics",
    "Global Studies", "Global Supply Chain Management", "Government",
    "Graphic Communication", "Graphic Design", "Health",
    "Health Administration", "Health Communication", "Health Education",
    "Health Information Management", "Health Science", "Hematology",
    "Hispanic Language & Literature", "Histology", "History",
    "History of Art & Architecture", "History/Preservation",
    "History Of Science, History Of Medicine", "Histotechnology",
    "Hospitality Management", "Human Biology", "Human Development",
    "Human Health Sciences", "Human Resources", "Human Services",
    "Human Sexuality", "Humanities", "Immunology",
    "Independent/Interdisiplinary Studies",
    "Industrial and Systems Engineering", "Industrial Arts",
    "Industrial Design", "Industrial Distribution", "Industrial Economics",
    "Industrial Engineering", "Industrial Pharmacy", "Industrial Psychology",
    "Industrial Technology", "Informatics", "Information Engineering",
    "Information Science & Engineering", "Information Sciences",
    "Information Security", "Information Systems", "Information Technology",
    "Integrated Animal Health Sciences", "Integrative Biology",
    "Intelligent Systems Engineering", "Interdisciplinary Engineering",
    "Interdisciplinary Studies", "Interior Design", "International Business",
    "International Health", "International Relations",
    "International Studies", "Internet of Things Engineering", "Italian",
    "Japanese", "Jewish Studies", "Journalism", "Kinesiology",
    "Labor Studies", "Laboratory Technology", "Landscape Architecture",
    "Latin American Studies", "Law", "Law, Public Policy, and Society",
    "Liberal Arts", "Liberal Studies", "Library Science", "Linguistics",
    "Literature", "Magnetic Resonance Imaging", "Machine Learning",
    "Livestock Systems Health", "Management", "Manufacturing Engineering",
    "Marine Biology", "Marine Engineering Technology", "Marine Science",
    "Marine Transportation", "Marriage and Family Therapy", "Marketing",
    "Massage Therapy", "Materials Science", "Mathematics",
    "Mechanical Design", "Mechanical Engineering", "Mechatronics",
    "Media Design", "Media Technology", "Medical Laboratory Tech",
    "Medical Physics", "Medical Product Development Management",
    "Medical Assistant", "Medical Tech", "Medicine", "Meteorology",
    "Microbiology", "Microelectronics", "Military Science",
    "Molecular Biology",
    "Molecular Biology, Cell Biology & Biochemistry", "Mortuary",
    "Multimedia", "Music", "Music Education",
    "Music Industry and Technology", "Music Performance",
    "Musical Theatre", "Museum Studies", "Musicology",
    "National Cybersecurity Studies",
    "National Security Studies/Homeland Security",
    "Native American Studies", "Natural Science", "Naval Engineering",
    "Neurobiology", "Neurology", "Neuropsychology", "Neuroscience",
    "Nuclear Engineering", "Nurse Practitioner", "Nursing", "Nutrition",
    "Nutrition and Dietetics", "Nutritional Sciences",
    "Occupational Therapy", "Occupational Therapy Assistant",
    "Oceanography", "Optometry", "Organismic Biology",
    "Organizational Development", "Osteopathic Medicine", "Paramedic",
    "Parasitology", "Pathology", "Performance", "Performing Arts",
    "Petroleum Engineering", "Pharmaceutical Sciences", "Pharmacology",
    "Pharmacy", "Philosophy", "Photography", "Physical Education",
    "Physical Science", "Physical Therapist Assistant", "Physical Therapy",
    "Physical Therapy - Pre-PT", "Physician Assistant", "Physics",
    "Physiology", "Podiatry", "Policy Studies", "Political Science",
    "Polymers and Coatings", "Practical Nursing", "Premedical",
    "Pre-Professional", "Preservation Studies", "Psychobiology",
    "Psychology", "Public Administration", "Public Health",
    "Public Health Science", "Public Policy", "Public Relations",
    "Quality Assurance",
    "Quantitative Methods, Analysis, Business Analytics",
    "Radiation Therapy", "Radiology", "Radiography",
    "Rangeland Resource Science", "Recreation Administration",
    "Recreational Therapy", "Regenerative Studies", "Regulatory Affairs",
    "Rehabilitation Counseling", "Rehabilitation Science", "Religion",
    "Religious Studies", "Remote Sensing & Geospatial Sciences",
    "Research Methods", "Respiratory Therapy", "Russian",
    "Russian and Central European Studies",
    "Science, Technology and Society", "Screenwriting",
    "Social Justice Studies", "Social Policy", "Social Sciences",
    "Social Welfare", "Social Work", "Social Work and Human Services",
    "Sociology", "Software Engineering", "Spanish", "Special Education",
    "Speech", "Sports Medicine", "Statistical Practice", "Statistics",
    "Structural Engineering", "Studio Arts", "Sustainable Manufacturing",
    "Taxation", "Teaching English to Speakers of Other Languages",
    "Technical/Professional Writing", "Telecommunication Engineering",
    "Theater Arts", "Theology", "Toxicology",
    "Traffic & Transportation Engineering", "Urban Affairs",
    "Urban Planning", "Veterinary Medicine", "Veterinary Tech",
    "Virology", "Visual and Performing Arts", "Viticulture",
    "Water Resource Management", "Wildlife Management",
    "Women's Studies", "World Languages and Cultures", "Writing", "Zoology",
]

class ProgramDetails(BaseModel):
    # GENERAL DETAILS
    Concentration_name: Optional[str] = Field(None, description="Specific concentration/track name.")
    description: Optional[str] = Field(None, description="Comprehensive program description.")
    program_website_url: Optional[str] = Field(None, alias="program website url", description="Official program page URL.")
    Accreditation_status: Optional[str] = Field(None, alias="Accreditation status", description="Name of accrediting body mentioned.")
    Level: str = Field("Masters", description="Program level (e.g. Masters, PhD, Certificate).")
    ProgramCategory: Optional[str] = Field(None, description="Assigned categories from the provided list, joined by ##.")

    # APPLICATION REQUIREMENTS
    Resume: Optional[str] = Field(None, description="Is CV required? (Required/Optional/Not Required/null)")
    StatementOfPurpose: Optional[str] = Field(None, description="Is statement required? (Required/Optional/Not Required/null)")
    Requirements: Optional[str] = Field(None, description="Any general app description.")
    WritingSample: Optional[str] = Field(None, description="Is writing sample required? (Required/Optional/Not Required/null)")
    IsAnalyticalNotRequired: bool = Field(False, description="Is analytical score NOT required?")
    IsAnalyticalOptional: bool = Field(False, description="Is it optional?")
    IsStemProgram: bool = Field(False, description="Is this an official STEM program?")
    IsACTRequired: bool = Field(False, description="(False for grad)")
    IsSATRequired: bool = Field(False, description="(False for grad)")

    # FINANCIAL & ADMISSION DETAILS
    QsWorldRanking: Optional[str] = Field(None)
    School: Optional[str] = Field(None, description="Specific school/college offering it.")
    MaxFails: Optional[float] = Field(None)
    MaxGPA: Optional[float] = Field(None)
    MinGPA: Optional[float] = Field(None, description="Minimum required GPA.")
    PreviousYearAcceptanceRates: Optional[str] = Field(None)
    Term: Optional[str] = Field(None, description="Admission term e.g. Fall.")
    LiveDate: Optional[str] = Field(None, description="Application opening date.")
    DeadlineDate: Optional[str] = Field(None, description="Application deadline.")
    Fees: Optional[float] = Field(None, description="Tuition fee amount as a number.")
    AverageScholarshipAmount: Optional[float] = Field(None)
    CostPerCredit: Optional[float] = Field(None)
    ScholarshipAmount: Optional[float] = Field(None)
    ScholarshipPercentage: Optional[float] = Field(None)
    ScholarshipType: Optional[str] = Field(None)
    Program_duration: Optional[str] = Field(None, alias="Program duration")
    Tuition_fee: Optional[str] = Field(None, alias="Tuition fee")

    # TEST SCORES & ENGLISH PROFICIENCY
    GreOrGmat: Optional[str] = Field(None, description="(GRE/GMAT/Either/Optional/Not Required/null)")
    EnglishScore: Optional[str] = Field(None, description="(Required/Not Required/Optional/null)")
    IsDuoLingoRequired: bool = Field(False)
    IsELSRequired: bool = Field(False)
    IsGMATOrGreRequired: bool = Field(False)
    IsGMATRequired: bool = Field(False)
    IsGRERequired: bool = Field(False)
    IsIELTSRequired: bool = Field(False)
    IsLSATRequired: bool = Field(False)
    IsMATRequired: bool = Field(False)
    IsMCATRequired: bool = Field(False)
    IsPTERequired: bool = Field(False)
    IsTOEFLIBRequired: bool = Field(False)
    IsTOEFLPBTRequired: bool = Field(False)
    IsEnglishNotRequired: bool = Field(False)
    IsEnglishOptional: bool = Field(False)
    MinimumDuoLingoScore: Optional[float] = Field(None)
    MinimumELSScore: Optional[float] = Field(None)
    MinimumGMATScore: Optional[float] = Field(None)
    MinimumGreScore: Optional[float] = Field(None)
    MinimumIELTSScore: Optional[float] = Field(None)
    MinimumMATScore: Optional[float] = Field(None)
    MinimumMCATScore: Optional[float] = Field(None)
    MinimumPTEScore: Optional[float] = Field(None)
    MinimumTOEFLScore: Optional[float] = Field(None)
    MinimumLSATScore: Optional[float] = Field(None)

def process_single_program_master(program_name, program_url, university_name, max_retries=3):
    """
    Mass extraction for a single graduate program. Handles Description, STEM status, App Reqs, Test Scores, and Costs.
    """
    from google.genai.types import GenerateContentConfig, Tool, GoogleSearch
    from robust_extraction_utils import _extract_json_from_text
    
    try:
        # Prompt expanded to handle detailed admission and score requirements for Graduate level
        refine_prompt = (
            f"You are a strict data extractor for the graduate program '{program_name}' at {university_name}.\n"
            f"Task: Extract detailed program information, admission requirements, and costs.\n\n"
            f"Grounding Instructions:\n"
            f"1. Use Google Search to find the specific program page: {program_url} or search '[Program Name] at [University]'.\n"
            f"2. If the specific program page fails or is empty, use the main university Graduate Programs/Admissions index to find general requirements.\n"
            f"3. CRITICAL: Use the official university website only. No 3rd party sites.\n\n"
            f"Fields to Extract (return null if not found):\n"
            f"- 'description': Comprehensive summary (2-3 sentences).\n"
            f"- 'ProgramCategory': Select ALL relevant categories from the pre-defined list below that fit this program. "
            f"Separate them with exactly '##' (e.g., 'CategoryA##CategoryB').\n"
            f"Allowed Categories: {', '.join(PROGRAM_CATEGORIES)}\n"
            f"- 'IsStemProgram': true/false (official STEM/CIP designation).\n"
            f"- 'Concentration_name': List any concentrations/tracks found, separated by commas.\n"
            f"- 'Resume', 'StatementOfPurpose', 'WritingSample', 'EnglishScore', 'GreOrGmat': Set to 'Required' or 'Not Required' or 'Optional'.\n"
            f"- 'FALLBACK RULE': English proficiency scores (TOEFL/IELTS/Duolingo) are MANDATORY. If they are not found on the program page, "
            f"search the University Admissions catalog or requirements page. Apply the university-wide minimums and 'Accepted Tests' list if program-specific ones are missing. "
            f"If a test is listed as accepted by the university/program, set its corresponding boolean (e.g., 'IsIELTSRequired') to true.\n"
            f"- 'IsGMATOrGreRequired', 'IsGMATRequired', 'IsGRERequired', 'IsDuoLingoRequired', 'IsELSRequired', 'IsIELTSRequired', 'IsPTERequired', 'IsTOEFLIBRequired', 'IsTOEFLPBTRequired', 'IsEnglishNotRequired', 'IsEnglishOptional': Boolean (true/false).\n"
            f"- 'MinimumGMATScore', 'MinimumGreScore', 'MinimumDuoLingoScore', 'MinimumELSScore', 'MinimumIELTSScore', 'MinimumPTEScore', 'MinimumTOEFLScore', 'MinGPA': Numerical value (float).\n"
            f"- 'CostPerCredit': The FULL-TIME non-resident tuition cost per credit hour (numerical float).\n"
            f"- 'ScholarshipType': Types of aid available (e.g., 'Merit-based, Need-based, etc.'), separated by commas.\n"
            f"- 'MaxFails', 'MaxGPA': Any stated limits on failures or GPA (numerical/null).\n\n"
            f"CRITICAL: DO NOT include any grounding citations or bracketed numbers like [1], [22], etc. in any text field.\n"
            f"Return ONLY a JSON object with these keys. No grounding citations or bracketed numbers.\n"
        )
        
        for attempt in range(max_retries):
             try:
                 resp = client.models.generate_content(
                      model=os.getenv("MODEL"),
                      contents=refine_prompt,
                      config=GenerateContentConfig(
                           temperature=0.1,
                           tools=[Tool(google_search=GoogleSearch())]
                      )
                 )
                 parsed = _extract_json_from_text(resp.text)
                 
                 # Final mapping ensures all keys exist in output for Graduate level
                 result = {
                     'Program name': program_name,
                     'Program Page url': program_url,
                     'description': parsed.get('description'),
                     'IsStemProgram': parsed.get('IsStemProgram', False),
                     'ProgramCategory': parsed.get('ProgramCategory'),
                     'Concentration name': parsed.get('Concentration_name'),
                     'Resume': parsed.get('Resume'),
                     'StatementOfPurpose': parsed.get('StatementOfPurpose'),
                     'WritingSample': parsed.get('WritingSample'),
                     'EnglishScore': parsed.get('EnglishScore'),
                     'GreOrGmat': parsed.get('GreOrGmat'),
                     'IsGMATOrGreRequired': parsed.get('IsGMATOrGreRequired', False),
                     'IsGMATRequired': parsed.get('IsGMATRequired', False),
                     'IsGRERequired': parsed.get('IsGRERequired', False),
                     'IsDuoLingoRequired': parsed.get('IsDuoLingoRequired', False),
                     'IsELSRequired': parsed.get('IsELSRequired', False),
                     'IsIELTSRequired': parsed.get('IsIELTSRequired', False),
                     'IsPTERequired': parsed.get('IsPTERequired', False),
                     'IsTOEFLIBRequired': parsed.get('IsTOEFLIBRequired', False),
                     'IsTOEFLPBTRequired': parsed.get('IsTOEFLPBTRequired', False),
                     'IsEnglishNotRequired': parsed.get('IsEnglishNotRequired', False),
                     'IsEnglishOptional': parsed.get('IsEnglishOptional', False),
                     'MinimumGMATScore': parsed.get('MinimumGMATScore'),
                     'MinimumGreScore': parsed.get('MinimumGreScore'),
                     'MinimumDuoLingoScore': parsed.get('MinimumDuoLingoScore'),
                     'MinimumELSScore': parsed.get('MinimumELSScore'),
                     'MinimumIELTSScore': parsed.get('MinimumIELTSScore'),
                     'MinimumPTEScore': parsed.get('MinimumPTEScore'),
                     'MinimumTOEFLScore': parsed.get('MinimumTOEFLScore'),
                     'MinGPA': parsed.get('MinGPA'),
                     'CostPerCredit': parsed.get('CostPerCredit'),
                     'ScholarshipType': parsed.get('ScholarshipType'),
                     'MaxFails': parsed.get('MaxFails'),
                     'MaxGPA': parsed.get('MaxGPA'),
                     'program website url': program_url,
                     'Accreditation status': None
                 }
                 
                 # Clean up any remaining citations in all string fields
                 for key, value in result.items():
                     if isinstance(value, str):
                         result[key] = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', value).strip()
                         
                 # Standardize boolean fields to False if null
                 bool_fields = [
                     'IsStemProgram', 'IsGMATOrGreRequired', 'IsGMATRequired', 'IsGRERequired', 
                     'IsACTRequired', 'IsSATRequired', 'IsDuoLingoRequired', 'IsELSRequired', 
                     'IsIELTSRequired', 'IsLSATRequired', 'IsMATRequired', 'IsMCATRequired', 
                     'IsPTERequired', 'IsTOEFLIBRequired', 'IsTOEFLPBTRequired', 
                     'IsEnglishNotRequired', 'IsEnglishOptional'
                 ]
                 for bf in bool_fields:
                     if result.get(bf) is None:
                         result[bf] = False
                         
                 return result
             except Exception as e:
                 error_str = str(e)
                 if "503" in error_str or "429" in error_str or "Too Many Requests" in error_str:
                      if attempt < max_retries - 1:
                           time.sleep(3 * (2 ** attempt))
                           continue
                 raise e
                 
    except Exception as e:
        return {
            'Program name': program_name, 'Program Page url': program_url, 'error': str(e)
        }
    
    return {'Program name': program_name, 'Program Page url': program_url, 'error': 'Failed to parse JSON'}


def run(university_name_input):
    university_name = university_name_input
    sanitized_name = university_name.replace(" ", "_").replace("/", "_")
    
    csv_path = os.path.join(output_dir, f'{sanitized_name}_graduate_programs.csv')
    master_json_path = os.path.join(output_dir, f'{sanitized_name}_master_data.json')
    step2_csv_path = os.path.join(output_dir, f'{sanitized_name}_extra_fields_data.csv')

    if not os.path.exists(csv_path):
        yield f'{{"status": "complete", "message": "CSV file not found: {csv_path}. Skipping Master Step.", "files": {{}}}}'
        return

    program_data = pd.read_csv(csv_path)
    if program_data.empty:
        yield f'{{"status": "error", "message": "CSV file is empty. Please check Step 1 results."}}'
        return

    try:
        from urllib.parse import urlparse
        first_url = program_data.iloc[0]['Program Page url']
        urlparse(first_url).netloc
    except Exception:
        pass

    master_data = []
    processed_programs = set()
    if os.path.exists(master_json_path):
        try:
             with open(master_json_path, 'r', encoding='utf-8') as f:
                 master_data = json.load(f)
                 for record in master_data:
                     processed_programs.add(record.get('Program name'))
             yield f'{{"status": "progress", "message": "Resuming: Loaded {len(master_data)} existing master records."}}'
        except Exception:
             pass

    programs_to_process = [row for index, row in program_data.iterrows() if row['Program name'] not in processed_programs]
    total_programs = len(program_data)
    
    if programs_to_process:
         yield f'{{"status": "progress", "message": "Starting parallel master extraction for {len(programs_to_process)} programs. Please wait..."}}'
         
         # Parallel execution safely limited to 5 workers
         max_workers = 5
         completed_count = len(processed_programs)
         
         with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
              futures = {
                  executor.submit(process_single_program_master, row['Program name'], row['Program Page url'], university_name): row['Program name']
                  for row in programs_to_process
              }
              
              for future in concurrent.futures.as_completed(futures):
                  p_name = futures[future]
                  completed_count += 1
                  try:
                      res = future.result()
                      master_data.append(res)
                      # Save intermittently
                      if completed_count % 5 == 0 or completed_count == total_programs:
                          with open(master_json_path, 'w', encoding='utf-8') as f:
                               json.dump(master_data, f, indent=4)
                      
                      yield f'{{"status": "progress", "message": "Master Extraction [{completed_count}/{total_programs}]: {p_name}"}}'
                  except Exception as exc:
                      yield f'{{"status": "warning", "message": "Failed {p_name}: {exc}"}}'

         # Final save ensures everything is flushed
         with open(master_json_path, 'w', encoding='utf-8') as f:
              json.dump(master_data, f, indent=4)

    else:
         yield f'{{"status": "progress", "message": "All {total_programs} programs already extracted in master JSON."}}'

    # Output expanded keys to satisfy frontend/merge scripts
    step2_keys = [
        'Program name', 'Program Page url', 'description', 'IsStemProgram', 'ProgramCategory',
        'Concentration name', 'Resume', 'StatementOfPurpose', 'WritingSample', 'EnglishScore', 'GreOrGmat',
        'IsGMATOrGreRequired', 'IsGRERequired', 'MinimumGreScore', 'IsGMATRequired', 'MinimumGMATScore',
        'IsDuoLingoRequired', 'MinimumDuoLingoScore', 'IsIELTSRequired', 'MinimumIELTSScore',
        'IsTOEFLIBRequired', 'MinimumTOEFLScore', 'IsEnglishNotRequired', 'IsEnglishOptional',
        'MinGPA', 'CostPerCredit', 'ScholarshipType'
    ]
    
    step2_data = []
    for record in master_data:
        row = {k: record.get(k) for k in step2_keys}
        step2_data.append(row)
        
    df = pd.DataFrame(step2_data)
    df.to_csv(step2_csv_path, index=False)

    yield f'{{"status": "complete", "message": "Master extraction complete.", "files": {{"grad_extra_csv": "{step2_csv_path}"}}}}'