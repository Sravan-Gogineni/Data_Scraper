from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
import os
import json
import requests
import time
import random
import logging
import re
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import pandas as pd
load_dotenv()

# CHANGE THIS LINE FOR VERTEX AI
client = genai.Client(
    vertexai=True, 
    project=os.getenv("GCP_PROJECT"), 
    location=os.getenv("GCP_REGION")
)

Model = os.getenv("MODEL")


logger = logging.getLogger(__name__)

class GeminiModelWrapper:
    """Wrapper for Gemini API with retry logic and exponential backoff.
    Re-exported here so Programs sub-scripts can do:
        from Institution import GeminiModelWrapper, client
    """
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt, max_retries=5, base_delay=2):
        from google.genai import types as _types
        google_search_tool = _types.Tool(google_search=_types.GoogleSearch())
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=_types.GenerateContentConfig(tools=[google_search_tool])
                )
                return response
            except Exception as e:
                error_str = str(e)
                if "503" in error_str or "429" in error_str or "Too Many Requests" in error_str or "Overloaded" in error_str:
                    if attempt < max_retries - 1:
                        sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        continue
                logger.error(f"Failed after {attempt + 1} attempts: {e}")
                raise e

class UniversityDetails(BaseModel):
    CollegeName: str = Field(description="The exact official name of the university.")
    Phone: str = Field(description="The primary contact phone number for the university. MUST be formatted exactly as (XXX) XXX-XXXX. Return empty string if not found.")
    Email: str = Field(description="The undergraduate admissions departments email. Return empty string if not found.")
    SecondaryEmail: str = Field(description="A secondary contact email address for the university. Return empty string if not found.")
    Street1: str = Field(description="The primary street address (e.g., '123 Main St') or (300 boston post). Return empty string if not found.")
    Street2: str = Field(description="Secondary address information such as suite or building. Return empty string if not found.")
    County: str = Field(description="The county where the university is located. Return empty string if not found.")
    City: str = Field(description="The city where the university is located. Return empty string if not found.")
    State: str = Field(description="The state where the university is located. Return empty string if not found.")
    Country: str = Field(description="The country where the university is located. Return empty string if not found.")
    ZipCode: str = Field(description="The zip or postal code. Return empty string if not found.")

class UniversityUrls(BaseModel):
    WebsiteUrl: str = Field(description="The official website URL of the university. Return empty string if not found.")
    AdmissionOfficeUrl: str = Field(description="The undergraduate admissions office URL of the university. Return empty string if not found.")
    VirtualTourUrl: str = Field(description="The virtual tour URL of the university this can be a youvisit link or any other virtual tour link of the university. Return empty string if not found.")
    Facebook: str = Field(description="The official Facebook URL of the university. Return empty string if not found.")
    Instagram: str = Field(description="The official Instagram URL of the university. Return empty string if not found.")
    Twitter: str = Field(description="The official Twitter URL of the university. Return empty string if not found.")
    Youtube: str = Field(description="The official Youtube URL of the university. Return empty string if not found.")
    Tiktok: str = Field(description="The official Tiktok URL of the university. Return empty string if not found.")
    FinancialAidUrl: str = Field(description="The official Financial Aid URL of the university. Return empty string if not found.")
    LinkedIn: str = Field(description="The official LinkedIn URL of the university. Return empty string if not found.")

class ApplicationRequirements(BaseModel):
    ApplicationFees: str = Field(description="The application fee amount in USD specifically for International students. If domestic and international fees differ, report ONLY the international fee (e.g., '$100'). Do NOT mention fee waivers, waiver eligibility, Early Decision, Early Action, or any conditions under which the fee may be waived. Return empty string if not found.")
    TestPolicy: str = Field(description="The general test policy (e.g., 'Test-Optional', 'Required', 'Not Required'). Return empty string if not found.")
    Recommendations: int = Field(description="The minimum number of recommendations required to submit the application some programs may require more than others in that case return the maximum number of recommendations required. Return empty string if not found.")
    PersonalEssay: str = Field(description="Determine if a personal statement, statement of purpose, or narrative essay about the applicant is required. Return 'Required' or 'Not Required'. Return an empty string if the information is missing.")
    WritingSample: str = Field(description="Determine if a pre-existing academic paper, research sample, or professional publication is required. Do NOT mark 'Required' if only a personal essay is asked for. Return 'Required' or 'Not Required'. Return an empty string if not found.")
    AdditionalDeadlines: str = Field(description="Any additional or early action/decision deadlines mentioned. Return empty string if not found.")
    IsMultipleApplicationsAllowed: bool = Field(description="Are students allowed to submit multiple applications simultaneously? Return True, False, or empty string.")

class StandardizedTests(BaseModel):
    IsACTRequired: bool = Field(description="Does any program require ACT scores? Return True, False, or empty string.")
    IsSATRequired: bool = Field(description="Does any program require SAT scores? Return True, False, or empty string.")
    IsGMATOrGreRequired: bool = Field(description="Does any program require GMAT or GRE scores? Return True, False, or empty string.")
    IsGMATRequired: bool = Field(description="Does any program require GMAT scores? If maximum number of programs does not require GMAT scores Return False, else True.")
    IsGRERequired: bool = Field(description="Does any program require GRE scores? If maximum number of programs does not require GRE scores Return False, else True.")
    IsLSATRequired: bool = Field(description="Does any program require LSAT scores? Return True, False, or empty string.")
    IsMATRequired: bool = Field(description="Does any program require MAT scores? If maximum number of programs does not require MAT scores Ret urn False, else True.")
    IsMCATRequired: bool = Field(description="Does any program require MCAT scores? If maximum number of programs does not require MCAT scores Return False, else True.")
    IsPTERequired: bool = Field(description="Does any program require PTE scores? If maximum number of programs does not require PTE scores Return False, else True.")

class EnglishTests(BaseModel):
    IsDuoLingoRequired: bool = Field(description="Search the university's international student admissions page. Return True ONLY if the Duolingo English Test (DET) is explicitly listed as an accepted English proficiency test. Return False if it is not mentioned or explicitly rejected.")
    IsELSRequired: bool = Field(description="Search the university's international student admissions page. Return True ONLY if ELS Language Centers or ELS English program completion is explicitly listed as an accepted alternative to English proficiency tests. Return False otherwise.")
    IsIELTSRequired: bool = Field(description="Search the university's international student admissions page. Return True ONLY if IELTS (Academic) is explicitly listed as an accepted English proficiency test. Return False if it is not mentioned.")
    IsTOEFLIBRequired: bool = Field(description="Search the university's international student admissions page. Return True ONLY if TOEFL iBT is explicitly listed as an accepted English proficiency test. Return False if not mentioned.")
    IsEnglishNotRequired: bool = Field(description="Return True ONLY if the university's international admissions page explicitly and categorically states that NO English proficiency test is required for ALL international applicants — not just for students from certain countries or English-medium institutions. A partial country-based or degree-based exemption does NOT qualify. If the university lists ANY English test (TOEFL, IELTS, Duolingo, etc.) as a requirement or even an option, return False. When in doubt, return False.")
    IsEnglishOptional: bool = Field(description="Return True ONLY if the university has a formal English proficiency test-waiver or test-optional policy. This is different from a country-based exemption. Return False otherwise.")
    IsAnalyticalNotRequired: bool = Field(description="Return True ONLY if the university explicitly states that the GRE Analytical Writing section or a similar analytical/writing component is NOT required for admission. Return False by default unless explicitly stated.")
    IsAnalyticalOptional: bool = Field(description="Return True ONLY if the university explicitly states that the GRE Analytical Writing section or a similar writing component is optional (students may choose to submit it or not). Return False otherwise.")

class UniversityMetadata(BaseModel):
    Introduction: str = Field(description="A brief paragraph of introduction about the university.")
    TypeofInstitution: str = Field(description="Type of institution (e.g., 'Public', 'Private').")
    InstitutionType: str = Field(description="Type classification  only `Public, Private, etc.`.")
    TermFormat: str = Field(description="The academic term format (e.g., 'Semester', 'Quarter', 'Trimester').")
    TotalProgramsAvailable: int = Field(description="Total number of  programs available. include all undergraduate and graduate programs.")

class RankingAndCampus(BaseModel):
    CollegeSetting: str = Field(description="The setting of the college (e.g., 'Urban', 'Suburban', 'Rural').")
    NumberOfCampuses: int = Field(description="Total number of campuses. Return as integer (e.g. 1).")
    QsWorldRanking: str = Field(description="The current QS World University Ranking. Return just the number or range.")
    UsRanking: str = Field(description="The current US News & World Report National Ranking. Should be from current year or latest not from previous years. find from official website of usnews.com")
    CountriesRepresented: int = Field(description="Number of countries represented by the student body. like from how many countries students are studying in this university.")

class StudentDemographics(BaseModel):
    TotalStudents: int = Field(description="Total number of all students.")
    TotalStudentsEnrolled: int = Field(description="Total actively enrolled students.")
    TotalInternationalStudents: int = Field(description="Total number of international students.")
    TotalFacultyAvailable: int = Field(description="Total number of faculty members working in the university only teaching partime or fulltime faculty not other employees.")
    Student_Faculty: str = Field(description="The student-to-faculty ratio (e.g., '15:1').")

class TuitionAndScholarships(BaseModel):
    UGAvgTuition: int = Field(description="Average undergraduate tuition per year. Return as a plain integer (e.g., 45000). No dollar signs, commas, or text.")
    TuitionFees: str = Field(description="The tuition fees for the university for both UG and Grad. if the university public then include in-state and out-of-state tuition fees. else include the tuition fees for both UG and Grad. Ex(Undergraduate tution fee: $10000/in-state, $20000/out-of-state per year, Graduate tution fee: $20000 per year) incase of private university just include the tuition fees for both UG and Grad. example: Undergraduate tution fee: $10000 per year, Graduate tution fee: $20000 per year" )
    UGScholarshipHigh: int = Field(description="Highest undergraduate merit scholarship offered as listed on the official university website. Return as a plain integer only (e.g., 20000). No dollar signs, commas, ranges, or text. Return 0 if not found.")
    UGScholarshipLow: int = Field(description="Lowest undergraduate merit scholarship offered as listed on the official university website. Return as a plain integer only (e.g., 5000). No dollar signs, commas, ranges, or text. Return 0 if not found.")
    GradAvgTuition: int = Field(description="Average graduate tuition per year. Return as a plain integer (e.g., 30000). No dollar signs, commas, or text.")
    GradScholarshipHigh: int = Field(description="Highest graduate scholarship or stipend offered as listed on the official university website. Return as a plain integer only (e.g., 25000). No dollar signs, commas, ranges, or text. Return 0 if not found.")
    GradScholarshipLow: int = Field(description="Lowest graduate scholarship offered as listed on the official university website. Return as a plain integer only (e.g., 5000). No dollar signs, commas, ranges, or text. Return 0 if not found.")

class SpecificEnrollment(BaseModel):
    TotalUndergradMajors: int = Field(description="Total bachelor's degree majors offered.")
    UGTotalStudents: int = Field(description="Total undergraduate students enrolled.")
    UGInternationalStudents: int = Field(description="Total international undergraduate students enrolled.")
    TotalGraduatePrograms: int = Field(description="Total master's/doctoral programs offered.")
    GradTotalStudents: int = Field(description="Total graduate students enrolled.")
    GradInternationalStudents: int = Field(description="Total international graduate students enrolled.")

def _extract_json_from_text(text: str) -> dict:
    """Helper to safely extract JSON from LLM responses containing markdown."""
    text = text.strip()
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].strip()
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
    except Exception:
        return {}

def _strip_citations(result: dict) -> dict:
    """
    Strips Gemini Google Search grounding citation markers (e.g. [1], [72, 73, 74])
    from all string values in an extracted result dict.
    These appear when the model cites its search sources inline.
    """
    citation_pattern = re.compile(r'\s*\[\d+(?:,\s*\d+)*\]')
    return {
        k: citation_pattern.sub("", v).strip() if isinstance(v, str) else v
        for k, v in result.items()
    }


def _get_ground_truth(university_name: str) -> tuple[str, str]:
    """Helper to perform Step 1: Getting official name and URL via Google Search."""
    grounding_prompt = f"Find the official, exact name and the main official website URL for the university commonly known as '{university_name}'. Return ONLY a JSON string with keys 'exact_name' and 'url'."
    
    grounding_config = GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())]
    )
    
    try:
        response = client.models.generate_content(
            model=Model, 
            contents=grounding_prompt, 
            config=grounding_config
        )
        ground_truth = _extract_json_from_text(response.text)
        exact_name = ground_truth.get("exact_name", university_name)
        url = ground_truth.get("url", "")
    except Exception:
        exact_name = university_name
        url = ""
        
    return exact_name, url

def _format_phone(phone: str) -> str:
    """Helper to enforce (XXX) XXX-XXXX format just in case the LLM fails."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return phone

def _verify_urls(result: dict, schema_keys: list) -> dict:
    """Helper to verify and drop dead URLs by hitting them with a HEAD request."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    for key in schema_keys:
        if key != "CollegeName" and result.get(key):
            test_url = str(result[key])
            if not test_url.startswith("http"):
                continue
            try:
                # Use HEAD request first as it is faster
                response = requests.head(test_url, headers=headers, allow_redirects=True, timeout=5)
                # Only remove if explicitly Not Found or Gone. 
                # (403 or 401 means the page exists but is blocking our script)
                if response.status_code in [404, 410]:
                    # Fallback to GET just in case HEAD is improperly implemented by the server
                    response = requests.get(test_url, headers=headers, allow_redirects=True, timeout=5)
                    if response.status_code in [404, 410]:
                        print(f"Removing dead URL for {key}: {test_url} (HTTP {response.status_code})")
                        result[key] = ""
            except requests.RequestException as e:
                # DNS failure or connection timeout usually means a hallucinated/invalid domain
                print(f"Failed to connect to URL for {key}: {test_url} - {str(e)}")
                result[key] = ""
    return result

def get_university_details(university_name: str) -> dict:
    """
    Fetches grounded university details in a structured format by performing
    a two-step grounded extraction using the Gemini API and Google Search tool.
    """
    exact_name, url = _get_ground_truth(university_name)
        
    # Step 2: Extraction based on Ground Truth
    schema_json = UniversityDetails.model_json_schema()
    schema_keys = list(UniversityDetails.model_fields.keys())
    
    extraction_prompt = (
        f"You are a strict data extractor. Use the following ground truths:\n"
        f"- Exact Name: {exact_name}\n"
        f"- Official URL: {url}\n\n"
        f"Using primarily these ground truths and the official website, extract exactly "
        f"the required fields for this university.\n"
        f"CRITICAL INSTRUCTION: Explicitly use the Google Search tool to find the specific 'UNDERGRADUATE ADMISSIONS' email address. Do not skip this step. Dive deep to find the specific email, not just a general one.\n\n"
        f"Do not hallucinate. Use empty strings for any information that genuinely cannot be found.\n\n"
        f"You MUST return ONLY a valid JSON object matching EXACTLY this JSON schema:\n"
        f"{json.dumps(schema_json, indent=2)}\n\n"
        f"PAY CLOSE ATTENTION to the 'description' field of each property in the schema, as it tells you specifically what information to extract (e.g. undergraduate admissions email vs secondary email).\n"
        f"Do not include any additional keys or markdown wrappers."
    )
    
    extraction_config = GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
        temperature=0.1
    )
    
    try:
        extraction_response = client.models.generate_content(
            model=Model,
            contents=extraction_prompt,
            config=extraction_config
        )
        result = _extract_json_from_text(extraction_response.text)
        if "properties" in result and isinstance(result["properties"], dict):
            result = result["properties"]
    except Exception:
        result = {}
        
    # Ensure schema keys are present
    for k in schema_keys:
        if k not in result:
            result[k] = ""
    if not result.get("CollegeName"):
        result["CollegeName"] = exact_name
        
    # Programmatic Fallback Formatter for Phone
    if result.get("Phone"):
        result["Phone"] = _format_phone(result["Phone"])
        
    return result

def _fetch_homepage_links(url: str) -> str:
    """Helper to fetch exact links from the homepage to eliminate hallucination"""
    homepage_links = []
    if url:
        try:
            req_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            resp = requests.get(url, headers=req_headers, timeout=8)
            # Find absolute links
            all_hrefs = set(re.findall(r'href=[\'"](https?://[^\'" >]+)[\'"]', resp.text))
            # Find relative links that relate to admissions/tours
            rel_hrefs = set(re.findall(r'href=[\'"](/[^"\' >]*?(?:admission|visit|tour)[^"\' >]*?)[\'"]', resp.text, re.IGNORECASE))
            
            for rel in rel_hrefs:
                all_hrefs.add(url.rstrip('/') + rel)
                
            # Filter for social media and relevant internal links
            social_domains = ['facebook.com', 'instagram.com', 'twitter.com', 'youtube.com', 'tiktok.com', 'youvisit.com']
            for u in all_hrefs:
                u_lower = u.lower()
                if any(domain in u_lower for domain in social_domains) or 'admission' in u_lower or 'tour' in u_lower or 'visit' in u_lower:
                    homepage_links.append(u)
        except Exception as e:
            print(f"Warning: Could not fetch homepage links for {url}: {e}")

    return "\n".join(homepage_links[:50]) # cap at 50 to avoid prompt inflation

def get_university_urls(university_name: str) -> dict:
    """
    Fetches grounded university URLs in a structured format bypassing Gemini AI hallucinations
    for URLs by strictly matching against homepage HTML anchors where possible.
    """
    exact_name, url = _get_ground_truth(university_name)
    links_context = _fetch_homepage_links(url)
    
    # Step 2: Extraction based on Ground Truth
    schema_json = UniversityUrls.model_json_schema()
    schema_keys = list(UniversityUrls.model_fields.keys())
    
    extraction_prompt = (
        f"You are a strict data extractor. Use the following ground truths:\n"
        f"- Exact Name: {exact_name}\n"
        f"- Official URL: {url}\n\n"
        f"I have already scraped the official homepage ({url}) and found these relevant links:\n"
        f"--- HOMEPAGE LINKS ---\n"
        f"{links_context}\n"
        f"----------------------\n\n"
        f"Using these EXACT homepage links, extract the required fields for this university.\n"
        f"CRITICAL RULES TO AVOID HALLUCINATION:\n"
        f"1. YOU MUST PRIORITIZE the 'HOMEPAGE LINKS' provided above. Do not guess handles.\n"
        f"2. For Social Media Links, extract the exact link from the 'HOMEPAGE LINKS' list that corresponds to their official account.\n"
        f"3. For internal pages (VirtualTourUrl, AdmissionOfficeUrl), use the links from the list. If it's missing, you may use Google Search, but do not hallucinate.\n"
        f"4. If a valid, verified link cannot be found in the list or via searching, you MUST return an empty string.\n\n"
        f"You MUST return ONLY a valid JSON object matching EXACTLY this JSON schema:\n"
        f"{json.dumps(schema_json, indent=2)}\n\n"
        f"PAY CLOSE ATTENTION to the 'description' field of each property in the schema.\n"
        f"Do not include any additional keys or markdown wrappers."
    )
    
    extraction_config = GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
        temperature=0.1
    )
    
    try:
        extraction_response = client.models.generate_content(
            model=Model,
            contents=extraction_prompt,
            config=extraction_config
        )
        result = _extract_json_from_text(extraction_response.text)
        if "properties" in result and isinstance(result["properties"], dict):
            result = result["properties"]
    except Exception:
        result = {}
        
    # Ensure schema keys are present
    for k in schema_keys:
        if k not in result:
            result[k] = ""
    if not result.get("CollegeName"):
        result["CollegeName"] = exact_name
        
    return _verify_urls(result, schema_keys)


# Model-specific configs: what page to pre-discover and what to tell the model
MODEL_EXTRACTION_CONFIG: dict[str, dict] = {
    "ApplicationRequirements": {
        "target_page_hint": "undergraduate admissions application requirements page",
        "search_query_suffix": "undergraduate admissions application requirements",
        "context_label": "UNDERGRADUATE ADMISSIONS PAGE",
        "extra_instructions": (
            "Focus exclusively on the undergraduate admissions requirements page. "
            "Do NOT use graduate requirements. If a requirement has different values for domestic vs international, return the international value."
        ),
    },
    "StandardizedTests": {
        "target_page_hint": "admissions standardized testing policy page",
        "search_query_suffix": "standardized testing requirements ACT SAT admissions",
        "context_label": "STANDARDIZED TESTING POLICY PAGE",
        "extra_instructions": (
            "Search the admissions and testing policy pages. Return True if ANY program at the university requires that test, otherwise False. "
            "Do not guess — only return True if the test is explicitly named."
        ),
    },
    "EnglishTests": {
        "target_page_hint": "international student admissions English proficiency requirements page",
        "search_query_suffix": "international students English proficiency requirements TOEFL IELTS",
        "context_label": "INTERNATIONAL ADMISSIONS / ENGLISH PROFICIENCY PAGE",
        "extra_instructions": (
            "Use ONLY the international student admissions page. "
            "Return True for a test (IsDuoLingoRequired, IsIELTSRequired, IsTOEFLIBRequired, IsELSRequired) ONLY if it is explicitly listed as an accepted proof of English proficiency. "
            "CRITICAL — IsEnglishNotRequired: Return True ONLY if the university explicitly and categorically states that NO English proficiency test is required for ALL international applicants. "
            "If the page lists even ONE test as an option or requirement, IsEnglishNotRequired MUST be False. "
            "A statement like 'students from English-speaking countries are exempt' does NOT make IsEnglishNotRequired True — that is a partial exemption, not a blanket waiver. "
            "Default IsEnglishNotRequired to False unless there is unmistakable evidence of a complete, universal waiver. "
            "IsEnglishOptional is True ONLY if there is a formal test-optional waiver policy that any international student can apply for."
        ),
    },
    "UniversityMetadata": {
        "target_page_hint": "university about page or fact sheet",
        "search_query_suffix": "about overview fact sheet institution type term format programs",
        "context_label": "ABOUT / FAST FACTS PAGE",
        "extra_instructions": (
            "Search the university's 'About Us', 'Fast Facts', or 'Institutional Profile' page. "
            "For Introduction, write a factual 2-sentence summary based only on what is stated on the page."
        ),
    },
    "RankingAndCampus": {
        "target_page_hint": "university rankings and campus facts page",
        "search_query_suffix": "QS World Ranking US News ranking campus setting number of campuses",
        "context_label": "RANKINGS / CAMPUS INFO PAGE",
        "extra_instructions": (
            "Check US News & World Report and QS World Rankings for verified ranking numbers. "
            "For CollegeSetting, use the official Carnegie Classification (Urban, Suburban, Rural). "
            "For CountriesRepresented, look on the university's fast-facts or diversity page."
        ),
    },
    "StudentDemographics": {
        "target_page_hint": "university enrollment statistics and fact sheet page",
        "search_query_suffix": "total enrollment students faculty ratio international students statistics",
        "context_label": "ENROLLMENT / FAST FACTS PAGE",
        "extra_instructions": (
            "Use the university's official enrollment or fast-facts page first. "
            "If not found, use IPEDS or CommonDataSet as a secondary source. "
            "Return raw integer values — do not include commas or text."
        ),
    },
    "TuitionAndScholarships": {
        "target_page_hint": "official tuition fees and financial aid scholarships page",
        "search_query_suffix": "tuition fees cost of attendance financial aid scholarships undergraduate graduate",
        "context_label": "TUITION & FINANCIAL AID PAGE",
        "extra_instructions": (
            "Navigate directly to the official Bursar or Financial Aid page. "
            "For public universities, report both in-state and out-of-state tuition separately. "
            "For scholarships, ONLY report amounts explicitly listed on the official page — do not estimate or hallucinate ranges. "
            "If a scholarship range is listed, put the high end in High and low end in Low."
        ),
    },
    "SpecificEnrollment": {
        "target_page_hint": "university graduate and undergraduate enrollment breakdown page",
        "search_query_suffix": "undergraduate graduate enrollment international students majors programs offered",
        "context_label": "ENROLLMENT BREAKDOWN PAGE",
        "extra_instructions": (
            "Use the university's official enrollment or CommonDataSet CDS C section for UG/Grad breakdowns. "
            "TotalUndergradMajors = number of bachelor's degree programs. "
            "TotalGraduatePrograms = number of master's + doctoral programs. "
            "Do not conflate total programs with total majors."
        ),
    },
}

def _find_target_url(exact_name: str, official_url: str, search_query_suffix: str) -> str:
    """Uses Google Search to find a specific sub-page (e.g. tuition page) of the university's website."""
    search_prompt = (
        f"Find the exact URL for {exact_name}'s {search_query_suffix}. "
        f"The university's official domain is {official_url}. "
        f"Return ONLY a JSON string with a single key 'target_url' containing the best matching URL. "
        f"If no specific page is found, return the base URL: {official_url}"
    )
    config = GenerateContentConfig(tools=[Tool(google_search=GoogleSearch())])
    try:
        resp = client.models.generate_content(model=Model, contents=search_prompt, config=config)
        data = _extract_json_from_text(resp.text)
        return data.get("target_url", official_url) or official_url
    except Exception:
        return official_url

def _extract_model_data(model_class, exact_name: str, url: str) -> dict:
    """
    Model-aware extraction: first discovers the most relevant sub-page for this model,
    then runs a targeted extraction prompt using that page as the primary source.
    """
    schema_keys = list(model_class.model_fields.keys())
    model_name = model_class.__name__
    
    # Get model-specific config or fall back to a generic one
    config_entry = MODEL_EXTRACTION_CONFIG.get(model_name, {
        "search_query_suffix": "official information",
        "context_label": "OFFICIAL PAGE",
        "extra_instructions": "Use the official university website as the primary source.",
    })
    
    # Step 1: Discover the best target URL for this specific model
    target_url = _find_target_url(exact_name, url, config_entry["search_query_suffix"])
    context_label = config_entry["context_label"]
    extra_instructions = config_entry["extra_instructions"]
    
    # Build a clean field → description guide instead of the raw JSON schema
    # (passing raw schema_json confuses the model into returning schema dicts as values)
    field_guide = {
        k: v.description
        for k, v in model_class.model_fields.items()
    }
    empty_template = {k: "" for k in schema_keys}
    
    extraction_prompt = (
        f"You are a strict data extractor for {exact_name}.\n"
        f"Ground truth:\n"
        f"  - Official Website: {url}\n"
        f"  - Most Relevant Page ({context_label}): {target_url}\n\n"
        f"EXTRACTION STRATEGY (follow in order):\n"
        f"1. START by reading the '{context_label}' at: {target_url}\n"
        f"2. Extract data from that page first. It is your PRIMARY source.\n"
        f"3. If a field is missing from that page, search within the official domain ({url}) next.\n"
        f"4. As a last resort, check trusted external sources (US News, CollegeBoard, CommonDataSet).\n"
        f"5. Do NOT guess or hallucinate. Return an empty string for any field genuinely not found.\n\n"
        f"SPECIFIC INSTRUCTIONS FOR THIS MODEL:\n"
        f"{extra_instructions}\n\n"
        f"FIELD GUIDE — what each key means:\n"
        f"{json.dumps(field_guide, indent=2)}\n\n"
        f"Return ONLY a valid JSON object with EXACTLY these keys filled with real extracted values:\n"
        f"{json.dumps(empty_template, indent=2)}\n\n"
        f"Replace each empty string with the actual value. Do not include markdown wrappers or extra keys."
    )
    
    api_config = GenerateContentConfig(tools=[Tool(google_search=GoogleSearch())], temperature=0.1)
    try:
        resp = client.models.generate_content(model=Model, contents=extraction_prompt, config=api_config)
        result = _extract_json_from_text(resp.text)
        if "properties" in result and isinstance(result["properties"], dict):
            result = result["properties"]
    except Exception as e:
        print(f"Error extracting {model_name}: {e}")
        result = {}
        
    for k in schema_keys:
        if k not in result:
            result[k] = ""

    # Coerce int-typed fields: strip any text/symbols the LLM may have returned, convert 0 to empty string
    for k, field in model_class.model_fields.items():
        if field.annotation is int:
            if isinstance(result.get(k), str):
                digits = re.sub(r'[^\d]', '', result[k])
                val = int(digits) if digits else 0
            else:
                val = result.get(k)
            # If the value is 0, keep it blank as requested
            result[k] = "" if val == 0 else val
            
        # Coerce bool-typed fields: default to False if missing or not an explicit True
        elif field.annotation is bool:
            val = result.get(k)
            if isinstance(val, str):
                result[k] = val.strip().lower() == "true"
            elif isinstance(val, bool):
                result[k] = val
            else:
                result[k] = False
                
        # Clean up string fields: remove trailing periods
        elif field.annotation is str:
            val = result.get(k)
            if isinstance(val, str):
                # Remove trailing periods
                result[k] = val.rstrip('.')

    # Strip waiver/conditional text from ApplicationFees (e.g. "but may be waived for...")
    if "ApplicationFees" in result and isinstance(result["ApplicationFees"], str):
        fee = result["ApplicationFees"]
        # Cut off at common conjunctions that introduce waiver conditions
        fee = re.split(r',?\s*\b(but|however|though|unless|except|although)\b', fee, flags=re.IGNORECASE)[0]
        # Also remove any remaining waiver-related trailing phrases
        fee = re.sub(r'\s*(may be waived|fee waiv\w*|waiv\w+).*', '', fee, flags=re.IGNORECASE)
        result["ApplicationFees"] = fee.strip().rstrip(',;.')

    return _strip_citations(result)


def get_university_comprehensive_data(university_name: str) -> dict:
    """
    Fetches ALL fields for a university by breaking down the extraction into 8 focused
    Pydantic schemas to ensure LLM accuracy and prevent hallucination.
    """
    exact_name, url = _get_ground_truth(university_name)
    
    # We define the sequence of LLM extraction models
    models_to_extract = [
        ApplicationRequirements, 
        StandardizedTests, 
        EnglishTests, 
        UniversityMetadata, 
        RankingAndCampus, 
        StudentDemographics, 
        TuitionAndScholarships, 
        SpecificEnrollment
    ]
    
    unified_result = {"CollegeName": exact_name}
    
    # Iterate through each mini-model and strictly extract its 6-8 fields
    # Due to LLM speed limits, this will execute queries sequentially
    for model in models_to_extract:
        print(f"[1/2] Finding target URL for {model.__name__}...")
        model_data = _extract_model_data(model, exact_name, url)
        print(f"[2/2] Extracted {model.__name__} ✓")
        unified_result.update(model_data)
        
    unified_result["IsImported"] = "True"
    return unified_result

# make all the extracted data into a csv file   
def save_to_csv(data: dict, filename: str):
    # The exact columns and order requested by the user
    final_columns = [
        "CollegeName", "CollegeCode", "LogoPath", "Phone", "Email", "SecondaryEmail", 
        "Street1", "Street2", "County", "City", "State", "Country", "ZipCode", 
        "WebsiteUrl", "AdmissionOfficeUrl", "VirtualTourUrl", "Facebook", "Instagram", 
        "Twitter", "Youtube", "Tiktok", "ApplicationFees", "TestPolicy", 
        "CoursesAndGrades", "Recommendations", "PersonalEssay", "WritingSample", 
        "FinancialAidUrl", "AdditionalInformation", "AdditionalDeadlines", 
        "IsAdditionalInformationAvailable", "Status", "IsMultipleApplicationsAllowed", 
        "MaximumApplicationsAllowed", "CreatedBy", "CreatedDate", "LiveDate", "TuitionFees", 
        "UpdatedBy", "UpdatedDate", "CountryCode", "LinkedIn", "IsACTRequired", 
        "IsAnalyticalNotRequired", "IsAnalyticalOptional", "IsDuoLingoRequired", 
        "IsELSRequired", "IsEnglishNotRequired", "IsEnglishOptional", "IsGMATOrGreRequired", 
        "IsGMATRequired", "IsGRERequired", "IsIELTSRequired", "IsLSATRequired", 
        "IsMATRequired", "IsMCATRequired", "IsPTERequired", "IsSATRequired", 
        "IsTOEFLIBRequired", "QsWorldRanking", "UsRanking", "BatchId", "IsImportVerified", 
        "IsImported", "BannerImagePath", "CollegeHtmlAdditionalInfo", "Introduction", 
        "NumberOfCampuses", "TotalFacultyAvailable", "TotalProgramsAvailable", 
        "TotalStudentsEnrolled", "CollegeSetting", "TypeofInstitution", "CountriesRepresented", 
        "GradAvgTuition", "GradInternationalStudents", "GradScholarshipHigh", 
        "GradScholarshipLow", "GradTotalStudents", "Student_Faculty", "TotalGraduatePrograms", 
        "TotalInternationalStudents", "TotalStudents", "TotalUndergradMajors", "UGAvgTuition", 
        "UGInternationalStudents", "UGScholarshipHigh", "UGScholarshipLow", "UGTotalStudents", 
        "InstitutionType", "IsEnrolled", "TermFormat", "OGAEnrolledProgramLevels"
    ]
    
    # Ensure all required columns exist with at least a blank value
    for col in final_columns:
        if col not in data:
            data[col] = ""
            
    df = pd.DataFrame([data])
    
    # Reorder columns and drop any extra ones not in the final_columns list
    df = df[final_columns]
    
    #filename is university name+institution.csv
    sanitized = data["CollegeName"].replace(" ", "_").replace("/", "_").replace("\\", "_")
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Inst_outputs")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{sanitized}_Institution.csv")
    df.to_csv(filepath, index=False)
    print(f"Data saved to {filepath}")
    return filepath


def process_institution_extraction(university_name: str, **kwargs):
    """
    Generator function that runs the institution extraction and yields
    SSE-compatible JSON progress and completion messages.
    This is the entry point called by the Flask backend (app.py).
    All extra kwargs are accepted but ignored to match the backend's call signature.
    """
    import json as _json

    models_to_extract = [
        ApplicationRequirements,
        StandardizedTests,
        EnglishTests,
        UniversityMetadata,
        RankingAndCampus,
        StudentDemographics,
        TuitionAndScholarships,
        SpecificEnrollment,
    ]

    try:
        yield _json.dumps({"status": "progress", "message": f"Finding official name and URL for '{university_name}'..."})
        exact_name, url = _get_ground_truth(university_name)
        yield _json.dumps({"status": "progress", "message": f"Ground truth resolved: {exact_name}"})

        # --- SKIP IF EXISTS CHECK ---
        sanitized = exact_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Inst_outputs")
        filepath = os.path.join(output_dir, f"{sanitized}_Institution.csv")
        
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            yield _json.dumps({
                "status": "complete", 
                "message": f"Institution data for '{exact_name}' already exists. Skipping extraction.",
                "files": {"inst_csv": filepath}
            })
            return
        # ----------------------------

        unified_result = {"CollegeName": exact_name}

        for model in models_to_extract:
            yield _json.dumps({"status": "progress", "message": f"Extracting {model.__name__}..."})
            model_data = _extract_model_data(model, exact_name, url)
            unified_result.update(model_data)
            yield _json.dumps({"status": "progress", "message": f"{model.__name__} extracted ✓"})

        unified_result["IsImported"] = "True"

        # Also extract contact + URL details
        yield _json.dumps({"status": "progress", "message": "Extracting contact details..."})
        contact_data = get_university_details(exact_name)
        for k, v in contact_data.items():
            if k != "CollegeName":
                unified_result.setdefault(k, v)

        yield _json.dumps({"status": "progress", "message": "Extracting URLs..."})
        url_data = get_university_urls(exact_name)
        for k, v in url_data.items():
            if k != "CollegeName":
                unified_result.setdefault(k, v)

        yield _json.dumps({"status": "progress", "message": "Saving CSV..."})
        filepath = save_to_csv(unified_result, exact_name)

        yield _json.dumps({
            "status": "complete",
            "message": f"Institution data for '{exact_name}' extracted successfully.",
            "files": {"inst_csv": filepath}
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield _json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    university_name = "University of New Haven"
    data = get_university_comprehensive_data(university_name)

    # Also extract contact details (Phone, Email, Address) and URLs (social media, admissions, etc.)
    contact_data = get_university_details(university_name)
    url_data = get_university_urls(university_name)
    for k, v in {**contact_data, **url_data}.items():
        if k != "CollegeName":
            data.setdefault(k, v)

    save_to_csv(data, university_name)