import pandas as pd
import re

def check(facts, lists, concepts):
    # Extract the list of elements that should not be negative
    elements_list = lists['DQC_0014_ListOfElements']
    # Filter elements to include only those with 'debit' or 'credit' balance type
    elements_list = elements_list[elements_list['Balance type'].isin(['debit', 'credit'])]
    # Extract the element names and their namespace
    element_qnames = elements_list[['namespace', 'element']].apply(lambda row: f"{row[0]}:{row[1]}", axis=1)
    
    # Initialize a list to store flagged facts
    flagged = []
    
    # Iterate over each fact in the facts DataFrame
    for index, fact in facts.iterrows():
        # Check if the fact's qname is in the list of elements that should not be negative
        if fact['prefix'] + ':' + fact['concept'] in element_qnames.values:
            # Check if the fact has no dimensions
            if not fact['dimensions']:
                # Check if the value is negative
                if fact['value'] < 0:
                    # Append the flagged fact to the list
                    flagged.append({
                        'qname': fact['prefix'] + ':' + fact['concept'],
                        'context_ref': fact['context_ref']
                    })
    
    return flagged