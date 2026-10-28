import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    
    # Define the concepts to check for each rule
    monetary_concepts = [
        'EffectiveIncomeTaxRateReconciliationFdiiAmount',
        'EffectiveIncomeTaxRateReconciliationBeatAmount',
        'EffectiveIncomeTaxRateReconciliationGiltiAmount',
        'EffectiveIncomeTaxRateReconciliationCrossBorderOtherAmount',
        'EffectiveIncomeTaxRateReconciliationCrossBorderTaxEffectAmount'
    ]
    
    percentage_concepts = [
        'EffectiveIncomeTaxRateReconciliationBeatPercent',
        'EffectiveIncomeTaxRateReconciliationGiltiPercent',
        'EffectiveIncomeTaxRateReconciliationFdiiPercent',
        'EffectiveIncomeTaxRateReconciliationCrossBorderOtherPercent',
        'EffectiveIncomeTaxRateReconciliationCrossBorderTaxEffectPercent'
    ]
    
    # Rule 10928: Check for monetary concepts tagged with IncomeTaxAuthorityAxis
    for concept in monetary_concepts:
        mask = (facts['concept'] == concept) & (facts['dimensions'].str.contains('us-gaap:IncomeTaxAuthorityAxis'))
        flagged.extend(facts.loc[mask, ['prefix', 'concept', 'context_ref']].apply(lambda x: {'qname': f"{x['prefix']}:{x['concept']}", 'context_ref': x['context_ref']}, axis=1).tolist())
    
    # Rule 10929: Check for percentage/rate concepts tagged with IncomeTaxAuthorityAxis
    for concept in percentage_concepts:
        mask = (facts['concept'] == concept) & (facts['dimensions'].str.contains('us-gaap:IncomeTaxAuthorityAxis'))
        flagged.extend(facts.loc[mask, ['prefix', 'concept', 'context_ref']].apply(lambda x: {'qname': f"{x['prefix']}:{x['concept']}", 'context_ref': x['context_ref']}, axis=1).tolist())
    
    # Rule 10930: Check for IncomeTaxAuthorityAxis used without TaxJurisdictionOfDomicileExtensibleEnumeration
    mask = facts['dimensions'].str.contains('us-gaap:IncomeTaxAuthorityAxis') & facts['concept'].isin(monetary_concepts + percentage_concepts)
    if mask.any():
        missing_tax_jurisdiction = facts.loc[mask, ['context_ref']].drop_duplicates().reset_index(drop=True)
        flagged.extend(missing_tax_jurisdiction.apply(lambda x: {'qname': 'us-gaap:TaxJurisdictionOfDomicileExtensibleEnumeration', 'context_ref': x['context_ref']}, axis=1).tolist())
    
    return flagged