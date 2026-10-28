import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    
    # Rule: Check for negative values on debit accounts
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['is_numeric'] and not pd.isna(fact['value']):
            # Get crdr from concepts if available
            concept_row = concepts[concepts['tag'] == fact['concept']]
            if not concept_row.empty:
                crdr = concept_row['crdr'].iloc[0]
                if crdr == 'D' and fact['value'] < 0:
                    flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Negative value on debit account"})
    
    # Rule: Check for positive values on credit accounts
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['is_numeric'] and not pd.isna(fact['value']):
            # Get crdr from concepts if available
            concept_row = concepts[concepts['tag'] == fact['concept']]
            if not concept_row.empty:
                crdr = concept_row['crdr'].iloc[0]
                if crdr == 'C' and fact['value'] > 0:
                    flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Positive value on credit account"})
    
    # Rule: Check for monetary facts with non-numeric values
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        # Get datatype from concepts if available
        concept_row = concepts[concepts['tag'] == fact['concept']]
        if not concept_row.empty:
            datatype = concept_row['datatype'].iloc[0]
            if datatype == 'monetary' and not fact['is_numeric']:
                flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Monetary fact with non-numeric value"})
    
    # Rule: Check for perShare facts with non-numeric values
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        # Get datatype from concepts if available
        concept_row = concepts[concepts['tag'] == fact['concept']]
        if not concept_row.empty:
            datatype = concept_row['datatype'].iloc[0]
            if datatype == 'perShare' and not fact['is_numeric']:
                flagged.append({"qname": qname, "context_ref": context_ref, "rule": "PerShare fact with non-numeric value"})
    
    # Rule: Check for duration facts with instant period type
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['period_type'] == 'duration' and fact['iord'] == 'I':
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Duration fact with instant period type"})
    
    # Rule: Check for instant facts with duration period type
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['period_type'] == 'instant' and fact['iord'] == 'D':
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Instant fact with duration period type"})
    
    # Rule: Check for missing start date on duration facts
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['period_type'] == 'duration' and pd.isna(fact['start']):
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Missing start date on duration fact"})
    
    # Rule: Check for missing end date on duration facts
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['period_type'] == 'duration' and pd.isna(fact['end']):
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Missing end date on duration fact"})
    
    # Rule: Check for invalid date format
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if not pd.isna(fact['start']) and not re.match(r'^\d{4}-\d{2}-\d{2}$', fact['start']):
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Invalid start date format"})
        if not pd.isna(fact['end']) and not re.match(r'^\d{4}-\d{2}-\d{2}$', fact['end']):
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Invalid end date format"})
    
    # Rule: Check for non-numeric values on numeric facts
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['is_numeric'] and pd.isna(fact['value']):
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Numeric fact with missing value"})
    
    # Rule: Check for missing dimensions
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['dimensions'] == '':
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Missing dimensions"})
    
    # Rule: Check for invalid unit
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['unit'] not in ['USD', 'shares', 'pure', 'USD/shares']:
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Invalid unit"})
    
    # Rule: Check for invalid decimals
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if fact['decimals'] not in ['-3', '0', 'INF']:
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Invalid decimals"})
    
    # Rule: Check for missing value on non-numeric facts
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if not fact['is_numeric'] and pd.isna(fact['text']):
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Non-numeric fact with missing text"})
    
    # Rule: Check for invalid text on non-numeric facts
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        if not fact['is_numeric'] and not isinstance(fact['text'], str):
            flagged.append({"qname": qname, "context_ref": context_ref, "rule": "Invalid text on non-numeric fact"})
    
    return flagged