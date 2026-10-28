import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    for index, row in facts.iterrows():
        concept_name = row['concept']
        value = row['value']
        if concept_name.endswith('EffectiveIncomeTaxRateReconciliationAtFederalStatutoryIncomeTaxRate'):
            continue
        if concept_name in ['InvestmentOwnedPercentOfNetAssets']:
            continue
        if pd.isna(value):
            continue
        if value > 10:
            flagged.append({"qname": f"{row['prefix']}:{concept_name}", "context_ref": row['context_ref']})
    return flagged