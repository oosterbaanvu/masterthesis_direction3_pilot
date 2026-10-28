import pandas as pd
import numpy as np
import re

def check(facts, lists, concepts):
    # Filter facts for the concept InvestmentOwnedAtFairValue
    investment_facts = facts[facts['concept'] == 'us-gaap:InvestmentOwnedAtFairValue']
    
    # Extract all unique dimensions and their members
    dimensions = {}
    for _, row in investment_facts.iterrows():
        dim_str = row['dimensions']
        if dim_str:
            for dim in dim_str.split(';'):
                axis, member = dim.split('=')
                if axis not in dimensions:
                    dimensions[axis] = []
                dimensions[axis].append(member)
    
    # Group facts by their dimensions and calculate total values
    grouped = investment_facts.groupby('dimensions').sum(numeric_only=True).reset_index()
    
    # Identify broader categories and their subsets
    broader_categories = {}
    for axis in dimensions:
        broader_categories[axis] = set(dimensions[axis])
    
    # Check for inconsistencies
    flagged = []
    for _, row in grouped.iterrows():
        dimensions_str = row['dimensions']
        total_value = row['value']
        
        # Check if this is a subset of a broader category
        for axis in broader_categories:
            if any(dim in dimensions_str for dim in broader_categories[axis]):
                # Find the broader category's total value
                broader_total = grouped[grouped['dimensions'].str.contains(axis, na=False)]['value'].sum()
                if total_value > broader_total:
                    flagged.append({
                        'qname': 'us-gaap:InvestmentOwnedAtFairValue',
                        'context_ref': row['context_ref']
                    })
                    break
    
    return flagged