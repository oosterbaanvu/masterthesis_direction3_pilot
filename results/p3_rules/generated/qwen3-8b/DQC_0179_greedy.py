import pandas as pd
import numpy as np
import re
from datetime import datetime

def check(facts, lists, concepts):
    flagged = []
    
    # Component 10139: Check for inappropriate axis usage
    forbidden_axes = {
        'AwardTypeAxis', 'srt:TitleOfIndividualAxis', 'srt:CurrencyAxis',
        'srt:RangeAxis', 'AwardDateAxis', 'StatementEquityComponentsAxis',
        'FairValueByAssetClassAxis', 'RelatedPartyTransactionsByRelatedPartyAxis',
        'SubsidiarySaleOfStockAxis', 'DebtInstrumentAxis', 'LongtermDebtTypeAxis'
    }
    forbidden_extensions = {
        'DividendDeclarationDateAxis', 'DividendDeclaredAxis',
        'DividendsDeclaredTypeAxis', 'DistributionsPaymentDateAxis'
    }
    
    for _, fact in facts.iterrows():
        qname = f"{fact['prefix']}:{fact['concept']}"
        dimensions = fact['dimensions'].split(';') if fact['dimensions'] else []
        axis_members = [d.split('=')[0] for d in dimensions]
        
        if any(axis in forbidden_axes for axis in axis_members):
            flagged.append({"qname": qname, "context_ref": fact['context_ref']})
        
        if any(axis in forbidden_extensions for axis in axis_members):
            flagged.append({"qname": qname, "context_ref": fact['context_ref']})
    
    # Component 10140: Check for consecutive dates
    date_concepts = {
        'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear',
        'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear',
        'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'
    }
    
    date_facts = facts[facts['concept'].isin(date_concepts)]
    date_facts = date_facts.sort_values(by=['context_ref', 'concept'])
    
    for _, row in date_facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        date_str = row['value'] if not pd.isna(row['value']) else None
        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            if flagged and flagged[-1]['qname'] == qname:
                continue
            if flagged and flagged[-1]['context_ref'] == row['context_ref']:
                continue
            if flagged and flagged[-1]['qname'] in date_concepts:
                prev_date = datetime.strptime(flagged[-1]['qname'], "%Y-%m-%d")
                if date < prev_date:
                    flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    # Component 10141: Check for inline scale > 0
    scale_concept = 'us-gaap:CommonStockDividendsPerShareDeclared'
    scale_facts = facts[facts['concept'] == scale_concept]
    
    for _, row in scale_facts.iterrows():
        if row['decimals'] and int(row['decimals']) > 0:
            flagged.append({"qname": scale_concept, "context_ref": row['context_ref']})
    
    # Component 10142: Check for appropriate period context
    period_concepts = {
        'us-gaap:CommonStockDividendsPerShareDeclared',
        'us-gaap:PreferredStockDividendsPerShareDeclared'
    }
    
    period_facts = facts[facts['concept'].isin(period_concepts)]
    period_facts = period_facts.sort_values(by=['context_ref', 'concept'])
    
    reporting_periods = []
    for _, row in period_facts.iterrows():
        if row['period_type'] == 'duration':
            start = datetime.strptime(row['start'], "%Y-%m-%d")
            end = datetime.strptime(row['end'], "%Y-%m-%d")
            reporting_periods.append((start, end))
    
    for _, row in period_facts.iterrows():
        if row['period_type'] == 'duration':
            start = datetime.strptime(row['start'], "%Y-%m-%d")
            end = datetime.strptime(row['end'], "%Y-%m-%d")
            if not any((start >= r[0] and end <= r[1]) for r in reporting_periods):
                flagged.append({"qname": row['concept'], "context_ref": row['context_ref']})
    
    # Component 10143: Check for duplicate concepts on same axis member
    axis_member = 'DividendsAxis'
    dividend_facts = facts[facts['dimensions'].str.contains(axis_member)]
    
    for _, row in dividend_facts.iterrows():
        qname = f"{row['prefix']}:{row['concept']}"
        if any(fact['concept'] == qname for fact in dividend_facts if fact['context_ref'] == row['context_ref']):
            flagged.append({"qname": qname, "context_ref": row['context_ref']})
    
    # Component 10144: Check for context date after payable date
    payable_concept = 'us-gaap:DividendsPayableAmountPerShare'
    payable_facts = facts[facts['concept'] == payable_concept]
    
    for _, row in payable_facts.iterrows():
        if row['period_type'] == 'instant':
            context_date = datetime.strptime(row['start'], "%Y-%m-%d")
        else:
            context_date = datetime.strptime(row['end'], "%Y-%m-%d")
        
        if row['value'] is not None and row['value'] > 0:
            if context_date > datetime.strptime('2021-06-30', "%Y-%m-%d"):
                flagged.append({"qname": payable_concept, "context_ref": row['context_ref']})
    
    # Component 10151: Check for missing DividendsAxis with date concepts
    date_concepts = {
        'us-gaap:DividendsPayableDateDeclaredDayMonthAndYear',
        'us-gaap:DividendsPayableDateOfRecordDayMonthAndYear',
        'us-gaap:DividendPayableDateToBePaidDayMonthAndYear'
    }
    
    for _, row in facts.iterrows():
        if row['concept'] in date_concepts:
            if not any(dimension.startswith('DividendsAxis') for dimension in row['dimensions'].split(';')):
                flagged.append({"qname": row['concept'], "context_ref": row['context_ref']})
    
    return flagged