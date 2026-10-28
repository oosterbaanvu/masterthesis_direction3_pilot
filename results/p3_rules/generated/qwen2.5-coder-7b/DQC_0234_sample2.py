import pandas as pd

def check(facts, lists, concepts):
    flagged = []

    # Define the lists of domestic-only income tax reconciliation concepts
    domestic_monetary_concepts = {
        'us-gaap:EffectiveIncomeTaxRateReconciliationFdiiAmount',
        'us-gaap:EffectiveIncomeTaxRateReconciliationBeatAmount',
        'us-gaap:EffectiveIncomeTaxRateReconciliationGiltiAmount',
        'us-gaap:EffectiveIncomeTaxRateReconciliationCrossBorderOtherAmount',
        'us-gaap:EffectiveIncomeTaxRateReconciliationCrossBorderTaxEffectAmount'
    }

    domestic_rate_concepts = {
        'us-gaap:EffectiveIncomeTaxRateReconciliationBeatPercent',
        'us-gaap:EffectiveIncomeTaxRateReconciliationGiltiPercent',
        'us-gaap:EffectiveIncomeTaxRateReconciliationFdiiPercent',
        'us-gaap:EffectiveIncomeTaxRateReconciliationCrossBorderOtherPercent',
        'us-gaap:EffectiveIncomeTaxRateReconciliationCrossBorderTaxEffectPercent'
    }

    # Check Rule 10928 and 10929
    for concept in domestic_monetary_concepts.union(domestic_rate_concepts):
        filtered_facts = facts[(facts['concept'] == concept) & (facts['dimensions'].str.contains('us-gaap:IncomeTaxAuthorityAxis'))]
        for _, fact in filtered_facts.iterrows():
            flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref']})

    # Check Rule 10930
    filtered_facts = facts[facts['dimensions'].str.contains('us-gaap:IncomeTaxAuthorityAxis')]
    for _, fact in filtered_facts.iterrows():
        if 'us-gaap:TaxJurisdictionOfDomicileExtensibleEnumeration' not in fact['dimensions']:
            flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref']})

    return flagged