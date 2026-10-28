import pandas as pd
import numpy as np

def check(facts, lists, concepts):
    flagged = []
    dim_equivalents = lists['DQC_011_ListOfElements']
    
    for index, row in dim_equivalents.iterrows():
        line_item = facts[(facts['prefix'] + ':' + facts['concept']) == row['LineItem']]
        dim_line_item = facts[(facts['prefix'] + ':' + facts['concept']) == row['DimensionLineItem']]
        
        if not line_item.empty and not dim_line_item.empty:
            line_item_value = line_item['value'].values[0]
            dim_line_item_value = dim_line_item['value'].values[0]
            weight = row['Weight']
            
            if not np.isnan(line_item_value) and not np.isnan(dim_line_item_value):
                if not np.isclose(line_item_value, dim_line_item_value * weight, atol=1e-2):
                    flagged.append({"qname": row['LineItem'], "context_ref": line_item['context_ref'].values[0]})
                    flagged.append({"qname": row['DimensionLineItem'], "context_ref": dim_line_item['context_ref'].values[0]})
    
    return flagged