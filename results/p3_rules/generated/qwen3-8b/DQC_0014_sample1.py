import pandas as pd
import numpy as np
import re

def check(facts, lists, concepts):
    # Extract the list of elements that should not be negative
    dqc_0014_list = lists['DQC_0014_ListOfElements']
    non_negative_elements = dqc_0014_list[['element']].rename(columns={'element': 'concept'})
    
    # Filter facts that are numeric, have no dimensions, and are in the non-negative elements list
    flagged = []
    for index, row in facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['is_numeric'] and pd.isna(row['dimensions']) and qname in non_negative_elements.values:
            if row['value'] < 0:
                flagged.append({
                    "qname": qname,
                    "context_ref": row['context_ref']
                })
    return flagged