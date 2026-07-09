"""MLX adapter — the 'official numbers' engine on Apple Silicon (in-process, no HTTP).

MLX exploits the M5 Neural Accelerators and gives faster prefill/decode than Ollama for the
prefill-heavy CircuChain prompts. Kept behind the same Provider interface so the paper can
report a cross-engine reproducibility receipt ("headline gaps reproduce on MLX and llama.cpp").

Requires the [mlx] extra:  pip install -e 'v2/[mlx]'   (mlx-lm). Import is lazy so the rest of
the harness runs on any machine without MLX installed.
"""
from __future__ import annotations

import asyncio
import re

from .base import Provider, GenParams
from ..schema import Completion

_THINK = re.compile(r"<think>(.*?)</think>\s*", re.S | re.I)
_CACHE: dict = {}


def _load(repo_id: str):
    if repo_id not in _CACHE:
        from mlx_lm import load  # lazy: only needed when backend == mlx
        _CACHE[repo_id] = load(repo_id)
    return _CACHE[repo_id]


class MLXProvider(Provider):
    def __init__(self, cfg: dict):
        super().__init__(cfg)
        self.repo_id = cfg["model_id"]  # HF repo id, e.g. "mlx-community/Qwen3-14B-4bit"

    async def generate(self, system: str, user: str, params: GenParams) -> Completion:
        return await asyncio.to_thread(self._generate_sync, system, user, params)

    def _generate_sync(self, system: str, user: str, params: GenParams) -> Completion:
        import mlx.core as mx
        from mlx_lm import generate as mlx_generate
        from mlx_lm.sample_utils import make_sampler

        model, tok = _load(self.repo_id)
        mx.random.seed(params.seed)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        prompt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        sampler = make_sampler(temp=params.temperature)  # temp=0 -> greedy/deterministic
        text = mlx_generate(
            model, tok, prompt=prompt, max_tokens=params.max_tokens, sampler=sampler, verbose=False
        )
        think = ""
        m = _THINK.search(text)
        if m:
            think = m.group(1).strip()
            text = _THINK.sub("", text, count=1)
        return Completion(text=text.strip(), think=think, raw=text, provenance=self.fingerprint())

    def fingerprint(self) -> dict:
        quant = None
        for tag in ("4bit", "8bit", "bf16", "mxfp4"):
            if tag in self.repo_id.lower():
                quant = tag
        return {"backend": "mlx", "model_id": self.repo_id, "weight_sha": self.repo_id, "quant": quant}
