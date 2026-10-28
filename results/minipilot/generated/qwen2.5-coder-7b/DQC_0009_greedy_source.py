import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    rule_elements = lists['DQC_0009_ListOfElements']
    
    for index, row in rule_elements.iterrows():
        fact1_label = row['Element label (fact1)']
        fact2_label = row['Element label (fact2)']
        
        fact1 = facts[(facts['concept'] == fact1_label) & (facts['is_numeric'])]
        fact2 = facts[(facts['concept'] == fact2_label) & (facts['is_numeric'])]
        
        if not fact1.empty and not fact2.empty:
            fact1_value = fact1['value'].iloc[0]
            fact2_value = fact2['value'].iloc[0]
            
            if fact1_value > fact2_value:
                flagged.append({"qname": f"{fact1['prefix'].iloc[0]}:{fact1['concept'].iloc[0]}", "context_ref": fact1['context_ref'].iloc[0]})
                flagged.append({"qname": f"{fact2['prefix'].iloc[0]}:{fact2['concept'].iloc[0]}", "context_ref": fact2['context_ref'].iloc[0]})
    
    return flagged