import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    
    # Define the allowed risk types for each benchmark
    benchmark_allowed_risk_types = {
        'SalesRevenueNetMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'SalesRevenueProductLineMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'SalesRevenueSegmentMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerProductAndServiceBenchmarkMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerSegmentBenchmarkMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'AccountsReceivableMember': ['CreditConcentrationRiskMember', 'GeographicConcentrationRiskMember'],
        'CostOfGoodsTotalMember': ['GeographicConcentrationRiskMember', 'SupplierConcentrationRiskMember', 'ProductConcentrationRiskMember', 'LaborForceConcentrationRiskMember']
    }
    
    # Define the exception members for Part 5
    exception_members = {
        'LaborForceConcentrationRiskMember',
        'UnionizedEmployeesConcentrationRiskMember'
    }
    
    # Process each fact
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        if fact['concept'] != 'ConcentrationRiskPercentage1':
            continue
        
        # Part 1: Check if value is not 1 and no dimensions
        if fact['dimensions'] == '' and not pd.isna(fact['value']) and abs(fact['value'] - 1) > 1e-9:
            flagged.append({
                'qname': qname,
                'context_ref': fact['context_ref']
            })
        
        # Part 2: Check if dimensions are missing both required axes
        if fact['dimensions'] != '':
            dimensions = dict(re.findall(r'(.+?):(.+?)', fact['dimensions']))
            has_type_axis = 'ConcentrationRiskByTypeAxis' in dimensions
            has_benchmark_axis = 'ConcentrationRiskByBenchmarkAxis' in dimensions
            if not (has_type_axis and has_benchmark_axis) and not (pd.isna(fact['value']) or abs(fact['value'] - 1) <= 1e-9):
                flagged.append({
                    'qname': qname,
                    'context_ref': fact['context_ref']
                })
        
        # Part 3: Check if missing ConcentrationRiskByBenchmarkAxis and has ConcentrationRiskByTypeAxis
        if fact['dimensions'] != '':
            dimensions = dict(re.findall(r'(.+?):(.+?)', fact['dimensions']))
            has_type_axis = 'ConcentrationRiskByTypeAxis' in dimensions
            has_benchmark_axis = 'ConcentrationRiskByBenchmarkAxis' in dimensions
            if has_type_axis and not has_benchmark_axis and not (pd.isna(fact['value']) or abs(fact['value'] - 1) <= 1e-9):
                flagged.append({
                    'qname': qname,
                    'context_ref': fact['context_ref']
                })
        
        # Part 4: Check if missing ConcentrationRiskByTypeAxis and has ConcentrationRiskByBenchmarkAxis
        if fact['dimensions'] != '':
            dimensions = dict(re.findall(r'(.+?):(.+?)', fact['dimensions']))
            has_type_axis = 'ConcentrationRiskByTypeAxis' in dimensions
            has_benchmark_axis = 'ConcentrationRiskByBenchmarkAxis' in dimensions
            if has_benchmark_axis and not has_type_axis and not (pd.isna(fact['value']) or abs(fact['value'] - 1) <= 1e-9):
                flagged.append({
                    'qname': qname,
                    'context_ref': fact['context_ref']
                })
        
        # Part 5: Check if has both axes but no third axis unless value is 1
        if fact['dimensions'] != '':
            dimensions = dict(re.findall(r'(.+?):(.+?)', fact['dimensions']))
            has_type_axis = 'ConcentrationRiskByTypeAxis' in dimensions
            has_benchmark_axis = 'ConcentrationRiskByBenchmarkAxis' in dimensions
            has_third_axis = len(dimensions) > 2
            if has_type_axis and has_benchmark_axis and not has_third_axis and not (pd.isna(fact['value']) or abs(fact['value'] - 1) <= 1e-9):
                # Check if the risk type is one of the exceptions
                if dimensions.get('ConcentrationRiskByTypeAxis') in exception_members:
                    continue
                flagged.append({
                    'qname': qname,
                    'context_ref': fact['context_ref']
                })
        
        # Part 6: Check if the benchmark and risk type are compatible
        if fact['dimensions'] != '':
            dimensions = dict(re.findall(r'(.+?):(.+?)', fact['dimensions']))
            has_type_axis = 'ConcentrationRiskByTypeAxis' in dimensions
            has_benchmark_axis = 'ConcentrationRiskByBenchmarkAxis' in dimensions
            if has_type_axis and has_benchmark_axis:
                benchmark = dimensions.get('ConcentrationRiskByBenchmarkAxis')
                risk_type = dimensions.get('ConcentrationRiskByTypeAxis')
                if benchmark in benchmark_allowed_risk_types and risk_type in benchmark_allowed_risk_types[benchmark]:
                    continue
                flagged.append({
                    'qname': qname,
                    'context_ref': fact['context_ref']
                })
        
        # Part 7: Check if the benchmark matches the US GAAP taxonomy
        if fact['dimensions'] != '':
            dimensions = dict(re.findall(r'(.+?):(.+?)', fact['dimensions']))
            has_benchmark_axis = 'ConcentrationRiskByBenchmarkAxis' in dimensions
            if has_benchmark_axis:
                benchmark = dimensions.get('ConcentrationRiskByBenchmarkAxis')
                # Check if the benchmark is in the US GAAP taxonomy
                if not concepts[concepts['tag'] == benchmark].shape[0]:
                    flagged.append({
                        'qname': qname,
                        'context_ref': fact['context_ref']
                    })
        
        # Part 8: Check if the risk type matches the US GAAP taxonomy
        if fact['dimensions'] != '':
            dimensions = dict(re.findall(r'(.+?):(.+?)', fact['dimensions']))
            has_type_axis = 'ConcentrationRiskByTypeAxis' in dimensions
            if has_type_axis:
                risk_type = dimensions.get('ConcentrationRiskByTypeAxis')
                # Check if the risk type is in the US GAAP taxonomy
                if not concepts[concepts['tag'] == risk_type].shape[0]:
                    flagged.append({
                        'qname': qname,
                        'context_ref': fact['context_ref']
                    })
    
    return flagged