import pandas as pd
from datetime import datetime, timedelta

def check(facts, lists, concepts):
    flagged = []
    current_date = datetime.now()
    reporting_period = current_date - timedelta(days=15*30)  # Approximate 15 months

    lease_asset_concepts = {
        'FinanceLeaseLiability': 'FinanceLeaseLiabilityStatementOfFinancialPositionExtensibleList',
        'FinanceLeaseLiabilityCurrent': 'FinanceLeaseLiabilityCurrentStatementOfFinancialPositionExtensibleList',
        'FinanceLeaseLiabilityNoncurrent': 'FinanceLeaseLiabilityNoncurrentStatementOfFinancialPositionExtensibleList',
        'FinanceLeaseRightOfUseAsset': 'FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList',
        'OperatingLeaseRightOfUseAsset': 'OperatingLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList'
    }

    for index, row in facts.iterrows():
        concept_name = row['concept']
        if concept_name in lease_asset_concepts:
            if pd.to_datetime(row['end']) < reporting_period:
                continue

            if concept_name in ['FinanceLeaseLiability', 'FinanceLeaseLiabilityCurrent', 'FinanceLeaseLiabilityNoncurrent']:
                if 'us-gaap:BalanceSheetLocationAxis' not in row['dimensions']:
                    flagged.append({"qname": f"{row['prefix']}:{concept_name}", "context_ref": row['context_ref']})
            else:
                if 'us-gaap:BalanceSheetLocationAxis' in row['dimensions']:
                    axis_values = row['dimensions'].split(';')
                    if len(axis_values) < 3:
                        flagged.append({"qname": f"{row['prefix']}:{concept_name}", "context_ref": row['context_ref']})

    return flagged