import pandas as pd
import re

def check(facts, lists, concepts):
    # Extract the list of elements from DQC_0014_ListOfElements
    elements_list = lists['DQC_0014_ListOfElements']
    # Filter elements to include only those with 'Balance type' as 'credit' or 'debit'
    valid_elements = elements_list[elements_list['Balance type'].str.lower().isin(['credit', 'debit'])]
    
    # Extract element names and namespaces
    element_qnames = valid_elements.apply(lambda row: f"{row['namespace']}:{row['element']}", axis=1)
    element_qnames = element_qnames.tolist()
    
    # Filter facts that are numeric, have no dimensions, and are in the valid elements list
    flagged = []
    for index, fact in facts.iterrows():
        if fact['is_numeric'] and not pd.isna(fact['value']) and fact['value'] < 0:
            qname = f"{fact['prefix']}:{fact['concept']}"
            if qname in element_qnames:
                if re.search(r';', fact['dimensions']) is None:
                    flagged.append({"qname": qname, "context_ref": fact['context_ref']})
    
    return flagged