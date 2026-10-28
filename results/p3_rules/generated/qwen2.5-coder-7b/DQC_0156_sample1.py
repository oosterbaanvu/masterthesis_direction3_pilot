import re

def check(facts, lists, concepts):
    flagged = []
    basic_and_diluted_pattern = re.compile(r'basicanddiluted', re.IGNORECASE)
    
    for _, row in facts.iterrows():
        if row['is_numeric'] and basic_and_diluted_pattern.search(row['concept']):
            flagged.append({
                "qname": f"{row['prefix']}:{row['concept']}",
                "context_ref": row['context_ref']
            })
    
    return flagged