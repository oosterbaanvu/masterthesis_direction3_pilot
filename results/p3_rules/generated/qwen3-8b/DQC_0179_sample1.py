import pandas as pd
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    
    # Component 10139: Check for prohibited axes
    prohibited_axes = {
        'AwardTypeAxis', 'srt:TitleOfIndividualAxis', 'srt:CurrencyAxis',
        'srt:RangeAxis', 'AwardDateAxis', 'StatementEquityComponentsAxis',
        'FairValueByAssetClassAxis', 'RelatedPartyTransactionsByRelatedPartyAxis',
        'SubsidiarySaleOfStockAxis', 'DebtInstrumentAxis', 'LongtermDebtTypeAxis'
    }
    prohibited_extensions = {
        'DividendDeclarationDateAxis', 'DividendDeclaredAxis',
        'DividendsDeclaredTypeAxis', 'DistributionsPaymentDateAxis'
    }
    
    for _, fact in facts.iterrows():
        concept = f"{fact['prefix']}:{fact['concept']}"
        dimensions = fact['dimensions'].split(';') if fact['dimensions'] else []
        axis_members = [dim.split('=')[0] for dim in dimensions]
        
        if any(axis in prohibited_axes for axis in axis_members):
            flagged.append({"qname": concept, "context_ref": fact['context_ref']})
        
        if any(axis in prohibited_extensions for axis in axis_members):
            flagged.append({"qname": concept, "context_ref": fact['context_ref']})
    
    # Component 10140: Check consecutive dates
    date_concepts = {
        'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear',
        'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear',
        'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'
    }
    
    date_facts = facts[facts['concept'].isin([c.split(':')[-1] for c in date_concepts])]
    
    for _, fact in date_facts.iterrows():
        concept = f"{fact['prefix']}:{fact['concept']}"
        if fact['period_type'] == 'instant':
            date = datetime.fromisoformat(fact['start'])
        else:
            date = datetime.fromisoformat(fact['start'])
        
        if concept in date_concepts:
            if any(c in date_concepts for c in date_facts['concept']):
                dates = [datetime.fromisoformat(fact['start']) for _, fact in date_facts.iterrows()]
                for i in range(1, len(dates)):
                    if dates[i] < dates[i-1]:
                        flagged.append({"qname": concept, "context_ref": fact['context_ref']})
    
    # Component 10141: Check inline scale for CommonStockDividendsPerShareDeclared
    common_stock_concept = 'us-gaap:CommonStockDividendsPerShareDeclared'
    common_stock_facts = facts[facts['concept'] == common_stock_concept]
    
    for _, fact in common_stock_facts.iterrows():
        if fact['decimals'] and int(fact['decimals']) > 0:
            flagged.append({"qname": common_stock_concept, "context_ref": fact['context_ref']})
    
    # Component 10142: Check period context for CommonStockDividendsPerShareDeclared
    common_stock_facts = facts[facts['concept'] == 'us-gaap:CommonStockDividendsPerShareDeclared']
    preferred_stock_facts = facts[facts['concept'] == 'us-gaap:PreferredStockDividendsPerShareDeclared']
    
    reporting_periods = set()
    for _, fact in common_stock_facts.iterrows():
        if fact['period_type'] == 'duration':
            reporting_periods.add((fact['start'], fact['end']))
    for _, fact in preferred_stock_facts.iterrows():
        if fact['period_type'] == 'duration':
            reporting_periods.add((fact['start'], fact['end']))
    
    for _, fact in common_stock_facts.iterrows():
        if fact['period_type'] == 'duration':
            if (fact['start'], fact['end']) not in reporting_periods:
                flagged.append({"qname": 'us-gaap:CommonStockDividendsPerShareDeclared', "context_ref": fact['context_ref']})
    
    # Component 10143: Check for multiple uses of same concept on same DividendsAxis member
    dividends_axis = 'DividendsAxis'
    dividends_members = set()
    for _, fact in facts.iterrows():
        if fact['dimensions']:
            for dim in fact['dimensions'].split(';'):
                if dim.startswith(dividends_axis):
                    member = dim.split('=')[1]
                    dividends_members.add((member, fact['concept']))
    
    for member, concept in dividends_members:
        count = sum(1 for _, fact in facts.iterrows() if fact['dimensions'] and 
                    any(dim.startswith(dividends_axis) and dim.split('=')[1] == member for dim in fact['dimensions'].split(';')) and 
                    fact['concept'] == concept)
        if count > 1:
            flagged.append({"qname": concept, "context_ref": fact['context_ref']})
    
    # Component 10144: Check context date for DividendsPayableAmountPerShare
    payable_concept = 'us-gaap:DividendsPayableAmountPerShare'
    payable_facts = facts[facts['concept'] == payable_concept]
    
    for _, fact in payable_facts.iterrows():
        if fact['period_type'] == 'instant':
            context_date = datetime.fromisoformat(fact['start'])
        else:
            context_date = datetime.fromisoformat(fact['start'])
        
        if fact['period_type'] == 'instant':
            payment_date = datetime.fromisoformat(fact['start'])
        else:
            payment_date = datetime.fromisoformat(fact['start'])
        
        if context_date > payment_date:
            flagged.append({"qname": payable_concept, "context_ref": fact['context_ref']})
    
    # Component 10151: Check for use of dividend dates without DividendsAxis
    date_concepts = {
        'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear',
        'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear',
        'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'
    }
    
    for _, fact in facts.iterrows():
        if fact['concept'] in [c.split(':')[-1] for c in date_concepts]:
            if not fact['dimensions'] or not any(dim.startswith('DividendsAxis') for dim in fact['dimensions'].split(';')):
                flagged.append({"qname": f"{fact['prefix']}:{fact['concept']}", "context_ref": fact['context_ref']})
    
    return flagged