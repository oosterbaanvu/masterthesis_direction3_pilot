import pandas as pd

def check(facts, concepts, lists):
    flagged = []

    # Rule 1: Check for wrong signs (Assets and Liabilities should be positive, Equity and Expenses should be negative)
    for _, fact in facts.iterrows():
        if fact['prefix'] + ':' + fact['concept'] in ['us-gaap:Assets', 'us-gaap:Liabilities']:
            if fact['value'] < 0:
                flagged.append({"qname": fact['prefix'] + ':' + fact['concept'], "context_ref": fact['context_ref'], "rule": "WrongSign"})
        elif fact['prefix'] + ':' + fact['concept'] in ['us-gaap:Equity', 'us-gaap:Expenses']:
            if fact['value'] > 0:
                flagged.append({"qname": fact['prefix'] + ':' + fact['concept'], "context_ref": fact['context_ref'], "rule": "WrongSign"})

    # Rule 2: Check for values that break accounting relationships (e.g., Assets = Liabilities + Equity)
    balance_sheet_facts = facts[facts['concept'].isin(['Assets', 'Liabilities', 'Equity'])]
    balance_check = balance_sheet_facts.groupby('context_ref').agg({'value': sum}).reset_index()
    for _, check in balance_check.iterrows():
        if check['value'] < 0:
            flagged.append({"qname": "us-gaap:Equity", "context_ref": check['context_ref'], "rule": "AccountingRelationship"})

    # Rule 3: Check for values assigned to the wrong period (e.g., Operating expenses should be for the same period as revenues)
    for _, fact in facts.iterrows():
        if fact['concept'] == 'OperatingExpenses':
            revenues = facts[(facts['context_ref'] == fact['context_ref']) & (facts['concept'] == 'Revenues')]['value'].values
            if revenues.size > 0 and fact['value'] > revenues[0]:
                flagged.append({"qname": "us-gaap:OperatingExpenses", "context_ref": fact['context_ref'], "rule": "WrongPeriod"})

    # Rule 4: Check for values reported under the wrong element (e.g., Revenue should not be reported as an expense)
    for _, fact in facts.iterrows():
        if fact['concept'] in ['Revenues', 'OperatingIncomeLoss']:
            if 'us-gaap:Expenses' in facts[(facts['context_ref'] == fact['context_ref'])]['concept'].values:
                flagged.append({"qname": fact['prefix'] + ':' + fact['concept'], "context_ref": fact['context_ref'], "rule": "WrongElement"})

    return flagged