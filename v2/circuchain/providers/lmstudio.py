"""LM Studio adapter — the primary local-inference path (OpenAI-compatible server on :1234).

LM Studio serves two APIs; we use both:
  * POST /v1/chat/completions   OpenAI-compatible generation
  * GET  /api/v0/models         native REST, richer metadata:
        {id, type: llm|vlm|embeddings, publisher, arch, compatibility_type: gguf|mlx,
         quantization, state: loaded|not-loaded, max_context_length, loaded_context_length}

Two operational facts learned from the live API, both encoded here:

1. CONTEXT-LENGTH TRAP. LM Studio's JIT loader defaults to the model's *full* max_context_length
   (often 262144), so it reserves an enormous KV cache and refuses to load
   ("requires approximately 86.30 GB of memory"). Models MUST be loaded with a constrained
   context. This provider therefore FAILS FAST with the exact `lms load` command instead of
   letting a multi-day sweep die on an OOM at hour 40.

2. NO WEIGHT HASH. Unlike Ollama, LM Studio exposes no digest. The provenance tuple is
   (publisher, arch, quantization, compatibility_type, loaded_context_length) — recorded in the
   sidecar. compatibility_type doubles as the ENGINE tag (gguf vs mlx), which is exactly what the
   cross-engine reproducibility receipt needs: the same model family run under both runtimes.
"""
from __future__ import annotations

import re

import httpx

from .base import Provider, GenParams
from ..schema import Completion

_THINK = re.compile(r"<think>(.*?)</think>\s*", re.S | re.I)
_DEFAULT_HOST = "http://localhost:1234"


class LMStudioNotLoaded(RuntimeError):
    pass


class LMStudioProvider(Provider):
    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.host = cfg.get("host", _DEFAULT_HOST)
        # how to toggle a reasoning trace for this model family:
        #   "qwen_slash" -> append /think or /no_think to the user turn (Qwen3.x soft switch)
        #   "none"       -> model has no runtime toggle
        self.think_style = cfg.get("think_style", "none")
        self.require_loaded = cfg.get("require_loaded", True)

    # ---------- generation ----------
    async def generate(self, system: str, user: str, params: GenParams) -> Completion:
        if self.require_loaded:
            self.assert_loaded(params.num_ctx)

        if self.think_style == "qwen_slash" and params.think is not None:
            user = f"{user}\n\n{'/think' if params.think else '/no_think'}"

        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": params.temperature,   # 0.0 -> greedy
            "max_tokens": params.max_tokens,
            "stream": False,
        }
        if params.seed is not None:
            payload["seed"] = params.seed        # honored by the llama.cpp runtime; MLX may ignore
        if params.stop:
            payload["stop"] = params.stop

        async with httpx.AsyncClient(timeout=None) as c:
            r = await c.post(f"{self.host}/v1/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()

        if "error" in data:
            raise RuntimeError(f"LM Studio error for {self.model_id}: {data['error']}")

        choice = data["choices"][0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        # Newer LM Studio surfaces a parsed reasoning channel; older models embed <think>...</think>
        think = msg.get("reasoning_content") or ""
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

    # ---------- introspection ----------
    def _model_info(self) -> dict:
        try:
            for m in httpx.get(f"{self.host}/api/v0/models", timeout=10).json().get("data", []):
                if m["id"] == self.model_id:
                    return m
        except Exception:  # noqa: BLE001
            pass
        return {}

    def assert_loaded(self, want_ctx: int) -> None:
        """Fail fast (with the fix) rather than letting JIT reserve a 262k-token KV cache."""
        info = self._model_info()
        if not info:
            raise LMStudioNotLoaded(
                f"Model {self.model_id!r} not found on the LM Studio server at {self.host}.\n"
                f"  Start it:  lms server start\n"
                f"  List:      lms ls"
            )
        if info.get("state") != "loaded":
            raise LMStudioNotLoaded(
                f"Model {self.model_id!r} is not loaded. Do NOT rely on JIT loading: it defaults to "
                f"max_context_length={info.get('max_context_length')} and will try to reserve a huge "
                f"KV cache. Load it with a constrained context first:\n\n"
                f"    lms load {self.model_id} --context-length {want_ctx} --gpu max -y\n"
            )

    def fingerprint(self) -> dict:
        info = self._model_info()
        return {
            "backend": "lmstudio",
            "model_id": self.model_id,
            "engine": info.get("compatibility_type"),   # gguf | mlx -> the cross-engine receipt
            "quant": info.get("quantization"),
            "arch": info.get("arch"),
            "publisher": info.get("publisher"),
            "loaded_context_length": info.get("loaded_context_length"),
            "weight_sha": None,                          # LM Studio exposes no digest
        }

    @staticmethod
    def list_installed(host: str = _DEFAULT_HOST) -> list:
        """Enumerate downloaded text models (llm + vlm), skipping embedding models."""
        data = httpx.get(f"{host}/api/v0/models", timeout=10).json().get("data", [])
        out = []
        for m in data:
            if m.get("type") not in ("llm", "vlm"):
                continue
            if "embed" in m["id"].lower():
                continue
            out.append({
                "name": m["id"],
                "arch": m.get("arch"),
                "engine": m.get("compatibility_type"),
                "quant": m.get("quantization"),
                "state": m.get("state"),
                "max_context_length": m.get("max_context_length"),
                "vision": m.get("type") == "vlm",
            })
        return out
