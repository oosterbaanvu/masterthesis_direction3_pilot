import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    
    # Component 10139: Check invalid axis usage
    invalid_axes = {
        'us-gaap:AwardDateAxis', 'us-gaap:StatementEquityComponentsAxis',
        'us-gaap:FairValueByAssetClassAxis', 'us-gaap:RelatedPartyTransactionsByRelatedPartyAxis',
        'us-gaap:SubsidiarySaleOfStockAxis', 'us-gaap:DebtInstrumentAxis',
        'us-gaap:LongtermDebtTypeAxis', 'srt:TitleOfIndividualAxis', 'srt:CurrencyAxis',
        'srt:RangeAxis'
    }
    invalid_extensions = {
        'us-gaap:DividendDeclarationDateAxis', 'us-gaap:DividendDeclaredAxis',
        'us-gaap:DividendsDeclaredTypeAxis', 'us-gaap:DistributionsPaymentDateAxis'
    }
    
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        dimensions = fact['dimensions'].split(';') if fact['dimensions'] else []
        axis = [d.split('=')[0] for d in dimensions]
        
        if any(axis_qname in invalid_axes for axis_qname in axis):
            flagged.append({"qname": qname, "context_ref": fact['context_ref']})
        
        if any(axis_qname in invalid_extensions for axis_qname in axis):
            flagged.append({"qname": qname, "context_ref": fact['context_ref']})
    
    # Component 10140: Check consecutive dates
    date_concepts = {
        'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear',
        'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'
    }
    date_facts = facts[facts['concept'].isin(date_concepts)]
    
    date_facts['date'] = pd.to_datetime(date_facts['start'].combine_first(date_facts['end']))
    
    for _, row in date_facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['concept'] == 'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear':
            next_date = date_facts[date_facts['concept'] == 'us-gaap:DividendPayableDateToBePaidDayMonthAndYear']
            if not next_date.empty and row['date'] >= next_date['date'].iloc[0]:
                flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    # Component 10141: Check inline scale for CommonStockDividendsPerShareDeclared
    common_stock_concept = 'us-gaap:CommonStockDividendsPerShareDeclared'
    common_stock_facts = facts[facts['concept'] == common_stock_concept]
    
    for _, row in common_stock_facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['decimals'] and int(row['decimals']) > 0:
            flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    # Component 10142: Check period context for CommonStock and PreferredStock
    preferred_stock_concept = 'us-gaap:PreferredStockDividendsPerShareDeclared'
    common_stock_facts = facts[facts['concept'].isin([common_stock_concept, preferred_stock_concept])]
    
    period_contexts = set()
    for _, row in common_stock_facts.iterrows():
        period_contexts.add(row['context_ref'])
    
    report_periods = set()
    for _, row in facts.iterrows():
        if row['period_type'] == 'duration':
            report_periods.add(row['context_ref'])
    
    for _, row in common_stock_facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['context_ref'] not in report_periods:
            flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    # Component 10143: Check duplicate use of DividendsAxis with same member
    dividends_axis = 'us-gaap:DividendsAxis'
    dividend_members = set()
    for _, row in facts.iterrows():
        if row['dimensions']:
            for dim in row['dimensions'].split(';'):
                if dim.startswith(dividends_axis):
                    member = dim.split('=')[1]
                    dividend_members.add((member, row['concept'], row['context_ref']))
    
    for member, concept, context in dividend_members:
        if len([d for d in dividend_members if d[0] == member and d[1] == concept]) > 1:
            flagged.append({"qname": f"{row['prefix']}:{concept}", "context_ref": context})
    
    # Component 10144: Check context date after payable date
    payable_concept = 'us-gaap:DividendsPayableAmountPerShare'
    payable_facts = facts[facts['concept'] == payable_concept]
    
    for _, row in payable_facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if row['period_type'] == 'instant':
            context_date = row['start']
        else:
            context_date = row['start']
        
        payable_date = row['start'] if row['concept'] == 'us-gaap:DividendsPayableDateToBePaidDayMonthAndYear' else row['end']
        
        if context_date > payable_date:
            flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    # Component 10151: Check use of dividend dates without DividendsAxis
    date_concepts = {
        'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear',
        'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear',
        'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'
    }
    date_facts = facts[facts['concept'].isin(date_concepts)]
    
    for _, row in date_facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if not any(dim.startswith('us-gaap:DividendsAxis') for dim in row['dimensions'].split(';') if row['dimensions']):
            flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    return flagged