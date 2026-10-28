import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    
    # Define the required concepts
    required_concepts = {
        'CommonStockSharesOutstanding': ['CommonStockSharesIssued', 'CommonStockSharesAuthorized'],
        'SharesOutstanding': ['CommonStockSharesIssued', 'CommonStockSharesAuthorized']
    }
    
    # Define the concepts for unlimited shares authorized
    unlimited_concepts = {
        'CommonStockSharesAuthorizedUnlimited': 'CommonStockSharesAuthorized'
    }
    
    # Iterate over each fact
    for index, fact in facts.iterrows():
        concept = fact['concept']
        value = fact['value']
        
        # Check if the fact is one of the required concepts
        if concept in required_concepts:
            # Check if the corresponding concept is missing
            for required_concept in required_concepts[concept]:
                if not (facts[(facts['concept'] == required_concept) & (facts['context_ref'] == fact['context_ref'])].empty):
                    continue
                flagged.append({"qname": f"{fact['prefix']}:{required_concept}", "context_ref": fact['context_ref']})
        
        # Check if the concept is 'CommonStockSharesAuthorized' and the value is 'unlimited'
        if concept == 'CommonStockSharesAuthorized' and value == 'unlimited':
            # Check if the 'CommonStockSharesAuthorizedUnlimited' concept is missing
            if facts[(facts['concept'] == 'CommonStockSharesAuthorizedUnlimited') & (facts['context_ref'] == fact['context_ref'])].empty:
                flagged.append({"qname": "us-gaap:CommonStockSharesAuthorizedUnlimited", "context_ref": fact['context_ref']})
    
    return flagged