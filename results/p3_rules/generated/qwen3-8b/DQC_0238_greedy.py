import pandas as pd
import numpy as np
import re

def check(facts, lists, concepts):
    # Filter facts tagged with ScheduleOfSegmentReportingInformationBySegmentTextBlock
    schedule_facts = facts[facts['concept'] == 'ScheduleOfSegmentReportingInformationBySegmentTextBlock']
    
    # Check if any fact is tagged with StatementBusinessSegmentsAxis
    statement_business_segments_axis_facts = facts[facts['dimensions'].str.contains('StatementBusinessSegmentsAxis', na=False)]
    
    # If there are schedule facts and no statement business segments axis facts, flag them
    if not schedule_facts.empty and statement_business_segments_axis_facts.empty:
        flagged = schedule_facts.to_dict('records')
    else:
        flagged = []
    
    return flagged