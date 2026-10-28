import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    concepts_needing_asset_acquisition_axis = {
        'us-gaap:AssetAcquisitionDateOfAcquisitionAgreement',
        'us-gaap:AssetAcquisitionEffectiveDateOfAcquisition',
        'us-gaap:AssetAcquisitionPriceOfAcquisitionExpected',
        'us-gaap:AssetAcquisitionIndemnificationAssetAmount'
    }

    for index, row in facts.iterrows():
        concept_qname = f"{row['prefix']}:{row['concept']}"
        if concept_qname in concepts_needing_asset_acquisition_axis and row['dimensions'] is None:
            flagged.append({"qname": concept_qname, "context_ref": row['context_ref']})

    return flagged