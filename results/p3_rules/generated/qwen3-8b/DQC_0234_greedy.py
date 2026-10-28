import pandas as pd
import re

def check(facts, lists, concepts):
    # Define the concepts for each rule
    monetary_concepts = {
        'EffectiveIncomeTaxRateReconciliationFdiiAmount',
        'EffectiveIncomeTaxRateReconciliationBeatAmount',
        'EffectiveIncomeTaxRateReconciliationGiltiAmount',
        'EffectiveIncomeTaxRateReconciliationCrossBorderOtherAmount',
        'EffectiveIncomeTaxRateReconciliationCrossBorderTaxEffectAmount'
    }
    
    rate_concepts = {
        'EffectiveIncomeTaxRateReconciliationBeatPercent',
        'EffectiveIncomeTaxRateReconciliationGiltiPercent',
        'EffectiveIncomeTaxRateReconciliationFdiiPercent',
        'EffectiveIncomeTaxRateReconciliationCrossBorderOtherPercent',
        'EffectiveIncomeTaxRateReconciliationCrossBorderTaxEffectPercent'
    }
    
    # Filter facts for the rules
    flagged = []
    
    # Rule 10928: Check monetary concepts with IncomeTaxAuthorityAxis
    for _, fact in facts.iterrows():
        if fact['concept'] in monetary_concepts and fact['dimensions']:
            if re.search(r'IncomeTaxAuthorityAxis=', fact['dimensions']):
                flagged.append({
                    'qname': f"{fact['prefix']}:{fact['concept']}",
                    'context_ref': fact['context_ref']
                })
    
    # Rule 10929: Check rate concepts with IncomeTaxAuthorityAxis
    for _, fact in facts.iterrows():
        if fact['concept'] in rate_concepts and fact['dimensions']:
            if re.search(r'IncomeTaxAuthorityAxis=', fact['dimensions']):
                flagged.append({
                    'qname': f"{fact['prefix']}:{fact['concept']}",
                    'context_ref': fact['context_ref']
                })
    
    # Rule 10930: Check if any fact with IncomeTaxAuthorityAxis lacks TaxJurisdictionOfDomicileExtensibleEnumeration
    has_income_tax_authority_axis = facts[facts['dimensions'].str.contains('IncomeTaxAuthorityAxis=', na=False)]
    if not has_income_tax_authority_axis.empty:
        tax_jurisdiction_concept = 'TaxJurisdictionOfDomicileExtensibleEnumeration'
        if tax_jurisdiction_concept not in facts['concept'].values:
            flagged.append({
                'qname': tax_jurisdiction_concept,
                'context_ref': 'N/A'  # No specific context_ref as it's a filing-level check
            })
    
    return flagged