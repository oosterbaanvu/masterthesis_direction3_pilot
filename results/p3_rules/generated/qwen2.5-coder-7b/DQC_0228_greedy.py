import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    other_aggregate_pairs = lists['OTHER_AGGREGATE']
    non_negative_items = lists['NON_NEG_ITEMS']

    for pair in other_aggregate_pairs:
        aggregate_concept, other_concept = pair
        source_concept, target_concept = aggregate_concept, other_concept

        source_facts = facts[(facts['concept'] == source_concept) & (facts['is_numeric'])]
        target_facts = facts[(facts['concept'] == target_concept) & (facts['is_numeric'])]

        if not source_facts.empty and not target_facts.empty:
            source_value = source_facts['value'].max()
            target_value = target_facts['value'].max()

            if source_value > target_value:
                flagged.append({"qname": f"{source_facts['prefix'].iloc[0]}:{source_concept}", "context_ref": source_facts['context_ref'].iloc[0]})
                flagged.append({"qname": f"{target_facts['prefix'].iloc[0]}:{target_concept}", "context_ref": target_facts['context_ref'].iloc[0]})

    return flagged