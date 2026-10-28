import pandas as pd

def check(facts, lists, concepts):
    flagged = []

    # Base axes to be avoided
    base_axes = {
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

    # Extension elements to be avoided
    extension_elements = {
        'us-gaap:DividendDeclarationDateAxis',
        'us-gaap:DividendDeclaredAxis',
        'us-gaap:DividendsDeclaredTypeAxis',
        'us-gaap:DistributionsPaymentDateAxis'
    }

    # Component 10139: Check base axis and extension elements
    for index, row in facts.iterrows():
        if row['concept'] in {'us-gaap:DividendsPayableAmountPerShare', 'us-gaap:DividendsPreferredStockCash'}:
            dimensions = set(row['dimensions'].split(';'))
            if dimensions.intersection(base_axes) or dimensions.intersection(extension_elements):
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    # Component 10140: Check consecutive dates
    date_columns = {
        'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear',
        'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear',
        'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'
    }
    for date_col in date_columns:
        date_facts = facts[facts['concept'] == date_col]
        for i in range(1, len(date_facts)):
            if date_facts.iloc[i]['value'] < date_facts.iloc[i - 1]['value']:
                flagged.append({"qname": f"{date_facts.iloc[i]['prefix']}:{date_facts.iloc[i]['concept']}", "context_ref": date_facts.iloc[i]['context_ref']})

    # Component 10141: Check scale for CommonStockDividendsPerShareDeclared
    for index, row in facts.iterrows():
        if row['concept'] == 'us-gaap:CommonStockDividendsPerShareDeclared' and row['inline_scale'] > 0:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    # Component 10142: Check period context for dividends
    for index, row in facts.iterrows():
        if row['concept'] in {'us-gaap:CommonStockDividendsPerShareDeclared', 'us-gaap:PreferredStockDividendsPerShareDeclared'}:
            period = row['start'] if row['period_type'] == 'duration' else row['end']
            if pd.to_datetime(period) < pd.to_datetime('2021-09-25'):
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    # Component 10143: Check DividendsAxis usage
    dividends_axis_facts = facts[facts['dimensions'].str.contains('us-gaap:DividendsAxis')]
    for index, row in dividends_axis_facts.iterrows():
        concept = row['concept']
        context_ref = row['context_ref']
        if dividends_axis_facts[(dividends_axis_facts['concept'] == concept) & (dividends_axis_facts['context_ref'] == context_ref)].shape[0] > 1:
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    # Component 10144: Check DividendsPayableAmountPerShare context
    for index, row in facts.iterrows():
        if row['concept'] == 'us-gaap:DividendsPayableAmountPerShare' and pd.to_datetime(row['start']) > pd.to_datetime('2021-06-30'):
            flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    # Component 10151: Check DividendsAxis for dates
    for date_col in date_columns:
        date_facts = facts[facts['concept'] == date_col]
        for index, row in date_facts.iterrows():
            if not 'us-gaap:DividendsAxis' in row['dimensions']:
                flagged.append({"qname": f"{row['prefix']}:{row['concept']}", "context_ref": row['context_ref']})

    return flagged