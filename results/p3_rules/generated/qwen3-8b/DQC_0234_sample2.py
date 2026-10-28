import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    
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
    
    # Rule 10928: Check for non-nil monetary concepts with IncomeTaxAuthorityAxis
    for _, fact in facts.iterrows():
        if fact['concept'] in monetary_concepts and not fact['nil']:
            if re.search(r'IncomeTaxAuthorityAxis=.*', fact['dimensions']):
                flagged.append({
                    'qname': f"{fact['prefix']}:{fact['concept']}",
                    'context_ref': fact['context_ref']
                })
    
    # Rule 10929: Check for non-nil rate concepts with IncomeTaxAuthorityAxis
    for _, fact in facts.iterrows():
        if fact['concept'] in rate_concepts and not fact['nil']:
            if re.search(r'IncomeTaxAuthorityAxis=.*', fact['dimensions']):
                flagged.append({
                    'qname': f"{fact['prefix']}:{fact['concept']}",
                    'context_ref': fact['context_ref']
                })
    
    # Rule 10930: Check for IncomeTaxAuthorityAxis without TaxJurisdictionOfDomicileExtensibleEnumeration
    for _, fact in facts.iterrows():
        if re.search(r'IncomeTaxAuthorityAxis=.*', fact['dimensions']) and not fact['nil']:
            jurisdiction_fact = facts[
                (facts['concept'] == 'TaxJurisdictionOfDomicileExtensibleEnumeration') &
                (facts['prefix'] == 'us-gaap') &
                (facts['nil'] is False)
            ]
            if jurisdiction_fact.empty:
                flagged.append({
                    'qname': f"{fact['prefix']}:{fact['concept']}",
                    'context_ref': fact['context_ref']
                })
    
    return flagged