from google import genai
from google.genai.types import GenerateContentConfig, Tool, GoogleSearch

try:
    client = genai.Client(vertexai=True)
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents="When is the next total solar eclipse in the United States?",
        config=GenerateContentConfig(
            tools=[
                Tool(
                    google_search=GoogleSearch(
                        exclude_domains=["domain.com"]
                    )
                )
            ],
        ),
    )
    print(response.text)
except Exception as e:
    import traceback
    traceback.print_exc()
