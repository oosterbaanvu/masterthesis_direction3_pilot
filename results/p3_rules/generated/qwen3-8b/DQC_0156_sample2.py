import pandas as pd
import re

def check(facts, lists, concepts):
    # Filter facts that are numeric, not null, and have the concept name containing 'basicanddiluted'
    filtered_facts = facts[
        (facts['is_numeric'] == True) &
        (facts['value'].notnull()) &
        (facts['concept'].str.contains('basicanddiluted', case=False, na=False))
    ]
    
    # Check if the concept is an extension (prefix is not in standard taxonomies)
    extension_concepts = filtered_facts[
        ~filtered_facts['prefix'].isin(concepts['tag'].unique())
    ]
    
    # Return the flagged facts
    return extension_concepts.to_dict(orient='records')