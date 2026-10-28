def check(facts, lists, concepts):
    import pandas as pd
    import numpy as np
    import re
    from datetime import datetime
    
    flagged = []
    
    # Rule: Check if numeric facts have correct sign based on concept's credit/debit
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['is_numeric'] and not pd.isna(fact['value']) and not pd.isna(fact['concept']):
            concept_row = concepts[concepts['tag'] == fact['concept']]
            if not concept_row.empty:
                crdr = concept_row['crdr'].iloc[0]
                if crdr == 'C' and fact['value'] < 0:
                    flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Wrong sign for credit item"})
                elif crdr == 'D' and fact['value'] > 0:
                    flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Wrong sign for debit item"})
    
    # Rule: Check for scale issues (values 1000 times too large)
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['is_numeric'] and not pd.isna(fact['value']) and not pd.isna(fact['concept']):
            concept_row = concepts[concepts['tag'] == fact['concept']]
            if not concept_row.empty:
                datatype = concept_row['datatype'].iloc[0]
                if datatype in ['monetary', 'perShare'] and not pd.isna(fact['value']):
                    if fact['value'] > 1e12 and not re.match(r'^\d+$', str(int(fact['value']))):
                        flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Scale issue (value 1000 times too large)"})
    
    # Rule: Check for period consistency (same period type for related elements)
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['is_numeric'] and not pd.isna(fact['value']) and not pd.isna(fact['concept']):
            concept_row = concepts[concepts['tag'] == fact['concept']]
            if not concept_row.empty:
                iord = concept_row['iord'].iloc[0]
                if iord == 'D' and fact['period_type'] != 'duration':
                    flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Wrong period type for duration concept"})
                elif iord == 'I' and fact['period_type'] != 'instant':
                    flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Wrong period type for instant concept"})
    
    # Rule: Check for missing facts (value is NaN)
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if pd.isna(fact['value']):
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Missing fact value"})
    
    # Rule: Check for value changes (compare with previous period)
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['is_numeric'] and not pd.isna(fact['value']) and not pd.isna(fact['concept']):
            concept_row = concepts[concepts['tag'] == fact['concept']]
            if not concept_row.empty:
                if concept_row['tlabel'].iloc[0] in ['Net Income (Loss)', 'Comprehensive Income (Loss)']:
                    prev_fact = facts[(facts['prefix'] == fact['prefix']) & (facts['concept'] == fact['concept']) & (facts['context_ref'] != context_ref)]
                    if not prev_fact.empty:
                        prev_value = prev_fact['value'].iloc[0]
                        if abs(fact['value'] - prev_value) / abs(prev_value) > 0.5:
                            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Large change in value compared to previous period"})
    
    # Rule: Check for value consistency with related elements (e.g., assets = liabilities + equity)
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['is_numeric'] and not pd.isna(fact['value']) and not pd.isna(fact['concept']):
            concept_row = concepts[concepts['tag'] == fact['concept']]
            if not concept_row.empty:
                if concept_row['tlabel'].iloc[0] == 'Assets':
                    liabilities = facts[(facts['prefix'] == 'us-gaap') & (facts['concept'] == 'Liabilities') & (facts['context_ref'] == context_ref)]
                    equity = facts[(facts['prefix'] == 'us-gaap') & (facts['concept'] == 'StockholdersEquity') & (facts['context_ref'] == context_ref)]
                    if not liabilities.empty and not equity.empty:
                        liabilities_value = liabilities['value'].iloc[0]
                        equity_value = equity['value'].iloc[0]
                        if abs(fact['value'] - liabilities_value - equity_value) > 1e6:
                            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Inconsistent assets with liabilities and equity"})
    
    return flagged