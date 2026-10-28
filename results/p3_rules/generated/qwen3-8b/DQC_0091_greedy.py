import pandas as pd
import numpy as np
import re

def check(facts, lists, concepts):
    # Filter percentage items (excluding tax reconciliation items)
    percent_items = concepts[concepts['datatype'] == 'percent']
    tax_reconciliation_items = percent_items[percent_items['tlabel'].str.contains('EffectiveIncomeTaxRate', case=False, na=False)]
    percent_items = percent_items[~percent_items['tlabel'].str.contains('EffectiveIncomeTaxRate', case=False, na=False)]
    
    # Extract qnames of percentage items
    percent_qnames = set(percent_items['tag'].str.replace('us-gaap:', '', regex=False))
    
    # Filter facts that are numeric and have a percentItemType
    flagged = []
    for index, fact in facts.iterrows():
        if fact['is_numeric'] and not pd.isna(fact['value']):
            qname = f"{fact['prefix']}:{fact['concept']}"
            if qname in percent_qnames:
                if fact['value'] > 10:
                    flagged.append({
                        "qname": qname,
                        "context_ref": fact['context_ref']
                    })
    return flagged