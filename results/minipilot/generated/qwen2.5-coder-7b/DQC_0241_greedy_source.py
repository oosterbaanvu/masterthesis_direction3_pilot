import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    bad_members = {'us-gaap:OverTheCounterMember', 'us-gaap:ExchangeTradedMember', 'us-gaap:ExchangeClearedMember'}
    
    for index, row in facts.iterrows():
        dimensions = row['dimensions'].split(';')
        for dim in dimensions:
            if dim.startswith('us-gaap:TransactionTypeAxis='):
                member = dim.split('=')[1]
                if member in bad_members:
                    flagged.append({
                        "qname": f"{row['prefix']}:{row['concept']}",
                        "context_ref": row['context_ref']
                    })
    
    return flagged