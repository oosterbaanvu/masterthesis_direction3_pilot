import pandas as pd
import numpy as np

def check(facts, concepts, lists):
    flagged = []
    
    # Rule 1: Check for wrong signs
    for index, row in facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['is_numeric']:
            if row['prefix'] == 'us-gaap' and row['concept'] in ['Assets', 'LiabilitiesAndStockholdersEquity', 'StockholdersEquity']:
                if row['value'] < 0:
                    flagged.append({"qname": qname, "context_ref": row['context_ref'], "rule": "WrongSign"})
            elif row['prefix'] == 'us-gaap' and row['concept'] in ['NetIncomeLoss', 'OperatingIncomeLoss', 'ProfitLoss']:
                if row['value'] > 0:
                    flagged.append({"qname": qname, "context_ref": row['context_ref'], "rule": "WrongSign"})
    
    # Rule 2: Check for wrong scale
    for index, row in facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['is_numeric']:
            if row['prefix'] == 'us-gaap' and row['concept'] in ['Assets', 'LiabilitiesAndStockholdersEquity', 'StockholdersEquity']:
                if row['decimals'] != '0':
                    flagged.append({"qname": qname, "context_ref": row['context_ref'], "rule": "WrongScale"})
            elif row['prefix'] == 'us-gaap' and row['concept'] in ['NetIncomeLoss', 'OperatingIncomeLoss', 'ProfitLoss']:
                if row['decimals'] != '-3':
                    flagged.append({"qname": qname, "context_ref": row['context_ref'], "rule": "WrongScale"})
    
    # Rule 3: Check for values that break accounting relationships
    for index, row in facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['is_numeric']:
            if row['prefix'] == 'us-gaap' and row['concept'] == 'StockholdersEquity':
                retained_earnings = facts[(facts['prefix'] == 'us-gaap') & (facts['concept'] == 'RetainedEarningsAccumulatedDeficit') & (facts['context_ref'] == row['context_ref'])]['value'].values[0]
                if not np.isnan(retained_earnings) and row['value'] < retained_earnings:
                    flagged.append({"qname": qname, "context_ref": row['context_ref'], "rule": "AccountingRelationship"})
    
    # Rule 4: Check for values assigned to the wrong period
    for index, row in facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['is_numeric']:
            if row['prefix'] == 'us-gaap' and row['concept'] == 'NetIncomeLoss':
                if row['period_type'] == 'instant':
                    flagged.append({"qname": qname, "context_ref": row['context_ref'], "rule": "WrongPeriod"})
    
    # Rule 5: Check for values reported under the wrong element
    for index, row in facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['is_numeric']:
            if row['prefix'] == 'us-gaap' and row['concept'] == 'NetIncomeLoss':
                if row['value'] > 0:
                    flagged.append({"qname": qname, "context_ref": row['context_ref'], "rule": "WrongElement"})
    
    return flagged