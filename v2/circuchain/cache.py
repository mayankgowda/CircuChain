"""Content-addressed completion cache + resumability (build step 10).

Key = sha256(model_key | provenance tuple | system | user | genparams). LM Studio exposes no
weight digest, so the provenance tuple (publisher, arch, quant, engine, loaded ctx) stands in
for weight_sha — re-loading a different quant/engine correctly invalidates the cache.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from typing import Optional

from .schema import Completion


def cache_key(model_key: str, provenance: dict, system: str, user: str, gp) -> str:
    prov = "|".join(str(provenance.get(k)) for k in
                    ("backend", "model_id", "weight_sha", "engine", "quant", "arch",
                     "loaded_context_length"))
    h = hashlib.sha256()
    for part in (model_key, prov, system, user, json.dumps(asdict(gp), sort_keys=True)):
        h.update(str(part).encode())
        h.update(b"\x00")
    return h.hexdigest()


class CompletionCache:
    def __init__(self, root: str):
        self.root = root

    def _path(self, model_key: str, key: str) -> str:
        return os.path.join(self.root, model_key, f"{key}.json")

    def get(self, model_key: str, key: str) -> Optional[Completion]:
        p = self._path(model_key, key)
        if not os.path.exists(p):
            return None
        d = json.load(open(p))
        return Completion(**{k: d[k] for k in
                             ("text", "think", "raw", "usage", "provenance", "truncated")})

    def put(self, model_key: str, key: str, comp: Completion) -> None:
        p = self._path(model_key, key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"text": comp.text, "think": comp.think, "raw": comp.raw,
                       "usage": comp.usage, "provenance": comp.provenance,
                       "truncated": comp.truncated}, f)
        os.replace(tmp, p)
