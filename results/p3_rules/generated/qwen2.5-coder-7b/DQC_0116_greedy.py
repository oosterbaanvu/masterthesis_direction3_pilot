import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    asset_acquisition_concepts = {
        'us-gaap:AssetAcquisitionDateOfAcquisitionAgreement',
        'us-gaap:AssetAcquisitionEffectiveDateOfAcquisition',
        'us-gaap:AssetAcquisitionPriceOfAcquisitionExpected',
        'us-gaap:AssetAcquisitionIndemnificationAssetAmount'
    }
    
    for index, row in facts.iterrows():
        if row['concept'] in asset_acquisition_concepts:
            if 'us-gaap:AssetAcquisitionAxis' not in row['dimensions']:
                flagged.append({
                    "qname": f"{row['prefix']}:{row['concept']}",
                    "context_ref": row['context_ref']
                })
    
    return flagged