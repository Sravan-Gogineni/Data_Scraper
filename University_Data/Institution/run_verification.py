from Institution import get_university_details
import json

def run_verification():
    print("Testing get_university_details for 'Stanford University'")
    result = get_university_details("Stanford University")
    print("\nResult:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    run_verification()
