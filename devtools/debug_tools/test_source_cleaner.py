
from typing import List

def merge_sources(sources: List[str]) -> str:
    if not sources:
        return "Calculated"
        
    valid_sources = []
    seen = set()
    
    for s in sources:
        if s and s != "N/A":
            s_norm = s.strip()
            # Split by & logic first? 
            # The original code might have flaws. 
            # Let's replicate strict logic from my replacement:
            
            # If s contains &, split it? The original code didn't seem to split & inputs?
            # Wait, if input is "Calculated (sec_edgar & yahoo)", we treat it as one source?
            # No, usually inputs are ["Yahoo", "SEC Edgar"] or ["Calculated (Yahoo)", "Calculated (SEC)"]
            
            if s_norm not in seen:
                valid_sources.append(s_norm)
                seen.add(s_norm)
    
    # 3. Clean up sources to avoid nesting "Calculated (Calculated (...))"
    cleaned_sources = []
    for s in valid_sources:
        # Recursively strip "Calculated (" wrapper
        clean_s = s
        while clean_s.startswith("Calculated (") and clean_s.endswith(")"):
             clean_s = clean_s[12:-1]
        
        if clean_s == "Calculated":
             continue
        cleaned_sources.append(clean_s)
    
    if not cleaned_sources and "Calculated" in valid_sources:
         return "Calculated"
         
    if not cleaned_sources:
        return "Calculated"

    # Unique sorting
    unique_sources = sorted(list(set(cleaned_sources)))
    formatted_sources = "&".join(unique_sources)
    return f"Calculated ({formatted_sources})"

# Test Cases
# The problematic case: "Calculated (sec_edgar)&Calculated (yahoo)" 
# Wait, where did THAT string come from?
# It likely came from `metrics` combining other `metrics`.
# If `metric_A.source` is "Calculated (sec_edgar)"
# And `metric_B.source` is "Calculated (yahoo)"
# And we merge them: `merge_sources(["Calculated (sec_edgar)", "Calculated (yahoo)"])`

print("Test 1:", merge_sources(["Calculated (sec_edgar)", "Calculated (yahoo)"]))
print("Test 2:", merge_sources(["Calculated (sec_edgar&yahoo)"])) # If already joined?
print("Test 3:", merge_sources(["Yahoo", "Calculated (Finnhub)"]))
print("Test 4:", merge_sources(["Calculated (Calculated (sec_edgar))"]))
