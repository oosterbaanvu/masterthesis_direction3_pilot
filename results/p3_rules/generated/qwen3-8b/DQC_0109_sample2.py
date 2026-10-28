import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    # Define the allowed risk types for each benchmark
    benchmark_to_risk_types = {
        "SalesRevenueNetMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "SalesRevenueProductLineMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "SalesRevenueSegmentMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "RevenueFromContractWithCustomerMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "RevenueFromContractWithCustomerProductAndServiceBenchmarkMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "RevenueFromContractWithCustomerSegmentBenchmarkMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "AccountsReceivableMember": ["CreditConcentrationRiskMember", "GeographicConcentrationRiskMember"],
        "CostOfGoodsTotalMember": ["GeographicConcentrationRiskMember", "SupplierConcentrationRiskMember", "ProductConcentrationRiskMember", "LaborForceConcentrationRiskMember"]
    }
    
    # Define the exempt risk types for part 5
    exempt_risk_types = ["LaborForceConcentrationRiskMember", "UnionizedEmployeesConcentrationRiskMember"]
    
    # Process each fact
    flagged = []
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        context_ref = fact['context_ref']
        
        # Part 1: Check if value is not 1 and no dimensions
        if fact['value'] != 1 and not fact['dimensions']:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 2: Check if both dimensions are missing when value is not 1
        if fact['value'] != 1 and not (fact['dimensions'].split(';') if fact['dimensions'] else []):
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 3: Check if only ConcentrationRiskByTypeAxis is present
        if not fact['dimensions']:
            continue
        dimensions = fact['dimensions'].split(';')
        type_axis_present = any(dim.startswith("us-gaap:ConcentrationRiskByTypeAxis=") for dim in dimensions)
        benchmark_axis_present = any(dim.startswith("us-gaap:ConcentrationRiskByBenchmarkAxis=") for dim in dimensions)
        if type_axis_present and not benchmark_axis_present:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 4: Check if only ConcentrationRiskByBenchmarkAxis is present
        if not fact['dimensions']:
            continue
        dimensions = fact['dimensions'].split(';')
        type_axis_present = any(dim.startswith("us-gaap:ConcentrationRiskByTypeAxis=") for dim in dimensions)
        benchmark_axis_present = any(dim.startswith("us-gaap:ConcentrationRiskByBenchmarkAxis=") for dim in dimensions)
        if benchmark_axis_present and not type_axis_present:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 5: Check for third axis if value is not 1
        if not fact['dimensions']:
            continue
        dimensions = fact['dimensions'].split(';')
        type_axis = next((dim.split('=')[1] for dim in dimensions if dim.startswith("us-gaap:ConcentrationRiskByTypeAxis=")), None)
        benchmark_axis = next((dim.split('=')[1] for dim in dimensions if dim.startswith("us-gaap:ConcentrationRiskByBenchmarkAxis=")), None)
        if type_axis and benchmark_axis and fact['value'] != 1 and len(dimensions) < 3:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 6: Check if benchmark and type axis members are compatible
        if not fact['dimensions']:
            continue
        dimensions = fact['dimensions'].split(';')
        type_axis = next((dim.split('=')[1] for dim in dimensions if dim.startswith("us-gaap:ConcentrationRiskByTypeAxis=")), None)
        benchmark_axis = next((dim.split('=')[1] for dim in dimensions if dim.startswith("us-gaap:ConcentrationRiskByBenchmarkAxis=")), None)
        if type_axis and benchmark_axis and benchmark_axis in benchmark_to_risk_types and type_axis not in benchmark_to_risk_types[benchmark_axis]:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 7: Check if benchmark axis member matches US GAAP taxonomy
        if not fact['dimensions']:
            continue
        dimensions = fact['dimensions'].split(';')
        benchmark_axis = next((dim.split('=')[1] for dim in dimensions if dim.startswith("us-gaap:ConcentrationRiskByBenchmarkAxis=")), None)
        if benchmark_axis and benchmark_axis not in lists['allowed_benchmark_members']:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 8: Check if type axis member matches US GAAP taxonomy
        if not fact['dimensions']:
            continue
        dimensions = fact['dimensions'].split(';')
        type_axis = next((dim.split('=')[1] for dim in dimensions if dim.startswith("us-gaap:ConcentrationRiskByTypeAxis=")), None)
        if type_axis and type_axis not in lists['allowed_type_members']:
            flagged.append({"qname": qname, "context_ref": context_ref})
    
    return flagged