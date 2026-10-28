import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    rule_elements = lists['DQC_0009_ListOfElements']
    
    for index, row in rule_elements.iterrows():
        fact1_label = row['Element label (fact1)']
        fact2_label = row['Element label (fact2)']
        
        fact1 = facts[(facts['concept'] == fact1_label) & (facts['is_numeric'] == True)]
        fact2 = facts[(facts['concept'] == fact2_label) & (facts['is_numeric'] == True)]
        
        if fact1.empty or fact2.empty:
            continue
        
        for _, f1 in fact1.iterrows():
            for _, f2 in fact2.iterrows():
                if f1['value'] > f2['value']:
                    flagged.append({
                        "qname": f"{f1['prefix']}:{f1['concept']}",
                        "context_ref": f1['context_ref']
                    })
                    flagged.append({
                        "qname": f"{f2['prefix']}:{f2['concept']}",
                        "context_ref": f2['context_ref']
                    })
    
    return flagged