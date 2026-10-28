import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    pattern = re.compile(r'EffectiveIncomeTaxRate')
    
    for index, row in facts.iterrows():
        concept_name = f"{row['prefix']}:{row['concept']}"
        if row['datatype'] == 'percent' and not pattern.search(row['concept']):
            if row['value'] > 10:
                flagged.append({"qname": concept_name, "context_ref": row['context_ref']})
    
    return flagged