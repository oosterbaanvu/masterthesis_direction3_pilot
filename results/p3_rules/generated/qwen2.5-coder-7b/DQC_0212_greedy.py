import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    
    # Define the concepts we are interested in
    relevant_concepts = {
        'CommonStockSharesOutstanding': 'us-gaap:CommonStockSharesOutstanding',
        'CommonStockSharesIssued': 'us-gaap:CommonStockSharesIssued',
        'CommonStockSharesAuthorized': 'us-gaap:CommonStockSharesAuthorized',
        'CommonStockSharesAuthorizedUnlimited': 'us-gaap:CommonStockSharesAuthorizedUnlimited',
        'SharesOutstanding': 'us-gaap:SharesOutstanding',
        'SharesIssued': 'us-gaap:SharesIssued',
        'SharesAuthorized': 'us-gaap:SharesAuthorized',
        'SharesAuthorizedUnlimited': 'us-gaap:SharesAuthorizedUnlimited'
    }
    
    # Filter facts to only include the relevant ones
    relevant_facts = facts[facts['concept'].isin(relevant_concepts.values())]
    
    # Iterate over each relevant fact
    for index, row in relevant_facts.iterrows():
        concept = row['concept']
        context_ref = row['context_ref']
        value = row['value']
        
        # Check if the concept is for shares outstanding
        if concept in ['CommonStockSharesOutstanding', 'SharesOutstanding']:
            # Check if shares issued is missing
            if pd.isna(facts[(facts['concept'] == relevant_concepts['CommonStockSharesIssued']) & (facts['context_ref'] == context_ref)]['value'].values):
                flagged.append({"qname": relevant_concepts['CommonStockSharesIssued'], "context_ref": context_ref})
            
            # Check if shares authorized is missing
            if pd.isna(facts[(facts['concept'] == relevant_concepts['CommonStockSharesAuthorized']) & (facts['context_ref'] == context_ref)]['value'].values):
                flagged.append({"qname": relevant_concepts['CommonStockSharesAuthorized'], "context_ref": context_ref})
            
            # Check if shares authorized is unlimited
            if pd.isna(facts[(facts['concept'] == relevant_concepts['CommonStockSharesAuthorizedUnlimited']) & (facts['context_ref'] == context_ref)]['value'].values):
                flagged.append({"qname": relevant_concepts['CommonStockSharesAuthorizedUnlimited'], "context_ref": context_ref})
        
        # Check if the concept is for shares issued
        elif concept in ['CommonStockSharesIssued', 'SharesIssued']:
            # Check if shares outstanding is missing
            if pd.isna(facts[(facts['concept'] == relevant_concepts['CommonStockSharesOutstanding']) & (facts['context_ref'] == context_ref)]['value'].values):
                flagged.append({"qname": relevant_concepts['CommonStockSharesOutstanding'], "context_ref": context_ref})
        
        # Check if the concept is for shares authorized
        elif concept in ['CommonStockSharesAuthorized', 'SharesAuthorized']:
            # Check if shares outstanding is missing
            if pd.isna(facts[(facts['concept'] == relevant_concepts['CommonStockSharesOutstanding']) & (facts['context_ref'] == context_ref)]['value'].values):
                flagged.append({"qname": relevant_concepts['CommonStockSharesOutstanding'], "context_ref": context_ref})
        
        # Check if the concept is for shares authorized unlimited
        elif concept in ['CommonStockSharesAuthorizedUnlimited', 'SharesAuthorizedUnlimited']:
            # Check if shares outstanding is missing
            if pd.isna(facts[(facts['concept'] == relevant_concepts['CommonStockSharesOutstanding']) & (facts['context_ref'] == context_ref)]['value'].values):
                flagged.append({"qname": relevant_concepts['CommonStockSharesOutstanding'], "context_ref": context_ref})
    
    return flagged