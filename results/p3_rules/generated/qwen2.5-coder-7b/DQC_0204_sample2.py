import pandas as pd

def check(facts, lists, concepts):
    flagged = []

    intangible_asset_concepts = {
        'us-gaap:FiniteLivedIntangibleAssetUsefulLife',
        'us-gaap:IndefiniteLivedIntangibleAsset',
        'us-gaap:FiniteLivedIntangibleAsset'
    }

    tangible_asset_concepts = {
        'us-gaap:PropertyPlantAndEquipment',
        'us-gaap:GrossPropertyPlantAndEquipment'
    }

    computer_software_concept = 'us-gaap:CapitalizedComputerSoftwareGross'

    for index, fact in facts.iterrows():
        concept = fact['prefix'] + ':' + fact['concept']
        dimensions = fact['dimensions']

        if concept in computer_software_concept:
            if 'us-gaap:PropertyPlantAndEquipmentByTypeAxis' in dimensions:
                flagged.append({'qname': concept, 'context_ref': fact['context_ref']})

        elif concept in intangible_asset_concepts:
            if 'us-gaap:PropertyPlantAndEquipmentByTypeAxis' in dimensions:
                flagged.append({'qname': concept, 'context_ref': fact['context_ref']})

        elif concept in tangible_asset_concepts:
            if 'us-gaap:FiniteLivedIntangibleAssetsByMajorClassAxis' in dimensions:
                flagged.append({'qname': concept, 'context_ref': fact['context_ref']})

    return flagged