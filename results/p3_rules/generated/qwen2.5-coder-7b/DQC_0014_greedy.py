import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    elements_to_check = lists['DQC_0014_ListOfElements']['element']
    
    for index, row in facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if qname in elements_to_check and row['value'] < 0 and not row['dimensions']:
            flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    return flagged