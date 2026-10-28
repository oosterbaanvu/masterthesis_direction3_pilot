import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    
    # Define the axes and members
    ppe_axis = 'us-gaap:PropertyPlantAndEquipmentByTypeAxis'
    tangible_members = ['us-gaap:ComputerSoftwareIntangibleAssetMember', 'us-gaap:SoftwareAndSoftwareDevelopmentCostsMember']
    intangible_members = ['us-gaap:ComputerSoftwareIntangibleAssetMember', 'us-gaap:SoftwareAndSoftwareDevelopmentCostsMember']
    finite_lived_axis = 'us-gaap:FiniteLivedIntangibleAssetsByMajorClassAxis'
    indefinite_lived_axis = 'us-gaap:IndefiniteLivedIntangibleAssetsByMajorClassAxis'
    capitalized_software_concept = 'us-gaap:CapitalizedComputerSoftwareGross'
    
    # Check each fact
    for index, row in facts.iterrows():
        concept = row['concept']
        dimensions = row['dimensions']
        prefix = row['prefix']
        
        # Check if the concept is used with the appropriate axis and member
        if concept in ['us-gaap:FiniteLivedIntangibleAssetUsefulLife', capitalized_software_concept]:
            if ppe_axis in dimensions and concept in tangible_members:
                flagged.append({"qname": f"{prefix}:{concept}", "context_ref": row['context_ref']})
            elif finite_lived_axis in dimensions and concept in intangible_members:
                flagged.append({"qname": f"{prefix}:{concept}", "context_ref": row['context_ref']})
            elif capitalized_software_concept in dimensions and concept in tangible_members:
                flagged.append({"qname": f"{prefix}:{concept}", "context_ref": row['context_ref']})
        
        # Check if the member is used with the appropriate axis
        if concept == 'us-gaap:FiniteLivedIntangibleAssetUsefulLife':
            if ppe_axis in dimensions and concept in tangible_members:
                flagged.append({"qname": f"{prefix}:{concept}", "context_ref": row['context_ref']})
            elif finite_lived_axis in dimensions and concept in intangible_members:
                flagged.append({"qname": f"{prefix}:{concept}", "context_ref": row['context_ref']})
        
        # Check if the concept is used with the appropriate axis
        if concept == capitalized_software_concept:
            if ppe_axis in dimensions and concept in tangible_members:
                flagged.append({"qname": f"{prefix}:{concept}", "context_ref": row['context_ref']})
    
    return flagged