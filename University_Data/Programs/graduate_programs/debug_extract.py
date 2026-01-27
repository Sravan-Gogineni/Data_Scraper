
import os
import sys

# Add parent directories to sys.path to allow importing from Institution
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir should be where debug_extract.py is located. 
# We'll run this from /Users/sravan19/projects/Scraper_UI/University_Data/Programs/graduate_programs
# if we put it there, or handle paths if we put it in root.
# Let's write it to the actual programs dir to mimic the environment best.

sys.path.append(current_dir)

import traceback
try:
    from extract_programs_list import run
except ImportError:
    traceback.print_exc()
    print("Could not import run from extract_programs_list.py")
    sys.exit(1)

print("Starting debug run for University of Findlay...")
gen = run("University of Findlay")

for msg in gen:
    print(msg)
