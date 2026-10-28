import pandas as pd
import re
from datetime import datetime, timedelta

def check(facts, lists, concepts):
    # Filter relevant facts for lease liabilities and assets
    lease_concepts = {
        'us-gaap:FinanceLeaseLiability',
        'us-gaap:FinanceLeaseLiabilityCurrent',
        'us-gaap:FinanceLeaseLiabilityNoncurrent',
        'us-gaap:FinanceLeaseRightOfUseAsset',
        'us-gaap:OperatingLeaseRightOfUseAsset'
    }
    relevant_facts = facts[facts['concept'].isin(lease_concepts)]
    
    # Filter facts within the 15-month window
    current_date = datetime.now()
    cutoff_date = current_date - timedelta(days=3*30)  # Approximate 15 months
    relevant_facts = relevant_facts[relevant_facts['period_type'] == 'instant']
    relevant_facts = relevant_facts[relevant_facts['start'].astype('datetime64[ns]') >= cutoff_date]
    
    # Identify required extensible lists
    extensible_lists = {
        'us-gaap:FinanceLeaseLiabilityStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseLiabilityCurrentStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseLiabilityNoncurrentStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList',
        'us-gaap:OperatingLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList'
    }
    
    # Check if the required extensible list or balance sheet location axis is used
    flagged = []
    for _, fact in relevant_facts.iterrows():
        qname = fact['prefix'] + ':' + fact['concept']
        context_ref = fact['context_ref']
        
        # Check if the fact is numeric
        if not fact['is_numeric']:
            continue
        
        # Check if the fact is associated with an extensible list
        extensible_list = lists[lists['concept'].isin(extensible_lists)]
        if not extensible_list.empty:
            extensible_list = extensible_list[extensible_list['context_ref'] == context_ref]
            if not extensible_list.empty:
                continue
        
        # Check if the fact is associated with the balance sheet location axis
        balance_sheet_axis = re.search(r'us-gaap:BalanceSheetLocationAxis=us-gaap:.*Member', fact['dimensions'])
        if balance_sheet_axis:
            balance_sheet_members = re.findall(r'us-gaap:BalanceSheetLocationAxis=us-gaap:([A-Za-z0-9_]+)Member', fact['dimensions'])
            if len(balance_sheet_members) >= 2:
                continue
        
        # If none of the above, flag the fact
        flagged.append({"qname": qname, "context_ref": context_ref})
    
    return flagged