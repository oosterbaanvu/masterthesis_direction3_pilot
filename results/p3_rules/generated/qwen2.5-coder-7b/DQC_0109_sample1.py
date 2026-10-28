import pandas as pd
import re
import math
from datetime import datetime

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
        'CostOfGoodsTotalMember': ['GeographicConcentrationRiskMember', 'SupplierConcentrationRiskMember', 'ProductConcentrationRiskMember', 'LaborForceConcentrationRiskMember'],
        'RevenueFromContractWithCustomerProductAndServiceBenchmarkMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember'],
        'RevenueFromContractWithCustomerSegmentBenchmarkMember': ['GeographicConcentrationRiskMember', 'CustomerConcentrationRiskMember', 'ProductConcentrationRiskMember', 'RevenueFromRightsConcentrationRiskMember', 'GovernmentContractsConcentrationRiskMember', 'SupplierConcentrationRiskMember']
    }

    labor_force_concentration_risk_member = 'LaborForceConcentrationRiskMember'
    unionized_employees_concentration_risk_member = 'UnionizedEmployeesConcentrationRiskMember'

    for index, fact in facts.iterrows():
        if fact['concept'] == 'ConcentrationRiskPercentage1':
            dimensions = fact['dimensions'].split(';') if fact['dimensions'] else []
            benchmark_axis = next((d.split('=')[1] for d in dimensions if 'ConcentrationRiskByBenchmarkAxis' in d), None)
            risk_type_axis = next((d.split('=')[1] for d in dimensions if 'ConcentrationRiskByTypeAxis' in d), None)
            major_customers_axis = next((d.split('=')[1] for d in dimensions if 'MajorCustomersAxis' in d), None)
            statement_geographical_axis = next((d.split('=')[1] for d in dimensions if 'StatementGeographicalAxis' in d), None)

            if fact['value'] != 1:
                if not benchmark_axis or not risk_type_axis:
                    flagged.append({'qname': f"{fact['prefix']}:{fact['concept']}", 'context_ref': fact['context_ref']})
                elif benchmark_axis == 'LaborForceConcentrationRiskMember' and risk_type_axis == 'UnionizedEmployeesConcentrationRiskMember':
                    pass
                elif benchmark_axis == 'LaborForceConcentrationRiskMember' and risk_type_axis != 'UnionizedEmployeesConcentrationRiskMember':
                    flagged.append({'qname': f"{fact['prefix']}:{fact['concept']}", 'context_ref': fact['context_ref']})
                elif benchmark_axis != 'LaborForceConcentrationRiskMember' and risk_type_axis == 'UnionizedEmployeesConcentrationRiskMember':
                    flagged.append({'qname': f"{fact['prefix']}:{fact['concept']}", 'context_ref': fact['context_ref']})
                elif benchmark_axis != 'LaborForceConcentrationRiskMember' and risk_type_axis != 'UnionizedEmployeesConcentrationRiskMember':
                    if benchmark_axis and risk_type_axis:
                        if benchmark_axis not in valid_benchmark_risk_pairs or risk_type_axis not in valid_benchmark_risk_pairs[benchmark_axis]:
                            flagged.append({'qname': f"{fact['prefix']}:{fact['concept']}", 'context_ref': fact['context_ref']})
                    else:
                        flagged.append({'qname': f"{fact['prefix']}:{fact['concept']}", 'context_ref': fact['context_ref']})

    return flagged