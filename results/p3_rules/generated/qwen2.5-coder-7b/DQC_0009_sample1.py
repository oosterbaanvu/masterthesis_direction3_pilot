import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    element_pairs = lists['DQC_0009_ListOfElements']

    for index, row in element_pairs.iterrows():
        fact1_label = row['Element label (fact1)']
        fact2_label = row['Element label (fact2)']

        fact1 = facts[(facts['concept'] == fact1_label) & (facts['is_numeric'])]
        fact2 = facts[(facts['concept'] == fact2_label) & (facts['is_numeric'])]

        if fact1.empty or fact2.empty:
            continue

        fact1 = fact1.sort_values(by='value')
        fact2 = fact2.sort_values(by='value')

        if fact1['value'].max() > fact2['value'].min():
            flagged.append({"qname": f"{fact1['prefix'].iloc[0]}:{fact1['concept'].iloc[0]}", "context_ref": fact1['context_ref'].iloc[0]})
            flagged.append({"qname": f"{fact2['prefix'].iloc[0]}:{fact2['concept'].iloc[0]}", "context_ref": fact2['context_ref'].iloc[0]})

    return flagged