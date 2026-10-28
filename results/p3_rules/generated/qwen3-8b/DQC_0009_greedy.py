import pandas as pd
import numpy as np
import re

def check(facts, lists, concepts):
    # Extract the list of elements for this rule
    elements_df = lists['DQC_0009_ListOfElements']
    
    # Initialize a list to hold flagged facts
    flagged = []
    
    # Iterate over each rule element
    for _, row in elements_df.iterrows():
        # Extract the fact1 and fact2 details
        fact1_qname = f"{row['Element name (fact1)']}"
        fact2_qname = f"{row['Element name (fact2)']}"
        
        # Filter facts for fact1 and fact2
        fact1 = facts[facts['concept'] == fact1_qname]
        fact2 = facts[facts['concept'] == fact2_qname]
        
        # Check if both facts exist
        if not fact1.empty and not fact2.empty:
            # Ensure the facts have the same context_ref
            common_contexts = fact1['context_ref'].intersection(fact2['context_ref'])
            
            # Iterate over common contexts
            for context in common_contexts:
                # Get the values for the current context
                fact1_value = fact1[fact1['context_ref'] == context]['value'].values[0]
                fact2_value = fact2[fact2['context_ref'] == context]['value'].values[0]
                
                # Check if the value of fact1 is greater than fact2
                if fact1_value > fact2_value:
                    # Create a dictionary for the flagged fact
                    flagged.append({
                        "qname": fact1_qname,
                        "context_ref": context
                    })
    
    return flagged