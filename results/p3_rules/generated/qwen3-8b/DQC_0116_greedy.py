import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    # Define the line items that require the Asset Acquisition Axis
    required_concepts = {
        'us-gaap:AssetAcquisitionDateOfAcquisitionAgreement',
        'us-gaap:AssetAcquisitionEffectiveDateOfAcquisition',
        'us-gaap:AssetAcquisitionPriceOfAcquisitionExpected',
        'us-gaap:AssetAcquisitionIndemnificationAssetAmount'
    }
    
    # Extract the relevant facts
    relevant_facts = facts[facts['concept'].isin(required_concepts)]
    
    # Check if the AssetAcquisitionAxis is present in the dimensions
    flagged = []
    for _, row in relevant_facts.iterrows():
        qname = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        dimensions = row['dimensions'].split(';') if pd.notna(row['dimensions']) else []
        asset_acquisition_axis_present = any(dim.startswith('AssetAcquisitionAxis') for dim in dimensions)
        
        if not asset_acquisition_axis_present:
            flagged.append({
                'qname': qname,
                'context_ref': context_ref
            })
    
    return flagged