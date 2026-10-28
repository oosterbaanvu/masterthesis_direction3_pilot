import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    
    # Rule 1: Check for wrong signs
    for index, row in facts.iterrows():
        concept_info = concepts[(concepts['tag'] == row['concept']) & (concepts['crdr'] == row['crdr']) & (concepts['iord'] == row['period_type'])]
        if not concept_info.empty and concept_info['datatype'].values[0] in ['monetary', 'perShare']:
            if row['value'] * int(concept_info['crdr'].values[0]) < 0:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "wrong_sign"})
    
    # Rule 2: Check for wrong scale
    for index, row in facts.iterrows():
        concept_info = concepts[(concepts['tag'] == row['concept']) & (concepts['crdr'] == row['crdr']) & (concepts['iord'] == row['period_type'])]
        if not concept_info.empty and concept_info['datatype'].values[0] == 'monetary':
            if row['value'] != np.round(row['value'], int(concept_info['decimals'].values[0])):
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "wrong_scale"})
    
    # Rule 3: Check for values that break accounting relationships
    for index, row in facts.iterrows():
        if row['concept'] == 'NetIncomeLoss':
            net_income = row['value']
            if not facts[(facts['concept'] == 'RetainedEarningsAccumulatedDeficit') & (facts['context_ref'] == row['context_ref'])].empty:
                retained_earnings = facts[(facts['concept'] == 'RetainedEarningsAccumulatedDeficit') & (facts['context_ref'] == row['context_ref'])]['value'].values[0]
                if net_income + retained_earnings < 0:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "accounting_relationship"})
    
    # Rule 4: Check for values reported under the wrong element
    for index, row in facts.iterrows():
        concept_info = concepts[(concepts['tag'] == row['concept']) & (concepts['crdr'] == row['crdr']) & (concepts['iord'] == row['period_type'])]
        if not concept_info.empty and concept_info['tag'].values[0] != row['concept']:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "wrong_element"})
    
    return flagged