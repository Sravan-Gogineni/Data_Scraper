import os
import sys
import shutil
import json
import importlib.util

# Paths
grad_dir = "/Users/sravan/projects/Scraper_UI/University_Data/Programs/graduate_programs"
undergrad_dir = "/Users/sravan/projects/Scraper_UI/University_Data/Programs/undergraduate_programs"

grad_csv = os.path.join(grad_dir, "Grad_prog_outputs", "graduate_programs.csv")
undergrad_csv = os.path.join(undergrad_dir, "Undergrad_prog_outputs", "undergraduate_programs.csv")

# Temporary paths
grad_csv_temp = grad_csv + ".bak"
undergrad_csv_temp = undergrad_csv + ".bak"

def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

grad_module = import_module_from_path("grad_step2", os.path.join(grad_dir, "program_extra_fields.py"))
undergrad_module = import_module_from_path("undergrad_step2", os.path.join(undergrad_dir, "program_extra_fields.py"))

def test_module(module, name, csv_path, temp_path):
    print(f"Testing {name}...")
    
    # Hide existing CSV if present
    restored = False
    if os.path.exists(csv_path):
        print(f"  Hiding existing CSV: {csv_path}")
        os.rename(csv_path, temp_path)
        restored = True
    
    try:
        # Run the module
        gen = module.run("TestUniversity")
        try:
            first_response = next(gen)
            print(f"  Response: {first_response}")
            data = json.loads(first_response)
            
            if data.get("status") == "complete" and "Skipping" in data.get("message", ""):
                print(f"  [PASS] {name} handled missing file correctly.")
            else:
                print(f"  [FAIL] {name} did not return expected skipped status. Got: {data.get('status')}")
                
        except StopIteration:
            print(f"  [FAIL] {name} yielded nothing.")
        except Exception as e:
            print(f"  [FAIL] {name} raised exception: {e}")
            
    finally:
        # Restore CSV if we hid it
        if restored and os.path.exists(temp_path):
            print(f"  Restoring CSV: {csv_path}")
            os.rename(temp_path, csv_path)

if __name__ == "__main__":
    test_module(grad_module, "Graduate Step 2", grad_csv, grad_csv_temp)
    print("-" * 20)
    test_module(undergrad_module, "Undergraduate Step 2", undergrad_csv, undergrad_csv_temp)
