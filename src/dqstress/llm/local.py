"""Local GGUF models through llama.cpp, with every call logged for the evidence trail."""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from llama_cpp import Llama

MODELS = {
    "qwen2.5-coder-7b": {"file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf", "released": "2024-11-12",
                         "repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF"},
    "qwen3-8b": {"file": "Qwen3-8B-Q4_K_M.gguf", "released": "2025-04-29", "repo": "Qwen/Qwen3-8B-GGUF",
                 "no_think": True},
    "granite-3.3-8b": {"file": "granite-3.3-8b-instruct-Q4_K_M.gguf", "released": "2025-04-16",
                       "repo": "ibm-granite/granite-3.3-8b-instruct-GGUF"},
}


@dataclass
class Completion:
    text: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float


class LocalModel:
    def __init__(self, name: str, model_dir: Path, n_ctx: int = 12288, threads: int = 4):
        self.name = name
        self.spec = MODELS[name]
        self.path = Path(model_dir) / self.spec["file"]
        self.llm = Llama(model_path=str(self.path), n_ctx=n_ctx, n_threads=threads, seed=0, verbose=False)

    def complete(self, system: str, user: str, temperature: float = 0.0, seed: int = 0,
                 max_tokens: int = 1200) -> Completion:
        if self.spec.get("no_think"):
            user = user + "\n/no_think"
        start = time.time()
        out = self.llm.create_chat_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature, seed=seed, max_tokens=max_tokens)
        text = out["choices"][0]["message"]["content"] or ""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        usage = out["usage"]
        return Completion(text, usage["prompt_tokens"], usage["completion_tokens"], time.time() - start)


def extract_code(text: str) -> str | None:
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, flags=re.DOTALL)
    if blocks:
        return max(blocks, key=len).strip()
    return text.strip() if "def check" in text else None


def log_call(log_path: Path, record: dict) -> None:
    record = dict(record)
    record["prompt_sha256"] = hashlib.sha256((record.get("system", "") + record.get("user", "")).encode()).hexdigest()
    with open(log_path, "a") as handle:
        handle.write(json.dumps(record) + "\n")
