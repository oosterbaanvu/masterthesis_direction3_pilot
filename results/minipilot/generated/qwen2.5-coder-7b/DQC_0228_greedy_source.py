import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    other_aggregate = lists['OTHER_AGGREGATE']
    non_neg_items = lists['NON_NEG_ITEMS']
    
    for item in other_aggregate:
        source = item[0]
        target = item[1]
        
        if source in non_neg_items:
            source_facts = facts[(facts['concept'] == source) & (facts['value'] > 0)]
            target_facts = facts[(facts['concept'] == target) & (facts['value'] > 0)]
            
            for source_fact in source_facts.itertuples():
                for target_fact in target_facts.itertuples():
                    if source_fact.value > target_fact.value:
                        flagged.append({"qname": f"{source_fact.prefix}:{source_fact.concept}", "context_ref": source_fact.context_ref})
                        flagged.append({"qname": f"{target_fact.prefix}:{target_fact.concept}", "context_ref": target_fact.context_ref})
    
    return flagged