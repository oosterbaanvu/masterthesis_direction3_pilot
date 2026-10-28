import pandas as pd
import numpy as np
import re

def check(facts, lists, concepts):
    # Define the monetary and percentage concepts for rules 10928 and 10929
    monetary_concepts = {
        'EffectiveIncomeTaxRateReconciliationFdiiAmount',
        'EffectiveIncomeTaxRateReconciliationBeatAmount',
        'EffectiveIncomeTaxRateReconciliationGiltiAmount',
        'EffectiveIncomeTaxRateReconciliationCrossBorderOtherAmount',
        'EffectiveIncomeTaxRateReconciliationCrossBorderTaxEffectAmount'
    }
    
    percentage_concepts = {
        'EffectiveIncomeTaxRateReconciliationBeatPercent',
        'EffectiveIncomeTaxRateReconciliationGiltiPercent',
        'EffectiveIncomeTaxRateReconciliationFdiiPercent',
        'EffectiveIncomeTaxRateReconciliationCrossBorderOtherPercent',
        'EffectiveIncomeTaxRateReconciliationCrossBorderTaxEffectPercent'
    }
    
    # Rule 10928: Check for monetary concepts with IncomeTaxAuthorityAxis
    rule_10928_issues = facts[
        (facts['concept'].isin(monetary_concepts)) &
        (facts['dimensions'].str.contains('IncomeTaxAuthorityAxis=')) &
        (~facts['nil'])
    ][['qname', 'context_ref']]
    
    # Rule 10929: Check for percentage concepts with IncomeTaxAuthorityAxis
    rule_10929_issues = facts[
        (facts['concept'].isin(percentage_concepts)) &
        (facts['dimensions'].str.contains('IncomeTaxAuthorityAxis=')) &
        (~facts['nil'])
    ][['qname', 'context_ref']]
    
    # Rule 10930: Check if any fact with IncomeTaxAuthorityAxis is missing TaxJurisdictionOfDomicileExtensibleEnumeration
    # First, find all facts with IncomeTaxAuthorityAxis
    facts_with_income_tax_authority = facts[
        facts['dimensions'].str.contains('IncomeTaxAuthorityAxis=')
    ]
    
    # Check if TaxJurisdictionOfDomicileExtensibleEnumeration is present in the filing
    tax_jurisdiction_concept = 'TaxJurisdictionOfDomicileExtensibleEnumeration'
    tax_jurisdiction_present = facts[
        (facts['concept'] == tax_jurisdiction_concept) &
        (~facts['nil'])
    ].shape[0] > 0
    
    # If there are facts with IncomeTaxAuthorityAxis and TaxJurisdictionOfDomicileExtensibleEnumeration is missing, flag
    rule_10930_issues = pd.DataFrame()
    if not tax_jurisdiction_present and not facts_with_income_tax_authority.empty:
        rule_10930_issues = facts_with_income_tax_authority[['qname', 'context_ref']]
    
    # Combine all issues
    flagged = pd.concat([rule_10928_issues, rule_10929_issues, rule_10930_issues]).dropna().to_dict('records')
    return flagged