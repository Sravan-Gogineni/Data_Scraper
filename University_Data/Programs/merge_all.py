import pandas as pd
import os
import re
import time
import random
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── Gemini client (VertexAI) ──────────────────────────────────────────────────
_gemini_client = genai.Client(
    vertexai=True,
    project=os.getenv("GCP_PROJECT"),
    location="us-east4",
)
_GEMINI_MODEL = os.getenv("MODEL")

def _gemini_generate(prompt: str, max_retries: int = 5, base_delay: float = 2.0) -> str:
    """Call Gemini and return the raw text response (no Google Search tool)."""
    for attempt in range(max_retries):
        try:
            response = _gemini_client.models.generate_content(
                model=_GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0),
            )
            if not response.candidates or not response.candidates[0].content.parts:
                return ""
            return response.text.strip()
        except Exception as e:
            err = str(e)
            if any(code in err for code in ("503", "429", "Too Many Requests", "Overloaded")):
                if attempt < max_retries - 1:
                    sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Gemini attempt {attempt+1} failed, retrying in {sleep_time:.1f}s: {e}")
                    time.sleep(sleep_time)
                    continue
            logger.error(f"Gemini error after {attempt+1} attempts: {e}")
            return ""
    return ""

# ── Predefined category list ──────────────────────────────────────────────────
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


def run(university_name=None):
    yield f'{{"status": "progress", "message": "Starting final merge of Graduate and Undergraduate programs..."}}'
    
    if not university_name:
        yield f'{{"status": "error", "message": "University name not provided for final merge."}}'
        return

    sanitized_name = university_name.replace(" ", "_").replace("/", "_")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Paths to the final CSVs
    grad_csv_path = os.path.join(script_dir, 'graduate_programs', 'Grad_prog_outputs', f'{sanitized_name}_graduate_programs_final.csv')
    undergrad_csv_path = os.path.join(script_dir, 'undergraduate_programs', 'Undergrad_prog_outputs', f'{sanitized_name}_undergraduate_programs_final.csv')
    
    output_csv_path = os.path.join(script_dir, f'{sanitized_name}_Final.csv')
    
    dfs = []
    
    # Load Graduate Programs
    if os.path.exists(grad_csv_path):
        df_grad = pd.read_csv(grad_csv_path)
        yield f'{{"status": "progress", "message": "Loaded {len(df_grad)} graduate programs"}}'
        dfs.append(df_grad)
    else:
        yield f'{{"status": "progress", "message": "Graduate programs file not found at {grad_csv_path}"}}'
        
    # Load Undergraduate Programs
    if os.path.exists(undergrad_csv_path):
        df_undergrad = pd.read_csv(undergrad_csv_path)
        yield f'{{"status": "progress", "message": "Loaded {len(df_undergrad)} undergraduate programs"}}'
        dfs.append(df_undergrad)
    else:
        yield f'{{"status": "progress", "message": "Undergraduate programs file not found at {undergrad_csv_path}"}}'
        
    if not dfs:
        yield f'{{"status": "error", "message": "No data found to merge."}}'
        return



    # Merge
    yield f'{{"status": "progress", "message": "Merging datasets..."}}'
    final_df = pd.concat(dfs, ignore_index=True)
    final_df['QsWorldRanking'] = ""
    final_df['CollegeApplicationFee'] = ""
    final_df['IsNewlyLaunched'] = "FALSE"
    final_df['IsImportVerified'] = "FALSE"
    final_df['Is_Recommendation_Sponser'] = "FALSE"
    final_df['IsRecommendationSystemOpted'] = "FALSE"
    final_df['Term']="Fall 2026"
    final_df['LiveDate']=""
    final_df['DeadlineDate']=""
    final_df['PreviousYearAcceptanceRates']=""
    final_df['IsStemProgram']= final_df['IsStemProgram'].fillna(False)
    final_df['IsStemProgram']= final_df['IsStemProgram'].astype(bool)
    final_df['IsACTRequired']= final_df['IsACTRequired'].fillna(False)
    final_df['IsACTRequired']= final_df['IsACTRequired'].astype(bool)
    final_df['IsSATRequired']= final_df['IsSATRequired'].fillna(False)
    final_df['IsSATRequired']= final_df['IsSATRequired'].astype(bool)
    final_df['IsAnalyticalNotRequired'] = final_df['IsAnalyticalNotRequired'].fillna(True)
    final_df['IsAnalyticalNotRequired'] = final_df['IsAnalyticalNotRequired'].astype(bool)
    final_df['IsAnalyticalOptional'] = final_df['IsAnalyticalOptional'].fillna(True)
    final_df['IsAnalyticalOptional'] = final_df['IsAnalyticalOptional'].astype(bool)

    final_df['ProgramName'] = final_df['ProgramName'].apply(standardize_program_name)

    yield f'{{"status": "progress", "message": "Assigning program categories via Gemini..."}}'
    final_df['ProgramCategory'] = final_df['ProgramName'].apply(get_program_category)

    ###############
    final_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    yield f'{{"status": "complete", "message": "Successfully merged {len(final_df)} programs", "files": {{"final_csv": "{output_csv_path}"}}}}'


def get_program_category(program_name: str) -> str:
    """Use Gemini to pick the single best-matching category from PROGRAM_CATEGORIES.

    Returns the matched category string, or an empty string if nothing fits.
    """
    if not isinstance(program_name, str) or not program_name.strip():
        return ""

    categories_str = "\n".join(f"- {c}" for c in PROGRAM_CATEGORIES)

    prompt = (
        f"You are a university program classifier. Given the program name below, "
        f"select the SINGLE best-matching category from the provided list.\n\n"
        f"Program Name: {program_name}\n\n"
        f"Categories:\n{categories_str}\n\n"
        f"Rules:\n"
        f"1. Return ONLY the exact category name from the list above — no extra text, "
        f"no explanation, no punctuation.\n"
        f"2. If no category fits well, return: Other\n"
        f"3. Do NOT invent new category names."
    )

    result = _gemini_generate(prompt)

    # Validate that the model returned a known category
    result_clean = result.strip().strip('"').strip("'")
    if result_clean in PROGRAM_CATEGORIES:
        return result_clean

    # Fuzzy fallback: case-insensitive match
    for cat in PROGRAM_CATEGORIES:
        if cat.lower() == result_clean.lower():
            return cat

    # If unrecognised, log and return the raw answer so we can inspect it
    logger.warning(f"Gemini returned unknown category '{result_clean}' for program '{program_name}'")
    return result_clean or ""

def standardize_program_name(name):
    name_str = str(name).strip()
    # Mapping of suffix to prefix
    mappings = {
        " MS": "Master of Science in",
        " MFA": "Master of Fine Arts in",
        " BS": "Bachelor of Science in",
        " BA": "Bachelor of Arts in",
        " MA": "Master of Arts in",
        "AAS": "Associate of Applied Science in",
        "AS": "Associate of Science in",
        "AA": "Associate of Arts in",
        "BFA": "Bachelor of Fine Arts in",
        "MBA": "Master of Business Administration in",
        "AOS": "Associate of Science in",
        " (MS)": "Master of Science in",
        " (MFA)": "Master of Fine Arts in",
        " (BS)": "Bachelor of Science in",
        " (BA)": "Bachelor of Arts in",
        " (MA)": "Master of Arts in",
        " (AAS)": "Associate of Applied Science in",
        " (AS)": "Associate of Science in",
        " (AA)": "Associate of Arts in",
        " (BFA)": "Bachelor of Fine Arts in",
        " (MBA)": "Master of Business Administration in",
        "(BA, BS)": "Bachelor of Arts in"

    }
    
    for suffix, prefix in mappings.items():
        if name_str.endswith(suffix):
            # Remove the suffix (e.g. " MS") and prepend the prefix
            # Original: "Program MS" -> "Program" -> "Master of Science in Program"
            clean_name = name_str[:-len(suffix)]
            return f"{prefix} {clean_name}"
            
    return name_str