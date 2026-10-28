import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    required_concepts = {
        'CommonStockSharesOutstanding': ['CommonStockSharesIssued', 'CommonStockSharesAuthorized', 'CommonStockSharesAuthorizedUnlimited'],
        'SharesOutstanding': ['CommonStockSharesIssued', 'CommonStockSharesAuthorized', 'CommonStockSharesAuthorizedUnlimited']
    }

    for index, row in facts.iterrows():
        prefix_concept = f"{row['prefix']}:{row['concept']}"
        context_ref = row['context_ref']
        
        if row['concept'] in required_concepts:
            for required in required_concepts[row['concept']]:
                if (prefix_concept, context_ref) not in facts.values:
                    flagged.append({"qname": prefix_concept, "context_ref": context_ref})
                    break

    return flagged