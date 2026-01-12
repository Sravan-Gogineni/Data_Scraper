import pandas as pd
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import json
import csv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Configure the client (using google-genai SDK 1.57.0)
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Wrapper for compatibility with existing code structure
class GeminiModelWrapper:
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt):
        # Configure the search tool for every call to ensure live data
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool]
            )
        )
        return response

# Initialize the model wrapper
model = GeminiModelWrapper(client, "gemini-2.5-pro")

# Logic moved to process_institution_extraction

def generate_text_safe(prompt):
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.replace("**", "").replace("```", "").strip()
    except Exception as e:
        logger.error(f"Error generating content: {e}")
    return ""
 
 # Default values (will be overridden by function args)


def extract_clean_value(response_text):
    """
    Extract clean value from AI response, removing evidence, URLs, and extra text.
    Returns only the actual value.
    """
    if not response_text:
        return None
    
    # Remove markdown formatting
    text = response_text.replace("**", "").replace("```", "").strip()
    
    # If empty after cleaning, return None
    if not text:
        return None
    
    # Split by common separators that indicate evidence/URL sections
    # Look for patterns like "Evidence:", "URL:", "Source:", etc.
    separators = ["\nEvidence:", "\nEvidence", "\nURL:", "\nURL", "\nSource:", "\nSource", 
                  "\nPage:", "\nPage", "\nWebsite:", "\nWebsite", "\nLink:", "\nLink",
                  "Evidence:", "URL:", "Source:", "Page:", "Website:", "Link:"]
    
    for sep in separators:
        if sep.lower() in text.lower():
            # Take only the part before the separator
            parts = text.split(sep)
            if parts:
                text = parts[0].strip()
            break
    
    # Get first line if multiline (before any remaining newlines)
    text = text.split('\n')[0].strip()
    
    # If the text is "null" (case insensitive), return None
    if text.lower().strip() == "null":
        return None
    
    # Return the cleaned text
    return text if text else None
def get_tuition_fee_url(website_url, university_name):
    prompt = (
        f"Find the tuition fee URL for the university {university_name} on the website {website_url}. "
        f"Search query: site:{website_url} tuition fees cost of attendance "
        "Return only the tuition fee URL, no other text. "
        "No fabrication or guessing, just the tuition fee URL. "
        "Only if the tuition fee URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the tuition fee URL is explicitly stated."
    )
    return generate_text_safe(prompt)



def get_womens_college(website_url, university_name):
    prompt = (
        f"Is the university {university_name}, {website_url} a women's college? "
        "Return only 'yes' or 'no', no other text. "
        "No fabrication or guessing, just yes or no. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_cost_of_living_min(website_url, university_name):
    prompt = (
        f"What is the minimum cost of living for students at the university {university_name} ,{website_url}? "
        "Return only the minimum cost of living amount, no other text. "
        "No fabrication or guessing, just the minimum cost of living. "
        "Only if the minimum cost of living is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the minimum cost of living is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_cost_of_living_max(website_url, university_name):
    prompt = (
        f"What is the maximum cost of living for students at the university {university_name}, {website_url}? "
        "Return only the maximum cost of living amount, no other text. "
        "No fabrication or guessing, just the maximum cost of living. "
        "Only if the maximum cost of living is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the maximum cost of living is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_orientation_available(website_url, university_name):
    prompt = (
        f"Is orientation available for students at the university {university_name}, {website_url}? "
        "Return only 'yes' or 'no', no other text. "
        "No fabrication or guessing, just yes or no. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_college_tour_after_admissions(website_url, university_name):
    prompt = (
        f"Does the university {university_name}, {website_url} offer in-person college tours after admissions? "
        "Return only 'yes' or 'no', no other text. "
        "No fabrication or guessing, just yes or no. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_university_name(website_url, university_name):
    prompt = (
        f"What is the name of the university {university_name} for the website {website_url}? "
        "Return only the name of the university, no other text. "
        "No fabrication or guessing, just the name of the university. "
        "Only if the name of the university is explicitly stated in the website, "
        "otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where "
        "the name of the university is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_college_setting(website_url, university_name):
    prompt = (
        f"What is the college setting for the university {university_name}, {website_url}? "
        "Search query: site:{website_url} college setting "
        "Example: urban, suburban, rural, etc. "
        "Return only the college setting, no other text. "
        "No fabrication or guessing, just the college setting. "
        "Only if the college setting is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the college setting is explicitly stated."
    )

    return generate_text_safe(prompt)

def get_type_of_institution(website_url, university_name):
    prompt = (
        f"What is the type of institution for the university {university_name}, {website_url}? "
        "Return only the type of institution, no other text. "
        "No fabrication or guessing, just the type of institution. "
        "Only if the type of institution is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the type of institution is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_student_faculty(website_url, university_name):
    prompt = (
        f"What is the student faculty ratio for the university {university_name}, {website_url}? "
        "Return only the student faculty, no other text. "
        "No fabrication or guessing, just the student faculty ratio. "
        "Only if the student faculty ratio is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the student faculty ratio is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_number_of_campuses(website_url, university_name):
    prompt = (
        f"What is the number of campuses for the university {university_name}, {website_url}? "
        "Return only the number of campuses, no other text. "
        "No fabrication or guessing, just the number of campuses. "
        "Only if the number of campuses is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the number of campuses is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_total_faculty_available(website_url, university_name):
    prompt = (
        f"What is the total number of faculty available for the university {university_name}, {website_url}? "
        "Return only the total number of faculty available, no other text. "
        "No fabrication or guessing, just the total number of faculty available. "
        "Only if the total number of faculty available is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of faculty available is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_total_programs_available(website_url, university_name):
    prompt = (
        f"What is the total number of programs available for the university {university_name}, {website_url}? "
        "Return only the total number of programs available, no other text. "
        "No fabrication or guessing, just the total number of programs available. "
        "Only if the total number of programs available is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of programs available is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_total_students_enrolled(website_url, university_name):
    prompt = (
        f"What is the total number of students enrolled in the university {university_name}, {website_url} till date? "
        "Return only the total number of students enrolled, no other text. "
        "No fabrication or guessing, just the total number of students enrolled. "
        "Only if the total number of students enrolled is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of students enrolled is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_total_graduate_programs(website_url, university_name):
    prompt = (
        f"What is the total number of graduate programs offered by the university {university_name}, {website_url}? "
        "Return only the total number of graduate programs, no other text. "
        "No fabrication or guessing, just the total number of graduate programs. "
        "Only if the total number of graduate programs is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of graduate programs is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_total_international_students(website_url, university_name):
    prompt = (
        f"What is the total number of international students currently enrolled in the university {university_name}, {website_url}? "
        "Return only the total number of international students, no other text. "
        "No fabrication or guessing, just the total number of international students. "
        "Only if the total number of international students is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of international students is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_total_students(website_url, university_name):
    prompt = (
        f"What is the total number of students enrolled in the university {university_name}, {website_url}? "
        "Return only the total number of students, no other text. "
        "No fabrication or guessing, just the total number of students. "
        "Only if the total number of students is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of students is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_total_undergrad_majors(website_url, university_name):
    prompt = (
        f"What is the total number of undergrad majors offered by the university {university_name}, {website_url}? "
        "Return only the total number of undergrad majors, no other text. "
        "No fabrication or guessing, just the total number of undergrad majors. "
        "Only if the total number of undergrad majors is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of undergrad majors is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_countries_represented(website_url, university_name):
    prompt = (
        f"How many countries students are represented by the university {university_name}, {website_url}? "
        "Return only the countries count, no other text. "
        "No fabrication or guessing, just the countries represented. "
        "Only if the countries represented is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the countries represented is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_street(website_url, university_name):
    prompt = (
        f"What is the street address for the university {university_name}, {website_url}? "
        "Return only just the street address, no other text. do not return extra address like city, state, country etc."
        "No fabrication or guessing, just the address. "
        "Only if the address is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the address is explicitly stated."
    )
    return generate_text_safe(prompt)



def get_county(website_url, university_name):
    prompt = (
        f"What county is the university {university_name}, {website_url} located in? "
        "Return only the county name, no other text. "
        "No fabrication or guessing, just the county name. "
        "Only if the county is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the county is explicitly stated."
    )
    return generate_text_safe(prompt)
    

def get_city(website_url, university_name):
    prompt = (
        f"What city is the university {university_name}, {website_url} located in? "
        "Return only the city name, no other text. "
        "No fabrication or guessing, just the city name. "
        "Only if the city is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the city is explicitly stated."
    )
    return generate_text_safe(prompt)


def get_state(website_url, university_name):
    prompt = (
        f"What state is the university {university_name}, {website_url} located in? "
        "Return only the state name, no other text. "
        "No fabrication or guessing, just the state name. "
        "Only if the state is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the state is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_country(website_url, university_name):
    prompt = (
        f"What country is the university {university_name}, {website_url} located in? "
        "Return only the country name, no other text. "
        "No fabrication or guessing, just the country name. "
        "Only if the country is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the country is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_zip_code(website_url, university_name):
    prompt = (
        f"What is the zip code for the university {university_name}, {website_url}? "
        "Return only the zip code, no other text. "
        "No fabrication or guessing, just the zip code. "
        "Only if the zip code is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the zip code is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_application_requirements(website_url, university_name):
    prompt = (
        f"What are the application requirements for the university {university_name}, {website_url}? "
        "Return only the application requirements, no other text. "
        "No fabrication or guessing, just the application requirements. "
        "Only if the application requirements is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the application requirements is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_contact_information(website_url, university_name):
    prompt = (
        f"What is the contact information for the university {university_name}, {website_url}? "
        "Return only the contact information, no other text. "
        "No fabrication or guessing, just the contact information. "
        "Only if the contact information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the contact information is explicitly stated."
    )
    return generate_text_safe(prompt)



def get_grad_tuition(website_url, university_name, graduate_tuition_fee_urls=None, common_tuition_fee_urls=None):
    # Use specific URL if provided, else use common URL, else use website_url
    url_to_use = graduate_tuition_fee_urls if graduate_tuition_fee_urls else (common_tuition_fee_urls if common_tuition_fee_urls else website_url)
    prompt = (
        f"What is the graduate tuition for the university {university_name} at {url_to_use}? "
        "Return only the graduate tuition, no other text. "
        "No fabrication or guessing, just the graduate tuition. "
        "Only if the graduate tuition is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the graduate tuition is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_grad_international_students(website_url, university_name):
    prompt = (
        f"What is the number of graduate international students for the university {university_name}, {website_url}? "
        "Return only the number of graduate international students, no other text. "
        "No fabrication or guessing, just the number of graduate international students. "
        "Only if the number of graduate international students is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the number of graduate international students is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_grad_scholarship_high(website_url, university_name, graduate_financial_aid_urls=None, common_financial_aid_urls=None):
    # Use specific URL if provided, else use common URL, else use website_url
    url_to_use = graduate_financial_aid_urls if graduate_financial_aid_urls else (common_financial_aid_urls if common_financial_aid_urls else website_url)
    prompt = (
        f"What is the highest graduate scholarship for the university {university_name} at {url_to_use}? "
        "Return only the highest graduate scholarship, no other text. "
        "No fabrication or guessing, just the highest graduate scholarship. "
        "Only if the highest graduate scholarship is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the highest graduate scholarship is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_logo_path(website_url, university_name):
    prompt = (
        f"What is the logo path or URL for the university {university_name}, {website_url}? "
        "Return only the logo path or URL, no other text. "
        "No fabrication or guessing, just the logo path. "
        "Only if the logo path is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the logo path is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_phone(website_url, university_name):
    prompt = (
        f"What is the main phone number for the university {university_name}, {website_url}? "
        "Return only the phone number, no other text. "
        "No fabrication or guessing, just the phone number. "
        "Only if the phone number is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the phone number is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_email(website_url, university_name):
    prompt = (
        f"What is the main contact email address for the university {university_name}, {website_url}? "
        " If there is no main contact email address, find the admissions email address."
        "Return only the email address, no other text. "
        "No fabrication or guessing, just the email address. "
        "Only if the email address is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the email address is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_secondary_email(website_url, university_name):
    prompt = (
        f"What is the secondary email address for the university {university_name}, {website_url}? "
        "Return only the secondary email address, no other text. "
        "No fabrication or guessing, just the secondary email address. "
        "Only if the secondary email address is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the secondary email address is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_website_url(website_url, university_name):
    prompt = (
        f"What is the official website URL for the university {university_name}, {website_url}? "
        "Return only the website URL, no other text. "
        "No fabrication or guessing, just the website URL. "
        "Only if the website URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the website URL is explicitly stated."
        "the return response should be http or https URL"
    )
    return generate_text_safe(prompt)

def get_admission_office_url(website_url, university_name):
    prompt = (
        f"What is the admission office URL for the university {university_name}, {website_url}? "
        "Return only the admission office URL, no other text. "
        "No fabrication or guessing, just the admission office URL. "
        "Only if the admission office URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the admission office URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_virtual_tour_url(website_url, university_name):
    prompt = (
        f"What is the virtual tour URL for the university {university_name}, {website_url}? "
        "Return only the virtual tour URL, no other text. "
        "No fabrication or guessing, just the virtual tour URL. "
        "Only if the virtual tour URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the virtual tour URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_financial_aid_url(website_url, university_name):
    prompt = (
        f"What is the financial aid URL for the university {university_name}, {website_url}? "
        "Return only the financial aid URL, no other text. "
        "No fabrication or guessing, just the financial aid URL. "
        "Only if the financial aid URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the financial aid URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_application_fees(website_url, university_name):
    prompt = (
        f"Find the application fee for both domestic and international applicants for the university {university_name}, {website_url}? "
        "Return a line of text with the application fee for both domestic and international applicants, no other text. " 
        "Do not return the text like 'The application fee for graduate programs is not explicitly stated for domestic applicants on the university's website'. In this case just return what you find so far in the website. If you don't find something then don't explicitly mention in the return response."
        "No fabrication or guessing, just the application fee for both domestic and international applicants."
        "Example of the return response: 'The application fee for both domestic and international applicants is $amount. (or) The application fee for domestic applicants is $amount and for international applicants is $amount. '"
        "Only if the application fees are explicitly stated in the website, otherwise return null. "
        "Do not return [Cite] in the return response."
        "Only refer the {website_url} or the {university_name}.edu or it's sub domains or it's pages to find the application fees."
        "Do not refer any other third party websites to find the application fees."
        "Also provide the evidence for your answer with correct URL or page where the application fees are explicitly stated."
    )
    return generate_text_safe(prompt)

def get_test_policy(website_url, university_name):
    prompt = (
        f"Find a line of text about test policy for both undergraduate and graduate programs for the university {university_name}, {website_url}? "
        "Return only the test policy, no other text. "
        "No fabrication or guessing, just a short line of text not a long paragraph. "
        "Only return the test policy if it is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the test policy is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_courses_and_grades(website_url, university_name):
    prompt = (
        f"What are the courses and grades requirements for the university {university_name}, {website_url}? "
        "Return only the courses and grades requirements, no other text. "
        "No fabrication or guessing, just the courses and grades requirements. "
        "Only return the courses and grades requirements if they are explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the courses and grades requirements are explicitly stated."
    )
    return generate_text_safe(prompt)

def get_recommendations(website_url, university_name):
    prompt = (
        f"How many recommendations are required to apply for both undergraduate and graduate programs for the university {university_name}, {website_url}? "
        "Return only the recommendation requirements, no other text. "
        "No fabrication or guessing, just the recommendation requirements. "
        "Only return the recommendation requirements if they are explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the recommendation requirements are explicitly stated."
    )
    return generate_text_safe(prompt)

def get_personal_essay(website_url, university_name):
    prompt = (
        f"Does applying to the university {university_name}, {website_url} require a personal essay? "
        "If yes, return Required. if not, return Not Required. no extra text "
        "No fabrication or guessing, just the personal essay requirements. "
        "Only if the personal essay requirements are explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the personal essay requirements are explicitly stated."
    )
    return generate_text_safe(prompt)

def get_writing_sample(website_url, university_name):
    prompt = (
        f"Does applying to the university {university_name}, {website_url} require a writing sample? "
        "If yes, return Required. if not, return Not Required. no extra text "
        "No fabrication or guessing, just the writing sample requirements. "
        "Only if the writing sample requirements are explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the writing sample requirements are explicitly stated."
    )
    return generate_text_safe(prompt)

def get_additional_information(website_url, university_name):
    prompt = (
        f"Is there any additional information required to apply to the university {university_name}, {website_url}? "
        "If yes, return a short line of text about the additional information requirements. if not, return null. no extra text "
        "No fabrication or guessing, just the additional information requirements. "
        "Only if the additional information requirements are explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the additional information requirements are explicitly stated."
    )
    return generate_text_safe(prompt)

def get_additional_deadlines(website_url, university_name):
    prompt = (
        f"What are the additional deadlines of {university_name}, {website_url} apart from application deadlines? "
        "The deadlines can be scholarships, financial aid, or other deadlines. "
        "Return only the additional deadlines like scholarships, financial aid, or other deadlines, no other text. "
        "No fabrication or guessing, just the additional deadlines. "
        "Only if the additional deadlines are explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the additional deadlines are explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_multiple_applications_allowed(website_url, university_name):
    prompt = (
        f"Can a student apply to multiple programs at the university {university_name}, {website_url}? "
        "Check through the website or its pages to find the answer. "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_act_required(website_url, university_name):
    prompt = (
        f"Is ACT scorerequired for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_analytical_not_required(website_url, university_name):
    prompt = (
        f"Is analytical writing not required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_analytical_optional(website_url, university_name):
    prompt = (
        f"Is analytical writing optional for the university {university_name}, {website_url}? "
        "Check through the website or its pages to find the answer. "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_duolingo_required(website_url, university_name):
    prompt = (
        f"Is Duolingo required for the university {university_name}, {website_url}? "
        "Check through the website or its pages to find the answer. "
        "Does international students need to take Duolingo?"
        "If the website explicitly states that the university does not require Duolingo, return 'False'. "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_els_required(website_url, university_name):
    prompt = (
        f"Is ELS required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_english_not_required(website_url, university_name):
    prompt = (
        f"Is English proficiency not required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_english_optional(website_url, university_name):
    prompt = (
        f"Is English proficiency test optional for the university {university_name}, {website_url}? "
        "if the website explicitly states the international student does not need to take English proficiency test, return 'True'. "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_gmat_or_gre_required(website_url, university_name):
    prompt = (
        f"Is GMAT or GRE required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_gmat_required(website_url, university_name):
    prompt = (
        f"Is GMAT required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_gre_required(website_url, university_name):
    prompt = (
        f"Is GRE score required for the university {university_name}, {website_url} to apply for any program for the international students? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_ielts_required(website_url, university_name):
    prompt = (
        f"Is IELTS score required for the university {university_name}, {website_url} to apply for any program for the international students? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_lsat_required(website_url, university_name):
    prompt = (
        f"Is LSAT required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_mat_required(website_url, university_name):
    prompt = (
        f"Is MAT required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_mcat_required(website_url, university_name):
    prompt = (
        f"Is MCAT required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_pte_required(website_url, university_name):
    prompt = (
        f"Is PTE required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_sat_required(website_url, university_name):
    prompt = (
        f"Is SAT required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_is_toefl_ib_required(website_url, university_name):
    prompt = (
        f"Is TOEFL iBT required for the university {university_name}, {website_url}? "
        "Return only 'True' or 'False', no other text. "
        "No fabrication or guessing, just True or False. "
        "Only if this information is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where this information is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_tuition_fees(website_url, university_name):
    # Use common URL if provided, else use website_url

    tuition_fee_url = get_tuition_fee_url(website_url, university_name)
    prompt = (
        f"Look for the tuition fees for the university {university_name} at {tuition_fee_url}. "
        "Please find the tuition fee for semester or year according to the website for the for both the undergraduate and graduate programs. "
        "The answer should be like this: 'Undergraduate (Full-Time): ~$7,438 per year (Resident), ~$19,318 (Non-Resident/Supplemental Tuition).Graduate (Full-Time): ~$8,872 per year (Resident), ~$18,952 (Non-Resident/Supplemental Tuition).' "
        "Return exactly how the above format is. "
        "No fabrication or guessing, just the answer you find in the website. or it's pages. "
        "Only if the tuition fees are explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the tuition fees are explicitly stated."
    )
    return generate_text_safe(prompt)

def get_facebook(website_url, university_name):
    prompt = (
        f"What is the Facebook URL for the university {university_name}, {website_url}? "
        "Return only the Facebook URL, no other text. "
        "No fabrication or guessing, just the Facebook URL. "
        "Only if the Facebook URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the Facebook URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_instagram(website_url, university_name):
    prompt = (
        f"What is the Instagram URL for the university {university_name}, {website_url}? "
        "Return only the Instagram URL, no other text. "
        "No fabrication or guessing, just the Instagram URL. "
        "Only if the Instagram URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the Instagram URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_twitter(website_url, university_name):
    prompt = (
        f"What is the Twitter URL for the university {university_name}, {website_url}? "
        "Return only the Twitter URL, no other text. "
        "No fabrication or guessing, just the Twitter URL. "
        "Only if the Twitter URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the Twitter URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_youtube(website_url, university_name):
    prompt = (
        f"What is the YouTube URL for the university {university_name}, {website_url}? "
        "Return only the YouTube URL, no other text. "
        "No fabrication or guessing, just the YouTube URL. "
        "Only if the YouTube URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the YouTube URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_tiktok(website_url, university_name):
    prompt = (
        f"What is the TikTok URL for the university {university_name}, {website_url}? "
        "Return only the TikTok URL, no other text. "
        "No fabrication or guessing, just the TikTok URL. "
        "Only if the TikTok URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the TikTok URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_linkedin(website_url, university_name):
    prompt = (
        f"What is the LinkedIn URL for the university {university_name}, {website_url}? "
        "Return only the LinkedIn URL, no other text. "
        "No fabrication or guessing, just the LinkedIn URL. "
        "Only if the LinkedIn URL is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the LinkedIn URL is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_grad_avg_tuition(website_url, university_name, graduate_tuition_fee_urls=None, common_tuition_fee_urls=None):
    # Use specific URL if provided, else use common URL, else use website_url
    url_to_use = graduate_tuition_fee_urls if graduate_tuition_fee_urls else (common_tuition_fee_urls if common_tuition_fee_urls else website_url)
    prompt = (
        f"What is the average graduate tuition for the university {university_name} at {url_to_use}? "
        "Please look at the tution fees page for the university and it's pages and look for the average graduate tuition per year"
        "Return only the average graduate tuition, no other text. "
        "No fabrication or guessing, just the average graduate tuition. "
        "Only if the average graduate tuition is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the average graduate tuition is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_grad_scholarship_low(website_url, university_name, graduate_financial_aid_urls=None, common_financial_aid_urls=None):
    # Use specific URL if provided, else use common URL, else use website_url
    url_to_use = graduate_financial_aid_urls if graduate_financial_aid_urls else (common_financial_aid_urls if common_financial_aid_urls else website_url)
    prompt = (
        f"What is the lowest graduate scholarship for the university {university_name} at {url_to_use}? "
        "Return only the lowest graduate scholarship, no other text. "
        "No fabrication or guessing, just the lowest graduate scholarship. "
        "Only if the lowest graduate scholarship is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the lowest graduate scholarship is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_grad_total_students(website_url, university_name):
    prompt = (
        f"What is the total number of graduate students at the university {university_name}, {website_url}? "
        "Return only the total number of graduate students, no other text. "
        "No fabrication or guessing, just the total number of graduate students. "
        "Only if the total number of graduate students is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of graduate students is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_ug_avg_tuition(website_url, university_name, undergraduate_tuition_fee_urls=None, common_tuition_fee_urls=None):
    # Use specific URL if provided, else use common URL, else use website_url
    url_to_use = undergraduate_tuition_fee_urls if undergraduate_tuition_fee_urls else (common_tuition_fee_urls if common_tuition_fee_urls else website_url)
    prompt = (
        f"What is the average undergraduate tuition for the university {university_name} at {url_to_use}? "
        "Return only the average undergraduate tuition, no other text. "
        "No fabrication or guessing, just the average undergraduate tuition. "
        "Only if the average undergraduate tuition is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the average undergraduate tuition is explicitly stated."
    )

    return generate_text_safe(prompt)

def get_ug_international_students(website_url, university_name):
    prompt = (
        f"What is the number of undergraduate international students for the university {university_name}, {website_url}? "
        "Return only the number of undergraduate international students, no other text. "
        "No fabrication or guessing, just the number of undergraduate international students. "
        "Only if the number of undergraduate international students is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the number of undergraduate international students is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_ug_scholarship_high(website_url, university_name, undergraduate_financial_aid_urls=None, common_financial_aid_urls=None):
    # Use specific URL if provided, else use common URL, else use website_url
    url_to_use = undergraduate_financial_aid_urls if undergraduate_financial_aid_urls else (common_financial_aid_urls if common_financial_aid_urls else website_url)
    prompt = (
        f"What is the highest undergraduate scholarship for the university {university_name} at {url_to_use}? "
        "Return only the highest undergraduate scholarship, no other text. "
        "The value can be in percentage or amount. "
        "No fabrication or guessing, just the highest undergraduate scholarship. "
        "Only if the highest undergraduate scholarship is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the highest undergraduate scholarship is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_ug_scholarship_low(website_url, university_name, undergraduate_financial_aid_urls=None, common_financial_aid_urls=None):
    # Use specific URL if provided, else use common URL, else use website_url
    url_to_use = undergraduate_financial_aid_urls if undergraduate_financial_aid_urls else (common_financial_aid_urls if common_financial_aid_urls else website_url)
    prompt = (
        f"What is the lowest scholarship that can be awarded to undergraduate students at the university {university_name} at {url_to_use}? "
        "The value can be in percentage or amount. "
        "Return only the lowest undergraduate scholarship, no other text. "
        "No fabrication or guessing, just the lowest undergraduate scholarship. "
        "Only if the lowest undergraduate scholarship is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the lowest undergraduate scholarship is explicitly stated."
    )
    return generate_text_safe(prompt)

def get_ug_total_students(website_url, university_name):
    prompt = (
        f"What is the total number of undergraduate students at the university {university_name}, {website_url}? "
        "Return only the total number of undergraduate students, no other text. "
        "No fabrication or guessing, just the total number of undergraduate students. "
        "Only if the total number of undergraduate students is explicitly stated in the website, otherwise return null. "
        "Also provide the evidence for your answer with correct URL or page where the total number of undergraduate students is explicitly stated."
    )
    return generate_text_safe(prompt)


def process_institution_extraction(
    university_name, 
    undergraduate_tuition_fee_urls=None, 
    graduate_tuition_fee_urls=None, 
    undergraduate_financial_aid_urls=None, 
    graduate_financial_aid_urls=None,
    common_financial_aid_urls=None,
    common_tuition_fee_urls=None
):
    print(f"Processing {university_name}...")
    yield '{"status": "progress", "message": "Initializing extraction..."}'
    
    # 1. Get Website URL
    yield f'{{"status": "progress", "message": "Finding official website for {university_name}..."}}'
    prompt = f"What is the official university website for {university_name}?"
    website_url = generate_text_safe(prompt)
    print(f"Found Website URL: {website_url}")
    # 2. Get Tuition Fee URL
    yield f'{{"status": "progress", "message": "Finding tuition fee URL for {university_name}..."}}'
    # Use AI to find the tuition fee URLs
    ai_found_tuition_url = get_tuition_fee_url(website_url, university_name)
    
    print(f"Found Tuition Fee URL: {ai_found_tuition_url}")

    # New fields at the top
    yield '{"status": "progress", "message": "Extracting general information..."}'
    new_fields_data = {
        "womens_college": get_womens_college(website_url, university_name),
        "cost_of_living_min": get_cost_of_living_min(website_url, university_name),
        "cost_of_living_max": get_cost_of_living_max(website_url, university_name),
        "orientation_available": get_orientation_available(website_url, university_name),
        "college_tour_after_admissions": get_college_tour_after_admissions(website_url, university_name),
    }

    yield '{"status": "progress", "message": "Extracting application requirements..."}'
    application_data = {
        "application_requirements": get_application_requirements(website_url, university_name),
        "application_fees": get_application_fees(website_url, university_name),
        "test_policy": get_test_policy(website_url, university_name),
        "courses_and_grades": get_courses_and_grades(website_url, university_name),
        "recommendations": get_recommendations(website_url, university_name),
        "personal_essay": get_personal_essay(website_url, university_name),
        "writing_sample": get_writing_sample(website_url, university_name),
        "additional_information": get_additional_information(website_url, university_name),
        "additional_deadlines": get_additional_deadlines(website_url, university_name),
        "tuition_fees": get_tuition_fees(website_url, university_name),
    }
    yield '{{ "status": "progress", "tuition_fees": "{tuition_fees}" }}'.format(tuition_fees=application_data["tuition_fees"])


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
        "street2": None,  # This would need a separate function if needed
        "county": get_county(website_url, university_name),
        "city": get_city(website_url, university_name),
        "state": get_state(website_url, university_name),
        "country": get_country(website_url, university_name),
        "zip_code": get_zip_code(website_url, university_name),
    }

    
    yield '{"status": "progress", "message": "Extracting contact information..."}'
    contact_data = {
        "contact_information": get_contact_information(website_url, university_name),
        "logo_path": get_logo_path(website_url, university_name),
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
    boolean_fields_data = {
        "is_additional_information_available": True if get_additional_information(website_url, university_name) else False, 
        "is_multiple_applications_allowed": get_is_multiple_applications_allowed(website_url, university_name),
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
        "is_lsat_required": get_is_lsat_required(website_url, university_name),
        "is_mat_required": get_is_mat_required(website_url, university_name),
        "is_mcat_required": get_is_mcat_required(website_url, university_name),
        "is_pte_required": get_is_pte_required(website_url, university_name),
        "is_sat_required": get_is_sat_required(website_url, university_name),
        "is_toefl_ib_required": get_is_toefl_ib_required(website_url, university_name),
        "is_import_verified": False,
        "is_imported": False,
        "is_enrolled": 0,
    }

    #combine the data into one dict
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

    # i want the final excel,csv with all the column names that we have in each dict and only the corresponding value for the each column, I don't want any other details like the evidence,urls,etc.
    # Merge all dictionaries into one flat dictionary (without nesting) for CSV/Excel
    merged_data = {}
    merged_data.update(new_fields_data)
    merged_data.update(university_data)
    merged_data.update(address_data)
    merged_data.update(application_data)
    merged_data.update(contact_data)
    merged_data.update(social_media_data)
    merged_data.update(student_statistics_data)
    merged_data.update(boolean_fields_data)

    # Clean the values (remove evidence, URLs, etc.)
    def clean_data_values(data_dict):
        """
        Cleans values in a dictionary using extract_clean_value.
        Returns a dict with cleaned values (no evidence, URLs, or extra text).
        """
        cleaned = {}
        for k, v in data_dict.items():
            if isinstance(v, str):
                cleaned[k] = extract_clean_value(v)
            else:
                cleaned[k] = v
        return cleaned

    flat_data = clean_data_values(merged_data)

    # Define new fields that should be at the end
    new_fields_list = list(new_fields_data.keys())

    # Create ordered column list: university_name first, then others (excluding new fields), then new fields at end
    ordered_columns = []
    if 'university_name' in flat_data:
        ordered_columns.append('university_name')

    # Add all other columns except university_name and new fields
    for key in flat_data.keys():
        if key != 'university_name' and key not in new_fields_list:
            ordered_columns.append(key)

    # Add new fields at the end
    for key in new_fields_list:
        if key in flat_data:
            ordered_columns.append(key)

    # Sanitize university name for filename (replace spaces with underscores, remove special characters)
    safe_university_name = university_name.replace(" ", "_").replace("/", "_").replace("\\", "_")

    def rename_columns(df, flat_data):
        """
        Rename columns to match final required column names and ensure all required columns are present.
        Missing columns will be added as empty.
        """
        # Mapping from current column names to final column names
        column_mapping = {
            'university_name': 'CollegeName',
            'college_setting': 'CollegeSetting',
            'type_of_institution': 'TypeofInstitution',
            'student_faculty': 'Student_Faculty',
            'number_of_campuses': 'NumberOfCampuses',
            'total_faculty_available': 'TotalFacultyAvailable',
            'total_programs_available': 'TotalProgramsAvailable',
            'total_students_enrolled': 'TotalStudentsEnrolled',
            'total_graduate_programs': 'TotalGraduatePrograms',
            'total_international_students': 'TotalInternationalStudents',
            'total_students': 'TotalStudents',
            'total_undergrad_majors': 'TotalUndergradMajors',
            'countries_represented': 'CountriesRepresented',
            'street1': 'Street1',
            'street2': 'Street2',
            'county': 'County',
            'city': 'City',
            'state': 'State',
            'country': 'Country',
            'zip_code': 'ZipCode',
            'application_fees': 'ApplicationFees',
            'test_policy': 'TestPolicy',
            'courses_and_grades': 'CoursesAndGrades',
            'recommendations': 'Recommendations',
            'personal_essay': 'PersonalEssay',
            'writing_sample': 'WritingSample',
            'additional_information': 'AdditionalInformation',
            'additional_deadlines': 'AdditionalDeadlines',
            'tuition_fees': 'TuitionFees',
            'logo_path': 'LogoPath',
            'phone': 'Phone',
            'email': 'Email',
            'secondary_email': 'SecondaryEmail',
            'website_url': 'WebsiteUrl',
            'admission_office_url': 'AdmissionOfficeUrl',
            'virtual_tour_url': 'VirtualTourUrl',
            'financial_aid_url': 'FinancialAidUrl',
            'facebook': 'Facebook',
            'instagram': 'Instagram',
            'twitter': 'Twitter',
            'youtube': 'Youtube',
            'tiktok': 'Tiktok',
            'linkedin': 'LinkedIn',
            'grad_avg_tuition': 'GradAvgTuition',
            'grad_international_students': 'GradInternationalStudents',
            'grad_scholarship_high': 'GradScholarshipHigh',
            'grad_scholarship_low': 'GradScholarshipLow',
            'grad_total_students': 'GradTotalStudents',
            'ug_avg_tuition': 'UGAvgTuition',
            'ug_international_students': 'UGInternationalStudents',
            'ug_scholarship_high': 'UGScholarshipHigh',
            'ug_scholarship_low': 'UGScholarshipLow',
            'ug_total_students': 'UGTotalStudents',
            'is_additional_information_available': 'IsAdditionalInformationAvailable',
            'is_multiple_applications_allowed': 'IsMultipleApplicationsAllowed',
            'is_act_required': 'IsACTRequired',
            'is_analytical_not_required': 'IsAnalyticalNotRequired',
            'is_analytical_optional': 'IsAnalyticalOptional',
            'is_duolingo_required': 'IsDuoLingoRequired',
            'is_els_required': 'IsELSRequired',
            'is_english_not_required': 'IsEnglishNotRequired',
            'is_english_optional': 'IsEnglishOptional',
            'is_gmat_or_gre_required': 'IsGMATOrGreRequired',
            'is_gmat_required': 'IsGMATRequired',
            'is_gre_required': 'IsGreRequired',
            'is_ielts_required': 'IsIELTSRequired',
            'is_lsat_required': 'IsLSATRequired',
            'is_mat_required': 'IsMATRequired',
            'is_mcat_required': 'IsMCATRequired',
            'is_pte_required': 'IsPTERequired',
            'is_sat_required': 'IsSATRequired',
            'is_toefl_ib_required': 'IsTOEFLIBRequired',
            'is_import_verified': 'IsImportVerified',
            'is_imported': 'IsImported',
            'is_enrolled': 'IsEnrolled',
        }
        
        # All required final column names
        final_columns = [
            'CollegeName', 'CollegeCode', 'LogoPath', 'Phone', 'Email', 'SecondaryEmail',
            'Street1', 'Street2', 'County', 'City', 'State', 'Country', 'ZipCode', 'WebsiteUrl',
            'AdmissionOfficeUrl', 'VirtualTourUrl', 'Facebook', 'Instagram', 'Twitter', 'Youtube',
            'Tiktok', 'ApplicationFees', 'TestPolicy', 'CoursesAndGrades', 'Recommendations',
            'PersonalEssay', 'WritingSample', 'FinancialAidUrl', 'AdditionalInformation',
            'AdditionalDeadlines', 'IsAdditionalInformationAvailable', 'Status',
            'IsMultipleApplicationsAllowed', 'MaximumApplicationsAllowed', 'CreatedBy',
            'CreatedDate', 'LiveDate', 'TuitionFees', 'UpdatedBy', 'UpdatedDate', 'CountryCode',
            'LinkedIn', 'IsACTRequired', 'IsAnalyticalNotRequired', 'IsAnalyticalOptional',
            'IsDuoLingoRequired', 'IsELSRequired', 'IsEnglishNotRequired', 'IsEnglishOptional',
            'IsGMATOrGreRequired', 'IsGMATRequired', 'IsGreRequired', 'IsIELTSRequired',
            'IsLSATRequired', 'IsMATRequired', 'IsMCATRequired', 'IsPTERequired', 'IsSATRequired',
            'IsTOEFLIBRequired', 'QsWorldRanking', 'UsRanking', 'BatchId', 'IsImportVerified',
            'IsImported', 'BannerImagePath', 'CollegeHtmlAdditionalInfo', 'Introduction',
            'NumberOfCampuses', 'TotalFacultyAvailable', 'TotalProgramsAvailable',
            'TotalStudentsEnrolled', 'CollegeSetting', 'TypeofInstitution', 'CountriesRepresented',
            'GradAvgTuition', 'GradInternationalStudents', 'GradScholarshipHigh',
            'GradScholarshipLow', 'GradTotalStudents', 'Student_Faculty', 'TotalGraduatePrograms',
            'TotalInternationalStudents', 'TotalStudents', 'TotalUndergradMajors', 'UGAvgTuition',
            'UGInternationalStudents', 'UGScholarshipHigh', 'UGScholarshipLow', 'UGTotalStudents',
            'InstitutionType', 'IsEnrolled', 'OGAEnrolledProgramLevels'
        ]
        
        # Rename existing columns
        df_renamed = df.rename(columns=column_mapping)
        
        # Add missing columns with empty values
        for col in final_columns:
            if col not in df_renamed.columns:
                df_renamed[col] = ''
        
        # Reorder columns to match final_columns order
        df_renamed = df_renamed[final_columns]
        
        return df_renamed

    # Create output directory if it doesn't exist
    # Use absolute path based on the script location to ensure consistency
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "Inst_outputs")
    os.makedirs(output_dir, exist_ok=True)

    # Create DataFrame from flat_data
    df = pd.DataFrame([flat_data])

    # Rename columns and ensure all required columns are present
    df_final = rename_columns(df, flat_data)

    # Write to CSV
    csv_filename = os.path.join(output_dir, f"{safe_university_name}_Institution.csv")
    df_final.to_csv(csv_filename, index=False, encoding='utf-8')

    # Write to Excel
    excel_filename = os.path.join(output_dir, f"{safe_university_name}_Institution.xlsx")
    try:
        df_final.to_excel(excel_filename, index=False, engine='openpyxl')
    except ImportError:
        print(f"Warning: openpyxl is not installed. Install it with: pip install openpyxl")
        print(f"Excel file {excel_filename} not created, but CSV is available.")
    except Exception as e:
        print(f"Error saving to Excel: {e}")
        print(f"Excel file {excel_filename} not created, but CSV is available.")


    # for the json, I want to save the data as a json file with all the fields like values, evidence, urls, etc.
    json_filename = os.path.join(output_dir, f"{safe_university_name}_Institution.json")
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    print(f"Saved cleaned {university_name} data to {csv_filename}, {excel_filename}, and {json_filename}.")
    yield f'{{"status": "complete", "files": {{"csv": "{csv_filename}", "excel": "{excel_filename}", "json": "{json_filename}"}}}}'
