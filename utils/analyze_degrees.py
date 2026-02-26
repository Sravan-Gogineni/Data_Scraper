
import csv
import re

def analyze_degrees(csv_path):
    unique_patterns = set()
    unique_degrees = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('ProgramName', '').strip()
            if not name:
                continue
            
            # Find content in last parenthesis
            match = re.search(r'\(([^)]+)\)$', name)
            if match:
                unique_degrees.add(match.group(1))
                unique_patterns.add(name)
            # Also check for "Master of ..." or "Bachelor of ..." at start if no parenthesis
            elif name.startswith("Master") or name.startswith("Bachelor") or name.startswith("Doctor"):
                unique_degrees.add(name.split(' ')[0] + " " + name.split(' ')[1])

    print("Unique Degree patterns found in parenthesis:")
    for d in sorted(unique_degrees):
        print(d)

if __name__ == '__main__':
    analyze_degrees('utils/The_University_of_Chicago_Final.csv')
