
import csv
import re

def analyze_uchicago(csv_path):
    suffixes = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('ProgramName', '').strip()
            if not name:
                continue
            
            # Look for the last word or token
            parts = name.split()
            if parts:
                last_part = parts[-1]
                # Check for patterns like MS, PhD, MSA, etc.
                # Also check for yMS, sPhD etc (typos)
                if last_part.endswith('yMS') or last_part.endswith('yMPS') or last_part.endswith('yMPP') or last_part.endswith('yprogram)') or last_part.endswith('Polic') or last_part.endswith('sCert'):
                     print(f"Suspicious suffix '{last_part}' found in: '{name}'")
                elif name.endswith('PhD') or name.endswith('MS') or name.endswith('MA') or name.endswith('M.A.') or name.endswith('M.S.'):
                     pass
                     # print(f"Valid ending: {name}")

    # print("Potential Degree Suffixes found:")
    # for s, count in sorted(suffixes.items(), key=lambda x: x[1], reverse=True):
    #     print(f"{s}: {count}")

if __name__ == '__main__':
    analyze_uchicago('utils/The_University_of_Chicago_Final.csv')
