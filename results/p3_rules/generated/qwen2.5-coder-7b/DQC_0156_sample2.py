import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    pattern = re.compile(r'basicanddiluted', re.IGNORECASE)
    
    for index, row in facts.iterrows():
        concept_name = row['concept']
        if pattern.search(concept_name):
            flagged.append({
                "qname": f"{row['prefix']}:{concept_name}",
                "context_ref": row['context_ref']
            })
    
    return flagged