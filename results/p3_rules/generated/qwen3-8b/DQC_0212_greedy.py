import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    
    # Filter facts that report shares outstanding or common stock shares outstanding
    relevant_facts = facts[
        (facts['concept'] == 'CommonStockSharesOutstanding') |
        (facts['concept'] == 'SharesOutstanding')
    ]
    
    # Define the required concepts for each case
    required_concepts = {
        'CommonStockSharesOutstanding': {
            'issued': ['CommonStockSharesIssued', 'SharesIssued'],
            'authorized': ['CommonStockSharesAuthorized', 'CommonStockSharesAuthorizedUnlimited']
        },
        'SharesOutstanding': {
            'issued': ['CommonStockSharesIssued', 'SharesIssued'],
            'authorized': ['CommonStockSharesAuthorized', 'CommonStockSharesAuthorizedUnlimited']
        }
    }
    
    # Check for missing required concepts
    for _, row in relevant_facts.iterrows():
        qname = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        
        # Determine the relevant required concepts
        concept_type = row['concept']
        required = required_concepts[concept_type]
        
        # Check for missing issued shares
        missing_issued = True
        for c in required['issued']:
            if (facts[(facts['concept'] == c) & (facts['context_ref'] == context_ref)].shape[0] > 0):
                missing_issued = False
                break
        
        if missing_issued:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Check for missing authorized shares
        missing_authorized = True
        for c in required['authorized']:
            if (facts[(facts['concept'] == c) & (facts['context_ref'] == context_ref)].shape[0] > 0):
                missing_authorized = False
                break
        
        if missing_authorized:
            flagged.append({"qname": qname, "context_ref": context_ref})
    
    return flagged