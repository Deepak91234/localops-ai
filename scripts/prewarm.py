#!/usr/bin/env python3
"""Run a real, bounded loopback Nemotron request before the presentation."""
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
KEYS = {"LLM_BASE_URL", "MODEL_NAME", "LLM_API_KEY", "LLM_TIMEOUT_SECONDS", "LLM_MAX_TOKENS", "LOCALOPS_DB_PATH"}


def load_local_env():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or key not in KEYS:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


def main():
    load_local_env()
    base_url = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
    model = os.getenv("MODEL_NAME", "nemotron3:33b")
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
        raise ValueError("LLM_BASE_URL must be an http(s) loopback URL without embedded credentials.")
    if "nemotron" not in model.lower() or "cloud" in model.lower():
        raise ValueError("Use an installed local Nemotron model; cloud model names are refused.")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Answer briefly in one sentence."},
            {"role": "user", "content": "This is a fictional LocalOps health test. A policy grants 20 PTO days each year. How many PTO days does it grant?"},
        ],
        "temperature": 0,
        "max_tokens": 128,
        "reasoning_effort": "none",
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    key = os.getenv("LLM_API_KEY", "")
    if key:
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(base_url + "/chat/completions", data=json.dumps(body).encode(), headers=headers)
    # Explicitly ignore proxy environment variables so loopback requests stay direct.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    started = time.perf_counter()
    with opener.open(request, timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "180"))) as response:
        payload = json.load(response)
        status = response.status
    answer = payload["choices"][0]["message"].get("content", "").strip()
    if not answer:
        raise ValueError("The local model returned no visible answer.")
    print(json.dumps({
        "endpoint": base_url + "/chat/completions",
        "model": payload.get("model", model),
        "status": status,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "answer": answer,
        "usage": payload.get("usage", {}),
        "local_only": True,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print(f"Prewarm failed: local endpoint returned HTTP {exc.code}.", file=sys.stderr)
        raise SystemExit(1)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(f"Prewarm failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
