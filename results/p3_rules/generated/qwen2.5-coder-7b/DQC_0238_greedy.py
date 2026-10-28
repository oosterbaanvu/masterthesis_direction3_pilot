import pandas as pd

def check(facts, lists, concepts):
    flagged = []
    
    # Check if ScheduleOfSegmentReportingInformationBySegmentTextBlock is present
    text_block_present = facts[facts['concept'] == 'ScheduleOfSegmentReportingInformationBySegmentTextBlock'].shape[0] > 0
    
    if text_block_present:
        # Check if any facts are tagged with StatementBusinessSegmentsAxis
        axis_facts = facts[facts['dimensions'].str.contains('us-gaap:StatementBusinessSegmentsAxis=')]
        
        if axis_facts.shape[0] == 0:
            # Flag all facts that use ScheduleOfSegmentReportingInformationBySegmentTextBlock
            flagged_facts = facts[facts['concept'] == 'ScheduleOfSegmentReportingInformationBySegmentTextBlock']
            flagged.extend(flagged_facts.to_dict(orient='records'))
    
    return flagged