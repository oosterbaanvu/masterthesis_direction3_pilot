import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    list_of_elements = lists['DQC_0014_ListOfElements']
    
    for index, row in facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if qname in list_of_elements['element'].values and row['dimensions'] == '':
            if row['value'] < 0:
                flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    return flagged