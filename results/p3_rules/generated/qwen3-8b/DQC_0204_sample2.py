import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    # Define the relevant concepts and axes
    intangible_concept = 'us-gaap:FiniteLivedIntangibleAssetUsefulLife'
    capitalized_software_concept = 'us-gaap:CapitalizedComputerSoftwareGross'
    ppe_axis = 'us-gaap:PropertyPlantAndEquipmentByTypeAxis'
    intangible_axis = 'us-gaap:FiniteLivedIntangibleAssetsByMajorClassAxis'
    intangible_members = ['us-gaap:ComputerSoftwareIntangibleAssetMember', 'us-gaap:SoftwareAndSoftwareDevelopmentCostsMember']
    
    # Filter facts for the relevant concepts
    intangible_facts = facts[facts['concept'] == intangible_concept]
    software_facts = facts[facts['concept'] == capitalized_software_concept]
    
    # Check condition 1: Intangible concepts with PPE axis
    for _, row in intangible_facts.iterrows():
        dimensions = row['dimensions'].split(';') if pd.notna(row['dimensions']) else []
        ppe_axis_used = any(d.startswith(ppe_axis) for d in dimensions)
        if ppe_axis_used:
            member = next((d.split('=')[1] for d in dimensions if d.startswith(ppe_axis)), None)
            if member not in intangible_members:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    # Check condition 2: Intangible axis with tangible members
    for _, row in intangible_facts.iterrows():
        dimensions = row['dimensions'].split(';') if pd.notna(row['dimensions']) else []
        intangible_axis_used = any(d.startswith(intangible_axis) for d in dimensions)
        if intangible_axis_used:
            member = next((d.split('=')[1] for d in dimensions if d.startswith(intangible_axis)), None)
            if member in intangible_members:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    # Check condition 3: PPE axis with intangible members
    for _, row in intangible_facts.iterrows():
        dimensions = row['dimensions'].split(';') if pd.notna(row['dimensions']) else []
        ppe_axis_used = any(d.startswith(ppe_axis) for d in dimensions)
        if ppe_axis_used:
            member = next((d.split('=')[1] for d in dimensions if d.startswith(ppe_axis)), None)
            if member in intangible_members:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    # Check condition 4: Capitalized software with PPE axis
    for _, row in software_facts.iterrows():
        dimensions = row['dimensions'].split(';') if pd.notna(row['dimensions']) else []
        ppe_axis_used = any(d.startswith(ppe_axis) for d in dimensions)
        if ppe_axis_used:
            member = next((d.split('=')[1] for d in dimensions if d.startswith(ppe_axis)), None)
            if member != 'us-gaap:SoftwareDevelopmentMember':
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    return flagged