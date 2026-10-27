import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    precondition_facts = {}
    
    # Evaluate precondition facts
    for index, row in lists['DQC_0013_ListOfElements'].iterrows():
        precondition_value = eval(row['preconditionValue'], {'facts': facts})
        precondition_facts[row['elementName']] = precondition_value
    
    # Check each fact for negative values when precondition is met
    for index, row in facts.iterrows():
        fact_name = f"{row['prefix']}:{row['concept']}"
        if row['value'] < 0 and precondition_facts.get(row['concept'], 0) > 0:
            flagged.append({
                "qname": fact_name,
                "context_ref": row['context_ref']
            })
    
    return flagged