
import csv
import sys
import os

# Ensure we can import from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from test_cleanup_logic import clean_program_name

def process_csv(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        count = 0
        changed_count = 0
        for row in reader:
            original_name = row['ProgramName']
            if original_name:
                cleaned_name = clean_program_name(original_name)
                if cleaned_name != original_name:
                    changed_count += 1
                row['ProgramName'] = cleaned_name
            writer.writerow(row)
            count += 1
            
    print(f"Processed {count} rows.")
    print(f"Updated {changed_count} program names.")
    print(f"Output written to {output_path}")

if __name__ == '__main__':
    input_csv = os.path.join(os.path.dirname(__file__), 'The_University_of_Chicago_Final.csv')
    output_csv = os.path.join(os.path.dirname(__file__), 'The_University_of_Chicago_Corrected.csv')
    process_csv(input_csv, output_csv)
