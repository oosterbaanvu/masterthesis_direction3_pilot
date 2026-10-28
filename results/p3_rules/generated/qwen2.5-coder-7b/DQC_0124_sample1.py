import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    
    # Define the relevant concepts and their corresponding list concepts
    relevant_concepts = {
        'us-gaap:FinanceLeaseLiability': 'us-gaap:FinanceLeaseLiabilityStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseLiabilityCurrent': 'us-gaap:FinanceLeaseLiabilityCurrentStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseLiabilityNoncurrent': 'us-gaap:FinanceLeaseLiabilityNoncurrentStatementOfFinancialPositionExtensibleList',
        'us-gaap:FinanceLeaseRightOfUseAsset': 'us-gaap:FinanceLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList',
        'us-gaap:OperatingLeaseRightOfUseAsset': 'us-gaap:OperatingLeaseRightOfUseAssetStatementOfFinancialPositionExtensibleList'
    }
    
    # Get the current reporting period
    reporting_period = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    # Filter facts to include only those within the last 15 months
    end_date_filter = pd.to_datetime(facts['end']) >= pd.to_datetime(reporting_period) - pd.DateOffset(years=1, months=3)
    filtered_facts = facts[end_date_filter]
    
    for concept, list_concept in relevant_concepts.items():
        # Filter facts for the current concept
        concept_facts = filtered_facts[(filtered_facts['prefix'] + ':' + filtered_facts['concept']) == concept]
        
        # Check if the concept facts are present in the list facts
        for index, row in concept_facts.iterrows():
            if list_concept not in lists['concept'].values:
                flagged.append({"qname": concept, "context_ref": row['context_ref']})
            else:
                # Check if the concept facts are tagged with the balance sheet location axis
                balance_sheet_facts = concept_facts[(concept_facts['dimensions'].str.contains('us-gaap:BalanceSheetLocationAxis'))]
                if len(balance_sheet_facts) == 1:
                    flagged.append({"qname": concept, "context_ref": row['context_ref']})
    
    return flagged