import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta

def check(facts, lists, concepts):
    # Filter facts for relevant lease liability and asset concepts
    relevant_concepts = {
        'us-gaap:FinanceLeaseLiability',
        'us-gaap:FinanceLeaseLiabilityCurrent',
        'us-gaap:FinanceLeaseLiabilityNoncurrent',
        'us-gaap:FinanceLeaseRightOfUseAsset',
        'us-gaap:OperatingLeaseRightOfUseAsset'
    }
    lease_facts = facts[facts['concept'].isin(relevant_concepts)]
    
    # Filter facts to those within the 15-month reporting window
    current_period_end = datetime.now().date()
    cutoff_date = current_period_end - timedelta(days=15*30)
    lease_facts = lease_facts[lease_facts['period_type'] == 'instant']
    lease_facts = lease_facts[lease_facts['end'] >= cutoff_date.strftime('%Y-%m-%d')]
    
    # Check if the lease fact is not included in the financial statements
    flagged = []
    for _, row in lease_facts.iterrows():
        qname = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        value = row['value']
        period = row['end']
        dimensions = row['dimensions'].split(';') if row['dimensions'] else []
        
        # Check if the lease fact is included in the financial statements via extensible list or balance sheet location
        extensible_list = False
        balance_sheet_location = False
        
        # Check for extensible list
        extensible_list_concept = f"{row['prefix']}:{'FinanceLeaseLiabilityStatementOfFinancialPositionExtensibleList' if row['concept'] == 'FinanceLeaseLiability' else 'FinanceLeaseLiabilityCurrentStatementOfFinancialPositionExtensibleList' if row['concept'] == 'FinanceLeaseLiabilityCurrent' else 'FinanceLeaseLiabilityNoncurrentStatementOfFinancialPositionExtensibleList' if row['concept'] == 'FinanceLeaseLiabilityNoncurrent' else 'FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList' if row['concept'] == 'FinanceLeaseRightOfUseAsset' else 'OperatingLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList'}"
        if extensible_list_concept in lists['concept'].values:
            extensible_list = True
        
        # Check for balance sheet location axis
        balance_sheet_location_axis = False
        for dim in dimensions:
            if dim.startswith('us-gaap:StatementClassAxis=') or dim.startswith('us-gaap:BalanceSheetLocationAxis='):
                balance_sheet_location_axis = True
                break
        
        if not extensible_list and not balance_sheet_location_axis:
            flagged.append({
                'qname': qname,
                'context_ref': context_ref
            })
    
    return flagged