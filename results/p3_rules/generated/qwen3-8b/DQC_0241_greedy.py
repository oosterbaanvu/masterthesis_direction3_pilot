import pandas as pd
import re

def check(facts, lists, concepts):
    # Extract the relevant dimensions for TransactionTypeAxis
    transaction_type_axis_members = {'OverTheCounterMember', 'ExchangeTradedMember', 'ExchangeClearedMember'}
    
    # Filter facts that have TransactionTypeAxis with the forbidden members
    flagged = facts[
        facts['dimensions'].str.contains(r'Axis=TransactionTypeAxis', case=False, na=False)
        & facts['dimensions'].str.contains(r'Member=' + '|'.join(transaction_type_axis_members), case=False, na=False)
    ]
    
    # Format the result as a list of dictionaries
    flagged = flagged.to_dict(orient='records')
    
    return flagged