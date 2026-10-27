"""Parse an XBRL instance document (as extracted by EDGAR, '<doc>_htm.xml') into a fact table.

One row per fact with its concept, period, dimensions, unit, decimals and value.
This is the common input for every control in the SEC experiments, so that the
official DQC rules, generic rules and AI-written rules all see the same facts.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from lxml import etree

XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
SKIP_NAMESPACES = {XBRLI, "http://www.xbrl.org/2003/linkbase", "http://www.w3.org/1999/xlink"}


def _prefix_for(namespace: str, nsmap: dict) -> str:
    for prefix, uri in nsmap.items():
        if uri == namespace and prefix:
            return prefix
    return namespace.rsplit("/", 2)[-2] if "/" in namespace else namespace


def _contexts(root) -> dict[str, dict]:
    contexts = {}
    for ctx in root.iter(f"{{{XBRLI}}}context"):
        period = ctx.find(f"{{{XBRLI}}}period")
        instant = period.findtext(f"{{{XBRLI}}}instant")
        start = period.findtext(f"{{{XBRLI}}}startDate")
        end = period.findtext(f"{{{XBRLI}}}endDate")
        members = []
        for member in ctx.iter(f"{{{XBRLDI}}}explicitMember"):
            members.append(f"{member.get('dimension')}={member.text.strip()}")
        for member in ctx.iter(f"{{{XBRLDI}}}typedMember"):
            members.append(f"{member.get('dimension')}={''.join(member.itertext()).strip()}")
        contexts[ctx.get("id")] = {
            "period_type": "instant" if instant else "duration",
            "start": (start or "").strip() or None,
            "end": (instant or end or "").strip() or None,
            "dimensions": ";".join(sorted(members)),
        }
    return contexts


def _units(root) -> dict[str, str]:
    units = {}
    for unit in root.iter(f"{{{XBRLI}}}unit"):
        divide = unit.find(f"{{{XBRLI}}}divide")
        if divide is not None:
            num = divide.find(f"{{{XBRLI}}}unitNumerator").findtext(f"{{{XBRLI}}}measure")
            den = divide.find(f"{{{XBRLI}}}unitDenominator").findtext(f"{{{XBRLI}}}measure")
            units[unit.get("id")] = f"{num.split(':')[-1]}/{den.split(':')[-1]}"
        else:
            measures = [m.text.split(":")[-1] for m in unit.findall(f"{{{XBRLI}}}measure")]
            units[unit.get("id")] = "*".join(measures)
    return units


def parse_instance(path: Path) -> pd.DataFrame:
    root = etree.parse(str(path), etree.XMLParser(huge_tree=True, remove_comments=True)).getroot()
    contexts, units = _contexts(root), _units(root)
    rows = []
    for element in root:
        if not isinstance(element.tag, str):
            continue
        namespace, local = element.tag[1:].split("}") if element.tag.startswith("{") else ("", element.tag)
        if namespace in SKIP_NAMESPACES or element.get("contextRef") is None:
            continue
        context = contexts.get(element.get("contextRef"), {})
        unit_ref = element.get("unitRef")
        nil = element.get(XSI_NIL) == "true"
        text = (element.text or "").strip()
        value = None
        if unit_ref is not None and not nil and text:
            try:
                value = float(text)
            except ValueError:
                value = None
        prefix = _prefix_for(namespace, element.nsmap)
        rows.append({
            "fact_id": element.get("id"),
            "prefix": prefix,
            "concept": local,
            "namespace": namespace,
            "context_ref": element.get("contextRef"),
            "period_type": context.get("period_type"),
            "start": context.get("start"),
            "end": context.get("end"),
            "dimensions": context.get("dimensions", ""),
            "unit": units.get(unit_ref) if unit_ref else None,
            "decimals": element.get("decimals"),
            "is_numeric": unit_ref is not None,
            "nil": nil,
            "value": value,
            "text": None if unit_ref is not None else text[:500],
        })
    facts = pd.DataFrame(rows)
    key = facts["prefix"] + ":" + facts["concept"] + "|" + facts["context_ref"] + "|" + facts["unit"].fillna("")
    facts["fact_key"] = [hashlib.sha1(k.encode()).hexdigest()[:16] for k in key]
    return facts
