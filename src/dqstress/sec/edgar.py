"""Polite access to SEC EDGAR archives.

The SEC asks automated clients to declare a contact in the User-Agent and to stay
below 10 requests per second. The contact is read from the SEC_USER_AGENT
environment variable so that no personal address is stored in the repository.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import requests
from lxml import html

ARCHIVE = "https://www.sec.gov/Archives/edgar/data"
MIN_INTERVAL_SECONDS = 0.5
_last_request = 0.0


def user_agent() -> str:
    agent = os.environ.get("SEC_USER_AGENT", "")
    if "@" not in agent:
        raise RuntimeError("Set SEC_USER_AGENT to 'project-name contact@example.org' before calling EDGAR")
    return agent


def filing_folder(cik: int | str, adsh: str) -> str:
    return f"{ARCHIVE}/{int(cik)}/{adsh.replace('-', '')}"


def primary_document_from_instance(instance: str) -> str | None:
    """Inline XBRL filings list the extracted instance as '<doc>_htm.xml'; the primary document is '<doc>.htm'."""
    if instance.endswith("_htm.xml"):
        return instance[: -len("_htm.xml")] + ".htm"
    return None


def get(url: str, stream: bool = False, timeout: int = 120) -> requests.Response:
    global _last_request
    wait = MIN_INTERVAL_SECONDS - (time.time() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.time()
    response = requests.get(url, headers={"User-Agent": user_agent()}, stream=stream, timeout=timeout)
    response.raise_for_status()
    return response


def download(url: str, target: Path) -> Path:
    if target.exists() and target.stat().st_size > 0:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    response = get(url, stream=True)
    tmp = target.with_suffix(target.suffix + ".part")
    with open(tmp, "wb") as handle:
        for block in response.iter_content(1 << 16):
            handle.write(block)
    tmp.rename(target)
    return target


NOTE_START = re.compile(r"explanatory\s+note|purpose\s+of\s+this\s+amendment", re.IGNORECASE)


def explanatory_note(url: str, max_bytes: int = 12_000_000, excerpt_chars: int = 4000) -> str | None:
    """Stream a primary document and return the text that follows its 'Explanatory Note'.

    Inline XBRL documents start with a large hidden header, so the note can sit
    several megabytes into the file; streaming stops as soon as the note is found.
    """
    response = get(url, stream=True)
    buffer = b""
    for block in response.iter_content(1 << 18):
        buffer += block
        text = _visible_text(buffer)
        match = NOTE_START.search(text)
        if match and len(text) - match.start() > excerpt_chars:
            response.close()
            return text[match.start(): match.start() + excerpt_chars]
        if len(buffer) > max_bytes:
            break
    response.close()
    text = _visible_text(buffer)
    match = NOTE_START.search(text)
    return text[match.start(): match.start() + excerpt_chars] if match else None


def _visible_text(raw: bytes) -> str:
    try:
        tree = html.fromstring(raw)
    except Exception:  # partial documents can fail to parse at the very start
        return ""
    for hidden in tree.xpath("//*[local-name()='header' or contains(@style,'display:none')]"):
        hidden.drop_tree()
    return re.sub(r"\s+", " ", tree.text_content())
