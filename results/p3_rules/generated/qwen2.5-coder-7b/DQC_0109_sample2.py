import pandas as pd
import re

def check(facts, lists, concepts):
    flagged = []
    
    # Define allowed risk types for each benchmark
    allowed_risk_types = {
        "SalesRevenueNetMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "SalesRevenueProductLineMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "SalesRevenueSegmentMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "RevenueFromContractWithCustomerMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "RevenueFromContractWithCustomerProductAndServiceBenchmarkMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "RevenueFromContractWithCustomerSegmentBenchmarkMember": ["GeographicConcentrationRiskMember", "CustomerConcentrationRiskMember", "ProductConcentrationRiskMember", "RevenueFromRightsConcentrationRiskMember", "GovernmentContractsConcentrationRiskMember", "SupplierConcentrationRiskMember"],
        "AccountsReceivableMember": ["CreditConcentrationRiskMember", "GeographicConcentrationRiskMember"],
        "CostOfGoodsTotalMember": ["GeographicConcentrationRiskMember", "SupplierConcentrationRiskMember", "ProductConcentrationRiskMember", "LaborForceConcentrationRiskMember"]
    }
    
    for index, row in facts.iterrows():
        if row['concept'] == 'ConcentrationRiskPercentage1':
            dimensions = row['dimensions'].split(';') if row['dimensions'] else []
            benchmark_axis = next((dim for dim in dimensions if 'ConcentrationRiskByBenchmarkAxis' in dim), None)
            risk_type_axis = next((dim for dim in dimensions if 'ConcentrationRiskByTypeAxis' in dim), None)
            value = row['value']
            
            # Part 1 - 9565
            if not dimensions and value != 1:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
            
            # Part 2- 9566
            if benchmark_axis and risk_type_axis:
                continue
            elif not (benchmark_axis or risk_type_axis) and value == 1:
                continue
            else:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
            
            # Part 3- 9567
            if benchmark_axis and not risk_type_axis:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
            
            # Part 4- 9568
            if not benchmark_axis and risk_type_axis:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
            
            # Part 5- 9569
            if benchmark_axis and risk_type_axis:
                if value != 1 and len(dimensions) != 3:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
                elif value == 1 and len(dimensions) == 3:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
            
            # Part 6- 9570
            if benchmark_axis and risk_type_axis:
                benchmark_member = re.search(r'=(.*?)(?=\s|$)', benchmark_axis).group(1)
                risk_type_member = re.search(r'=(.*?)(?=\s|$)', risk_type_axis).group(1)
                if benchmark_member == 'SalesRevenueNetMember' and risk_type_member != 'SupplierConcentrationRiskMember':
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
            
            # Part 7- 9571
            if benchmark_axis:
                benchmark_member = re.search(r'=(.*?)(?=\s|$)', benchmark_axis).group(1)
                if benchmark_member in ['CustomerConcentrationRiskMember', 'AccountsReceivableMember']:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
            
            # Part 8- 9572
            if risk_type_axis:
                risk_type_member = re.search(r'=(.*?)(?=\s|$)', risk_type_axis).group(1)
                if risk_type_member in ['CustomerConcentrationRiskMember', 'AccountsReceivableMember']:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
    
    return flagged