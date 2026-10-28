import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    
    # Get the list of elements that should not be negative
    negative_elements = lists['DQC_0014_ListOfElements']
    
    # Filter the facts to only include those with no dimensions
    no_dimension_facts = facts[facts['dimensions'] == '']
    
    # Iterate through each fact to check if it is in the list of negative elements and has a negative value
    for index, row in no_dimension_facts.iterrows():
        fact_qname = f"{row['prefix']}:{row['concept']}"
        if fact_qname in negative_elements['element'].values and row['value'] < 0:
            flagged.append({"qname": fact_qname, "context_ref": row['context_ref']})
    
    return flagged