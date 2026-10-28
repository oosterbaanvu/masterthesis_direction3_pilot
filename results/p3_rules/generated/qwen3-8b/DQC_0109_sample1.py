import pandas as pd
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    # Define the allowed risk types per benchmark
    benchmark_risk_map = {
        'SalesRevenueNetMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'SalesRevenueProductLineMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'SalesRevenueSegmentMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerProductAndServiceBenchmarkMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerSegmentBenchmarkMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'AccountsReceivableMember': ['CreditConcentrationRiskMember', 'GeographicConcentrationRiskMember'],
        'CostOfGoodsTotalMember': ['GeographicConcentrationRiskMember', 'SupplierConcentrationRiskMember', 'ProductConcentrationRiskMember', 'LaborForceConcentrationRiskMember']
    }
    
    # Define exceptions for part 5
    exempt_risk_types = {'LaborForceConcentrationRiskMember', 'UnionizedEmployeesConcentrationRiskMember'}
    
    # Process each fact
    for index, row in facts.iterrows():
        prefix, concept = row['prefix'], row['concept']
        qname = f"{prefix}:{concept}"
        context_ref = row['context_ref']
        dimensions = row['dimensions'].split(';') if row['dimensions'] else []
        value = row['value']
        
        # Check if the concept is ConcentrationRiskPercentage1
        if concept != 'ConcentrationRiskPercentage1':
            continue
        
        # Part 1: Check if value is not 1 and no dimensions
        if not dimensions and value != 1:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 2: Check if dimensions are missing both required axes
        required_axes = ['ConcentrationRiskByBenchmarkAxis', 'ConcentrationRiskByTypeAxis']
        has_required_axes = all(axis in [d.split('=')[0] for d in dimensions] for axis in required_axes)
        if not has_required_axes and value != 1:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 3: Check if missing ConcentrationRiskByBenchmarkAxis but has ConcentrationRiskByTypeAxis
        has_benchmark = any(d.split('=')[0] == 'ConcentrationRiskByBenchmarkAxis' for d in dimensions)
        has_type = any(d.split('=')[0] == 'ConcentrationRiskByTypeAxis' for d in dimensions)
        if has_type and not has_benchmark:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 4: Check if missing ConcentrationRiskByTypeAxis but has ConcentrationRiskByBenchmarkAxis
        if has_benchmark and not has_type:
            flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 5: Check if both axes are present but no third axis unless value is 1
        if has_benchmark and has_type:
            third_axis = any(d.split('=')[0] not in ['ConcentrationRiskByBenchmarkAxis', 'ConcentrationRiskByTypeAxis'] for d in dimensions)
            if not third_axis and value != 1:
                # Check for exempt risk types
                risk_type = [d.split('=')[1] for d in dimensions if d.split('=')[0] == 'ConcentrationRiskByTypeAxis'][0]
                if risk_type in exempt_risk_types:
                    continue
                flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 6: Check if benchmark and risk type are consistent
        if has_benchmark and has_type:
            benchmark = [d.split('=')[1] for d in dimensions if d.split('=')[0] == 'ConcentrationRiskByBenchmarkAxis'][0]
            risk_type = [d.split('=')[1] for d in dimensions if d.split('=')[0] == 'ConcentrationRiskByTypeAxis'][0]
            if benchmark not in benchmark_risk_map.get(risk_type, []) and risk_type not in ['ExtensionRiskTypeMember']:
                flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 7: Check if benchmark matches US GAAP taxonomy
        if has_benchmark:
            benchmark = [d.split('=')[1] for d in dimensions if d.split('=')[0] == 'ConcentrationRiskByBenchmarkAxis'][0]
            if benchmark not in lists['allowed_benchmark_members']:
                flagged.append({"qname": qname, "context_ref": context_ref})
        
        # Part 8: Check if risk type matches US GAAP taxonomy
        if has_type:
            risk_type = [d.split('=')[1] for d in dimensions if d.split('=')[0] == 'ConcentrationRiskByTypeAxis'][0]
            if risk_type not in lists['allowed_risk_type_members']:
                flagged.append({"qname": qname, "context_ref": context_ref})
    
    return flagged