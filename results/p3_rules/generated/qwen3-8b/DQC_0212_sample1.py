import pandas as pd
import re
from datetime import datetime

def check(facts, lists, concepts):
    # Filter facts that report shares outstanding or common stock shares outstanding
    relevant_facts = facts[
        (facts['concept'] == 'CommonStockSharesOutstanding') | 
        (facts['concept'] == 'SharesOutstanding')
    ]
    
    flagged = []
    
    for _, row in relevant_facts.iterrows():
        qname = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        
        # Check for missing shares issued
        if row['concept'] == 'CommonStockSharesOutstanding':
            # Check if CommonStockSharesIssued is missing
            issued_fact = facts[
                (facts['concept'] == 'CommonStockSharesIssued') & 
                (facts['context_ref'] == context_ref)
            ]
            if issued_fact.empty:
                flagged.append({"qname": qname, "context_ref": context_ref})
            
            # Check if SharesIssued is missing
            issued_fact = facts[
                (facts['concept'] == 'SharesIssued') & 
                (facts['context_ref'] == context_ref)
            ]
            if issued_fact.empty:
                flagged.append({"qname": qname, "context_ref": context_ref})
        
        elif row['concept'] == 'SharesOutstanding':
            # Check if CommonStockSharesIssued is missing
            issued_fact = facts[
                (facts['concept'] == 'CommonStockSharesIssued') & 
                (facts['context_ref'] == context_ref)
            ]
            if issued_fact.empty:
                flagged.append({"qname": qname, "context_ref": context_ref})
            
            # Check if SharesIssued is missing
            issued_fact = facts[
                (facts['concept'] == 'SharesIssued') & 
                (facts['context_ref'] == context_ref)
            ]
            if issued_fact.empty:
                flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Check for missing shares authorized
        if row['concept'] == 'CommonStockSharesOutstanding':
            # Check if CommonStockSharesAuthorized is missing
            authorized_fact = facts[
                (facts['concept'] == 'CommonStockSharesAuthorized') & 
                (facts['context_ref'] == context_ref)
            ]
            if authorized_fact.empty:
                flagged.append({"qname": qname, "context_ref": context_ref})
            
            # Check if CommonStockSharesAuthorizedUnlimited is missing
            authorized_unlimited_fact = facts[
                (facts['concept'] == 'CommonStockSharesAuthorizedUnlimited') & 
                (facts['context_ref'] == context_ref)
            ]
            if authorized_unlimited_fact.empty:
                flagged.append({"qname": qname, "context_ref": context_ref})
        
        elif row['concept'] == 'SharesOutstanding':
            # Check if CommonStockSharesAuthorized is missing
            authorized_fact = facts[
                (facts['concept'] == 'CommonStockSharesAuthorized') & 
                (facts['context_ref'] == context_ref)
            ]
            if authorized_fact.empty:
                flagged.append({"qname": qname, "context_ref": context_ref})
            
            # Check if CommonStockSharesAuthorizedUnlimited is missing
            authorized_unlimited_fact = facts[
                (facts['concept'] == 'CommonStockSharesAuthorizedUnlimited') & 
                (facts['context_ref'] == context_ref)
            ]
            if authorized_unlimited_fact.empty:
                flagged.append({"qname": qname, "context_ref": context_ref})
    
    return flagged