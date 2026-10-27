"""Measure prompt-processing and generation speed of a local GGUF model on this machine."""
import json
import sys
import time

from llama_cpp import Llama

model_path = sys.argv[1]
threads = int(sys.argv[2]) if len(sys.argv) > 2 else 4
llm = Llama(model_path=model_path, n_ctx=8192, n_threads=threads, seed=0, verbose=False)
prompt = ("You are a data engineer. Write a Python function check(facts) that returns the rows of a pandas "
          "DataFrame `facts` (columns: concept, period_end, duration_quarters, unit, dimensions, value) where "
          "Assets does not equal LiabilitiesAndStockholdersEquity for the same period. " * 6)
start = time.time()
out = llm.create_chat_completion(messages=[{"role": "user", "content": prompt}], max_tokens=256, temperature=0)
elapsed = time.time() - start
usage = out["usage"]
print(json.dumps({"model": model_path.split("/")[-1], "threads": threads, "prompt_tokens": usage["prompt_tokens"],
                  "completion_tokens": usage["completion_tokens"], "seconds": round(elapsed, 1)}))
