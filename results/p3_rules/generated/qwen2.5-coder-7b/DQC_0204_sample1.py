import pandas as pd
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    
    property_plant_equipment_by_type_axis = 'us-gaap:PropertyPlantAndEquipmentByTypeAxis'
    finite_lived_intangible_assets_by_major_class_axis = 'us-gaap:FiniteLivedIntangibleAssetsByMajorClassAxis'
    indefinite_lived_intangible_assets_by_major_class_axis = 'us-gaap:IndefiniteLivedIntangibleAssetsByMajorClassAxis'
    capitalized_computer_software_gross = 'us-gaap:CapitalizedComputerSoftwareGross'
    
    tangible_assets = ['us-gaap:ComputerSoftwareIntangibleAssetMember', 'us-gaap:SoftwareAndSoftwareDevelopmentCostsMember']
    intangible_assets = ['us-gaap:ComputerSoftwareIntangibleAssetMember', 'us-gaap:IndefiniteLivedIntangibleAssetMember']
    
    for index, row in facts.iterrows():
        prefix, concept = row['prefix'], row['concept']
        context_ref = row['context_ref']
        dimensions = row['dimensions']
        
        if concept == capitalized_computer_software_gross:
            if property_plant_equipment_by_type_axis in dimensions:
                software_member = 'us-gaap:SoftwareDevelopmentMember'  # Assuming this is the member used for software
                if software_member in dimensions:
                    flagged.append({"qname": f"{prefix}:{concept}", "context_ref": context_ref})
        
        elif concept in ['us-gaap:FiniteLivedIntangibleAssetUsefulLife', 'us-gaap:IndefiniteLivedIntangibleAssetUsefulLife']:
            if property_plant_equipment_by_type_axis in dimensions:
                if any(asset in dimensions for asset in tangible_assets):
                    flagged.append({"qname": f"{prefix}:{concept}", "context_ref": context_ref})
            elif finite_lived_intangible_assets_by_major_class_axis in dimensions:
                if any(asset in dimensions for asset in tangible_assets):
                    flagged.append({"qname": f"{prefix}:{concept}", "context_ref": context_ref})
            elif indefinite_lived_intangible_assets_by_major_class_axis in dimensions:
                if any(asset in dimensions for asset in intangible_assets):
                    flagged.append({"qname": f"{prefix}:{concept}", "context_ref": context_ref})
    
    return flagged