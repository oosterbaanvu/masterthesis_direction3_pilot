"""Baseline controls for SEC filings: generic schema-level rules and statistical checks.

Every control takes a fact table (dqstress.sec.xbrl_instance.parse_instance) and returns the facts it
flags as (qname, context_ref) pairs, the same output contract as the AI-written rules.
"""
