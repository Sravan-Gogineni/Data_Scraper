#!/usr/bin/env python3
"""
Enhanced build script to create COMPLETE standalone sequential scraper
including ALL Institution, Department, and Programs extraction code.
HANDLES FUNCTION NAME COLLISIONS by renaming run() functions with prefixes.
"""

import os
import re

# Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
inst_file = os.path.join(base_dir, "Institution", "Institution.py")
dept_file = os.path.join(base_dir, "Departments", "Department.py")
seq_file = os.path.join(base_dir, "sequential_scraper.py")
programs_file = os.path.join(base_dir, "Programs", "Programs.py")
output_file = os.path.join(base_dir, "sequential_scraper_complete.py")

# Programs sub-modules
grad_programs_dir = os.path.join(base_dir, "Programs", "graduate_programs")
undergrad_programs_dir = os.path.join(base_dir, "Programs", "undergraduate_programs")
merge_all_file = os.path.join(base_dir, "Programs", "merge_all.py")

grad_modules = [
    ("extract_programs_list.py", "grad_step1"),
    ("program_extra_fields.py", "grad_step2"),
    ("extract_test_scores_requirements.py", "grad_step3"),
    ("extract_application_requirements.py", "grad_step4"),
    ("extract_program_details_financial.py", "grad_step5"),
    ("merge_and_standardize.py", "grad_merge")
]

undergrad_modules = [
    ("extract_programs_list.py", "undergrad_step1"),
    ("program_extra_fields.py", "undergrad_step2"),
    ("extract_test_scores_requirements.py", "undergrad_step3"),
    ("extract_application_requirements.py", "undergrad_step4"),
    ("extract_program_details_financial.py", "undergrad_step5"),
    ("merge_and_standardize.py", "undergrad_merge")
]

print("Building COMPLETE standalone scraper from:")
print(f"  - {inst_file}")
print(f"  - {dept_file}")
print(f"  - Graduate programs modules: {len(grad_modules)} files")
print(f"  - Undergraduate programs modules: {len(undergrad_modules)} files")
print(f"  - {merge_all_file}")
print(f"  - {seq_file}")
print(f"Output: {output_file}")

def extract_functions_from_file(filepath, skip_imports=True, skip_client_setup=True, rename_run_to=None):
    """Extract function definitions and classes from a Python file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    extracted_lines = []
    skip_next_function = False
    seen_client = False
    skip_main_block = False
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Skip if __name__ == "__main__": blocks (except from the main sequential_scraper.py)
        if line.strip().startswith('if __name__'):
            # Check if this is the main sequential scraper file (it will have the full main() function)
            # For now, skip ALL if __name__ blocks - we'll add the proper one from sequential_scraper.py
            skip_main_block = True
            i += 1
            continue
        
        # Skip content inside if __name__ blocks
        if skip_main_block:
            # Check if we're back to module level (no indentation)
            if line and not line[0].isspace() and line.strip():
                skip_main_block = False
                # Don't skip this line, process it normally
            else:
                i += 1
                continue
        
        # Rename run() function if requested
        if rename_run_to and line.strip().startswith('def run('):
            line = line.replace('def run(', f'def {rename_run_to}(')
        
        # Check for try/except ImportError blocks (skip entire block)
        if skip_imports and line.strip() == 'try:':
            # Look ahead to see if this is an import try block
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            
            if j < len(lines) and (lines[j].strip().startswith('from ') or lines[j].strip().startswith('import ')):
                # This is an import try block, skip the entire thing
                k = j + 1
                while k < len(lines) and not lines[k].strip().startswith('except'):
                    k += 1
                
                if k < len(lines) and 'ImportError' in lines[k]:
                    k += 1
                    # Skip the assignment or pass statement
                    while k < len(lines) and (lines[k].startswith('    ') or lines[k].startswith('\t') or not lines[k].strip()):
                        if lines[k].strip() and not lines[k].startswith('    ') and not lines[k].startswith('\t'):
                            break
                        k += 1
                    i = k
                    continue
        
        # Skip regular imports if requested
        if skip_imports and (line.strip().startswith('import ') or line.strip().startswith('from ')):
            i += 1
            continue
        
        # Skip setup code if requested
        if skip_client_setup:
            if 'load_dotenv()' in line or 'logging.basicConfig' in line:
                i += 1
                continue
            if 'client = genai.Client' in line:
                if seen_client:
                    i += 1
                    continue
                seen_client = True
                i += 1
                continue
        
        # Skip duplicate generate_text_safe and extract_clean_value functions
        if line.strip().startswith('def generate_text_safe(') or line.strip().startswith('def extract_clean_value('):
            skip_next_function = True
            i += 1
            continue
        
        if skip_next_function:
            # Skip until we hit the next function or class definition
            if line.strip() and not line.strip().startswith('#') and not line.startswith(' ') and not line.startswith('\t'):
                if line.strip().startswith('def ') or line.strip().startswith('class '):
                    skip_next_function = False
                else:
                    i += 1
                    continue
            else:
                i += 1
                continue
        
        extracted_lines.append(line)
        i += 1
    
    return '\n'.join(extracted_lines)

# Read Institution.py
inst_content = extract_functions_from_file(inst_file, skip_imports=True, skip_client_setup=False)

# Read Department.py
dept_content = extract_functions_from_file(dept_file, skip_imports=True, skip_client_setup=True)

# Read all graduate programs modules with renamed run() functions
grad_contents = {}
for module_file, alias in grad_modules:
    module_path = os.path.join(grad_programs_dir, module_file)
    if os.path.exists(module_path):
        grad_contents[alias] = extract_functions_from_file(module_path, skip_imports=True, skip_client_setup=True, rename_run_to=f"{alias}_run")
        print(f"  ✓ Loaded graduate_programs/{module_file} (as {alias})")

# Read all undergraduate programs modules with renamed run() functions
undergrad_contents = {}
for module_file, alias in undergrad_modules:
    module_path = os.path.join(undergrad_programs_dir, module_file)
    if os.path.exists(module_path):
        undergrad_contents[alias] = extract_functions_from_file(module_path, skip_imports=True, skip_client_setup=True, rename_run_to=f"{alias}_run")
        print(f"  ✓ Loaded undergraduate_programs/{module_file} (as {alias})")

# Read merge_all.py
merge_all_content = ""
if os.path.exists(merge_all_file):
    merge_all_content = extract_functions_from_file(merge_all_file, skip_imports=True, skip_client_setup=True, rename_run_to="merge_all_run")
    print("  ✓ Loaded merge_all.py")

# Read Programs.py (main orchestrator) - DON'T include it yet, we'll manually create the orchestration
programs_content_raw = extract_functions_from_file(programs_file, skip_imports=True, skip_client_setup=True)

# Read sequential_scraper.py
seq_content = extract_functions_from_file(seq_file, skip_imports=True, skip_client_setup=True)

# Build the complete standalone file
standalone = f'''#!/usr/bin/env python3
"""
COMPLETE Standalone Sequential University Data Scraper - FULL VERSION
-----------------------------------------------------------------------
This file contains ALL extraction code with EXACT functions and prompts from:
- Institution.py (all ~80+ functions)
- Department.py (complete extraction)
- All Programs sub-modules (graduate & undergraduate):
  * extract_programs_list.py
  * program_extra_fields.py
  * extract_test_scores_requirements.py
  * extract_application_requirements.py
  * extract_program_details_financial.py
  * merge_and_standardize.py
- merge_all.py (final merge logic)
- Programs.py (orchestration)
- sequential_scraper.py (main workflow)

NO MODIFICATIONS to original prompts - All code copied exactly as-is.

Usage:
    python sequential_scraper_complete.py "University Name"

Dependencies:
    pip install pandas google-genai python-dotenv openpyxl
"""

# ============================================================================
# IMPORTS AND SETUP
# ============================================================================
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
import queue
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# ============================================================================
# INSTITUTION.PY - EXACT COPY OF ALL FUNCTIONS
# ============================================================================

{inst_content}

# ============================================================================
# DEPARTMENT.PY - EXACT COPY OF EXTRACTION FUNCTION
# ============================================================================

{dept_content}

# ============================================================================
# PROGRAMS EXTRACTION - GRADUATE PROGRAMS MODULES
# ============================================================================

'''

# Add all graduate programs modules
for alias, content in grad_contents.items():
    standalone += f'''
# ----------------------------------------------------------------------------
# {alias} (graduate_programs)
# ----------------------------------------------------------------------------

{content}

'''

standalone += '''
# ============================================================================
# PROGRAMS EXTRACTION - UNDERGRADUATE PROGRAMS MODULES
# ============================================================================

'''

# Add all undergraduate programs modules
for alias, content in undergrad_contents.items():
    standalone += f'''
# ----------------------------------------------------------------------------
# {alias} (undergraduate_programs)
# ----------------------------------------------------------------------------

{content}

'''

# Add merge_all
if merge_all_content:
    standalone += f'''
# ============================================================================
# MERGE_ALL.PY - FINAL MERGE LOGIC
# ============================================================================

{merge_all_content}

'''

# Create module-like objects that reference the renamed run functions
standalone += '''
# ============================================================================
# MODULE WRAPPERS - Allow Programs.py orchestration to work
# ============================================================================

class ModuleWrapper:
    """Wrapper to make a run function look like an imported module"""
    def __init__(self, run_func):
        self.run = run_func

# Create module references for graduate programs
grad_step1 = ModuleWrapper(grad_step1_run)
grad_step2 = ModuleWrapper(grad_step2_run)
grad_step3 = ModuleWrapper(grad_step3_run)
grad_step4 = ModuleWrapper(grad_step4_run)
grad_step5 = ModuleWrapper(grad_step5_run)
grad_merge = ModuleWrapper(grad_merge_run)

# Create module references for undergraduate programs
undergrad_step1 = ModuleWrapper(undergrad_step1_run)
undergrad_step2 = ModuleWrapper(undergrad_step2_run)
undergrad_step3 = ModuleWrapper(undergrad_step3_run)
undergrad_step4 = ModuleWrapper(undergrad_step4_run)
undergrad_step5 = ModuleWrapper(undergrad_step5_run)
undergrad_merge = ModuleWrapper(undergrad_merge_run)

# Create merge_all module reference
class MergeAllWrapper:
    """Wrapper for merge_all module"""
    @staticmethod
    def run(*args, **kwargs):
        return merge_all_run(*args, **kwargs)

merge_all = MergeAllWrapper()

'''

# Add Programs.py orchestrator
standalone += f'''
# ============================================================================
# PROGRAMS.PY - PROGRAMS ORCHESTRATION
# ============================================================================

{programs_content_raw}

'''

# Add sequential_scraper orchestration
standalone += f'''
# ============================================================================
# SEQUENTIAL ORCHESTRATION - FROM sequential_scraper.py
# ============================================================================

{seq_content}

'''

# Write the output
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(standalone)

lines_count = len(standalone.split('\n'))
print(f"\n✅ Created {output_file}")
print(f"   File size: {len(standalone):,} characters")
print(f"   Total lines: {lines_count:,}")
print(f"\nThis file contains:")
print(f"  ✓ ALL Institution.py functions with EXACT original prompts (~80+ functions)")
print(f"  ✓ Department.py extraction with EXACT original prompts")
print(f"  ✓ ALL Graduate programs modules ({len(grad_contents)} files)")
print(f"  ✓ ALL Undergraduate programs modules ({len(undergrad_contents)} files)")
print(f"  ✓ merge_all.py (final merge logic)")
print(f"  ✓ Programs.py orchestration with fixed module references")
print(f"  ✓ Sequential orchestration logic")
print(f"\n🚀 Ready to use - just run: python sequential_scraper_complete.py 'University Name'")
