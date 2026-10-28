import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    broader_categories = {
        'EquitySecuritiesByIndustryAxis': ['us-gaap:EquityMember'],
        'InvestmentTypeAxis': ['abc:FirstLienSecuredDebtMember'],
        'InvestmentIssuerAffiliationAxis': ['us-gaap:InvestmentUnaffiliatedIssuerMember'],
        'InvestmentIssuerNameAxis': ['us-gaap:InvestmentUnaffiliatedIssuerMember'],
        'StatementGeographicalAxis': ['us-gaap:US']
    }

    for category, subcategories in broader_categories.items():
        for subcategory in subcategories:
            broader_value = facts[(facts['prefix'] + ':' + facts['concept'] == 'us-gaap:InvestmentOwnedAtFairValue') &
                                 (facts['dimensions'].str.contains(category + '=' + subcategory))].value.sum()
            for subsubcategory in facts[(facts['prefix'] + ':' + facts['concept'] == 'us-gaap:InvestmentOwnedAtFairValue') &
 (facts['dimensions'].str.contains(category + '=' + subcategory))].dimensions.unique():
                subsubcategory_value = facts[(facts['prefix'] + ':' + facts['concept'] == 'us-gaap:InvestmentOwnedAtFairValue') &
 (facts['dimensions'] == subsubcategory)].value.sum()
                if subsubcategory_value > broader_value:
                    flagged.append({"qname": "us-gaap:InvestmentOwnedAtFairValue", "context_ref": subsubcategory})

    return flagged