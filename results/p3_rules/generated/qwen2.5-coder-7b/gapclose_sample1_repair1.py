def check(facts, concepts, lists):
    flagged = []

    # Rule 1: Check for incorrect sign on financial facts
    for index, row in facts.iterrows():
        concept_metadata = concepts[(concepts['tag'] == row['concept']) & (concepts['balance'] == row['crdr']) & (concepts['iord'] == row['period_type'])]
        if not concept_metadata.empty and concept_metadata['datatype'].str.contains('monetary').any():
            if (concept_metadata['crdr'] == 'C' and row['value'] < 0) or (concept_metadata['crdr'] == 'D' and row['value'] > 0):
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "IncorrectSign"})

    # Rule 2: Check for values that are too large
    for index, row in facts.iterrows():
        if row['value'] > 1e15:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "ValueTooLarge"})

    # Rule 3: Check for missing facts
    for index, row in facts.iterrows():
        concept_metadata = concepts[(concepts['tag'] == row['concept']) & (concepts['balance'] == row['crdr']) & (concepts['iord'] == row['period_type'])]
        if concept_metadata.empty:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "MissingConcept"})

    # Rule 4: Check for period swap
    for index, row in facts.iterrows():
        if row['period_type'] == 'duration':
            start_date = pd.to_datetime(row['start'])
            end_date = pd.to_datetime(row['end'])
            if start_date > end_date:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "PeriodSwap"})

    # Rule 5: Check for incorrect tag
    for index, row in facts.iterrows():
        concept_metadata = concepts[(concepts['tag'] == row['concept']) & (concepts['balance'] == row['crdr']) & (concepts['iord'] == row['period_type'])]
        if not concept_metadata.empty and concept_metadata['tag'].iloc[0] != row['concept']:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref'], "rule": "IncorrectTag"})

    return flagged