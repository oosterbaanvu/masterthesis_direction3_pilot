import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta

def check(facts, lists, concepts):
    # Define the lease-related concepts and their corresponding extensible list items
    lease_concepts = {
        'us-gaap:FinanceLeaseLiability': 'us-gaap:FinanceLeaseLiabilityStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseLiabilityCurrent': 'us-gaap:FinanceLeaseLiabilityCurrentStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseLiabilityNoncurrent': 'us-gaap:FinanceLeaseLiabilityNoncurrentStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseRightOfUseAsset': 'us-gaap:FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList',
        'us-gaap:OperatingLeaseRightOfUseAsset': 'us-gaap:OperatingLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList'
    }
    
    # Define the current reporting period end date (assuming today's date)
    current_reporting_period_end = datetime.now()
    
    # Filter facts within the 15-month window
    facts = facts[facts['period'].apply(lambda x: x >= (current_reporting_period_end - timedelta(days=15*30)))].copy()
    
    flagged = []
    
    # Check each lease-related concept
    for concept, extensible_list in lease_concepts.items():
        # Get all facts for the current concept
        concept_facts = facts[facts['qname'] == concept]
        
        if concept_facts.empty:
            continue
        
        # Check if the concept is used in the filing
        for _, fact_row in concept_facts.iterrows():
            # Check if the concept is used but not included in the financial statements
            if not lists[lists['qname'] == extensible_list].empty:
                # Check if the extensible list or balance sheet location axis is used
                if not lists[lists['qname'] == extensible_list].empty:
                    # Check if the extensible list is used
                    extensible_list_facts = lists[lists['qname'] == extensible_list]
                    if not extensible_list_facts.empty:
                        # Check if the extensible list is used with the concept
                        if any(extensible_list_facts['qname'].str.contains(concept)):
                            continue  # Extensible list is used, no issue
                        else:
                            # Check if the balance sheet location axis is used with at least two account members
                            balance_sheet_location_facts = facts[facts['dimensions'].str.contains('us-gaap:BalanceSheetLocationAxis')]
                            if len(balance_sheet_location_facts) >= 2:
                                continue  # Balance sheet location axis is used with multiple accounts, no issue
                            else:
                                # Neither extensible list nor balance sheet location axis is used
                                flagged.append({
 'qname': fact_row['qname'],
 'context_ref': fact_row['context_ref']
                                })
                else:
                    # Check if the balance sheet location axis is used with at least two account members
                    balance_sheet_location_facts = facts[facts['dimensions'].str.contains('us-gaap:BalanceSheetLocationAxis')]
                    if len(balance_sheet_location_facts) >= 2:
                        continue  # Balance sheet location axis is used with multiple accounts, no issue
                    else:
                        # Neither extensible list nor balance sheet location axis is used
                        flagged.append({
                            'qname': fact_row['qname'],
                            'context_ref': fact_row['context_ref']
                        })
            else:
                # Check if the concept is used but not included in the financial statements
                flagged.append({
                    'qname': fact_row['qname'],
                    'context_ref': fact_row['context_ref']
                })
    
    return flagged