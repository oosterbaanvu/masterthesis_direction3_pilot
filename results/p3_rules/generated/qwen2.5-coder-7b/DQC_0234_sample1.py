def check(facts, lists, concepts):
    flagged = []

    # Get the list of domestic-only concepts for monetary and percentage/rate
    domestic_monetary_concepts = lists.get("DQC.US.0234.10928", [])
    domestic_rate_concepts = lists.get("DQC.US.0234.10929", [])

    # Get the concept metadata for TaxJurisdictionOfDomicileExtensibleEnumeration
    tax_jurisdiction_concept = concepts.get("TaxJurisdictionOfDomicileExtensibleEnumeration", None)

    # Rule 10928: Check for domestic monetary concepts tagged with IncomeTaxAuthorityAxis
    for index, row in facts[facts['dimensions'].str.contains('us-gaap:IncomeTaxAuthorityAxis')].iterrows():
        concept = row['concept']
        if concept in domestic_monetary_concepts:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    # Rule 10929: Check for domestic rate/percent concepts tagged with IncomeTaxAuthorityAxis
    for index, row in facts[facts['dimensions'].str.contains('us-gaap:IncomeTaxAuthorityAxis')].iterrows():
        concept = row['concept']
        if concept in domestic_rate_concepts:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    # Rule 10930: Check for IncomeTaxAuthorityAxis used without TaxJurisdictionOfDomicileExtensibleEnumeration
    for index, row in facts[facts['dimensions'].str.contains('us-gaap:IncomeTaxAuthorityAxis')].iterrows():
        if tax_jurisdiction_concept is None or row['concept'] != 'TaxJurisdictionOfDomicileExtensibleEnumeration':
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    return flagged