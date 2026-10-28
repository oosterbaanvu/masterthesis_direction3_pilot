import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    
    # Constants
    INTANGIBLE_MONETARY_ITEMS = set(lists['INTANGIBLE_MONETARY_ITEMS'])
    INTANGIBLE_DURATION_ITEMS = set(lists['INTANGIBLE_DURATION_ITEMS'])
    PPE_MEMBERS = set(lists['PPE_MEMBERS'])
    INTANGIBLE_FINITE_ASSETS_MEMBERS = set(lists['INTANGIBLE_FINITE_ASSETS_MEMBERS'])
    INTANGIBLE_INDEFINITE_ASSETS_MEMBERS = set(lists['INTANGIBLE_INDEFINITE_ASSETS_MEMBERS'])
    
    # Rule 1: Intangible Asset concepts are used with the axis PropertyPlantAndEquipmentByTypeAxis
    for index, row in facts.iterrows():
        if row['concept'] in INTANGIBLE_MONETARY_ITEMS | INTANGIBLE_DURATION_ITEMS and row['dimensions'] == 'us-gaap:PropertyPlantAndEquipmentByTypeAxis=*':
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    # Rule 2: The FiniteLivedIntangibleAssetsByMajorClassAxis axis is used with members that are associated with tangible Property plant and equipment
    for index, row in facts.iterrows():
        if row['concept'] in ['us-gaap:FiniteLivedIntangibleAssetUsefulLife'] and row['dimensions'] == 'us-gaap:FiniteLivedIntangibleAssetsByMajorClassAxis=*' and row['value'] in [3, 13]:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    # Rule 3: The PropertyPlantAndEquipmentByTypeAxis axis is used with members that are associated with definite lived and indefinite lived intangible assets
    for index, row in facts.iterrows():
        if row['concept'] in ['us-gaap:FiniteLivedIntangibleAssetUsefulLife'] and row['dimensions'] == 'us-gaap:PropertyPlantAndEquipmentByTypeAxis=*' and row['value'] in [3, 13]:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    # Rule 4: The concept CapitalizedComputerSoftwareGross is used with the PropertyPlantAndEquipmentByTypeAxis axis
    for index, row in facts.iterrows():
        if row['concept'] == 'us-gaap:CapitalizedComputerSoftwareGross' and row['dimensions'] == 'us-gaap:PropertyPlantAndEquipmentByTypeAxis=*':
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    return flagged