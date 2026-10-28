import pandas as pd
import re

def check(facts, lists, concepts):
    # Extract the list of elements for the rule
    elements_df = lists['DQC_0009_ListOfElements']
    
    # Initialize a list to store flagged facts
    flagged = []
    
    # Iterate through each rule element
    for _, row in elements_df.iterrows():
        # Extract the fact1 and fact2 information
        fact1_label = row['Element label (fact1)']
        fact1_name = row['Element name (fact1)']
        fact2_label = row['Element label (fact2)']
        fact2_name = row['Element name (fact2)']
        
        # Filter facts for fact1 and fact2
        fact1_rows = facts[(facts['prefix'] + ':' + facts['concept'] == fact1_name)]
        fact2_rows = facts[(facts['prefix'] + ':' + facts['concept'] == fact2_name)]
        
        # Check if both facts exist
        if not fact1_rows.empty and not fact2_rows.empty:
            # Check if both facts have numeric values
            if not fact1_rows['is_numeric'].any() or not fact2_rows['is_numeric'].any():
                continue
            
            # Extract the numeric values
            fact1_value = fact1_rows['value'].values[0]
            fact2_value = fact2_rows['value'].values[0]
            
            # Check if fact1 value is greater than fact2 value
            if fact1_value > fact2_value:
                # Create a dictionary for the flagged fact
                flagged.append({
                    'qname': f"{fact1_name}",
                    'context_ref': fact1_rows['context_ref'].values[0]
                })
    
    return flagged