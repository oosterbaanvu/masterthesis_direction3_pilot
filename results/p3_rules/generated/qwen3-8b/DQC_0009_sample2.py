import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    # Filter the list of elements for this rule
    rule_elements = lists['DQC_0009_ListOfElements']
    
    # Initialize a list to store flagged facts
    flagged = []
    
    # Iterate over each rule element
    for _, row in rule_elements.iterrows():
        # Extract the relevant elements
        fact1_label = row['Element label (fact1)']
        fact1_name = row['Element name (fact1)']
        fact2_label = row['Element label (fact2)']
        fact2_name = row['Element name (fact2)']
        
        # Filter facts for fact1 and fact2
        fact1 = facts[(facts['prefix'] + ':' + facts['concept']) == (row['prefix'] + ':' + fact1_name)]
        fact2 = facts[(facts['prefix'] + ':' + facts['concept']) == (row['prefix'] + ':' + fact2_name)]
        
        # Ensure both facts exist
        if not fact1.empty and not fact2.empty:
            # Check if the value of fact1 is greater than fact2
            for _, f1 in fact1.iterrows():
                for _, f2 in fact2.iterrows():
                    if not pd.isna(f1['value']) and not pd.isna(f2['value']):
                        if f1['value'] > f2['value']:
                            # Create a message for the issue
                            message = {
                                "qname": f"{f1['prefix']}:{f1['concept']}",
                                "context_ref": f1['context_ref'],
                                "fact1": {
 "label": fact1_label,
 "value": f1['value'],
 "name": fact1_name,
 "period": f1['period'],
 "dimensions": f1['dimensions'],
 "unit": f1['unit']
                                },
                                "fact2": {
 "label": fact2_label,
 "value": f2['value'],
 "name": fact2_name,
 "period": f2['period'],
 "dimensions": f2['dimensions'],
 "unit": f2['unit']
                                },
                                "rule_version": row['Rule version']
                            }
                            flagged.append(message)
    
    return flagged