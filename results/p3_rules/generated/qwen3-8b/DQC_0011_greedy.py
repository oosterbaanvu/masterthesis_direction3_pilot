import pandas as pd
import numpy as np
import re

def check(facts, lists, concepts):
    flagged = []
    rule_list = lists['DQC_011_ListOfElements']
    
    for _, row in rule_list.iterrows():
        line_item = row['LineItem']
        dimension_line_item = row['DimensionLineItem']
        axis = row['Axis']
        member = row['Member']
        weight = row['Weight']
        
        # Find the standalone fact (line_item)
        standalone_fact = facts[(facts['concept'] == line_item) & (facts['dimensions'] == '')]
        
        # Find the dimensional fact (dimension_line_item) with the specified axis and member
        dimensional_fact = facts[(facts['concept'] == dimension_line_item) & 
                                (facts['dimensions'].str.contains(f"{axis}={member}"))]
        
        # Ensure both facts exist
        if not standalone_fact.empty and not dimensional_fact.empty:
            standalone_value = standalone_fact['value'].values[0]
            dimensional_value = dimensional_fact['value'].values[0]
            
            # Check if the dimensional value should be the inverse or equal
            expected_value = standalone_value * weight
            if not np.isclose(dimensional_value, expected_value, atol=1e-6):
                flagged.append({
                    "qname": f"{standalone_fact['prefix'].values[0]}:{line_item}",
                    "context_ref": standalone_fact['context_ref'].values[0]
                })
    
    return flagged