import pandas as pd
import numpy as np
import re

def check(facts, lists, concepts):
    flagged = []
    
    # Filter facts that report shares outstanding or common stock shares outstanding
    relevant_facts = facts[
        (facts['concept'] == 'CommonStockSharesOutstanding') |
        (facts['concept'] == 'SharesOutstanding')
    ]
    
    for _, row in relevant_facts.iterrows():
        qname = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        
        # Check for missing shares issued
        if row['concept'] == 'CommonStockSharesOutstanding':
            issued_concepts = ['CommonStockSharesIssued', 'SharesIssued']
        else:  # 'SharesOutstanding'
            issued_concepts = ['CommonStockSharesIssued', 'SharesIssued']
        
        issued_present = any(
            (facts['prefix'] + ':' + concept == qname) and 
            (facts['context_ref'] == context_ref) for concept in issued_concepts
        )
        
        if not issued_present:
            # Check if shares outstanding and shares issued are the same
            # For simplicity, assume that if a fact is present for shares issued, it's the same as outstanding
            # In a real scenario, you would need to compare values, but that's not available here
            flagged.append({
                'qname': qname,
                'context_ref': context_ref
            })
        
        # Check for missing shares authorized
        authorized_concepts = ['CommonStockSharesAuthorized', 'CommonStockSharesAuthorizedUnlimited']
        
        authorized_present = any(
            (facts['prefix'] + ':' + concept == qname) and 
            (facts['context_ref'] == context_ref) for concept in authorized_concepts
        )
        
        if not authorized_present:
            # Check if shares outstanding and shares authorized are the same
            # Again, assuming that if a fact is present for shares authorized, it's the same as outstanding
            # In a real scenario, you would need to compare values, but that's not available here
            flagged.append({
                'qname': qname,
                'context_ref': context_ref
            })
    
    return flagged