import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    
    # Define the allowed concepts and their valid axes
    allowed_concepts = {
        'us-gaap:FiniteLivedIntangibleAssetUsefulLife': ['FiniteLivedIntangibleAssetsByMajorClassAxis', 'IndefiniteLivedIntangibleAssetsByMajorClassAxis'],
        'us-gaap:CapitalizedComputerSoftwareGross': ['PropertyPlantAndEquipmentByTypeAxis']
    }
    
    # Process each fact
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        dimensions = fact['dimensions'].split(';') if fact['dimensions'] else []
        
        # Check if the concept is in the allowed list
        if fact['concept'] in allowed_concepts:
            valid_axes = allowed_concepts[fact['concept']]
            axis_member_pairs = [d.split('=') for d in dimensions]
            
            # Check if the axis and member are valid
            for axis, member in axis_member_pairs:
                if axis in valid_axes:
                    # Check if the member is valid for the axis
                    if fact['concept'] == 'us-gaap:FiniteLivedIntangibleAssetUsefulLife':
                        if axis == 'PropertyPlantAndEquipmentByTypeAxis':
                            # Check if the member is an intangible asset
                            if not re.match(r'us-gaap:ComputerSoftwareIntangibleAssetMember|us-gaap:ComputerSoftwareIntangibleAssetMember', member):
                                flagged.append({"qname": qname, "context_ref": fact['context_ref']})
                        elif axis == 'FiniteLivedIntangibleAssetsByMajorClassAxis':
                            # Check if the member is a tangible asset
                            if re.match(r'us-gaap:SoftwareAndSoftwareDevelopmentCostsMember', member):
                                flagged.append({"qname": qname, "context_ref": fact['context_ref']})
                    elif fact['concept'] == 'us-gaap:CapitalizedComputerSoftwareGross':
                        if axis == 'PropertyPlantAndEquipmentByTypeAxis':
                            # Check if the member is not SoftwareDevelopmentMember
                            if re.match(r'us-gaap:SoftwareDevelopmentMember', member):
                                flagged.append({"qname": qname, "context_ref": fact['context_ref']})
    
    return flagged