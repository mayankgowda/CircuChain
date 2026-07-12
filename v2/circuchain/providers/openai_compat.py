"""Generic OpenAI-compatible serverless provider (Together / Fireworks / DeepInfra /
OpenRouter / Alibaba / any /v1/chat/completions endpoint).

Used to burst the slow reasoning columns off the M5 to a rented endpoint. Contract-integrity
rule (enforced by the operator, not the code): a whole causal contrast must run on ONE backend,
because API precision differs from the local MLX-8bit weights — so the provenance sidecar records
(provider, base_url, model_id) and the paper marks which columns are API vs local.

The API key is read from an ENV VAR named by cfg['api_key_env']; it is never written to config,
logs, provenance, or the cache. If the var is unset the provider fails fast with the var name.
"""
from __future__ import annotations

import os
import re

import httpx

from .base import Provider, GenParams
from ..schema import Completion

_THINK = re.compile(r"<think>(.*?)</think>\s*", re.S | re.I)


class OpenAICompatProvider(Provider):
    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.base_url = cfg["base_url"].rstrip("/")
        self.provider = cfg.get("provider", "openai_compat")
        env = cfg.get("api_key_env", "OPENAI_API_KEY")
        self.api_key = os.environ.get(env)
        if not self.api_key:
            raise RuntimeError(
                f"API key env var {env!r} is not set. Export it in your shell "
                f"(e.g. `export {env}=...`) — it is never stored in config or the repo.")
        self.think_style = cfg.get("think_style", "none")
        self.extra_body = cfg.get("extra_body", {}) or {}

    async def generate(self, system: str, user: str, params: GenParams) -> Completion:
        if self.think_style == "qwen_slash" and params.think is not None:
            user = f"{user}\n\n{'/think' if params.think else '/no_think'}"

        payload = {
            "model": self.model_id,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": params.temperature,
            "max_tokens": params.max_tokens,
            "stream": False,
        }
        if params.top_p is not None:
            payload["top_p"] = params.top_p
        if params.top_k is not None:
            payload["top_k"] = params.top_k
        if params.stop:
            payload["stop"] = params.stop
        payload.update(self.extra_body)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        # generous read timeout for long reasoning tails; retries live in the runner
        timeout = httpx.Timeout(connect=15, read=300 + params.max_tokens / 5, write=60, pool=60)
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            if r.status_code == 429:
                retry_after = r.headers.get("retry-after", "?")
                raise RuntimeError(f"{self.provider} 429 rate-limited (retry-after={retry_after})")
            if r.status_code >= 400:
                raise RuntimeError(f"{self.provider} HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()

        if "error" in data:
            raise RuntimeError(f"{self.provider} error for {self.model_id}: {data['error']}")

        choice = data["choices"][0]
        msg = choice.get("message", {}) or {}
        content = msg.get("content") or ""
        think = msg.get("reasoning_content") or msg.get("reasoning") or ""
        if not think:
            m = _THINK.search(content)
            if m:
                think = m.group(1)
                content = _THINK.sub("", content, count=1)
        return Completion(
            text=content.strip(),
            think=think.strip(),
            raw=r.text,
            usage=data.get("usage", {}),
            provenance=self.fingerprint(),
            truncated=choice.get("finish_reason") == "length",
        )

    def fingerprint(self) -> dict:
        # NB: no api_key here — provenance is public-safe.
        return {
            "backend": "openai_compat",
            "provider": self.provider,
            "base_url": self.base_url,
            "model_id": self.model_id,
            "engine": "api",
            "quant": self.cfg.get("api_quant", "provider-default"),
            "weight_sha": None,
        }
