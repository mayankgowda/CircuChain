"""Backend-agnostic model providers. Local-first (Ollama/MLX); API adapters optional."""
from __future__ import annotations


def build_provider(cfg: dict):
    """Factory: cfg['backend'] in {lmstudio, ollama, mlx, openai, anthropic} -> a Provider."""
    backend = cfg.get("backend", "lmstudio")
    if backend == "lmstudio":
        from .lmstudio import LMStudioProvider
        return LMStudioProvider(cfg)
    if backend in ("openai_compat", "api"):
        from .openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(cfg)
    if backend == "ollama":
        from .ollama import OllamaProvider
        return OllamaProvider(cfg)
    if backend == "mlx":
        from .mlx import MLXProvider
        return MLXProvider(cfg)
    if backend == "openai":
        from .openai_api import OpenAIProvider
        return OpenAIProvider(cfg)
    if backend == "anthropic":
        from .anthropic_api import AnthropicProvider
        return AnthropicProvider(cfg)
    raise ValueError(f"unknown backend: {backend}")
