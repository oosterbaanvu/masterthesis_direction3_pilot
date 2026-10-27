import pandas as pd
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []

    # Component 10139
    invalid_axes = {
        'us-gaap:AwardTypeAxis',
        'srt:TitleOfIndividualAxis',
        'srt:CurrencyAxis',
        'srt:RangeAxis',
        'us-gaap:AwardDateAxis',
        'us-gaap:StatementEquityComponentsAxis',
        'us-gaap:FairValueByAssetClassAxis',
        'us-gaap:RelatedPartyTransactionsByRelatedPartyAxis',
        'us-gaap:SubsidiarySaleOfStockAxis',
        'us-gaap:DebtInstrumentAxis',
        'us-gaap:LongtermDebtTypeAxis'
    }
    invalid_extension_elements = {
        'us-gaap:DividendDeclarationDateAxis',
        'us-gaap:DividendDeclaredAxis',
        'us-gaap:DividendsDeclaredTypeAxis',
        'us-gaap:DistributionsPaymentDateAxis'
    }

    for index, row in facts.iterrows():
        concept = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        dimensions = set(row['dimensions'].split(';') if row['dimensions'] else [])

        if concept in {'us-gaap:DividendsPayableAmountPerShare', 'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear', 'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear', 'us-gaap:DividendPayableDateToBePaidDayMonthAndYear', 'us-gaap:CommonStockDividendsPerShareDeclared', 'us-gaap:PreferredStockDividendsPerShareDeclared'}:
            if any(axis in dimensions for axis in invalid_axes):
                flagged.append({"qname": concept, "context_ref": context_ref})
            if any(element in dimensions for element in invalid_extension_elements):
                flagged.append({"qname": concept, "context_ref": context_ref})

    # Component 10140
    date_concepts = {
        'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear',
        'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear',
        'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'
    }

    date_facts = facts[facts['concept'].isin(date_concepts)]
    date_facts = date_facts.sort_values(by=['context_ref', 'start'])

    for i in range(1, len(date_facts)):
        if date_facts.iloc[i]['start'] < date_facts.iloc[i-1]['start']:
            flagged.append({"qname": date_facts.iloc[i]['prefix'] + ':' + date_facts.iloc[i]['concept'], "context_ref": date_facts.iloc[i]['context_ref']})

    # Component 10141
    dividend_concepts = {
        'us-gaap:CommonStockDividendsPerShareDeclared',
        'us-gaap:PreferredStockDividendsPerShareDeclared'
    }

    dividend_facts = facts[facts['concept'].isin(dividend_concepts)]
    for index, row in dividend_facts.iterrows():
        concept = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        if row['decimals'] and int(row['decimals']) > 0:
            flagged.append({"qname": concept, "context_ref": context_ref})

    # Component 10142
    for index, row in dividend_facts.iterrows():
        concept = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        period_type = row['period_type']
        start = row['start']
        end = row['end']
        if period_type == 'duration' and (end - start).days < 5 and (end - start).days != 90:
            flagged.append({"qname": concept, "context_ref": context_ref})

    # Component 10143
    dividends_axis_facts = facts[facts['dimensions'].str.contains('us-gaap:DividendsAxis')]
    for index, row in dividends_axis_facts.iterrows():
        concept = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        dimensions = set(row['dimensions'].split(';') if row['dimensions'] else [])
        if concept in {'us-gaap:DividendsPreferredStockCash', 'us-gaap:DividendsCommonStockCash'} and len(dimensions.intersection({'us-gaap:DividendsAxis'})) > 1:
            flagged.append({"qname": concept, "context_ref": context_ref})

    # Component 10144
    for index, row in dividend_facts.iterrows():
        concept = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        start = row['start']
        if concept == 'us-gaap:DividendsPayableAmountPerShare' and start < datetime.strptime('2022-08-03', '%Y-%m-%d'):
            flagged.append({"qname": concept, "context_ref": context_ref})

    # Component 10151
    for index, row in facts.iterrows():
        concept = row['prefix'] + ':' + row['concept']
        context_ref = row['context_ref']
        dimensions = set(row['dimensions'].split(';') if row['dimensions'] else [])
        if concept in {'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear', 'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear', 'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'} and not dimensions.intersection({'us-gaap:DividendsAxis'}):
            flagged.append({"qname": concept, "context_ref": context_ref})

    return flagged