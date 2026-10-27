import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    pattern = re.compile(r'basicanddiluted', re.IGNORECASE)
    
    for index, row in facts.iterrows():
        if row['is_numeric'] and pattern.search(row['concept']):
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    return flagged