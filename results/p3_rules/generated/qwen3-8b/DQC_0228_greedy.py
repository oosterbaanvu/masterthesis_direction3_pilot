import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    other_aggregate_pairs = lists['OTHER_AGGREGATE']
    non_neg_items = lists['NON_NEG_ITEMS']
    
    for pair in other_aggregate_pairs:
        aggregate_concept, other_concept = pair
        
        # Extract source and target based on mapping convention (assuming source is aggregate, target is other)
        source_concept = aggregate_concept
        target_concept = other_concept
        
        # Filter facts for non-negative items
        source_facts = facts[
            (facts['prefix'] + ':' + facts['concept'] == source_concept) &
            (facts['concept'].isin(non_neg_items)) &
            (~facts['value'].isna())
        ]
        
        target_facts = facts[
            (facts['prefix'] + ':' + facts['concept'] == target_concept) &
            (facts['concept'].isin(non_neg_items)) &
            (~facts['value'].isna())
        ]
        
        # Ensure both facts exist for the same context_ref
        common_contexts = source_facts['context_ref'].intersection(target_facts['context_ref'])
        
        for context in common_contexts:
            source_fact = source_facts[source_facts['context_ref'] == context]
            target_fact = target_facts[target_facts['context_ref'] == context]
            
            if source_fact['value'].values[0] > target_fact['value'].values[0]:
                flagged.append({
                    "qname": source_concept,
                    "context_ref": context
                })
                flagged.append({
                    "qname": target_concept,
                    "context_ref": context
                })
    
    return flagged