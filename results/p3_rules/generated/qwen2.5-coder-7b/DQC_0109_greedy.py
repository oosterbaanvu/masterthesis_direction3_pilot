import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    valid_benchmark_risk_pairs = {
        'SalesRevenueNetMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'SalesRevenueProductLineMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'SalesRevenueSegmentMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerProductAndServiceBenchmarkMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerSegmentBenchmarkMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'AccountsReceivableMember': ['CreditConcentrationRiskMember', 'GeographicConcentrationRiskMember'],
        'CostOfGoodsTotalMember': ['GeographicConcentrationRiskMember', 'SupplierConcentrationRiskMember', 'ProductConcentrationRiskMember', 'LaborForceConcentrationRiskMember']
    }

    for index, row in facts.iterrows():
        if row['concept'] == 'ConcentrationRiskPercentage1':
            dimensions = row['dimensions'].split(';') if row['dimensions'] else []
            benchmark_axis = next((d.split('=')[1] for d in dimensions if d.startswith('us-gaap:ConcentrationRiskByBenchmarkAxis')), None)
            risk_type_axis = next((d.split('=')[1] for d in dimensions if d.startswith('us-gaap:ConcentrationRiskByTypeAxis')), None)
            third_axis = next((d.split('=')[1] for d in dimensions if d not in ['us-gaap:ConcentrationRiskByBenchmarkAxis', 'us-gaap:ConcentrationRiskByTypeAxis']), None)

            if row['value'] == 1:
                if not benchmark_axis or not risk_type_axis:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
                elif third_axis and third_axis not in ['LaborForceConcentrationRiskMember', 'UnionizedEmployeesConcentrationRiskMember']:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
            else:
                if benchmark_axis and risk_type_axis and third_axis and third_axis not in ['LaborForceConcentrationRiskMember', 'UnionizedEmployeesConcentrationRiskMember']:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
                elif benchmark_axis and risk_type_axis and third_axis is None:
                    flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})
                elif benchmark_axis and risk_type_axis and third_axis in ['LaborForceConcentrationRiskMember', 'UnionizedEmployeesConcentrationRiskMember']:
                    if benchmark_axis not in valid_benchmark_risk_pairs or risk_type_axis not in valid_benchmark_risk_pairs[benchmark_axis]:
                        flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    return flagged