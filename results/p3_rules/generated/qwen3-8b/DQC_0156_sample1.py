import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    # Filter facts that are numeric, not null, and have a concept name containing 'basicanddiluted'
    filtered_facts = facts[
        (facts['is_numeric'] == True) &
        (facts['value'].notna()) &
        (facts['concept'].str.contains('basicanddiluted', case=False, na=False))
    ]
    
    # Check if the concept is an extension (prefix is not in standard taxonomies)
    extension_concepts = filtered_facts[
        ~filtered_facts['prefix'].isin(concepts['tag'].unique())
    ]
    
    # Collect flagged items
    for _, row in extension_concepts.iterrows():
        flagged.append({
            "qname": f"{row['prefix']}:{row['concept']}",
            "context_ref": row['context_ref']
        })
    
    return flagged