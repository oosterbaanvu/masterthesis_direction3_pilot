import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    
    # Rule: Check if numeric facts have correct sign based on accounting direction
    for _, fact in facts.iterrows():
        if fact['is_numeric'] and fact['value'] is not np.nan:
            if fact['concept'] in ['Assets', 'AssetsCurrent', 'PropertyPlantAndEquipmentNet', 'InventoryNet', 'AccountsReceivableNetCurrent', 'PrepaidExpenseAndOtherAssetsCurrent', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents', 'CashAndCashEquivalentsAtCarryingValue']:
                if fact['value'] < 0:
                    flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Incorrect sign for asset"})
            elif fact['concept'] in ['Liabilities', 'LiabilitiesCurrent', 'LiabilitiesAndStockholdersEquity', 'AccountsPayableCurrent', 'AccruedLiabilitiesCurrent', 'OtherLiabilitiesNoncurrent', 'OperatingLeaseLiabilityCurrent', 'OperatingLeaseLiabilityNoncurrent']:
                if fact['value'] > 0:
                    flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Incorrect sign for liability"})
            elif fact['concept'] in ['NetIncomeLoss', 'ProfitLoss', 'GrossProfit', 'OperatingIncomeLoss', 'IncomeTaxExpenseBenefit', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'ComprehensiveIncomeNetOfTax', 'NetCashProvidedByUsedInOperatingActivities', 'NetCashProvidedByUsedInFinancingActivities', 'NetCashProvidedByUsedInInvestingActivities', 'OperatingExpenses', 'GeneralAndAdministrativeExpense', 'DepreciationDepletionAndAmortization', 'ResearchAndDevelopmentExpense', 'Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax']:
                if fact['value'] < 0:
                    flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Incorrect sign for income or expense"})
    
    # Rule: Check if period type matches the concept's period type
    for _, fact in facts.iterrows():
        concept_row = concepts[concepts['tag'] == fact['concept']]
        if not concept_row.empty:
            concept_period_type = concept_row['iord'].iloc[0]
            if fact['period_type'] != concept_period_type:
                flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Mismatched period type"})
    
    # Rule: Check if unit matches the concept's data type
    for _, fact in facts.iterrows():
        concept_row = concepts[concepts['tag'] == fact['concept']]
        if not concept_row.empty:
            concept_data_type = concept_row['datatype'].iloc[0]
            if concept_data_type == 'monetary' and fact['unit'] not in ['USD', 'USD/shares']:
                flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Mismatched unit for monetary concept"})
            elif concept_data_type == 'perShare' and fact['unit'] not in ['shares', 'USD/shares']:
                flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Mismatched unit for perShare concept"})
    
    # Rule: Check if context_ref is valid (e.g. not empty or invalid format)
    for _, fact in facts.iterrows():
        if not fact['context_ref'] or not re.match(r'^[a-zA-Z0-9_-]+$', fact['context_ref']):
            flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Invalid context_ref"})
    
    # Rule: Check if dimensions are properly formatted
    for _, fact in facts.iterrows():
        if fact['dimensions']:
            dimensions_list = fact['dimensions'].split(';')
            for dim in dimensions_list:
                if not re.match(r'^[a-zA-Z0-9_]+:[a-zA-Z0-9_]+$', dim):
                    flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Invalid dimension format"})
    
    # Rule: Check if value is not NaN for numeric facts
    for _, fact in facts.iterrows():
        if fact['is_numeric'] and pd.isna(fact['value']):
            flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Missing value for numeric fact"})
    
    # Rule: Check if text is not None for non-numeric facts
    for _, fact in facts.iterrows():
        if not fact['is_numeric'] and fact['text'] is None:
            flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref'], "rule": "Missing text for non-numeric fact"})
    
    return flagged