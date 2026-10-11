import asyncio
import json
import time
from typing import Any
import httpx
from ..config import Settings
from ..security import is_loopback_url


class InferenceUnavailable(RuntimeError):
    pass


class LocalLLM:
    """OpenAI-compatible loopback inference. Never forwards traffic to a hosted service."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.llm_base_url.rstrip("/")
        self.model = settings.model_name
        self.config_error = None if is_loopback_url(self.base_url) else "LLM_BASE_URL must be a loopback http(s) URL. Hosted and LAN inference are blocked."
        self.semaphore = asyncio.Semaphore(1)
        self.cached_health: dict[str, Any] | None = None
        self.health_at = 0.0

    def _client(self):
        if self.config_error:
            raise InferenceUnavailable(self.config_error)
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"} if self.settings.llm_api_key else {}
        return httpx.AsyncClient(base_url=self.base_url + "/", headers=headers, timeout=self.settings.llm_timeout, follow_redirects=False, trust_env=False)

    async def health_check(self, force=False):
        if self.cached_health and not force and time.monotonic() - self.health_at < 8:
            return self.cached_health
        result = {"available": False, "model": self.model, "base_url": self.base_url, "local_only": True, "error": None}
        try:
            async with self._client() as client:
                response = await client.get("models", timeout=3)
                response.raise_for_status()
                models = [m["id"] for m in response.json().get("data", [])]
                if self.model not in models:
                    raise InferenceUnavailable(f"Configured model '{self.model}' is not installed. Local models: {', '.join(models) or 'none'}")
                if "nemotron" not in self.model.lower():
                    raise InferenceUnavailable("Select an installed Nemotron model for the LocalOps demo.")
                if "cloud" in self.model.lower():
                    raise InferenceUnavailable("Cloud-backed model identifiers are blocked. Select the installed local Nemotron weights.")
                result.update(available=True, installed_models=models)
        except (httpx.HTTPError, ValueError, KeyError, InferenceUnavailable) as exc:
            result["error"] = str(exc) or type(exc).__name__
        self.cached_health, self.health_at = result, time.monotonic()
        return result

    async def chat(self, system: str, prompt: str, max_tokens: int | None = None):
        health = await self.health_check()
        if not health["available"]:
            raise InferenceUnavailable(health["error"] or "Local Nemotron is unavailable.")
        waiting = time.perf_counter()
        try:
            async with self.semaphore:
                started = time.perf_counter()
                inference_wait_ms = (started - waiting) * 1000
                async with self._client() as client:
                    response = await client.post("chat/completions", json={
                        "model": self.model,
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                        "temperature": 0.15,
                        "max_tokens": max_tokens or self.settings.max_tokens,
                        "reasoning_effort": "none",
                        "stream": False,
                    })
                    response.raise_for_status()
                    payload = response.json()
            answer = payload["choices"][0]["message"].get("content", "")
            if not answer or not answer.strip():
                raise InferenceUnavailable("Nemotron returned no visible answer. Increase LLM_MAX_TOKENS or use a model with reasoning disabled.")
            return {"answer": answer.strip(), "model": payload.get("model", self.model), "inference_latency_ms": round((time.perf_counter() - started) * 1000, 2), "inference_wait_ms": round(inference_wait_ms, 2), "usage": payload.get("usage", {}), "source": "local_nemotron", "base_url": self.base_url, "finish_reason": payload["choices"][0].get("finish_reason")}
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            raise InferenceUnavailable(f"Local inference request failed: {exc}") from exc

    async def structured_output(self, system: str, prompt: str):
        result = await self.chat(system + " Return a single valid JSON object and no Markdown.", prompt)
        text = result["answer"].strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            result["structured"] = json.loads(text)
        except json.JSONDecodeError as exc:
            error = InferenceUnavailable("The model response was not valid JSON; it was not executed.")
            error.response = result
            raise error from exc
        return result
