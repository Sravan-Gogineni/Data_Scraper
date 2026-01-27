import pandas as pd

df = pd.read_csv("/Users/sravan/projects/Scraper_UI/RIT_Cleaned.csv")

def get_level(program_name):
    name = str(program_name).lower()
    
    # Explicit overrides for common tricky ones
    if "mba" in name:
        return "Graduate"
        
    if "minor" in name and ("certificate" in name or "certification" in name):
        return "Undergraduate-Certificate"
    
    if "advanced certificate" in name or "graduate certificate" in name:
        return "Graduate-Certificate"
        
    levels_map = {
        "Doctoral": ["phd", "edd", "dpt", "pharmd", "otd", "doctor"],
        "Graduate-Certificate": ["graduate certificate", "advanced certificate"], # More specific first
        "Associate": ["associate"],
        "Graduate": ["master", "masters", "ma", "m.s", "ms", "mfa", "mba"],
        "Undergraduate": ["bachelor", "bachelors", "baccalaureate", "ba", "bs", "minor", "bsc", "bfa"]
    }
    
    # Check specific phrases first
    if "bachelor" in name or "undergraduate" in name:
        return "Undergraduate"
    if "master" in name or "graduate" in name:
        if "certificate" in name and "graduate" not in name and "master" not in name:
             pass # ambiguous, let it fall through or handle if needed
        else:
             # Be careful not to catch "Graduate Certificate" as just "Graduate" if we want distinction. 
             # But usually Graduate Certificate is distinct.
             # If name is "Graduate Certificate in X", it matches "Graduate" keyword?
             # My map order matters.
             pass

    # Re-doing the map logic to be order sensitive
    # 1. Doctoral
    if any(k in name for k in levels_map["Doctoral"]):
        return "Doctoral"
        
    # 2. Graduate Certificate (specific)
    if any(k in name for k in levels_map["Graduate-Certificate"]):
        return "Graduate-Certificate"

    # 3. Graduate (Masters)
    if any(k in name for k in levels_map["Graduate"]):
        return "Graduate"
        
    # 4. Undergraduate
    if any(k in name for k in levels_map["Undergraduate"]):
        return "Undergraduate"
        
    # 5. Associates
    if any(k in name for k in levels_map["Associate"]):
        return "Associate"
    
    # Fallback for generic 'Certificate' if not caught above
    if "certificate" in name:
        return "Graduate-Certificate" # Defaulting RIT certificates to Grad based on file context? 
        # Actually in RIT file, there are some "Undergraduate" things.
        # But if it just says "Certificate in X", and it's in a mixed file...
        # Let's look at existing valid ones.
        # "Accounting and Financial Analytics Advanced Certificate" -> Grad Cert.
        
    return "Graduate" # Default fallback if nothing matches? Or keep original?
    # Better to return generic or original if we can't determine.
    # But usually empty string is better to see gaps.
    
    return ""

# Apply correction
df['Level'] = df['ProgramName'].apply(get_level)

# Save
df.to_csv("/Users/sravan/projects/Scraper_UI/RIT_Cleaned_Fixed.csv", index=False)
print("done")
