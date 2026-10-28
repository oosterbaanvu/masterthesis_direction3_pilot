import pandas as pd
import re

def check(facts, lists, concepts):
    # Filter facts that are numeric and have the concept name containing 'basicanddiluted'
    filtered_facts = facts[
        (facts['is_numeric'] == True) &
        (facts['concept'].str.contains('basicanddiluted', case=False, na=False))
    ]
    
    # Check if the concept is an extension element (prefix is not in standard taxonomies)
    extension_concepts = filtered_facts[
        ~filtered_facts['prefix'].isin(concepts['tag'].unique())
    ]
    
    # Extract relevant information for the rule message
    flagged = extension_concepts.apply(
        lambda row: {
            "qname": f"{row['prefix']}:{row['concept']}",
            "context_ref": row['context_ref']
        },
        axis=1
    ).tolist()
    
    return flagged