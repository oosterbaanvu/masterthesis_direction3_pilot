import pandas as pd
import re

def check(facts, lists, concepts):
    # Filter facts that are in the statement section
    statement_facts = facts[facts['prefix'].str.contains('us-gaap', case=False, na=False)]
    
    # Extract all statement presentation networks
    statement_networks = lists['statement_presentation_networks']
    
    # Check if any statement network contains ConsolidatedEntitiesAxis
    consolidated_entities_axis = 'srt:ConsolidatedEntitiesAxis'
    has_consolidated_entities = False
    
    for network in statement_networks:
        if consolidated_entities_axis in network:
            has_consolidated_entities = True
            break
    
    if not has_consolidated_entities:
        return []
    
    # Filter facts that have ConsolidatedEntitiesAxis in their dimensions
    flagged_facts = facts[
        facts['dimensions'].str.contains(consolidated_entities_axis, case=False, na=False)
    ]
    
    return flagged_facts.to_dict(orient='records')