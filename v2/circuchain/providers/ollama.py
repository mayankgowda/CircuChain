"""Ollama adapter — the primary local-inference path on the M5 (localhost:11434).

Handles both the first-class `thinking` channel (newer Ollama) and inline <think>...</think>
blocks (older reasoning models). temperature=0 + seed for determinism. list_installed() backs
the `circuchain models --installed` gap check so a multi-day run never dies on a missing weight.
"""
from __future__ import annotations

import re

import httpx

from .base import Provider, GenParams
from ..schema import Completion

_THINK = re.compile(r"<think>(.*?)</think>\s*", re.S | re.I)
_DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider(Provider):
    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.host = cfg.get("host", _DEFAULT_HOST)

    async def generate(self, system: str, user: str, params: GenParams) -> Completion:
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,                      # one-shot; simpler and deterministic to log
            "options": {                          # temp/seed live under options in Ollama
                "temperature": params.temperature,
                "seed": params.seed,
                "num_predict": params.max_tokens,
                "num_ctx": params.num_ctx,
                "stop": params.stop,
            },
        }
        if params.think is not None:              # first-class thinking channel where supported
            payload["think"] = params.think

        async with httpx.AsyncClient(timeout=None) as c:
            r = await c.post(f"{self.host}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        msg = data.get("message", {})
        content, think = msg.get("content", ""), msg.get("thinking", "")
        if not think:                             # fall back to inline <think> extraction
            m = _THINK.search(content)
            if m:
                think = m.group(1)
                content = _THINK.sub("", content, count=1)

        eval_count = data.get("eval_count")
        truncated = bool(eval_count and eval_count >= params.max_tokens)
        return Completion(
            text=content.strip(),
            think=think.strip(),
            raw=r.text,
            usage={"prompt": data.get("prompt_eval_count"), "eval": eval_count},
            provenance=self.fingerprint(),
            truncated=truncated,
        )

    def fingerprint(self) -> dict:
        try:
            info = httpx.post(f"{self.host}/api/show", json={"model": self.model_id}).json()
        except Exception:
            info = {}
        details = info.get("details", {})
        return {
            "backend": "ollama",
            "model_id": self.model_id,
            "weight_sha": info.get("digest") or details.get("parent_model") or "unknown",
            "quant": details.get("quantization_level"),
            "family": details.get("family"),
        }

    @staticmethod
    def list_installed(host: str = _DEFAULT_HOST) -> list:
        """Enumerate what the author actually has pulled (GET /api/tags)."""
        tags = httpx.get(f"{host}/api/tags").json().get("models", [])
        out = []
        for m in tags:
            d = m.get("details", {})
            out.append({
                "name": m["name"], "size": m.get("size"),
                "quant": d.get("quantization_level"), "family": d.get("family"),
                "digest": m.get("digest"),
            })
        return out
