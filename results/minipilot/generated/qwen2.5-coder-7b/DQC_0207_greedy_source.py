import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    for axis in ['EquitySecuritiesByIndustryAxis', 'InvestmentTypeAxis', 'InvestmentIssuerAffiliationAxis', 'InvestmentIssuerNameAxis', 'StatementGeographicalAxis']:
        # Select facts with the BDC subtotals
        bdc_facts = facts[(facts['concept'] == 'InvestmentOwnedAtFairValue') & (facts['dimensions'].str.contains(axis))]
        # Select facts with the BDC subtotals and more dimensions
        bdc_facts_and_more = facts[(facts['concept'] == 'InvestmentOwnedAtFairValue') & (facts['dimensions'].str.contains(axis + r'\b'))]
        
        # Check if the BDC subtotals are less than the BDC subtotals with more dimensions
        for bdc_fact, bdc_fact_and_more in zip(bdc_facts, bdc_facts_and_more):
            if bdc_fact['value'] < bdc_fact_and_more['value']:
                flagged.append({"qname": f"{bdc_fact['prefix']}:{bdc_fact['concept']}", "context_ref": bdc_fact['context_ref']})
                flagged.append({"qname": f"{bdc_fact_and_more['prefix']}:{bdc_fact_and_more['concept']}", "context_ref": bdc_fact_and_more['context_ref']})
    
    return flagged