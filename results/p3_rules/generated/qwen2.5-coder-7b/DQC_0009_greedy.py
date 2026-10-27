import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    element_pairs = lists['DQC_0009_ListOfElements'][['Element label (fact1)', 'Element name (fact1)', 'Element label (fact2)', 'Element name (fact2)']].values
    
    for fact1_label, fact1_name, fact2_label, fact2_name in element_pairs:
        fact1 = facts[(facts['concept'] == fact1_label) & (facts['prefix'] + ':' + facts['concept'] == fact1_name)]
        fact2 = facts[(facts['concept'] == fact2_label) & (facts['prefix'] + ':' + facts['concept'] == fact2_name)]
        
        if not fact1.empty and not fact2.empty:
            if fact1['value'].values[0] > fact2['value'].values[0]:
                flagged.append({"qname": fact1['prefix'] + ':' + fact1['concept'], "context_ref": fact1['context_ref']})
                flagged.append({"qname": fact2['prefix'] + ':' + fact2['concept'], "context_ref": fact2['context_ref']})
    
    return flagged