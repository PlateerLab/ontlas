"""Embedding port: text in, vectors out, from whichever model a space is given.

An embedder is swapped the way a graph store is. `hash` needs nothing and matches wording, not meaning, and says so through
`semantic`; `openai` is any service with the /v1/embeddings shape; `fastembed` runs a small multilingual model on the CPU.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import urllib.error
import urllib.request
import zlib
from collections import OrderedDict
from typing import Any, Callable

CACHE_MAX = 20_000
_WORD = re.compile(r"[0-9a-zA-Z가-힣]+")


class EmbedError(RuntimeError):
    """The model could not be reached or answered with something that is not vectors."""


class Embedder:
    kind = ""
    name = ""
    dim = 0
    semantic = True  # False: it compares wording, so a search should not be read as understanding

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def describe(self) -> dict:
        return {"kind": self.kind, "name": self.name, "dim": self.dim, "semantic": self.semantic}


def _unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


class HashEmbedder(Embedder):
    """Words and character pieces hashed into a fixed vector. Works anywhere and repeats exactly, so tests and a first look
    need no model. Two sentences that mean the same in other words score low: that is what `semantic = False` warns of."""

    kind = "hash"
    semantic = False

    def __init__(self, dim: int = 512):
        if dim < 16:
            raise ValueError("hash embedder needs at least 16 dimensions")
        self.dim = dim
        self.name = f"hash-{dim}"

    def _vector(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for word in _WORD.findall(text.lower()):
            pieces = [word] + [word[i:i + n] for n in (2, 3) for i in range(max(len(word) - n + 1, 0))]
            for p in pieces:
                h = zlib.crc32(p.encode("utf-8"))
                v[h % self.dim] += 1.0 if (h >> 16) & 1 else -1.0
        return _unit(v)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


class OpenAIEmbedder(Embedder):
    """Any service that answers POST {url}/embeddings the OpenAI way: a hosted API, vLLM, a gateway."""

    kind = "openai"

    def __init__(self, url: str, model: str, *, key: str = "", key_env: str = "", dim: int = 0, batch: int = 32,
                 timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.name = model
        self.key = key or (os.environ.get(key_env, "") if key_env else "")
        self.dim = dim
        self.batch = batch
        self.timeout = timeout

    def _post(self, texts: list[str]) -> list[list[float]]:
        req = urllib.request.Request(self.url + "/embeddings", method="POST",
                                     data=json.dumps({"model": self.name, "input": texts}).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        if self.key:
            req.add_header("Authorization", "Bearer " + self.key)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise EmbedError(f"embedding service answered {e.code}") from None
        except (OSError, ValueError):
            raise EmbedError("embedding service did not answer") from None
        rows = sorted(body.get("data") or [], key=lambda x: x.get("index", 0))
        if len(rows) != len(texts):
            raise EmbedError(f"embedding service returned {len(rows)} vectors for {len(texts)} texts")
        return [r["embedding"] for r in rows]

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            out += self._post(texts[i:i + self.batch])
        if out and not self.dim:
            self.dim = len(out[0])
        return [_unit(v) for v in out]


class FastEmbedder(Embedder):
    """A small model run on the CPU through ONNX. Downloaded once, then local: no key, no service."""

    kind = "fastembed"
    DEFAULT = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model: str = DEFAULT, *, cache_dir: str = ""):
        try:
            from fastembed import TextEmbedding
        except ImportError as e:
            raise ImportError("the fastembed embedder needs the [embed] extra") from e
        self.name = model
        self.model = TextEmbedding(model_name=model, cache_dir=cache_dir or None)
        self.dim = len(next(iter(self.model.embed(["."]))))
        self.lock = threading.Lock()  # one ONNX session, shared by every visitor

    def embed(self, texts: list[str]) -> list[list[float]]:
        with self.lock:
            return [_unit([float(x) for x in v]) for v in self.model.embed(texts)]


class CachedEmbedder(Embedder):
    """The same text is embedded once, however many spaces hold it."""

    def __init__(self, inner: Embedder, limit: int = CACHE_MAX):
        self.inner, self.limit = inner, limit
        self.kind, self.name, self.semantic = inner.kind, inner.name, inner.semantic
        self.seen: OrderedDict[str, list[float]] = OrderedDict()
        self.lock = threading.Lock()

    @property
    def dim(self) -> int:
        return self.inner.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        keys = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts]
        with self.lock:
            missing = {k: t for k, t in zip(keys, texts) if k not in self.seen}
        if missing:
            made = self.inner.embed(list(missing.values()))
            with self.lock:
                self.seen.update(zip(missing, made))
                while len(self.seen) > self.limit:
                    self.seen.popitem(last=False)
        with self.lock:
            hit = {k: self.seen.get(k) for k in keys}
        if any(v is None for v in hit.values()):  # pushed out by a bigger batch
            return self.inner.embed(texts)
        return [hit[k] for k in keys]


_KINDS: dict[str, Callable[[dict], Embedder]] = {}
_OPEN: dict[str, Embedder] = {}
_LOCK = threading.Lock()


def register_embedder(kind: str, make: Callable[[dict], Embedder]) -> None:
    """A model the package does not know joins by name: `embedder: {kind: <yours>, ...}` in a studio file."""
    _KINDS[kind] = make


def _opt(spec: dict, *names: str) -> dict[str, Any]:
    return {k: spec[k] for k in names if k in spec}


register_embedder("hash", lambda s: HashEmbedder(int(s.get("dim", 512))))
register_embedder("openai", lambda s: OpenAIEmbedder(s["url"], s["model"], **_opt(s, "key", "key_env", "dim", "batch", "timeout")))
register_embedder("fastembed", lambda s: FastEmbedder(s.get("model", FastEmbedder.DEFAULT), **_opt(s, "cache_dir")))


def open_embedder(spec: dict | None) -> Embedder:
    """One per spec for the whole process: a model is loaded once and its cache is shared between visitors' spaces."""
    spec = dict(spec or {"kind": "hash"})
    kind = spec.get("kind", "hash")
    if kind not in _KINDS:
        raise ValueError(f"unknown embedder kind '{kind}'; known: {', '.join(sorted(_KINDS))}")
    key = json.dumps(spec, sort_keys=True, default=str)
    with _LOCK:
        if key not in _OPEN:
            _OPEN[key] = CachedEmbedder(_KINDS[kind](spec))
        return _OPEN[key]
