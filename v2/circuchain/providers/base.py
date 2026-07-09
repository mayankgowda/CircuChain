"""Uniform async provider interface. Widened from v1's BaseModelHandler.generate()."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from ..schema import Completion


@dataclass
class GenParams:
    temperature: float = 0.0
    seed: int = 20260709
    max_tokens: int = 8192            # hard cap on the CoT tail (budget control); log truncation
    num_ctx: int = 8192
    stop: List[str] = field(default_factory=list)
    think: Optional[bool] = None      # request/allow a reasoning channel if the model has one


class Provider(ABC):
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.model_id = cfg["model_id"]
        self.key = cfg.get("key", self.model_id)

    @abstractmethod
    async def generate(self, system: str, user: str, params: GenParams) -> Completion:
        ...

    @abstractmethod
    def fingerprint(self) -> dict:
        """weight_sha / quant / backend / lib versions -> provenance sidecar for reproducibility."""
        ...
