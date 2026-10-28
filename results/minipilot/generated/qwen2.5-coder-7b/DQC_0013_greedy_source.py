import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    precondition_value = "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest.value"
    precondition_criteria = "> 0"
    element_label = "Effective Income Tax Rate Reconciliation, Tax Credit, Percent"
    namespace = "us-gaap"
    element_name = "EffectiveIncomeTaxRateReconciliationTaxCredits"
    
    # Calculate the precondition value
    income_before_tax = facts[facts['concept'] == 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest']['value'].max()
    if pd.isna(income_before_tax):
        income_before_tax = facts[facts['concept'] == 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments']['value'].max()
        if pd.isna(income_before_tax):
            income_before_tax = facts[facts['concept'] == 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic']['value'].max()
            if pd.isna(income_before_tax):
                income_before_tax = facts[facts['concept'] == 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesForeign']['value'].max()
                if pd.isna(income_before_tax):
                    income_before_tax = 0
    
    # Check for negative values
    for index, row in facts.iterrows():
        if row['concept'] in lists['DQC_0013_ListOfElements']['elementName'].values and income_before_tax > 0:
            if row['value'] < 0:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    return flagged