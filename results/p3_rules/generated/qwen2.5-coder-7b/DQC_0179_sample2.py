import pandas as pd
import numpy as np
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []

    # Component 10139
    prohibited_axes = {
        'us-gaap:AwardTypeAxis',
        'srt:TitleOfIndividualAxis',
        'srt:CurrencyAxis',
        'srt:RangeAxis',
        'AwardDateAxis',
        'StatementEquityComponentsAxis',
        'FairValueByAssetClassAxis',
        'RelatedPartyTransactionsByRelatedPartyAxis',
        'SubsidiarySaleOfStockAxis',
        'DebtInstrumentAxis',
        'LongtermDebtTypeAxis',
        'DividendDeclarationDateAxis',
        'DividendDeclaredAxis',
        'DividendsDeclaredTypeAxis',
        'DistributionsPaymentDateAxis'
    }
    for index, row in facts.iterrows():
        if row['concept'] == 'us-gaap:DividendsPayableAmountPerShare' and row['dimensions'] in prohibited_axes:
            flagged.append({'qname': f"{row['prefix']}:{row['concept']}", 'context_ref': row['context_ref']})

    # Component 10140
    date_concepts = ['us-gaap:DividendsPayableDateDeclaredDayMonthAndYear', 'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear', 'us-gaap:DividendPayableDateToBePaidDayMonthAndYear']
    for i in range(len(facts)):
        for j in range(i + 1, len(facts)):
            if facts.iloc[i]['concept'] in date_concepts and facts.iloc[j]['concept'] in date_concepts and facts.iloc[i]['context_ref'] == facts.iloc[j]['context_ref']:
                date1 = datetime.strptime(facts.iloc[i]['text'], '%Y-%m-%d')
                date2 = datetime.strptime(facts.iloc[j]['text'], '%Y-%m-%d')
                if date1 > date2:
                    flagged.append({'qname': f"{facts.iloc[i]['prefix']}:{facts.iloc[i]['concept']}", 'context_ref': facts.iloc[i]['context_ref']})
                    flagged.append({'qname': f"{facts.iloc[j]['prefix']}:{facts.iloc[j]['concept']}", 'context_ref': facts.iloc[j]['context_ref']})

    # Component 10141
    for index, row in facts.iterrows():
        if row['concept'] == 'us-gaap:CommonStockDividendsPerShareDeclared' and row['decimals'] is not None and int(row['decimals']) > 0:
            flagged.append({'qname': f"{row['prefix']}:{row['concept']}", 'context_ref': row['context_ref']})

    # Component 10142
    # This component requires more complex logic to determine valid periods, which is not provided in the rule documentation.

    # Component 10143
    for index, row in facts.iterrows():
        if row['concept'] == 'us-gaap:DividendsPreferredStockCash' and row['dimensions'] == 'DividendsAxis=UMH:DividendPaymentDateFourMember':
            flagged.append({'qname': f"{row['prefix']}:{row['concept']}", 'context_ref': row['context_ref']})

    # Component 10144
    for index, row in facts.iterrows():
        if row['concept'] == 'us-gaap:DividendsPayableAmountPerShare' and row['value'] > 0 and datetime.strptime(facts.loc[facts['context_ref'] == row['context_ref'], 'text'].values[0], '%Y-%m-%d') < datetime.now():
            flagged.append({'qname': f"{row['prefix']}:{row['concept']}", 'context_ref': row['context_ref']})

    # Component 10151
    prohibited_date_concepts = ['us-gaap:DividendsPayableDateDeclaredDayMonthAndYear', 'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear', 'us-gaap:DividendPayableDateToBePaidDayMonthAndYear']
    for index, row in facts.iterrows():
        if row['concept'] in prohibited_date_concepts and row['dimensions'] != 'DividendsAxis':
            flagged.append({'qname': f"{row['prefix']}:{row['concept']}", 'context_ref': row['context_ref']})

    return flagged