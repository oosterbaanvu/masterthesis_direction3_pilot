import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    
    # Iterate over all statement presentation networks
    for network in lists['STATEMENT_PRES_NETWORKS']:
        # Retrieve the concept names used in the parent-child relationships
        concept_names = set()
        for parent, child in network:
            parent_concept = facts[(parent.split(':')[0], parent.split(':')[1])]['concept']
            child_concept = facts[(child.split(':')[0], child.split(':')[1])]['concept']
            concept_names.update([parent_concept, child_concept])
        
        # Check if ConsolidatedEntitiesAxis is present in any statement network
        if 'srt:ConsolidatedEntitiesAxis' in concept_names:
            # Retrieve the facts that use ConsolidatedEntitiesAxis
            for index, row in facts.iterrows():
                if 'srt:ConsolidatedEntitiesAxis' in row['dimensions']:
                    flagged.append({"qname": row['prefix'] + ':' + row['concept'], "context_ref": row['context_ref']})
    
    return flagged