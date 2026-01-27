import os
import sys
import json
import importlib
import queue
import threading
import re
import time

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Graduate Scripts
from graduate_programs import extract_programs_list as grad_step1
from graduate_programs import program_extra_fields as grad_step2
from graduate_programs import extract_test_scores_requirements as grad_step3
from graduate_programs import extract_application_requirements as grad_step4
from graduate_programs import extract_program_details_financial as grad_step5
from graduate_programs import merge_and_standardize as grad_merge

# Import Undergraduate Scripts
from undergraduate_programs import extract_programs_list as undergrad_step1

try:
    from undergraduate_programs import program_extra_fields as undergrad_step2
except ImportError:
    undergrad_step2 = None

try:
    from undergraduate_programs import extract_test_scores_requirements as undergrad_step3
except ImportError:
    undergrad_step3 = None

try:
    from undergraduate_programs import extract_application_requirements as undergrad_step4
except ImportError:
    undergrad_step4 = None

try:
    from undergraduate_programs import extract_program_details_financial as undergrad_step5
except ImportError:
    undergrad_step5 = None

from undergraduate_programs import merge_and_standardize as undergrad_merge

# Import Final Merge Script
import merge_all

def process_programs_extraction(university_name, step):
    """
    Orchestrate the extraction process based on the step.
    Generator that yields JSON strings with updates.
    """
    
    # Map steps to modules
    # Each step list contains [grad_module, undergrad_module]
    steps_map = {
        1: [grad_step1, undergrad_step1],
        2: [grad_step2, undergrad_step2],
        3: [grad_step3, undergrad_step3],
        4: [grad_step4, undergrad_step4],
        5: [grad_step5, undergrad_step5],
        6: [grad_merge, undergrad_merge]  # This is the standardize step
    }

    try:
        step = int(step)
    except ValueError:
        yield f'{{"status": "error", "message": "Invalid step number: {step}"}}'
        return

    if step == 7: # Special step for Final Merge
        yield f'{{"status": "progress", "message": "Starting Step 7: Final Merge..."}}'
        try:
            for update in merge_all.run(university_name):
                yield update
        except Exception as e:
            yield f'{{"status": "error", "message": "Error in Final Merge: {str(e)}"}}'
        return

    if step == 8: # Special step for Concurrent Execution (Steps 2, 3, 4, 5)
        yield f'{{"status": "progress", "message": "Starting Concurrent Extraction for Steps 2, 3, 4, 5..."}}'
        
        modules_to_run = [
            (grad_step2, "[Grad] Step 2"),
            (grad_step3, "[Grad] Step 3"),
            (grad_step4, "[Grad] Step 4"),
            (grad_step5, "[Grad] Step 5"),
            (undergrad_step2, "[Undergrad] Step 2"),
            (undergrad_step3, "[Undergrad] Step 3"),
            (undergrad_step4, "[Undergrad] Step 4"),
            (undergrad_step5, "[Undergrad] Step 5")
        ]
        
        msg_queue = queue.Queue()
        accumulated_files = {}
        
        def run_module(module, name, q):
            try:
                if module and hasattr(module, 'run'):
                    for update in module.run(university_name):
                        try:
                            # Parse JSON to inject prefix in message
                            try:
                                data = json.loads(update)
                            except:
                                data = None
                            
                            if isinstance(data, dict):
                                if 'message' in data:
                                    data['message'] = f"[{name}] {data['message']}"
                                
                                # Intercept complete status from sub-modules
                                if data.get('status') == 'complete':
                                    # Collect files
                                    if 'files' in data:
                                        data['files_update'] = data['files']
                                    
                                    # Change status to progress so frontend doesn't disconnect
                                    data['status'] = 'progress'
                                    data['message'] = f"[{name}] Sub-task completed."
                                    
                                q.put(json.dumps(data))
                            else:
                                # Not a dict (e.g. string or list), treat clearly
                                safe_msg = str(update)
                                msg_obj = {
                                    "status": "progress",
                                    "message": f"[{name}] {safe_msg}"
                                }
                                q.put(json.dumps(msg_obj))

                        except Exception as parse_error:
                             # Fallback for any other errors
                             safe_msg = str(update)
                             msg_obj = {
                                "status": "error",
                                "message": f"[{name}] Error processing update: {safe_msg}"
                             }
                             q.put(json.dumps(msg_obj))
                else:
                    q.put(f'{{"status": "warning", "message": "{name} module not available"}}')
            except Exception as e:
                q.put(f'{{"status": "error", "message": "Error in {name}: {str(e)}"}}')

        threads = []
        for mod, name in modules_to_run:
            t = threading.Thread(target=run_module, args=(mod, name, msg_queue))
            t.start()
            threads.append(t)
            
        # Monitor threads and queue
        alive_threads = len(threads)
        while alive_threads > 0:
            try:
                # Wait for message with timeout
                msg = msg_queue.get(timeout=0.1)
                
                # Check for file updates to accumulate
                try:
                    data = json.loads(msg)
                    if 'files_update' in data:
                        accumulated_files.update(data['files_update'])
                        del data['files_update'] # Remove before yielding
                        # Include all current files in the update
                        data['files'] = accumulated_files
                        msg = json.dumps(data)
                except:
                    pass
                    
                yield msg
            except queue.Empty:
                # Check threads status
                alive_threads = sum(1 for t in threads if t.is_alive())
        
        # Drain remaining messages
        while not msg_queue.empty():
            msg = msg_queue.get()
            try:
                data = json.loads(msg)
                if 'files_update' in data:
                    accumulated_files.update(data['files_update'])
                    del data['files_update']
                    msg = json.dumps(data)
            except:
                pass
            yield msg
            
        yield json.dumps({
            "status": "complete", 
            "message": "Concurrent extraction completed for Steps 2, 3, 4, 5", 
            "files": accumulated_files
        })
        return

    if step == 9: # Combined Flow (Step 1 + Step 8)
        yield f'{{"status": "progress", "message": "Starting Automated Combined Flow for {university_name}..."}}'
        
        # Phase 1: Step 1 (Extract List) with Retry
        max_retries = 5
        grad_count = 0
        undergrad_count = 0
        accumulated_files = {}

        for attempt in range(1, max_retries + 1):
            yield f'{{"status": "progress", "message": "--- Step 1: Program Extraction Attempt {attempt}/{max_retries} ---"}}'
            
            # Run Grad Step 1
            yield f'{{"status": "progress", "message": "Extracting Graduate programs..."}}'
            try:
                for update in grad_step1.run(university_name):
                    try:
                        data = json.loads(update)
                        if data.get('status') == 'complete':
                            if 'files' in data:
                                accumulated_files.update(data['files'])
                            msg = data.get('message', '')
                            # Extract count
                            match = re.search(r'Found (\d+) graduate', msg)
                            if match:
                                grad_count = int(match.group(1))
                            yield json.dumps({"status": "progress", "message": f"[Grad] {msg}", "files": accumulated_files})
                        else:
                            yield update
                    except:
                        yield update
            except Exception as e:
                yield f'{{"status": "error", "message": "Error in Grad Step 1: {str(e)}"}}'

            # Run Undergrad Step 1
            yield f'{{"status": "progress", "message": "Extracting Undergraduate programs..."}}'
            try:
                for update in undergrad_step1.run(university_name):
                    try:
                        data = json.loads(update)
                        if data.get('status') == 'complete':
                            if 'files' in data:
                                accumulated_files.update(data['files'])
                            msg = data.get('message', '')
                            # Extract count
                            match = re.search(r'Found (\d+) undergraduate', msg)
                            if match:
                                undergrad_count = int(match.group(1))
                            yield json.dumps({"status": "progress", "message": f"[Undergrad] {msg}", "files": accumulated_files})
                        else:
                            yield update
                    except:
                        yield update
            except Exception as e:
                yield f'{{"status": "error", "message": "Error in Undergrad Step 1: {str(e)}"}}'

            if grad_count > 0 and undergrad_count > 0:
                yield f'{{"status": "progress", "message": "Success! Found {grad_count} Grad and {undergrad_count} Undergrad programs. Proceeding to enrichment."}}'
                break
            elif attempt < max_retries:
                missing = []
                if grad_count == 0: missing.append("Graduate")
                if undergrad_count == 0: missing.append("Undergraduate")
                yield f'{{"status": "warning", "message": "Missing {', '.join(missing)} programs list on attempt {attempt}. Retrying Step 1..."}}'
                import time
                time.sleep(2) 
            else:
                yield f'{{"status": "error", "message": "Max retries reached. Could not find both Grad and Undergrad lists. (Grad: {grad_count}, Undergrad: {undergrad_count}). Automation stopped."}}'
                return

        # Phase 2: Step 8 (Parallel)
        # We only reach here if both counts > 0 due to the 'return' in the else block above
        yield f'{{"status": "progress", "message": "--- Transitioning to Parallel Extraction (Steps 2-5) ---"}}'
            # Reuse Step 8 logic by calling recursively or just inline
            # For simplicity, I'll yield from process_programs_extraction(university_name, 8)
            # But we need to handle the 'complete' status of Step 8 carefully
        # Phase 2 Step 8 logic
        step8_gen = process_programs_extraction(university_name, 8)
        for update in step8_gen:
            try:
                data = json.loads(update)
                if data.get('status') == 'complete':
                    if 'files' in data:
                        accumulated_files.update(data['files'])
                    # Don't yield 'complete' yet
                    yield f'{{"status": "progress", "message": "Parallel extraction completed. Finalizing..."}}'
                else:
                    yield update
            except:
                yield update

        yield json.dumps({
            "status": "complete", 
            "message": "Automated combined flow completed successfully.", 
            "files": accumulated_files
        })
        return

    if step not in steps_map:
        yield f'{{"status": "error", "message": "Unknown step: {step}"}}'
        return

    # Track files from both executions
    accumulated_files = {}

    grad_module, undergrad_module = steps_map[step]
    
    yield f'{{"status": "progress", "message": "Starting Step {step} for {university_name}..."}}'

    # Execute Graduate Script
    yield f'{{"status": "progress", "message": "--- Processing Graduate Programs ---"}}'
    try:
        if step == 6: # Standardize step
            if hasattr(grad_module, 'run'):
                for update in grad_module.run(university_name):
                    try:
                        data = json.loads(update)
                        if data.get('status') == 'complete':
                            if 'files' in data:
                                accumulated_files.update(data['files'])
                            data['status'] = 'progress'
                            data['message'] = "[Grad] " + data.get('message', '')
                            yield json.dumps(data)
                        else:
                            yield update
                    except:
                        yield update
        elif hasattr(grad_module, 'run'):
            for update in grad_module.run(university_name):
                try:
                    data = json.loads(update)
                    if data.get('status') == 'complete':
                        if 'files' in data:
                            accumulated_files.update(data['files'])
                        data['status'] = 'progress'
                        data['message'] = "[Grad] " + data.get('message', '')
                        yield json.dumps(data)
                    else:
                        yield update
                except:
                    yield update
        else:
            yield f'{{"status": "warning", "message": "Graduate script for Step {step} does not have a run function"}}'
    except Exception as e:
        yield f'{{"status": "error", "message": "Error in Graduate Step {step}: {str(e)}"}}'
        # Continue to Undergrad even if Grad fails to ensure robustness? 
        # Yes, let's try Undergrad.

    # Execute Undergraduate Script
    if undergrad_module:
        yield f'{{"status": "progress", "message": "--- Processing Undergraduate Programs ---"}}'
        try:
             if step == 6: # Standardize step
                 if hasattr(undergrad_module, 'run'):
                    for update in undergrad_module.run(university_name):
                        try:
                            data = json.loads(update)
                            if data.get('status') == 'complete':
                                if 'files' in data:
                                    accumulated_files.update(data['files'])
                                data['status'] = 'progress'
                                data['message'] = "[Undergrad] " + data.get('message', '')
                                yield json.dumps(data)
                            else:
                                yield update
                        except:
                            yield update
             elif hasattr(undergrad_module, 'run'):
                for update in undergrad_module.run(university_name):
                    try:
                        data = json.loads(update)
                        if data.get('status') == 'complete':
                            if 'files' in data:
                                accumulated_files.update(data['files'])
                            data['status'] = 'progress'
                            data['message'] = "[Undergrad] " + data.get('message', '')
                            yield json.dumps(data)
                        else:
                            yield update
                    except:
                         yield update
             else:
                yield f'{{"status": "warning", "message": "Undergraduate script for Step {step} does not have a run function"}}'
        except Exception as e:
            yield f'{{"status": "error", "message": "Error in Undergraduate Step {step}: {str(e)}"}}'
    else:
         yield f'{{"status": "warning", "message": "Undergraduate module for Step {step} not found or disabled."}}'

    # If this was Step 6, we also auto-run the final merge (Step 7 logic)
    if step == 6:
        yield f'{{"status": "progress", "message": "--- Running Final Merge ---"}}'
        try:
            for update in merge_all.run(university_name):
                try:
                    data = json.loads(update)
                    if data.get('status') == 'complete':
                        if 'files' in data:
                            accumulated_files.update(data['files'])
                        data['status'] = 'progress'
                        data['message'] = "[Merge] " + data.get('message', '')
                        yield json.dumps(data)
                    else:
                        yield update
                except:
                    yield update
        except Exception as e:
            yield f'{{"status": "error", "message": "Error in Final Merge: {str(e)}"}}'

    # Final Complete Message
    yield json.dumps({
        "status": "complete", 
        "message": f"Step {step} completed for both Program levels", 
        "files": accumulated_files
    })
