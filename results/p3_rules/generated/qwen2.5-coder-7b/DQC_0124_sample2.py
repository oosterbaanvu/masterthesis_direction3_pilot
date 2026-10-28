import pandas as pd
import datetime

def check(facts, lists, concepts):
    flagged = []
    current_date = datetime.datetime.now()
    reporting_period = current_date - datetime.timedelta(days=477)  # 15 months ago

    lease_assets = [
        'FinanceLeaseLiability',
        'FinanceLeaseLiabilityCurrent',
        'FinanceLeaseLiabilityNoncurrent',
        'FinanceLeaseRightOfUseAsset',
        'OperatingLeaseRightOfUseAsset'
    ]

    lease_asset_extensible_lists = {
        'FinanceLeaseLiability': 'FinanceLeaseLiabilityStatementOfFinancialPositionExtensibleList',
        'FinanceLeaseLiabilityCurrent': 'FinanceLeaseLiabilityCurrentStatementOfFinancialPositionExtensibleList',
        'FinanceLeaseLiabilityNoncurrent': 'FinanceLeaseLiabilityNoncurrentStatementOfFinancialPositionExtensibleList',
        'FinanceLeaseRightOfUseAsset': 'FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList',
        'OperatingLeaseRightOfUseAsset': 'OperatingLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList'
    }

    for concept in lease_assets:
        lease_facts = facts[(facts['concept'] == concept) & (pd.to_datetime(facts['end']) >= reporting_period)]
        if not lease_facts.empty:
            extensible_list = lease_asset_extensible_lists.get(concept)
            if extensible_list:
                extensible_facts = lease_facts[lease_facts['prefix'] + ':' + 'extensibleList'] == extensible_list
                if not extensible_facts.empty:
                    flagged.extend(extensible_facts[['prefix', 'concept', 'context_ref']].to_dict(orient='records'))
                else:
                    balance_sheet_facts = lease_facts[lease_facts['dimensions'].str.contains('us-gaap:BalanceSheetLocationAxis')]
                    if not balance_sheet_facts.empty and balance_sheet_facts.shape[0] < 2:
                        flagged.extend(balance_sheet_facts[['prefix', 'concept', 'context_ref']].to_dict(orient='records'))
            else:
                balance_sheet_facts = lease_facts[lease_facts['dimensions'].str.contains('us-gaap:BalanceSheetLocationAxis')]
                if not balance_sheet_facts.empty and balance_sheet_facts.shape[0] < 2:
                    flagged.extend(balance_sheet_facts[['prefix', 'concept', 'context_ref']].to_dict(orient='records'))
    
    return flagged