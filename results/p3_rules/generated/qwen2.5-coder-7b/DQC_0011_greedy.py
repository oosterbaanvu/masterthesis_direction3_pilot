import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    list_of_elements = lists['DQC_011_ListOfElements']
    
    for index, row in facts.iterrows():
        fact_qname = f"{row['prefix']}:{row['concept']}"
        fact_value = row['value']
        fact_dimensions = row['dimensions']
        
        if fact_dimensions == '':
            for _, list_row in list_of_elements.iterrows():
                if list_row['LineItem'] == fact_qname:
                    dimension_fact_qname = list_row['DimensionLineItem']
                    dimension_fact_value = list_row['Weight'] * fact_value
                    dimension_fact_dimensions = f"{list_row['Axis']}={list_row['Member']}"
                    
                    dimension_fact = facts[(facts['prefix'] + ':' + facts['concept']) == dimension_fact_qname] & (facts['dimensions'] == dimension_fact_dimensions)
                    if not dimension_fact.empty:
                        dimension_fact_value = dimension_fact.iloc[0]['value']
                        if not np.isclose(fact_value, dimension_fact_value):
                            flagged.append({"qname": fact_qname, "context_ref": row['context_ref']})
                            flagged.append({"qname": dimension_fact_qname, "context_ref": dimension_fact.iloc[0]['context_ref']})
    
    return flagged