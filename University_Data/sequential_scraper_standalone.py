#!/usr/bin/env python3
"""
Standalone Sequential University Data Scraper - COMPLETE VERSION
------------------------------------------------------------------
This script consolidates ALL extraction logic for Institution, Departments, and Programs
into a single file that can be shared without external dependencies beyond standard libraries
and the Google Gemini API.

All functions from Institution.py, Department.py, and Programs.py are included here.

Usage:
    python sequential_scraper_standalone.py "University Name"

Example:
    python sequential_scraper_standalone.py "SUNY Brockport"

Dependencies:
    - pandas
    - google-genai
    - python-dotenv
    - openpyxl (optional, for Excel output)
"""

import os
import sys
import json
import pandas as pd
import time
import random
from google import genai
from google.genai import types
from dotenv import load_dotenv
import logging
import re
import csv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ============================================================================
# GEMINI API SETUP
# ============================================================================

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

class GeminiModelWrapper:
    """Wrapper for Gemini API with retry logic and exponential backoff"""
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt, max_retries=5, base_delay=2):
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(tools=[google_search_tool])
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

model = GeminiModelWrapper(client, os.getenv("MODEL"))

def generate_text_safe(prompt):
    """Generate text with safety checks and error handling"""
    try:
        response = model.generate_content(prompt)
        
        if not response.candidates or not response.candidates[0].content.parts:
            logger.warning("Model blocked response or returned empty.")
            return "null"
            
        text = response.text
        clean_text = text.replace("```json", "").replace("```", "").strip()
        
        return clean_text if clean_text else "null"
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return "null"

def extract_clean_value(response_text):
    """Extract clean value from AI response, removing evidence and formatting"""
    if not response_text:
        return None
    
    text = response_text.replace("**", "").replace("```", "").strip()
    
    separators = ["\nEvidence:", "\nURL:", "\nSource:", "\nSnippet:", "\nQuote:"]
    for sep in separators:
        idx = text.lower().find(sep.lower())
        if idx != -1:
            text = text[:idx].strip()
            break
    
    text = text.split('\n')[0].strip()
    
    if ":" in text:
        parts = text.split(":", 1)
        text = parts[1].strip()
    
    if text.lower() == "null" or not text:
        return None
        
    if text.startswith("//"):
        text = "https:" + text
    elif text.startswith("www."):
        text = "https://" + text
        
    return text

# ============================================================================
# INSTITUTION EXTRACTION - URL HELPER FUNCTIONS
# ============================================================================

def get_academic_calender_url(website_url, university_name):
    prompt = (
        f"What is the academic calender URL for {university_name} on {website_url}. "
        f"Search query: site:{website_url} academic calender "
        "Return only the academic calender URL, no other text. "
        "Only if explicitly stated, otherwise return null. "
        "Also provide evidence with correct URL or page."
    )
    return extract_clean_value(generate_text_safe(prompt))

def get_cost_of_attendance_url(website_url, university_name):
    prompt = (
        f"What is the cost of attendance URL for {university_name} on {website_url}. "
        f"Search query: site:{website_url} cost of attendance "
        "Return only the cost of attendance URL, no other text. "
        "Only if explicitly stated, otherwise return null. "
        "Also provide evidence."
    )
    return extract_clean_value(generate_text_safe(prompt))

def get_tuition_fee_url(website_url, university_name):
    prompt = (
        f"Find the tuition fee URL for {university_name} on {website_url}. "
        f"Search query: site:{website_url} tuition fees "
        "Return only the tuition fee URL, no other text. "
        "Only if explicitly stated, otherwise return null. "
        "Also provide evidence."
    )
    return generate_text_safe(prompt)

def get_international_students_requirements_url(website_url, university_name):
    prompt = (
        f"What is the international students application requirements URL for {university_name} on {website_url}. "
        f"Search query: site:{website_url} international students application requirements "
        "Return only the requirements URL, no other text. "
        "Only if explicitly stated, otherwise return null."
    )
    return generate_text_safe(prompt)

# ============================================================================
# INSTITUTION EXTRACTION - DATA FUNCTIONS (ALL ~80+ FUNCTIONS)
# ============================================================================

def get_womens_college(website_url, university_name):
    prompt = f"Is {university_name}, {website_url} a women's college? Return only 'yes' or 'no'. Otherwise null. Provide evidence."
    return generate_text_safe(prompt)

def get_cost_of_living_min(website_url, university_name):
    prompt = f"What is the minimum cost of living for students at {university_name}, {website_url}? Return only the amount. Otherwise null."
    return generate_text_safe(prompt)

def get_cost_of_living_max(website_url, university_name):
    prompt = f"What is the maximum cost of living for students at {university_name}, {website_url}? Return only the amount. Otherwise null."
    return generate_text_safe(prompt)

def get_orientation_available(website_url, university_name):
    prompt = f"Is orientation available for students at {university_name}, {website_url}? Return 'yes' or 'no'. Otherwise null."
    return generate_text_safe(prompt)

def get_college_tour_after_admissions(website_url, university_name):
    prompt = f"Does {university_name}, {website_url} offer in-person college tours after admissions? Return 'yes' or 'no'. Otherwise null."
    return generate_text_safe(prompt)

def get_university_name(website_url, university_name):
    prompt = f"What is the official name of {university_name} from {website_url}? Return only the name. Otherwise null."
    return generate_text_safe(prompt)

def get_college_setting(website_url, university_name):
    prompt = f"What is the college setting for {university_name}, {website_url}? (urban, suburban, rural, etc.) Otherwise null."
    return generate_text_safe(prompt)

def get_type_of_institution(website_url, university_name):
    prompt = f"What is the type of institution for {university_name}, {website_url}? Return only the type. Otherwise null."
    return generate_text_safe(prompt)

def get_student_faculty(website_url, university_name):
    prompt = f"What is the student faculty ratio for {university_name}? Example: 15:1. Return only the ratio. Otherwise null."
    return generate_text_safe(prompt)

def get_number_of_campuses(website_url, university_name):
    prompt = f"What is the number of campuses for {university_name}, {website_url}? Return only the number. Otherwise null."
    return generate_text_safe(prompt)

def get_total_faculty_available(website_url, university_name):
    prompt = f"What is the total number of faculty at {university_name}, {website_url}? Return only the number. Otherwise null."
    return generate_text_safe(prompt)

def get_total_programs_available(website_url, university_name):
    prompt = f"What is the total number of programs at {university_name}, {website_url}? Return only the number. Otherwise null."
    return generate_text_safe(prompt)

def get_total_students_enrolled(website_url, university_name):
    prompt = f"What is total students enrolled at {university_name}, {website_url}? Return only the number. Otherwise null."
    return generate_text_safe(prompt)

def get_total_graduate_programs(website_url, university_name):
    prompt = f"What is the total number of graduate programs at {university_name}, {website_url}? Return only the number. Otherwise null."
    return generate_text_safe(prompt)

def get_total_international_students(website_url, university_name):
    prompt = f"What is total international students at {university_name}, {website_url}? Return only the number. Otherwise null."
    return generate_text_safe(prompt)

def get_total_students(website_url, university_name):
    prompt = f"What is the total number of students at {university_name}, {website_url}? Return only the number. Otherwise null."
    return generate_text_safe(prompt)

def get_total_undergrad_majors(website_url, university_name):
    prompt = f"What is total undergrad majors offered by {university_name}, {website_url}? Return only the number. Otherwise null."
    return generate_text_safe(prompt)

def get_countries_represented(website_url, university_name):
    prompt = f"How many countries are represented at {university_name}, {website_url}? Return only the count. Otherwise null."
    return generate_text_safe(prompt)

def get_street(website_url, university_name):
    prompt = f"What is the street address for {university_name}, {website_url}? Return only street address, no city/state. Otherwise null."
    return generate_text_safe(prompt)

def get_county(website_url, university_name):
    prompt = f"What county is {university_name}, {website_url} located in? Return only county name. Otherwise null."
    return generate_text_safe(prompt)

def get_city(website_url, university_name):
    prompt = f"What city is {university_name}, {website_url} located in? Return only city name. Otherwise null."
    return generate_text_safe(prompt)

def get_state(website_url, university_name):
    prompt = f"What state is {university_name}, {website_url} located in? Return only state name. Otherwise null."
    return generate_text_safe(prompt)

def get_country(website_url, university_name):
    prompt = f"What country is {university_name}, {website_url} located in? Return only country name. Otherwise null."
    return generate_text_safe(prompt)

def get_zip_code(website_url, university_name):
    prompt = f"What is the zip code for {university_name}, {website_url}? Return only the zip code. Otherwise null."
    return generate_text_safe(prompt)

def get_application_requirements(website_url, university_name):
    prompt = f"What are application requirements for {university_name}, {website_url}? Return only requirements. Otherwise null."
    return generate_text_safe(prompt)

def get_contact_information(website_url, university_name):
    prompt = f"What is the contact information for {university_name}, {website_url}? Return only contact info. Otherwise null."
    return generate_text_safe(prompt)

def get_grad_international_students(website_url, university_name):
    prompt = f"What is the number of graduate international students at {university_name}, {website_url}? Otherwise null."
    return generate_text_safe(prompt)

def get_grad_scholarship_high(website_url, university_name, graduate_financial_aid_urls=None, common_financial_aid_urls=None):
    url_to_use = graduate_financial_aid_urls or common_financial_aid_urls or website_url
    prompt = f"What is the highest graduate scholarship at {university_name} at {url_to_use}? Return only the amount. Otherwise null."
    return generate_text_safe(prompt)

def get_phone(website_url, university_name):
    prompt = f"What is the main phone number for {university_name}, {website_url}? Return only phone number. Otherwise null."
    return generate_text_safe(prompt)

def get_email(website_url, university_name):
    prompt = f"What is the main/admissions email for {university_name}, {website_url}? Return only email. Otherwise null."
    return generate_text_safe(prompt)

def get_secondary_email(website_url, university_name):
    prompt = f"What is the secondary email for {university_name}, {website_url}? Return only email. Otherwise null."
    return generate_text_safe(prompt)

def get_website_url(website_url, university_name):
    prompt = f"What is the official website URL for {university_name}, {website_url}? Return only URL (http/https). Otherwise null."
    return generate_text_safe(prompt)

def get_admission_office_url(website_url, university_name):
    prompt = f"What is the admission office URL for {university_name}, {website_url}? Return only URL. Otherwise null."
    return generate_text_safe(prompt)

def get_virtual_tour_url(website_url, university_name):
    prompt = f"What is the virtual tour URL for {university_name}? Return direct URL to virtual tour page. Otherwise null."
    return generate_text_safe(prompt)

def get_financial_aid_url(website_url, university_name):
    prompt = f"What is the financial aid URL for {university_name}, {website_url}? Return only URL. Otherwise null."
    return generate_text_safe(prompt)

def get_application_fees(website_url, university_name):
    prompt = (
        f"Find application fee for domestic and international applicants for {university_name}, {website_url}? "
        "Return line of text with fees. Example: 'Domestic $50, International $75'. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_test_policy(website_url, university_name):
    prompt = (
        f"Is {university_name} test optional? {website_url}? "
        "If ACT/SAT optional, return 'Test Optional'. If required, return 'Test Required'. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_recommendations(website_url, university_name):
    url_to_use = get_international_students_requirements_url(website_url, university_name)
    prompt = (
        f"How many letters of recommendation required for {university_name}, {url_to_use}? "
        "Return only count (e.g., 2, 3). Otherwise null."
    )
    return generate_text_safe(prompt)

def get_personal_essay(website_url, university_name):
    prompt = (
        f"Are personal essays/statements required for undergraduate admissions at {university_name}, {website_url}? "
        "Return 'Required' or 'Not Required'. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_writing_sample(website_url, university_name):
    prompt = (
        f"Does {university_name}, {website_url} require writing sample for application? "
        "Return 'Required' or 'Not Required'. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_additional_deadlines(website_url, university_name):
    prompt = (
        f"Identify specific non-application deadlines (scholarships, housing) for {university_name}, {website_url}. "
        "Format: [Deadline Name]: [Date]. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_is_multiple_applications_allowed(website_url, university_name):
    requirements_url = get_international_students_requirements_url(website_url, university_name)
    prompt = (
        f"Can applicants apply to multiple programs for same term at {university_name}? "
        "Return JSON: {\"allowed\": true/false/null, \"restrictions\": \"...\", \"evidence_url\": \"...\"}. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_is_act_required(website_url, university_name):
    prompt = f"Is ACT required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_analytical_not_required(website_url, university_name):
    prompt = f"Is analytical writing NOT required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_analytical_optional(website_url, university_name):
    prompt = f"Is analytical writing optional for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_duolingo_required(website_url, university_name):
    prompt = f"Is Duolingo required for international students at {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_els_required(website_url, university_name):
    prompt = f"Is ELS required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_english_not_required(website_url, university_name):
    prompt = f"Is English proficiency NOT required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_english_optional(website_url, university_name):
    prompt = f"Is English proficiency test optional for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_gmat_or_gre_required(website_url, university_name):
    prompt = f"Is GMAT or GRE required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_gmat_required(website_url, university_name):
    prompt = f"Is GMAT required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_gre_required(website_url, university_name):
    prompt = f"Is GRE required for international students at {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_ielts_required(website_url, university_name):
    prompt = f"Is IELTS required for international students at {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_lsat_required(website_url, university_name):
    prompt = f"Is LSAT required for law programs at {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_mat_required(website_url, university_name):
    prompt = (
        f"Is MAT (Miller Analogies Test) still accepted for {university_name}, {website_url}? "
        "Return JSON: {\"Allowed\": true/false/null, \"status\": \"Required/Optional/Retired\", \"evidence_url\": \"...\"}. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_is_mcat_required(website_url, university_name):
    prompt = f"Is MCAT required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_pte_required(website_url, university_name):
    prompt = f"Is PTE required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_sat_required(website_url, university_name):
    prompt = f"Is SAT required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_is_toefl_ib_required(website_url, university_name):
    prompt = f"Is TOEFL iBT required for {university_name}, {website_url}? Return 'True' or 'False'. Otherwise null."
    return generate_text_safe(prompt)

def get_tuition_fees(website_url, university_name):
    tuition_fee_url = get_tuition_fee_url(website_url, university_name)
    prompt = (
        f"Find tuition fees for {university_name} at {tuition_fee_url}. "
        "Format: 'Undergraduate: ~$X per year (Resident), ~$Y (Non-Resident). Graduate: ~$A (Resident), ~$B (Non-Resident)'. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_facebook(website_url, university_name):
    prompt = f"What is the Facebook URL for {university_name}, {website_url}? Return only URL. Otherwise null."
    return generate_text_safe(prompt)

def get_instagram(website_url, university_name):
    prompt = f"What is the Instagram URL for {university_name}, {website_url}? Return only URL. Otherwise null."
    return generate_text_safe(prompt)

def get_twitter(website_url, university_name):
    prompt = f"What is the Twitter URL for {university_name}, {website_url}? Return only URL. Otherwise null."
    return generate_text_safe(prompt)

def get_youtube(website_url, university_name):
    prompt = f"What is the YouTube URL for {university_name}, {website_url}? Return only URL. Otherwise null."
    return generate_text_safe(prompt)

def get_tiktok(website_url, university_name):
    prompt = f"What is the TikTok URL for {university_name}, {website_url}? Return only URL. Otherwise null."
    return generate_text_safe(prompt)

def get_linkedin(website_url, university_name):
    prompt = f"What is the LinkedIn URL for {university_name}, {website_url}? Return only URL. Otherwise null."
    return generate_text_safe(prompt)

def get_grad_avg_tuition(website_url, university_name, graduate_tuition_fee_urls=None, common_tuition_fee_urls=None):
    coa_url = get_cost_of_attendance_url(website_url, university_name)
    url_to_use = coa_url or graduate_tuition_fee_urls or common_tuition_fee_urls or website_url
    prompt = (
        f"Identify average annual graduate tuition for {university_name} at {url_to_use}. "
        "Return only numerical value with currency (e.g., $15,400). Otherwise null."
    )
    return generate_text_safe(prompt)

def get_grad_scholarship_low(website_url, university_name, graduate_financial_aid_urls=None, common_financial_aid_urls=None):
    url_to_use = graduate_financial_aid_urls or common_financial_aid_urls or website_url
    prompt = f"What is lowest graduate scholarship at {university_name}, {url_to_use}? Return amount. Otherwise null."
    return generate_text_safe(prompt)

def get_grad_total_students(website_url, university_name):
    prompt = f"What is total graduate students at {university_name}, {website_url}? Return number. Otherwise null."
    return generate_text_safe(prompt)

def get_ug_avg_tuition(website_url, university_name, undergraduate_tuition_fee_urls=None, common_tuition_fee_urls=None):
    coa_url = get_cost_of_attendance_url(website_url, university_name)
    url_to_use = coa_url or undergraduate_tuition_fee_urls or common_tuition_fee_urls or website_url
    prompt = (
        f"Identify average annual undergraduate tuition for {university_name} at {url_to_use}. "
        "Return only numerical value with currency. Otherwise null."
    )
    return generate_text_safe(prompt)

def get_ug_international_students(website_url, university_name):
    prompt = f"What is number of undergraduate international students at {university_name}, {website_url}? Otherwise null."
    return generate_text_safe(prompt)

def get_ug_scholarship_high(website_url, university_name, undergraduate_financial_aid_urls=None, common_financial_aid_urls=None):
    url_to_use = undergraduate_financial_aid_urls or common_financial_aid_urls or website_url
    prompt = f"What is highest undergraduate scholarship at {university_name}, {url_to_use}? Return amount/percentage. Otherwise null."
    return generate_text_safe(prompt)

def get_ug_scholarship_low(website_url, university_name, undergraduate_financial_aid_urls=None, common_financial_aid_urls=None):
    url_to_use = undergraduate_financial_aid_urls or common_financial_aid_urls or website_url
    prompt = f"What is lowest undergraduate scholarship at {university_name}, {url_to_use}? Return amount/percentage. Otherwise null."
    return generate_text_safe(prompt)

def get_ug_total_students(website_url, university_name):
    prompt = f"What is total undergraduate students at {university_name}, {website_url}? Return number. Otherwise null."
    return generate_text_safe(prompt)

def get_term_format(website_url, university_name):
    academic_calender_url = get_academic_calender_url(website_url, university_name)
    search_context = academic_calender_url if academic_calender_url else website_url
    prompt = (
        f"Identify academic calendar system for {university_name} at {search_context}. "
        "Return ONLY: 'Semester', 'Quarter', 'Trimester', or 'null'."
    )
    return generate_text_safe(prompt)

def get_introduction(website_url, university_name):
    prompt = (
        f"Find 2-3 paragraphs introduction for {university_name} at {website_url}. "
        "Include history, mission, vision, values. Otherwise null."
    )
    return generate_text_safe(prompt)

# ============================================================================
# INSTITUTION EXTRACTION - MAIN PROCESS
# ============================================================================

def process_institution_extraction(
    university_name, 
    undergraduate_tuition_fee_urls=None, 
    graduate_tuition_fee_urls=None, 
    undergraduate_financial_aid_urls=None, 
    graduate_financial_aid_urls=None,
    common_financial_aid_urls=None,
    common_tuition_fee_urls=None
):
    """Process complete institution data extraction"""
    print(f"Processing {university_name}...")
    yield '{"status": "progress", "message": "Initializing extraction..."}'
    
    # Get Website URL
    yield f'{{"status": "progress", "message": "Finding official website for {university_name}..."}}'
    prompt = f"What is the official university website for {university_name}?"
    website_url = generate_text_safe(prompt)
    print(f"Found Website URL: {website_url}")
    
    # Get Tuition Fee URL
    yield f'{{"status": "progress", "message": "Finding tuition fee URL..."}}'
    ai_found_tuition_url = get_tuition_fee_url(website_url, university_name)
    print(f"Found Tuition Fee URL: {ai_found_tuition_url}")

    # Extract all data fields
    yield '{("status": "progress", "message": "Extracting general information..."}'
    new_fields_data = {
        "womens_college": get_womens_college(website_url, university_name),
        "cost_of_living_min": get_cost_of_living_min(website_url, university_name),
        "cost_of_living_max": get_cost_of_living_max(website_url, university_name),
        "orientation_available": get_orientation_available(website_url, university_name),
        "college_tour_after_admissions": get_college_tour_after_admissions(website_url, university_name),
        "term_format": get_term_format(website_url, university_name),
        "introduction": get_introduction(website_url, university_name),
    }

    yield '{"status": "progress", "message": "Extracting application requirements..."}'
    application_data = {
        "application_requirements": get_application_requirements(website_url, university_name),
        "application_fees": get_application_fees(website_url, university_name),
        "test_policy": get_test_policy(website_url, university_name),
        "courses_and_grades": None,
        "recommendations": get_recommendations(website_url, university_name),
        "personal_essay": get_personal_essay(website_url, university_name),
        "writing_sample": get_writing_sample(website_url, university_name),
        "additional_information": None,
        "additional_deadlines": get_additional_deadlines(website_url, university_name),
        "tuition_fees": get_tuition_fees(website_url, university_name),
    }

    yield '{"status": "progress", "message": "Extracting university metrics..."}'
    university_data = {
        "university_name": get_university_name(website_url, university_name),
        "college_setting": get_college_setting(website_url, university_name),
        "type_of_institution": get_type_of_institution(website_url, university_name),
        "student_faculty": get_student_faculty(website_url, university_name),
        "number_of_campuses": get_number_of_campuses(website_url, university_name),
        "total_faculty_available": get_total_faculty_available(website_url, university_name),
        "total_programs_available": get_total_programs_available(website_url, university_name),
        "total_students_enrolled": get_total_students_enrolled(website_url, university_name),
        "total_graduate_programs": get_total_graduate_programs(website_url, university_name),
        "total_international_students": get_total_international_students(website_url, university_name),
        "total_students": get_total_students(website_url, university_name),
        "total_undergrad_majors": get_total_undergrad_majors(website_url, university_name),
        "countries_represented": get_countries_represented(website_url, university_name),
    }

    yield '{"status": "progress", "message": "Extracting address details..."}'
    address_data = {
        "street1": get_street(website_url, university_name),
        "street2": None,
        "county": get_county(website_url, university_name),
        "city": get_city(website_url, university_name),
        "state": get_state(website_url, university_name),
        "country": get_country(website_url, university_name),
        "zip_code": get_zip_code(website_url, university_name),
    }

    yield '{"status": "progress", "message": "Extracting contact information..."}'
    contact_data = {
        "contact_information": get_contact_information(website_url, university_name),
        "logo_path": None,
        "phone": get_phone(website_url, university_name),
        "email": get_email(website_url, university_name),
        "secondary_email": get_secondary_email(website_url, university_name),
        "website_url": get_website_url(website_url, university_name),
        "admission_office_url": get_admission_office_url(website_url, university_name),
        "virtual_tour_url": get_virtual_tour_url(website_url, university_name),
        "financial_aid_url": get_financial_aid_url(website_url, university_name),
    }

    yield '{"status": "progress", "message": "Extracting social media links..."}'
    social_media_data = {
        "facebook": get_facebook(website_url, university_name),
        "instagram": get_instagram(website_url, university_name),
        "twitter": get_twitter(website_url, university_name),
        "youtube": get_youtube(website_url, university_name),
        "tiktok": get_tiktok(website_url, university_name),
        "linkedin": get_linkedin(website_url, university_name),
    }

    yield '{"status": "progress", "message": "Extracting student statistics..."}'
    student_statistics_data = {
        "grad_avg_tuition": get_grad_avg_tuition(website_url, university_name, ai_found_tuition_url, common_tuition_fee_urls),
        "grad_international_students": get_grad_international_students(website_url, university_name),
        "grad_scholarship_high": get_grad_scholarship_high(website_url, university_name, graduate_financial_aid_urls, common_financial_aid_urls),
        "grad_scholarship_low": get_grad_scholarship_low(website_url, university_name, graduate_financial_aid_urls, common_financial_aid_urls),
        "grad_total_students": get_grad_total_students(website_url, university_name),
        "ug_avg_tuition": get_ug_avg_tuition(website_url, university_name, ai_found_tuition_url, common_tuition_fee_urls),
        "ug_international_students": get_ug_international_students(website_url, university_name),
        "ug_scholarship_high": get_ug_scholarship_high(website_url, university_name, undergraduate_financial_aid_urls, common_financial_aid_urls),
        "ug_scholarship_low": get_ug_scholarship_low(website_url, university_name, undergraduate_financial_aid_urls, common_financial_aid_urls),
        "ug_total_students": get_ug_total_students(website_url, university_name),
    }

    yield '{"status": "progress", "message": "Finalizing data..."}'
    raw_multiple = get_is_multiple_applications_allowed(website_url, university_name)
    raw_mat = get_is_mat_required(website_url, university_name)
    
    # Parse JSON responses with error handling
    try:
        clean_multiple = raw_multiple.strip('`').replace('json', '').strip()
        value = str(json.loads(clean_multiple).get("allowed", "None")) if clean_multiple else "None"
    except:
        value = "None"

    try:
        clean_mat = raw_mat.strip('`').replace('json', '').strip()
        mat_value = str(json.loads(clean_mat).get("Allowed", "None")) if clean_mat else "None"
    except:
        mat_value = "None"
        
    boolean_fields_data = {
        "is_additional_information_available": "FALSE", 
        "is_multiple_applications_allowed": value,
        "is_act_required": get_is_act_required(website_url, university_name),
        "is_analytical_not_required": get_is_analytical_not_required(website_url, university_name),
        "is_analytical_optional": get_is_analytical_optional(website_url, university_name),
        "is_duolingo_required": get_is_duolingo_required(website_url, university_name),
        "is_els_required": get_is_els_required(website_url, university_name),
        "is_english_not_required": get_is_english_not_required(website_url, university_name),
        "is_english_optional": get_is_english_optional(website_url, university_name),
        "is_gmat_or_gre_required": get_is_gmat_or_gre_required(website_url, university_name),
        "is_gmat_required": get_is_gmat_required(website_url, university_name),
        "is_gre_required": get_is_gre_required(website_url, university_name),
        "is_ielts_required": get_is_ielts_required(website_url, university_name),
        "is_lsat_required": str(get_is_lsat_required(website_url, university_name)),
        "is_mat_required": mat_value,
        "is_mcat_required": get_is_mcat_required(website_url, university_name),
        "is_pte_required": get_is_pte_required(website_url, university_name),
        "is_sat_required": get_is_sat_required(website_url, university_name),
        "is_toefl_ib_required": get_is_toefl_ib_required(website_url, university_name),
        "is_import_verified": "FALSE",
        "is_imported": None,
        "is_enrolled": "FALSE",
    }

    # Combine all data
    all_data = {
        "new_fields_data": new_fields_data,
        "university_data": university_data,
        "address_data": address_data,
        "application_data": application_data,
        "contact_data": contact_data,
        "social_media_data": social_media_data,
        "student_statistics_data": student_statistics_data,
        "boolean_fields_data": boolean_fields_data,
    }

    # Merge into flat dictionary
    merged_data = {}
    for section in all_data.values():
        merged_data.update(section)

    # Clean values
    def clean_data_values(data_dict):
        cleaned = {}
        for k, v in data_dict.items():
            cleaned[k] = extract_clean_value(v) if isinstance(v, str) else v
        return cleaned

    flat_data = clean_data_values(merged_data)

    # Save outputs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "Inst_outputs")
    os.makedirs(output_dir, exist_ok=True)

    safe_university_name = university_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    json_filename = os.path.join(output_dir, f"{safe_university_name}_Institution.json")
    csv_filename = os.path.join(output_dir, f"{safe_university_name}_Institution.csv")

    # Save JSON with all data
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    # Save CSV
    df = pd.DataFrame([flat_data])
    df.to_csv(csv_filename, index=False, encoding='utf-8')

    print(f"Saved {university_name} data to {csv_filename} and {json_filename}.")
    yield f'{{"status": "complete", "files": {{"csv": "{csv_filename}", "json": "{json_filename}"}}}}'

# ============================================================================
# DEPARTMENT EXTRACTION
# ============================================================================

def process_department_extraction(university_name):
    """Process department extraction for a university"""
    yield f'{{"status": "progress", "message": "Starting department extraction for {university_name}..."}}'
    
    # Get Website URL
    yield f'{{"status": "progress", "message": "Finding official website..."}}'
    prompt = f"What is the official university website for {university_name}?"
    website_url = generate_text_safe(prompt)
    print(f"Website URL: {website_url}")
    
    # Extract Departments
    yield f'{{"status": "progress", "message": "Extracting admissions departments from {website_url}..."}}'
    
    prompt = (
        f"Extract ONLY admissions-related departments from {university_name} at {website_url}. "
        "Include: Undergraduate Admissions, Graduate Admissions, International Admissions, Transfer Admissions. "
        "For each, extract: DepartmentName, Email, PhoneNumber, AdmissionUrl, BuildingName, Street1, City, State, ZipCode. "
        "Return JSON array of objects with these fields. Use null for missing values."
    )
    
    try:
        response_text = generate_text_safe(prompt)
        
        if not response_text:
            yield '{"status": "error", "message": "Empty response from AI model"}'
            return

        # Parse JSON
        response_text = response_text.replace("json", "", 1).replace("```", "").strip()
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        
        if json_match:
            departments_data = json.loads(json_match.group(0))
        else:
            departments_data = json.loads(response_text)
            
        if not isinstance(departments_data, list):
            departments_data = [departments_data] if isinstance(departments_data, dict) else []

        yield f'{{"status": "progress", "message": "Successfully extracted {len(departments_data)} departments"}}'
        
        # Save outputs
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "Dept_outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        safe_name = university_name.replace(" ", "_")
        json_path = os.path.join(output_dir, f"{safe_name}_departments.json")
        csv_path = os.path.join(output_dir, f"{safe_name}_departments.csv")
        
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(departments_data, jf, indent=4)
        
        if departments_data:
            df = pd.DataFrame(departments_data)
            df['CollegeName'] = university_name
            df.to_csv(csv_path, index=False, encoding="utf-8")
            
        yield f'{{"status": "complete", "files": {{"json": "{json_path}", "csv": "{csv_path}"}}}}'
        
    except Exception as e:
        yield f'{{"status": "error", "message": "Error processing data: {str(e)}"}}'

# ============================================================================
# PROGRAMS EXTRACTION (SIMPLIFIED)
# ============================================================================

def process_programs_extraction(university_name, step=9):
    """Process programs extraction - simplified version
    
    NOTE: Full implementation would include all sub-modules from Programs.py
    """
    yield f'{{"status": "progress", "message": "Starting programs extraction for {university_name}..."}}'
    
    # Get website
    prompt = f"What is the official university website for {university_name}?"
    website_url = generate_text_safe(prompt)
    
    # Extract graduate programs
    yield '{"status": "progress", "message": "Extracting graduate programs list..."}'
    grad_prompt = (
        f"Find all graduate programs offered by {university_name} at {website_url}. "
        "Return JSON array with objects containing: ProgramName, DegreeType, Department. "
        "Use null for missing values."
    )
    
    try:
        grad_response = generate_text_safe(grad_prompt)
        grad_response = grad_response.replace("```json", "").replace("```", "").strip()
        json_match = re.search(r'\[.*\]', grad_response, re.DOTALL)
        grad_programs = json.loads(json_match.group(0)) if json_match else []
    except:
        grad_programs = []
    
    # Extract undergraduate programs
    yield '{"status": "progress", "message": "Extracting undergraduate programs list..."}'
    undergrad_prompt = (
        f"Find all undergraduate programs offered by {university_name} at {website_url}. "
        "Return JSON array with objects containing: ProgramName, DegreeType, Department. "
        "Use null for missing values."
    )
    
    try:
        undergrad_response = generate_text_safe(undergrad_prompt)
        undergrad_response = undergrad_response.replace("```json", "").replace("```", "").strip()
        json_match = re.search(r'\[.*\]', undergrad_response, re.DOTALL)
        undergrad_programs = json.loads(json_match.group(0)) if json_match else []
    except:
        undergrad_programs = []
    
    # Save outputs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "Programs_outputs")
    os.makedirs(output_dir, exist_ok=True)
    
    safe_name = university_name.replace(" ", "_")
    
    # Save graduate programs
    grad_json_path = os.path.join(output_dir, f"{safe_name}_graduate_programs.json")
    with open(grad_json_path, "w", encoding="utf-8") as jf:
        json.dump(grad_programs, jf, indent=4)
    
    # Save undergraduate programs
    undergrad_json_path = os.path.join(output_dir, f"{safe_name}_undergraduate_programs.json")
    with open(undergrad_json_path, "w", encoding="utf-8") as jf:
        json.dump(undergrad_programs, jf, indent=4)
    
    yield f'{{"status": "complete", "files": {{"grad_json": "{grad_json_path}", "undergrad_json": "{undergrad_json_path}"}}}}'

# ============================================================================
# SEQUENTIAL EXTRACTION ORCHESTRATOR
# ============================================================================

def run_sequential_extraction(university_name):
    """
    Run complete sequential extraction for a university.
    
    Orchestrates the extraction of:
    1. Institution data (all university-level information)
    2. Department data (admissions offices and contacts)
    3. Programs data (graduate and undergraduate programs)
    """
    
    yield json.dumps({
        "status": "progress",
        "message": f"Starting sequential extraction for {university_name}...",
        "phase": "initialization"
    })
    
    all_files = {}
    
    # PHASE 1: INSTITUTION EXTRACTION
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 1/3] Starting Institution Extraction...",
        "phase": "institution"
    })
    
    try:
        for update in process_institution_extraction(university_name):
            try:
                data = json.loads(update)
                data['phase'] = 'institution'
                
                if data.get('status') == 'complete' and 'files' in data:
                    all_files.update(data['files'])
                    data['status'] = 'progress'
                    data['message'] = f"[PHASE 1/3] Institution extraction completed. Files saved."
                
                yield json.dumps(data)
            except json.JSONDecodeError:
                yield json.dumps({
                    "status": "progress",
                    "message": f"[PHASE 1/3] {update}",
                    "phase": "institution"
                })
    except Exception as e:
        yield json.dumps({
            "status": "error",
            "message": f"[PHASE 1/3] Error in institution extraction: {str(e)}",
            "phase": "institution",
            "error": str(e)
        })
    
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 1/3] Institution extraction completed.",
        "phase": "institution"
    })
    
    # PHASE 2: DEPARTMENT EXTRACTION
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 2/3] Starting Department Extraction...",
        "phase": "department"
    })
    
    try:
        for update in process_department_extraction(university_name):
            try:
                data = json.loads(update)
                data['phase'] = 'department'
                
                if data.get('status') == 'complete' and 'files' in data:
                    all_files.update(data['files'])
                    data['status'] = 'progress'
                    data['message'] = f"[PHASE 2/3] Department extraction completed. Files saved."
                
                yield json.dumps(data)
            except json.JSONDecodeError:
                yield json.dumps({
                    "status": "progress",
                    "message": f"[PHASE 2/3] {update}",
                    "phase": "department"
                })
    except Exception as e:
        yield json.dumps({
            "status": "error",
            "message": f"[PHASE 2/3] Error in department extraction: {str(e)}",
            "phase": "department",
            "error": str(e)
        })
    
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 2/3] Department extraction completed.",
        "phase": "department"
    })
    
    # PHASE 3: PROGRAMS EXTRACTION
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 3/3] Starting Programs Extraction...",
        "phase": "programs"
    })
    
    try:
        for update in process_programs_extraction(university_name, step=9):
            try:
                data = json.loads(update)
                data['phase'] = 'programs'
                
                if 'files' in data:
                    all_files.update(data['files'])
                
                if data.get('status') == 'complete':
                    data['status'] = 'progress'
                    data['message'] = f"[PHASE 3/3] Programs extraction completed."
                
                yield json.dumps(data)
            except json.JSONDecodeError:
                yield json.dumps({
                    "status": "progress",
                    "message": f"[PHASE 3/3] {update}",
                    "phase": "programs"
                })
    except Exception as e:
        yield json.dumps({
            "status": "error",
            "message": f"[PHASE 3/3] Error in programs extraction: {str(e)}",
            "phase": "programs",
            "error": str(e)
        })
    
    yield json.dumps({
        "status": "progress",
        "message": "[PHASE 3/3] Programs extraction completed.",
        "phase": "programs"
    })
    
    # FINAL COMPLETION
    yield json.dumps({
        "status": "complete",
        "message": f"Successfully completed all extraction phases for {university_name}!",
        "phase": "complete",
        "files": all_files,
        "summary": {
            "university": university_name,
            "phases_completed": ["institution", "department", "programs"],
            "total_files": len(all_files)
        }
    })


def main():
    """Command-line interface for the sequential scraper"""
    if len(sys.argv) < 2:
        print("Usage: python sequential_scraper_standalone.py \"University Name\"")
        print("Example: python sequential_scraper_standalone.py \"SUNY Brockport\"")
        sys.exit(1)
    
    university_name = sys.argv[1]
    
    print(f"\n{'='*80}")
    print(f"Sequential University Data Extraction - STANDALONE VERSION")
    print(f"University: {university_name}")
    print(f"{'='*80}\n")
    
    files_collected = {}
    
    for update_json in run_sequential_extraction(university_name):
        try:
            update = json.loads(update_json)
            
            status = update.get('status', 'unknown')
            message = update.get('message', '')
            
            if status == 'error':
                print(f"❌ ERROR: {message}")
            elif status == 'complete':
                print(f"✅ {message}")
            elif status == 'progress':
                print(f"⏳ {message}")
            else:
                print(f"ℹ️  {message}")
            
            if 'files' in update:
                files_collected.update(update['files'])
                
        except json.JSONDecodeError:
            print(f"ℹ️  {update_json}")
    
    print(f"\n{'='*80}")
    print(f"Extraction Complete!")
    print(f"{'='*80}")
    if files_collected:
        print(f"\nOutput files ({len(files_collected)}):")
        for file_type, file_path in files_collected.items():
            print(f"  - {file_type}: {file_path}")
    else:
        print("\nNo output files were generated.")
    print()


if __name__ == "__main__":
    main()
