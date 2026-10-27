"""Inject realistic errors into an XBRL instance document.

Errors are written into the instance XML itself, so every control (official DQC rules,
generic rules, statistical checks, AI-written rules) is evaluated on exactly the same
modified filing. Each operator mirrors a correction type observed in real SEC amendments
(see results/p1_corrections), and every change is logged with the original value.

Eligible facts: numeric, not nil, non-zero, us-gaap element, no dimensions, unit USD or shares.
"""
from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from lxml import etree

from dqstress.sec.xbrl_instance import XBRLI, XSI_NIL

US_GAAP_PREFIX = "us-gaap"
OPERATORS = ["sign_flip", "scale_x1000", "changed_amount", "one_digit", "retag", "period_swap", "drop_fact"]
LEVEL_OF = {"sign_flip": "L2", "scale_x1000": "L3", "changed_amount": "L4/L6", "one_digit": "L4/L6",
            "retag": "L5", "period_swap": "L7", "drop_fact": "L1"}


@dataclass
class Injection:
    operator: str
    level: str
    changes: list[dict] = field(default_factory=list)


def _format_like(original: str, value: float) -> str:
    if "." in original:
        decimals = len(original.split(".")[1])
        return f"{value:.{decimals}f}"
    return str(int(round(value)))


def _eligible(root) -> list:
    contexts_with_dims = {ctx.get("id") for ctx in root.iter(f"{{{XBRLI}}}context")
                          if ctx.find(f".//{{{XBRLI}}}segment") is not None or ctx.find(f".//{{{XBRLI}}}scenario") is not None}
    units = {}
    for unit in root.iter(f"{{{XBRLI}}}unit"):
        measures = [m.text.split(":")[-1] for m in unit.findall(f"{{{XBRLI}}}measure")]
        units[unit.get("id")] = "*".join(measures)
    eligible = []
    for element in root:
        if not isinstance(element.tag, str) or element.get("contextRef") is None or element.get("unitRef") is None:
            continue
        if element.prefix != US_GAAP_PREFIX or element.get("contextRef") in contexts_with_dims:
            continue
        if element.get(XSI_NIL) == "true" or units.get(element.get("unitRef")) not in {"USD", "shares"}:
            continue
        try:
            value = float(element.text)
        except (TypeError, ValueError):
            continue
        if value != 0:
            eligible.append(element)
    return eligible


def _record(element, operator, old_value, new_value, new_concept=None):
    return {"concept": f"{element.prefix}:{etree.QName(element).localname}", "context_ref": element.get("contextRef"),
            "fact_id": element.get("id"), "operator": operator, "old_value": old_value, "new_value": new_value,
            "new_concept": new_concept}


def inject(instance: Path, operator: str, n_facts: int, rng: random.Random, target: Path,
           concept_weights: dict[str, float] | None = None, amount_ratios: list[float] | None = None,
           retag_pairs: list[tuple[str, str, float]] | None = None) -> Injection | None:
    """Apply one operator to `n_facts` facts and write the modified instance to `target`.

    concept_weights: optional calibrated placement (relative weight per element name); uniform otherwise.
    amount_ratios: empirical new/old ratios for 'changed_amount' (bootstrapped).
    retag_pairs: (wrong_element, right_element, weight) observed in corrections; injection writes the
                 wrong element where the right one was reported.
    Returns None when the filing has no eligible fact for this operator.
    """
    tree = etree.parse(str(instance), etree.XMLParser(huge_tree=True, remove_comments=True))
    root = tree.getroot()
    eligible = _eligible(root)
    by_concept: dict[str, list] = {}
    for element in eligible:
        by_concept.setdefault(etree.QName(element).localname, []).append(element)
    injection = Injection(operator, LEVEL_OF[operator])

    if operator == "retag":
        pairs = [(wrong, right, w) for wrong, right, w in (retag_pairs or []) if right in by_concept and wrong not in by_concept]
        if not pairs:
            return None
        chosen = rng.choices(pairs, weights=[w for _, _, w in pairs], k=1)[0]
        namespace = etree.QName(by_concept[chosen[1]][0]).namespace
        for element in by_concept[chosen[1]][:n_facts]:
            old_tag = element.tag
            element.tag = f"{{{namespace}}}{chosen[0]}"
            injection.changes.append(_record(element, operator, element.text, element.text, f"{US_GAAP_PREFIX}:{chosen[0]}")
                                     | {"concept": f"{US_GAAP_PREFIX}:{etree.QName(old_tag).localname}"})
    elif operator == "period_swap":
        # Swap current and prior-period values of the same element (same unit, same period type).
        contexts = {ctx.get("id"): ctx for ctx in root.iter(f"{{{XBRLI}}}context")}
        def period_key(element):
            period = contexts[element.get("contextRef")].find(f"{{{XBRLI}}}period")
            return period.findtext(f"{{{XBRLI}}}instant") or period.findtext(f"{{{XBRLI}}}endDate")
        candidates = []
        for concept, elements in by_concept.items():
            dated = sorted(((period_key(e), e) for e in elements), key=lambda pair: pair[0] or "")
            distinct = {d for d, _ in dated}
            if len(distinct) >= 2 and dated[-1][1].text != dated[-2][1].text:
                candidates.append((concept, dated[-1][1], dated[-2][1]))
        if not candidates:
            return None
        weights = [concept_weights.get(c, 1e-3) if concept_weights else 1.0 for c, _, _ in candidates]
        for concept, current, prior in _weighted_sample(candidates, weights, n_facts, rng):
            injection.changes.append(_record(current, operator, current.text, prior.text))
            injection.changes.append(_record(prior, operator, prior.text, current.text))
            current.text, prior.text = prior.text, current.text
    else:
        if not eligible:
            return None
        weights = [concept_weights.get(etree.QName(e).localname, 1e-3) if concept_weights else 1.0 for e in eligible]
        for element in _weighted_sample(eligible, weights, n_facts, rng):
            old_text = element.text
            old = float(old_text)
            if operator == "sign_flip":
                element.text = _format_like(old_text, -old)
            elif operator == "scale_x1000":
                element.text = _format_like(old_text, old * 1000)
            elif operator == "changed_amount":
                ratio = rng.choice(amount_ratios) if amount_ratios else 10 ** rng.uniform(-0.5, 0.5)
                element.text = _format_like(old_text, old * ratio)
            elif operator == "one_digit":
                digits = list(str(int(abs(old))))
                position = rng.randrange(len(digits))
                digits[position] = rng.choice([d for d in "0123456789" if d != digits[position]] if position else "123456789".replace(digits[0], ""))
                element.text = _format_like(old_text, float("".join(digits)) * (1 if old > 0 else -1))
            elif operator == "drop_fact":
                injection.changes.append(_record(element, operator, old_text, None))
                element.getparent().remove(element)
                continue
            injection.changes.append(_record(element, operator, old_text, element.text))
    if not injection.changes:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(target), xml_declaration=True, encoding="utf-8")
    return injection


def _weighted_sample(items: list, weights: list[float], k: int, rng: random.Random) -> list:
    items, weights = list(items), np.asarray(weights, dtype=float)
    chosen = []
    for _ in range(min(k, len(items))):
        probabilities = weights / weights.sum()
        index = int(rng.choices(range(len(items)), weights=probabilities, k=1)[0])
        chosen.append(items.pop(index))
        weights = np.delete(weights, index)
    return chosen
