import pandas as pd
import re

def check(facts, lists, concepts):
    # Define the relevant concepts and axes
    intangible_concept = 'us-gaap:FiniteLivedIntangibleAssetUsefulLife'
    capitalized_software_concept = 'us-gaap:CapitalizedComputerSoftwareGross'
    ppe_axis = 'us-gaap:PropertyPlantAndEquipmentByTypeAxis'
    intangible_axis = 'us-gaap:FiniteLivedIntangibleAssetsByMajorClassAxis'
    intangible_member = 'us-gaap:ComputerSoftwareIntangibleAssetMember'
    software_member = 'us-gaap:SoftwareAndSoftwareDevelopmentCostsMember'
    software_development_member = 'us-gaap:SoftwareDevelopmentMember'
    
    # Filter facts for the relevant concepts
    intangible_facts = facts[facts['concept'] == intangible_concept]
    software_facts = facts[facts['concept'] == capitalized_software_concept]
    
    # Check for intangible concept with incorrect axis
    invalid_intangible_facts = intangible_facts[
        (intangible_facts['dimensions'].str.contains(ppe_axis) &
         ~intangible_facts['dimensions'].str.contains(intangible_axis)) |
        (intangible_facts['dimensions'].str.contains(intangible_axis) &
         ~intangible_facts['dimensions'].str.contains(ppe_axis))
    ]
    
    # Check for software concept with incorrect axis
    invalid_software_facts = software_facts[
        software_facts['dimensions'].str.contains(ppe_axis) &
        ~software_facts['dimensions'].str.contains('us-gaap:PropertyPlantAndEquipmentGross')
    ]
    
    # Combine results
    flagged = invalid_intangible_facts.to_dict(orient='records') + invalid_software_facts.to_dict(orient='records')
    return flagged