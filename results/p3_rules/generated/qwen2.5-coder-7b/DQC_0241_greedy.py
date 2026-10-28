import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    transaction_type_axis_members = {
        'us-gaap:OverTheCounterMember',
        'us-gaap:ExchangeTradedMember',
        'us-gaap:ExchangeClearedMember'
    }
    
    for index, row in facts.iterrows():
        if row['dimensions'] in transaction_type_axis_members:
            flagged.append({
                "qname": f"{row['prefix']}:{row['concept']}",
                "context_ref": row['context_ref']
            })
    
    return flagged